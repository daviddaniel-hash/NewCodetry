"""
profiler.py — Smart Data Profiler

Automatically analyses a pandas DataFrame and computes per-column statistics,
dataset-level summaries, correlation matrices, and IQR-based outlier detection.
"""

import math
import warnings
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


# ---------------------------------------------------------------------------
# Column-type detection
# ---------------------------------------------------------------------------

def detect_column_types(df: pd.DataFrame) -> Dict[str, str]:
    """Return a mapping of column name → detected type.

    Possible types: 'numeric', 'categorical', 'datetime', 'boolean', 'text', 'unknown'
    """
    types: Dict[str, str] = {}
    for col in df.columns:
        series = df[col].dropna()
        if series.empty:
            types[col] = "unknown"
            continue

        # Boolean check first (before numeric). Sample to avoid scanning large series.
        _BOOL_SET = {True, False, 0, 1, "True", "False", "true", "false", "yes", "no", "Yes", "No"}
        _sample = series.iloc[:1000] if len(series) > 1000 else series
        if series.dtype == bool or set(_sample.unique()).issubset(_BOOL_SET):
            types[col] = "boolean"
            continue

        # Numeric
        if pd.api.types.is_numeric_dtype(series):
            types[col] = "numeric"
            continue

        # Datetime – try to parse
        if pd.api.types.is_datetime64_any_dtype(series):
            types[col] = "datetime"
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                parsed = pd.to_datetime(series.astype(str).head(50), infer_datetime_format=True, errors="coerce")
            if parsed.notna().mean() > 0.7:
                types[col] = "datetime"
                continue
        except Exception:
            pass

        # Text vs categorical – heuristic: high cardinality relative to row count
        n_unique = series.nunique()
        n_total = len(series)
        avg_len = series.astype(str).str.len().mean()
        if n_unique / max(n_total, 1) > 0.5 and avg_len > 20:
            types[col] = "text"
        else:
            types[col] = "categorical"

    return types


# ---------------------------------------------------------------------------
# Per-column statistics
# ---------------------------------------------------------------------------

def _numeric_stats(series: pd.Series) -> Dict[str, Any]:
    """Compute statistics for a numeric column."""
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return {"error": "No valid numeric data"}
    stats: Dict[str, Any] = {
        "count": int(s.count()),
        "missing": int(series.isna().sum()),
        "missing_pct": round(series.isna().mean() * 100, 2),
        "mean": round(float(s.mean()), 4),
        "median": round(float(s.median()), 4),
        "std": round(float(s.std()), 4),
        "min": round(float(s.min()), 4),
        "max": round(float(s.max()), 4),
        "p25": round(float(s.quantile(0.25)), 4),
        "p50": round(float(s.quantile(0.50)), 4),
        "p75": round(float(s.quantile(0.75)), 4),
        "skewness": round(float(s.skew()), 4) if len(s) >= 3 else None,
        "kurtosis": round(float(s.kurtosis()), 4) if len(s) >= 4 else None,
    }
    return stats


def _categorical_stats(series: pd.Series) -> Dict[str, Any]:
    """Compute statistics for a categorical column."""
    s = series.dropna().astype(str)
    vc = s.value_counts()
    return {
        "count": int(s.count()),
        "missing": int(series.isna().sum()),
        "missing_pct": round(series.isna().mean() * 100, 2),
        "unique": int(s.nunique()),
        "top_values": vc.head(10).to_dict(),
        "top_value": str(vc.index[0]) if len(vc) else None,
        "top_freq": int(vc.iloc[0]) if len(vc) else None,
        "top_freq_pct": round(float(vc.iloc[0] / len(s) * 100), 2) if len(vc) else None,
    }


