"""
visualizer.py — Auto Visualization Generator

Creates matplotlib/seaborn charts and returns them as base64-encoded PNG strings
so they can be embedded directly in HTML without any external files.
"""

import base64
import io
import warnings
from typing import Any, Dict, List, Optional

import matplotlib
matplotlib.use("Agg")  # non-interactive backend — must be set before pyplot import
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

warnings.filterwarnings("ignore")

# --------------------------------------------------------------------------
# Palette & style helpers
# --------------------------------------------------------------------------

PALETTE = "viridis"
BG_COLOR = "#1a1a2e"
ACCENT = "#e94560"
TEXT_COLOR = "#eaeaea"
GRID_COLOR = "#2a2a4a"


def _apply_dark_style(ax, fig=None):
    """Apply a consistent dark theme to axes and figure."""
    if fig:
        fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor("#16213e")
    ax.tick_params(colors=TEXT_COLOR, labelsize=8)
    ax.xaxis.label.set_color(TEXT_COLOR)
    ax.yaxis.label.set_color(TEXT_COLOR)
    ax.title.set_color(TEXT_COLOR)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_COLOR)
    ax.grid(color=GRID_COLOR, linestyle="--", linewidth=0.5, alpha=0.7)


def _fig_to_b64(fig) -> str:
    """Render *fig* to a base64-encoded PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=120, facecolor=fig.get_facecolor())
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return b64


# --------------------------------------------------------------------------
# Individual chart generators
# --------------------------------------------------------------------------

def distribution_histograms(df: pd.DataFrame, col_types: Dict[str, str]) -> Dict[str, str]:
    """Return base64 histograms for each numeric column."""
    charts: Dict[str, str] = {}
    numeric_cols = [c for c, t in col_types.items() if t == "numeric"]
    for col in numeric_cols:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(s) < 3:
            continue
        fig, ax = plt.subplots(figsize=(6, 4))
        _apply_dark_style(ax, fig)
        n_bins = min(30, max(10, int(np.sqrt(len(s)))))
        ax.hist(s, bins=n_bins, color=ACCENT, edgecolor="#0f3460", alpha=0.85)
        # KDE overlay
        try:
            from scipy.stats import gaussian_kde  # optional, nice-to-have
            xs = np.linspace(s.min(), s.max(), 200)
            kde = gaussian_kde(s)
            ax2 = ax.twinx()
            ax2.plot(xs, kde(xs), color="#e2b04a", linewidth=1.5)
            ax2.set_yticks([])
            _apply_dark_style(ax2)
        except ImportError:
            pass
        ax.set_title(f"Distribution of '{col}'", fontsize=11, fontweight="bold")
        ax.set_xlabel(col, fontsize=9)
        ax.set_ylabel("Frequency", fontsize=9)
        charts[col] = _fig_to_b64(fig)
    return charts


def correlation_heatmap(df: pd.DataFrame, col_types: Dict[str, str]) -> Optional[str]:
    """Return a base64 correlation heatmap for numeric columns."""
    numeric_cols = [c for c, t in col_types.items() if t == "numeric"]
    num_df = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    num_df = num_df.dropna(axis=1, thresh=max(1, len(num_df) // 2))
    if num_df.shape[1] < 2:
        return None
    corr = num_df.corr()
    n = corr.shape[0]
    fig_size = max(6, n * 0.6 + 2)
    fig, ax = plt.subplots(figsize=(min(fig_size, 16), min(fig_size, 14)))
    _apply_dark_style(ax, fig)
    mask = np.triu(np.ones_like(corr, dtype=bool))
    cmap = sns.diverging_palette(230, 20, as_cmap=True)
    sns.heatmap(
        corr,
        mask=mask,
        cmap=cmap,
        vmax=1,
        vmin=-1,
        center=0,
        annot=n <= 15,
        fmt=".2f",
        square=True,
        linewidths=0.5,
        ax=ax,
        annot_kws={"size": 7, "color": TEXT_COLOR},
        cbar_kws={"shrink": 0.8},
    )
    ax.set_title("Correlation Matrix (Pearson)", fontsize=13, fontweight="bold", color=TEXT_COLOR, pad=12)
    ax.tick_params(axis="x", rotation=45, labelsize=8)
    ax.tick_params(axis="y", rotation=0, labelsize=8)
    ax.tick_params(colors=TEXT_COLOR)
    # Colorbar text
    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(colors=TEXT_COLOR, labelsize=7)
    return _fig_to_b64(fig)


def missing_values_heatmap(df: pd.DataFrame) -> Optional[str]:
    """Return a base64 missing-values matrix."""
    if df.isnull().sum().sum() == 0:
        return None
    cols_with_missing = df.columns[df.isnull().any()].tolist()
    if not cols_with_missing:
        return None
    sub = df[cols_with_missing].copy()
    # Limit rows for readability
    if len(sub) > 200:
        sub = sub.iloc[:200]
    fig, ax = plt.subplots(figsize=(max(6, len(cols_with_missing) * 0.5 + 2), 6))
    _apply_dark_style(ax, fig)
    missing_matrix = sub.isnull().astype(int)
    sns.heatmap(
        missing_matrix.T,
        cmap=["#16213e", ACCENT],
        cbar=False,
        ax=ax,
        yticklabels=cols_with_missing,
        xticklabels=False,
    )
    ax.set_title("Missing Values Matrix", fontsize=13, fontweight="bold", color=TEXT_COLOR, pad=10)
    ax.tick_params(axis="y", colors=TEXT_COLOR, labelsize=8)
    ax.set_xlabel("Rows (sample)", fontsize=9, color=TEXT_COLOR)
    return _fig_to_b64(fig)


def missing_values_bar(df: pd.DataFrame) -> Optional[str]:
    """Return a base64 bar chart of missing-value percentages per column."""
    missing_pct = df.isnull().mean() * 100
    missing_pct = missing_pct[missing_pct > 0].sort_values(ascending=False)
    if missing_pct.empty:
        return None
    fig, ax = plt.subplots(figsize=(max(6, len(missing_pct) * 0.5 + 2), 5))
    _apply_dark_style(ax, fig)
    colors = [ACCENT if v > 30 else "#e2b04a" if v > 10 else "#4a9eff" for v in missing_pct]
    bars = ax.bar(range(len(missing_pct)), missing_pct.values, color=colors, edgecolor=GRID_COLOR, linewidth=0.5)
    ax.set_xticks(range(len(missing_pct)))
    ax.set_xticklabels(missing_pct.index, rotation=45, ha="right", fontsize=8, color=TEXT_COLOR)
    ax.set_ylabel("Missing %", fontsize=9, color=TEXT_COLOR)
    ax.set_title("Missing Values by Column", fontsize=13, fontweight="bold", color=TEXT_COLOR, pad=10)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    for bar, val in zip(bars, missing_pct.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5, f"{val:.1f}%",
                ha="center", va="bottom", fontsize=7, color=TEXT_COLOR)
    return _fig_to_b64(fig)


def categorical_bar_charts(df: pd.DataFrame, col_types: Dict[str, str]) -> Dict[str, str]:
    """Return base64 bar charts for top categories in categorical columns."""
    charts: Dict[str, str] = {}
    cat_cols = [c for c, t in col_types.items() if t == "categorical"]
    for col in cat_cols:
        s = df[col].dropna().astype(str)
        if s.empty:
            continue
        vc = s.value_counts().head(12)
        fig, ax = plt.subplots(figsize=(7, 4))
        _apply_dark_style(ax, fig)
        palette = sns.color_palette("husl", len(vc))
        bars = ax.barh(vc.index[::-1], vc.values[::-1], color=palette[::-1], edgecolor=GRID_COLOR, linewidth=0.4)
        ax.set_title(f"Top Categories — '{col}'", fontsize=11, fontweight="bold")
        ax.set_xlabel("Count", fontsize=9)
        for bar in bars:
            w = bar.get_width()
            ax.text(w + 0.3, bar.get_y() + bar.get_height() / 2, str(int(w)),
                    va="center", fontsize=7, color=TEXT_COLOR)
        charts[col] = _fig_to_b64(fig)
    return charts


def box_plots(df: pd.DataFrame, col_types: Dict[str, str]) -> Dict[str, str]:
    """Return base64 box plots for numeric columns (outlier visualisation)."""
    charts: Dict[str, str] = {}
    numeric_cols = [c for c, t in col_types.items() if t == "numeric"]
    for col in numeric_cols:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(s) < 4:
            continue
        fig, ax = plt.subplots(figsize=(5, 4))
        _apply_dark_style(ax, fig)
        bp = ax.boxplot(
            s,
            vert=True,
            patch_artist=True,
            notch=False,
            widths=0.5,
            boxprops=dict(facecolor="#0f3460", color=ACCENT),
            whiskerprops=dict(color=TEXT_COLOR),
            capprops=dict(color=TEXT_COLOR),
            medianprops=dict(color="#e2b04a", linewidth=2),
            flierprops=dict(marker="o", markerfacecolor=ACCENT, markersize=4, linestyle="none"),
        )
        ax.set_title(f"Box Plot — '{col}'", fontsize=11, fontweight="bold")
        ax.set_ylabel(col, fontsize=9)
        ax.set_xticks([])
        charts[col] = _fig_to_b64(fig)
    return charts


def time_series_plots(df: pd.DataFrame, col_types: Dict[str, str]) -> Dict[str, str]:
    """Return base64 time-series line plots for datetime + numeric column combos."""
    charts: Dict[str, str] = {}
    datetime_cols = [c for c, t in col_types.items() if t == "datetime"]
    numeric_cols = [c for c, t in col_types.items() if t == "numeric"]
    if not datetime_cols or not numeric_cols:
        return charts

    for dt_col in datetime_cols[:2]:  # limit to 2 datetime axes
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            dates = pd.to_datetime(df[dt_col], infer_datetime_format=True, errors="coerce")
        valid_mask = dates.notna()
        if valid_mask.sum() < 5:
            continue
        for num_col in numeric_cols[:4]:  # limit to 4 numeric series
            num_vals = pd.to_numeric(df.loc[valid_mask, num_col], errors="coerce")
            plot_df = pd.DataFrame({"date": dates[valid_mask], "value": num_vals}).dropna().sort_values("date")
            if len(plot_df) < 5:
                continue
            fig, ax = plt.subplots(figsize=(9, 4))
            _apply_dark_style(ax, fig)
            ax.plot(plot_df["date"], plot_df["value"], color=ACCENT, linewidth=1.2, marker="o",
                    markersize=2.5, markerfacecolor="#e2b04a")
            ax.fill_between(plot_df["date"], plot_df["value"], alpha=0.15, color=ACCENT)
            ax.set_title(f"{num_col} over {dt_col}", fontsize=11, fontweight="bold")
            ax.set_xlabel(dt_col, fontsize=9)
            ax.set_ylabel(num_col, fontsize=9)
            fig.autofmt_xdate()
            key = f"{dt_col}___{num_col}"
            charts[key] = _fig_to_b64(fig)
    return charts


def numeric_overview(df: pd.DataFrame, col_types: Dict[str, str]) -> Optional[str]:
    """Return a combined violin/strip plot for all numeric columns (normalised)."""
    numeric_cols = [c for c, t in col_types.items() if t == "numeric"]
    if not numeric_cols:
        return None
    # Normalise each column to [0, 1] so they fit on the same axes
    norm_data = {}
    for col in numeric_cols:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(s) < 3:
            continue
        rng = s.max() - s.min()
        norm_data[col] = (s - s.min()) / rng if rng > 0 else s - s.min()
    if not norm_data:
        return None
    plot_df = pd.DataFrame(norm_data).melt(var_name="Column", value_name="Normalised Value")
    fig, ax = plt.subplots(figsize=(max(8, len(norm_data) * 0.8 + 2), 5))
    _apply_dark_style(ax, fig)
    sns.violinplot(data=plot_df, x="Column", y="Normalised Value", palette="husl", ax=ax,
                   inner="quartile", linewidth=0.6)
    ax.set_title("Numeric Columns Overview (Normalised)", fontsize=13, fontweight="bold")
    ax.set_xlabel("")
    ax.tick_params(axis="x", rotation=45, labelsize=8)
    return _fig_to_b64(fig)


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------

def generate_all(df: pd.DataFrame, col_types: Dict[str, str]) -> Dict[str, Any]:
    """Generate all visualisations and return a dict of base64 PNG strings."""
    return {
        "histograms": distribution_histograms(df, col_types),
        "correlation_heatmap": correlation_heatmap(df, col_types),
        "missing_heatmap": missing_values_heatmap(df),
        "missing_bar": missing_values_bar(df),
        "category_bars": categorical_bar_charts(df, col_types),
        "box_plots": box_plots(df, col_types),
        "time_series": time_series_plots(df, col_types),
        "numeric_overview": numeric_overview(df, col_types),
    }
