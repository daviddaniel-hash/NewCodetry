"""
insights.py — Smart Insight Generator

Analyses profiler output and generates plain-English insights ranked by
importance / severity.
"""

import math
from typing import Any, Dict, List


# Severity levels (higher = more important)
CRITICAL = 4
HIGH = 3
MEDIUM = 2
LOW = 1


def _insight(severity: int, category: str, message: str, detail: str = "") -> Dict[str, Any]:
    labels = {CRITICAL: "🔴 Critical", HIGH: "🟠 High", MEDIUM: "🟡 Medium", LOW: "🔵 Low"}
    return {
        "severity": severity,
        "severity_label": labels.get(severity, "⚪ Info"),
        "category": category,
        "message": message,
        "detail": detail,
    }


# ---------------------------------------------------------------------------
# Individual insight generators
# ---------------------------------------------------------------------------

def _missing_value_insights(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    insights: List[Dict[str, Any]] = []
    cols = profile.get("columns", {})
    for col, stats in cols.items():
        pct = stats.get("missing_pct", 0)
        if pct >= 50:
            insights.append(_insight(
                CRITICAL, "Missing Values",
                f"'{col}' is missing {pct:.1f}% of its values — column may be unusable.",
                f"Only {100 - pct:.1f}% of rows have data."
            ))
        elif pct >= 20:
            insights.append(_insight(
                HIGH, "Missing Values",
                f"'{col}' has a high missing rate: {pct:.1f}%.",
                "Consider imputation or exclusion before modelling."
            ))
        elif pct >= 5:
            insights.append(_insight(
                MEDIUM, "Missing Values",
                f"'{col}' is missing {pct:.1f}% of values.",
                "Minor gaps detected — verify if missingness is random."
            ))
    return insights


def _correlation_insights(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    insights: List[Dict[str, Any]] = []
    corr = profile.get("correlation")
    if not corr:
        return insights
    for pair in corr.get("strong_pairs", []):
        r = pair["r"]
        c1, c2 = pair["col1"], pair["col2"]
        if abs(r) >= 0.95:
            insights.append(_insight(
                CRITICAL, "Correlation",
                f"'{c1}' and '{c2}' are near-perfectly correlated (r = {r:.3f}).",
                "These columns may be duplicates or derived from each other — consider dropping one."
            ))
        elif abs(r) >= 0.85:
            insights.append(_insight(
                HIGH, "Correlation",
                f"'{c1}' and '{c2}' are strongly correlated (r = {r:.3f}).",
                "Multicollinearity may affect regression/ML models."
            ))
        else:
            insights.append(_insight(
                MEDIUM, "Correlation",
                f"'{c1}' and '{c2}' are moderately-strongly correlated (r = {r:.3f}).",
                "Worth noting for feature selection."
            ))
    return insights


def _outlier_insights(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    insights: List[Dict[str, Any]] = []
    for col, out in profile.get("outliers", {}).items():
        pct = out.get("outlier_pct", 0)
        cnt = out.get("outlier_count", 0)
        if pct >= 10:
            insights.append(_insight(
                HIGH, "Outliers",
                f"'{col}' has {cnt} outliers ({pct:.1f}% of non-null values).",
                f"IQR fences: [{out['lower_fence']}, {out['upper_fence']}]. "
                f"Sample: {out['outlier_values'][:5]}"
            ))
        elif pct >= 3:
            insights.append(_insight(
                MEDIUM, "Outliers",
                f"'{col}' has {cnt} outlier(s) ({pct:.1f}%).",
                f"IQR fences: [{out['lower_fence']}, {out['upper_fence']}]."
            ))
        elif cnt > 0:
            insights.append(_insight(
                LOW, "Outliers",
                f"'{col}' has {cnt} mild outlier(s) ({pct:.1f}%).",
                ""
            ))
    return insights


def _skewness_insights(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    insights: List[Dict[str, Any]] = []
    cols = profile.get("columns", {})
    col_types = profile.get("col_types", {})
    for col, stats in cols.items():
        if col_types.get(col) != "numeric":
            continue
        skew = stats.get("skewness")
        if skew is None or math.isnan(skew):
            continue
        if abs(skew) >= 2:
            direction = "right (positive)" if skew > 0 else "left (negative)"
            insights.append(_insight(
                HIGH, "Skewness",
                f"'{col}' is highly skewed {direction} (skewness = {skew:.2f}).",
                "Consider log/sqrt transformation for modelling."
            ))
        elif abs(skew) >= 1:
            direction = "right" if skew > 0 else "left"
            insights.append(_insight(
                MEDIUM, "Skewness",
                f"'{col}' shows moderate {direction} skew (skewness = {skew:.2f}).",
                "Distribution is non-symmetric."
            ))
    return insights


def _low_variance_insights(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    insights: List[Dict[str, Any]] = []
    cols = profile.get("columns", {})
    col_types = profile.get("col_types", {})
    for col, stats in cols.items():
        if col_types.get(col) == "numeric":
            std = stats.get("std", None)
            mean = stats.get("mean", None)
            if std is None or mean is None:
                continue
            if mean != 0:
                cv = abs(std / mean)  # coefficient of variation
                if cv < 0.01:
                    insights.append(_insight(
                        MEDIUM, "Low Variance",
                        f"'{col}' is nearly constant (CV = {cv:.4f}).",
                        "This column contributes little information — consider dropping."
                    ))
        elif col_types.get(col) == "categorical":
            top_freq_pct = stats.get("top_freq_pct", 0) or 0
            if top_freq_pct >= 95:
                top_val = stats.get("top_value", "?")
                insights.append(_insight(
                    MEDIUM, "Low Variance",
                    f"'{col}' is dominated by '{top_val}' ({top_freq_pct:.1f}% of values).",
                    "Near-constant categorical column — limited discriminative power."
                ))
    return insights


def _data_quality_insights(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    insights: List[Dict[str, Any]] = []
    ds = profile.get("dataset", {})

    # Duplicate rows
    dup_pct = ds.get("duplicate_pct", 0)
    dup_cnt = ds.get("duplicate_rows", 0)
    if dup_pct >= 10:
        insights.append(_insight(
            HIGH, "Data Quality",
            f"Dataset has {dup_cnt} duplicate rows ({dup_pct:.1f}% of total).",
            "Duplicates can skew statistics and model training."
        ))
    elif dup_cnt > 0:
        insights.append(_insight(
            LOW, "Data Quality",
            f"{dup_cnt} duplicate row(s) found ({dup_pct:.1f}%).",
            "Consider deduplication."
        ))

    # Very small dataset
    rows = ds.get("row_count", 0)
    if rows < 30:
        insights.append(_insight(
            HIGH, "Data Quality",
            f"Dataset is very small ({rows} rows).",
            "Statistical conclusions may be unreliable with fewer than 30 rows."
        ))
    elif rows < 100:
        insights.append(_insight(
            MEDIUM, "Data Quality",
            f"Dataset has only {rows} rows.",
            "Some statistics may have high variance."
        ))

    return insights


def _column_type_insights(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flag unusual patterns like all-unique categoricals."""
    insights: List[Dict[str, Any]] = []
    cols = profile.get("columns", {})
    col_types = profile.get("col_types", {})
    ds = profile.get("dataset", {})
    n_rows = ds.get("row_count", 1)

    for col, stats in cols.items():
        if col_types.get(col) == "categorical":
            unique = stats.get("unique", 0)
            if unique == n_rows and n_rows > 10:
                insights.append(_insight(
                    LOW, "Column Type",
                    f"'{col}' has all unique values — it may be an ID/key column.",
                    "High-cardinality categoricals are often unsuitable as features."
                ))
    return insights


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_insights(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate all insights from a profiler result dict, ranked by severity."""
    all_insights: List[Dict[str, Any]] = []
    all_insights.extend(_missing_value_insights(profile))
    all_insights.extend(_correlation_insights(profile))
    all_insights.extend(_outlier_insights(profile))
    all_insights.extend(_skewness_insights(profile))
    all_insights.extend(_low_variance_insights(profile))
    all_insights.extend(_data_quality_insights(profile))
    all_insights.extend(_column_type_insights(profile))

    # Sort: highest severity first, then alphabetically by message
    all_insights.sort(key=lambda x: (-x["severity"], x["message"]))
    return all_insights