def _datetime_stats(series: pd.Series) -> Dict[str, Any]:
    """Compute statistics for a datetime column."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        s = pd.to_datetime(series, infer_datetime_format=True, errors="coerce").dropna()
    if s.empty:
        return {"error": "No parseable dates"}
    sorted_s = s.sort_values()
    gaps = sorted_s.diff().dropna()
    stats: Dict[str, Any] = {
        "count": int(s.count()),
        "missing": int(series.isna().sum()),
        "missing_pct": round(series.isna().mean() * 100, 2),
        "min_date": str(sorted_s.min().date()),
        "max_date": str(sorted_s.max().date()),
        "range_days": int((sorted_s.max() - sorted_s.min()).days),
        "most_common_day": str(s.dt.day_name().mode()[0]) if not s.empty else None,
        "most_common_hour": int(s.dt.hour.mode()[0]) if not s.empty else None,
        "avg_gap_days": round(float(gaps.dt.total_seconds().mean() / 86400), 2) if not gaps.empty else None,
    }
    return stats


def _text_stats(series: pd.Series) -> Dict[str, Any]:
    """Compute statistics for a free-text column."""
    s = series.dropna().astype(str)
    lengths = s.str.len()
    word_counts = s.str.split().str.len()
    return {
        "count": int(s.count()),
        "missing": int(series.isna().sum()),
        "missing_pct": round(series.isna().mean() * 100, 2),
        "avg_length": round(float(lengths.mean()), 2),
        "min_length": int(lengths.min()),
        "max_length": int(lengths.max()),
        "avg_word_count": round(float(word_counts.mean()), 2),
        "min_word_count": int(word_counts.min()),
        "max_word_count": int(word_counts.max()),
    }


def _boolean_stats(series: pd.Series) -> Dict[str, Any]:
    """Compute statistics for a boolean column."""
    s = series.dropna()
    vc = s.value_counts()
    _truthy = {True, 1, "True", "true", "yes", "Yes"}
    true_count = int(sum(vc.get(k, 0) for k in _truthy))
    return {
        "count": int(s.count()),
        "missing": int(series.isna().sum()),
        "missing_pct": round(series.isna().mean() * 100, 2),
        "true_count": true_count,
        "false_count": int(s.count()) - true_count,
        "top_value": str(vc.index[0]) if len(vc) else None,
    }


def column_statistics(df: pd.DataFrame, col_types: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    """Return per-column statistics for all columns in *df*."""
    stats: Dict[str, Dict[str, Any]] = {}
    for col in df.columns:
        ctype = col_types.get(col, "unknown")
        if ctype == "numeric":
            stats[col] = _numeric_stats(df[col])
        elif ctype == "categorical":
            stats[col] = _categorical_stats(df[col])
        elif ctype == "datetime":
            stats[col] = _datetime_stats(df[col])
        elif ctype == "text":
            stats[col] = _text_stats(df[col])
        elif ctype == "boolean":
            stats[col] = _boolean_stats(df[col])
        else:
            stats[col] = {"missing": int(df[col].isna().sum()), "missing_pct": round(df[col].isna().mean() * 100, 2)}
    return stats


# ---------------------------------------------------------------------------
# Dataset-level statistics
# ---------------------------------------------------------------------------

def dataset_statistics(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute top-level statistics for the entire dataset."""
    mem_bytes = df.memory_usage(deep=True).sum()
    missing_per_col = df.isna().sum()
    return {
        "row_count": len(df),
        "column_count": len(df.columns),
        "total_cells": df.size,
        "memory_bytes": int(mem_bytes),
        "memory_human": _human_bytes(mem_bytes),
        "duplicate_rows": int(df.duplicated().sum()),
        "duplicate_pct": round(df.duplicated().mean() * 100, 2),
        "total_missing": int(missing_per_col.sum()),
        "total_missing_pct": round(missing_per_col.sum() / df.size * 100, 2),
        "columns_with_missing": int((missing_per_col > 0).sum()),
        "column_names": list(df.columns),
    }


def _human_bytes(n: int) -> str:
    """Return a human-readable byte size string."""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


# ---------------------------------------------------------------------------
# Correlation matrix
# ---------------------------------------------------------------------------

def correlation_matrix(df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """Return Pearson correlation matrix for all numeric columns."""
    numeric_df = df.select_dtypes(include=[np.number])
    # Also try to coerce columns to numeric
    for col in df.columns:
        if col not in numeric_df.columns:
            coerced = pd.to_numeric(df[col], errors="coerce")
            if coerced.notna().sum() > len(df) * 0.5:
                numeric_df[col] = coerced
    if numeric_df.shape[1] < 2:
        return None
    corr = numeric_df.corr(method="pearson")
    return {
        "columns": list(corr.columns),
        "matrix": corr.to_dict(),
        "strong_pairs": _strong_correlations(corr),
    }


def _strong_correlations(corr: pd.DataFrame, threshold: float = 0.7) -> List[Dict[str, Any]]:
    """Return pairs of columns with |r| > threshold (excluding diagonal)."""
    pairs: List[Dict[str, Any]] = []
    cols = list(corr.columns)
    for i, c1 in enumerate(cols):
        for c2 in cols[i + 1:]:
            r = corr.loc[c1, c2]
            if not math.isnan(r) and abs(r) > threshold:
                pairs.append({"col1": c1, "col2": c2, "r": round(float(r), 4)})
    pairs.sort(key=lambda x: abs(x["r"]), reverse=True)
    return pairs


# ---------------------------------------------------------------------------
# Outlier detection (IQR method)
# ---------------------------------------------------------------------------

def detect_outliers(df: pd.DataFrame, col_types: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    """Detect outliers in numeric columns using the IQR method."""
    results: Dict[str, Dict[str, Any]] = {}
    for col, ctype in col_types.items():
        if ctype != "numeric":
            continue
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(s) < 4:
            continue
        q1 = s.quantile(0.25)
        q3 = s.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outlier_mask = (s < lower) | (s > upper)
        outlier_vals = s[outlier_mask]
        results[col] = {
            "lower_fence": round(float(lower), 4),
            "upper_fence": round(float(upper), 4),
            "outlier_count": int(outlier_mask.sum()),
            "outlier_pct": round(float(outlier_mask.mean() * 100), 2),
            "outlier_values": [round(float(v), 4) for v in outlier_vals.tolist()[:20]],
        }
    return results


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def profile(df: pd.DataFrame) -> Dict[str, Any]:
    """Run a full profile pass on *df* and return a structured results dict."""
    col_types = detect_column_types(df)
    return {
        "dataset": dataset_statistics(df),
        "col_types": col_types,
        "columns": column_statistics(df, col_types),
        "correlation": correlation_matrix(df),
        "outliers": detect_outliers(df, col_types),
    }
