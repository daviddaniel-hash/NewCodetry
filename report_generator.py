"""
report_generator.py — Interactive HTML Report Generator

Produces a single, fully self-contained HTML file (all CSS/JS/images inline)
with a dark/light theme toggle, smooth animations, collapsible sections, and
all visualisations embedded as base64 images.
"""

import html
import json
from datetime import datetime
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# CSS (dark / light themes)
# ---------------------------------------------------------------------------

_CSS = """
:root {
  --bg: #0d1117;
  --surface: #161b22;
  --surface2: #21262d;
  --border: #30363d;
  --text: #c9d1d9;
  --text-muted: #8b949e;
  --accent: #58a6ff;
  --accent2: #f78166;
  --accent3: #3fb950;
  --accent4: #d29922;
  --radius: 10px;
  --shadow: 0 4px 24px rgba(0,0,0,0.5);
  --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
body.light {
  --bg: #f6f8fa;
  --surface: #ffffff;
  --surface2: #f0f2f4;
  --border: #d0d7de;
  --text: #1f2328;
  --text-muted: #656d76;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  transition: var(--transition);
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* ---- Header ---- */
header {
  background: linear-gradient(135deg, #0d1117 0%, #161b22 50%, #0d1117 100%);
  border-bottom: 1px solid var(--border);
  padding: 28px 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: var(--shadow);
}
body.light header {
  background: linear-gradient(135deg, #ffffff 0%, #f0f2f4 50%, #ffffff 100%);
}
.header-title { display: flex; align-items: center; gap: 12px; }
.header-title h1 { font-size: 1.5rem; font-weight: 700; color: var(--accent); letter-spacing: -0.5px; }
.header-title span { font-size: 1.8rem; }
.header-meta { font-size: 0.8rem; color: var(--text-muted); margin-top: 4px; }

/* ---- Theme toggle ---- */
#theme-btn {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 6px 16px;
  cursor: pointer;
  color: var(--text);
  font-size: 0.85rem;
  transition: var(--transition);
  display: flex;
  align-items: center;
  gap: 6px;
}
#theme-btn:hover { background: var(--accent); color: #fff; border-color: var(--accent); }

/* ---- Nav sidebar ---- */
nav {
  position: fixed;
  left: 0;
  top: 80px;
  width: 220px;
  height: calc(100vh - 80px);
  overflow-y: auto;
  background: var(--surface);
  border-right: 1px solid var(--border);
  padding: 20px 0;
  transition: var(--transition);
  z-index: 50;
}
nav ul { list-style: none; }
nav ul li a {
  display: block;
  padding: 8px 24px;
  font-size: 0.82rem;
  color: var(--text-muted);
  border-left: 3px solid transparent;
  transition: var(--transition);
}
nav ul li a:hover, nav ul li a.active {
  color: var(--accent);
  border-left-color: var(--accent);
  background: rgba(88, 166, 255, 0.08);
  text-decoration: none;
}
nav .nav-section { padding: 12px 24px 4px; font-size: 0.7rem; text-transform: uppercase;
  letter-spacing: 1px; color: var(--text-muted); font-weight: 600; }

/* ---- Main content ---- */
main {
  margin-left: 220px;
  padding: 32px;
  max-width: 1200px;
  animation: fadeIn 0.6s ease;
}
@keyframes fadeIn { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: none; } }

/* ---- Sections ---- */
.section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  margin-bottom: 24px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.25);
  transition: var(--transition);
}
.section:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.4); }
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  cursor: pointer;
  background: var(--surface2);
  border-bottom: 1px solid var(--border);
  user-select: none;
  transition: var(--transition);
}
.section-header:hover { background: rgba(88, 166, 255, 0.06); }
.section-header h2 { font-size: 1.05rem; font-weight: 600; display: flex; align-items: center; gap: 10px; }
.section-header .toggle-icon { font-size: 1rem; transition: transform 0.3s; color: var(--text-muted); }
.section-header.collapsed .toggle-icon { transform: rotate(-90deg); }
.section-body { padding: 24px; }
.section-body.hidden { display: none; }

/* ---- Stat cards ---- */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.stat-card {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px 20px;
  text-align: center;
  transition: var(--transition);
  animation: popIn 0.4s ease backwards;
}
.stat-card:hover { transform: translateY(-2px); border-color: var(--accent); }
.stat-card .value { font-size: 1.6rem; font-weight: 700; color: var(--accent); }
.stat-card .label { font-size: 0.75rem; color: var(--text-muted); margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }
@keyframes popIn { from { opacity: 0; transform: scale(0.92); } to { opacity: 1; transform: scale(1); } }

/* ---- Column type badges ---- */
.badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.badge-numeric  { background: rgba(58, 185, 80, 0.15); color: #3fb950; border: 1px solid #3fb950; }
.badge-categorical { background: rgba(88,166,255,0.15); color: #58a6ff; border: 1px solid #58a6ff; }
.badge-datetime { background: rgba(210,153,34,0.15); color: #d29922; border: 1px solid #d29922; }
.badge-text     { background: rgba(188,140,255,0.15); color: #bc8cff; border: 1px solid #bc8cff; }
.badge-boolean  { background: rgba(247,129,102,0.15); color: #f78166; border: 1px solid #f78166; }
.badge-unknown  { background: rgba(139,148,158,0.15); color: #8b949e; border: 1px solid #8b949e; }

/* ---- Column detail cards ---- */
.col-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }
.col-card {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px 18px;
  transition: var(--transition);
}
.col-card:hover { border-color: var(--accent); }
.col-card h3 { font-size: 0.9rem; font-weight: 600; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.col-card table { width: 100%; border-collapse: collapse; font-size: 0.78rem; }
.col-card td { padding: 3px 6px; border-bottom: 1px solid var(--border); }
.col-card td:first-child { color: var(--text-muted); width: 45%; }
.col-card td:last-child { font-weight: 500; }

/* ---- Charts ---- */
.chart-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }
.chart-card {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  transition: var(--transition);
}
.chart-card:hover { transform: scale(1.01); border-color: var(--accent); }
.chart-card .chart-title {
  padding: 10px 16px;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border);
}
.chart-card img { width: 100%; display: block; }

/* ---- Insights ---- */
.insight {
  display: flex;
  gap: 14px;
  padding: 14px 16px;
  border-radius: 8px;
  margin-bottom: 10px;
  border-left: 4px solid;
  transition: var(--transition);
  animation: slideIn 0.4s ease backwards;
}
.insight:hover { transform: translateX(4px); }
.insight-critical { background: rgba(248,81,73,0.07); border-color: #f85149; }
.insight-high     { background: rgba(210,153,34,0.07); border-color: #d29922; }
.insight-medium   { background: rgba(88,166,255,0.07); border-color: #58a6ff; }
.insight-low      { background: rgba(63,185,80,0.07);  border-color: #3fb950; }
.insight-icon { font-size: 1.1rem; flex-shrink: 0; }
.insight-body {}
.insight-title { font-weight: 600; font-size: 0.88rem; }
.insight-category { font-size: 0.7rem; color: var(--text-muted); margin-bottom: 2px; text-transform: uppercase; letter-spacing: 0.5px; }
.insight-detail { font-size: 0.78rem; color: var(--text-muted); margin-top: 3px; }
@keyframes slideIn { from { opacity: 0; transform: translateX(-16px); } to { opacity: 1; transform: none; } }

/* ---- Missing values progress bars ---- */
.missing-bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; font-size: 0.78rem; }
.missing-bar-label { width: 160px; text-align: right; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.missing-bar-track { flex: 1; background: var(--surface2); border-radius: 4px; height: 8px; overflow: hidden; }
.missing-bar-fill { height: 100%; border-radius: 4px; transition: width 1s ease; }
.missing-bar-pct { width: 40px; text-align: right; font-weight: 600; }

/* ---- Correlation table ---- */
.corr-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
.corr-table th, .corr-table td { padding: 8px 12px; border: 1px solid var(--border); text-align: center; }
.corr-table th { background: var(--surface2); font-weight: 600; }
.corr-positive-strong { color: #f85149; font-weight: 700; }
.corr-positive-mid { color: #d29922; }
.corr-negative-strong { color: #58a6ff; font-weight: 700; }
.corr-negative-mid { color: #bc8cff; }

/* ---- Footer ---- */
footer {
  text-align: center;
  padding: 24px;
  font-size: 0.78rem;
  color: var(--text-muted);
  border-top: 1px solid var(--border);
  margin-left: 220px;
}
footer span { color: var(--accent); }

/* ---- Responsive ---- */
@media (max-width: 768px) {
  nav { display: none; }
  main, footer { margin-left: 0; padding: 16px; }
  .chart-grid { grid-template-columns: 1fr; }
}
"""


# ---------------------------------------------------------------------------
# JavaScript
# ---------------------------------------------------------------------------

_JS = """
// Theme toggle
const btn = document.getElementById('theme-btn');
const body = document.body;
const saved = localStorage.getItem('theme');
if (saved === 'light') { body.classList.add('light'); btn.textContent = '🌙 Dark Mode'; }
btn.addEventListener('click', () => {
  body.classList.toggle('light');
  const isLight = body.classList.contains('light');
  btn.textContent = isLight ? '🌙 Dark Mode' : '☀️ Light Mode';
  localStorage.setItem('theme', isLight ? 'light' : 'dark');
});

// Collapsible sections
document.querySelectorAll('.section-header').forEach(header => {
  header.addEventListener('click', () => {
    const body = header.nextElementSibling;
    const icon = header.querySelector('.toggle-icon');
    body.classList.toggle('hidden');
    header.classList.toggle('collapsed');
  });
});

// Active nav link on scroll
const sections = document.querySelectorAll('section[id]');
const navLinks = document.querySelectorAll('nav a');
window.addEventListener('scroll', () => {
  let current = '';
  sections.forEach(s => {
    if (window.scrollY >= s.offsetTop - 120) current = s.id;
  });
  navLinks.forEach(a => {
    a.classList.toggle('active', a.getAttribute('href') === '#' + current);
  });
});

// Animate insight delays
document.querySelectorAll('.insight').forEach((el, i) => {
  el.style.animationDelay = (i * 0.05) + 's';
});

// Animate stat card delays
document.querySelectorAll('.stat-card').forEach((el, i) => {
  el.style.animationDelay = (i * 0.07) + 's';
});
"""


# ---------------------------------------------------------------------------
# HTML-building helpers
# ---------------------------------------------------------------------------

def _e(text: Any) -> str:
    """HTML-escape a value."""
    return html.escape(str(text))


def _badge(col_type: str) -> str:
    return f'<span class="badge badge-{_e(col_type)}">{_e(col_type)}</span>'


def _fmt(val: Any, digits: int = 4) -> str:
    """Format a numeric value for display."""
    if val is None:
        return "—"
    try:
        f = float(val)
        if f != f:  # NaN
            return "—"
        return f"{f:,.{digits}f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return _e(str(val))


def _stat_card(value: str, label: str) -> str:
    return f'<div class="stat-card"><div class="value">{_e(value)}</div><div class="label">{_e(label)}</div></div>'


def _chart_img(b64: str, title: str = "") -> str:
    title_html = f'<div class="chart-title">{_e(title)}</div>' if title else ""
    return f'<div class="chart-card">{title_html}<img src="data:image/png;base64,{b64}" alt="{_e(title)}" loading="lazy"></div>'


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _section(sec_id: str, icon: str, title: str, content: str, collapsed: bool = False) -> str:
    collapsed_cls = " collapsed" if collapsed else ""
    hidden_cls = " hidden" if collapsed else ""
    return f"""
<section id="{_e(sec_id)}" class="section">
  <div class="section-header{collapsed_cls}">
    <h2>{icon} {_e(title)}</h2>
    <span class="toggle-icon">▼</span>
  </div>
  <div class="section-body{hidden_cls}">{content}</div>
</section>"""


def _build_overview(profile: Dict[str, Any]) -> str:
    ds = profile.get("dataset", {})
    col_types = profile.get("col_types", {})
    type_counts: Dict[str, int] = {}
    for t in col_types.values():
        type_counts[t] = type_counts.get(t, 0) + 1

    cards = [
        _stat_card(f"{ds.get('row_count', 0):,}", "Rows"),
        _stat_card(f"{ds.get('column_count', 0):,}", "Columns"),
        _stat_card(ds.get("memory_human", "—"), "Memory"),
        _stat_card(f"{ds.get('duplicate_rows', 0):,}", "Duplicate Rows"),
        _stat_card(f"{ds.get('total_missing_pct', 0):.1f}%", "Missing Values"),
        _stat_card(f"{ds.get('columns_with_missing', 0):,}", "Cols w/ Missing"),
    ]
    for t, cnt in sorted(type_counts.items()):
        cards.append(_stat_card(str(cnt), f"{t.title()} Columns"))

    grid = f'<div class="stats-grid">{"".join(cards)}</div>'

    # Missing values bar chart
    cols_data = profile.get("columns", {})
    missing_rows = []
    for col, stats in cols_data.items():
        pct = stats.get("missing_pct", 0) or 0
        if pct > 0:
            fill_color = "#f85149" if pct >= 30 else "#d29922" if pct >= 10 else "#58a6ff"
            missing_rows.append((pct, col, fill_color))
    missing_rows.sort(reverse=True)
    if missing_rows:
        bars_html = "".join(
            f'<div class="missing-bar-row">'
            f'<div class="missing-bar-label" title="{_e(col)}">{_e(col)}</div>'
            f'<div class="missing-bar-track"><div class="missing-bar-fill" style="width:{pct:.1f}%;background:{fc}"></div></div>'
            f'<div class="missing-bar-pct">{pct:.1f}%</div>'
            f'</div>'
            for pct, col, fc in missing_rows
        )
        grid += f"<h3 style='margin:16px 0 10px;font-size:0.95rem;'>Missing Values per Column</h3>{bars_html}"

    return grid


def _build_columns(profile: Dict[str, Any]) -> str:
    col_types = profile.get("col_types", {})
    columns = profile.get("columns", {})
    cards = []
    for col, stats in columns.items():
        ctype = col_types.get(col, "unknown")
        rows_html = ""
        skip = {"top_values", "outlier_values"}
        for k, v in stats.items():
            if k in skip:
                continue
            if isinstance(v, dict):
                continue
            rows_html += f"<tr><td>{_e(k.replace('_', ' ').title())}</td><td>{_fmt(v)}</td></tr>"
        # top_values for categoricals
        if ctype == "categorical" and "top_values" in stats:
            top = list(stats["top_values"].items())[:5]
            if top:
                rows_html += "<tr><td>Top Values</td><td>" + ", ".join(f"{_e(k)}: {v}" for k, v in top) + "</td></tr>"
        card = f"""
<div class="col-card">
  <h3>{_e(col)} {_badge(ctype)}</h3>
  <table>{rows_html}</table>
</div>"""
        cards.append(card)
    return f'<div class="col-grid">{"".join(cards)}</div>'


def _build_correlation(profile: Dict[str, Any]) -> str:
    corr = profile.get("correlation")
    if not corr:
        return "<p style='color:var(--text-muted)'>Not enough numeric columns for correlation analysis.</p>"

    strong_pairs = corr.get("strong_pairs", [])
    pairs_html = ""
    if strong_pairs:
        pairs_html = "<h3 style='margin:20px 0 10px;font-size:0.95rem;'>Strongly Correlated Pairs (|r| &gt; 0.7)</h3><table class='corr-table'><tr><th>Column A</th><th>Column B</th><th>r</th><th>Interpretation</th></tr>"
        for p in strong_pairs:
            r = p["r"]
            cls = "corr-positive-strong" if r >= 0.85 else "corr-positive-mid" if r > 0 else ("corr-negative-strong" if r <= -0.85 else "corr-negative-mid")
            interp = "Very strong positive" if r >= 0.85 else ("Strong positive" if r >= 0.7 else ("Very strong negative" if r <= -0.85 else "Strong negative"))
            pairs_html += f"<tr><td>{_e(p['col1'])}</td><td>{_e(p['col2'])}</td><td class='{cls}'>{r:.3f}</td><td>{interp}</td></tr>"
        pairs_html += "</table>"
    else:
        pairs_html = "<p style='color:var(--text-muted)'>No strongly correlated pairs found (|r| &gt; 0.7).</p>"

    return pairs_html


def _build_insights(insights: List[Dict[str, Any]]) -> str:
    if not insights:
        return "<p style='color:var(--text-muted)'>No notable insights detected. Data looks clean! 🎉</p>"
    severity_map = {"🔴 Critical": ("insight-critical", "🔴"), "🟠 High": ("insight-high", "🟠"),
                    "🟡 Medium": ("insight-medium", "🟡"), "🔵 Low": ("insight-low", "🔵")}
    items = []
    for ins in insights:
        css_cls, icon = severity_map.get(ins["severity_label"], ("insight-low", "⚪"))
        detail_html = f'<div class="insight-detail">{_e(ins["detail"])}</div>' if ins.get("detail") else ""
        items.append(f"""
<div class="insight {css_cls}">
  <div class="insight-icon">{icon}</div>
  <div class="insight-body">
    <div class="insight-category">{_e(ins['category'])}</div>
    <div class="insight-title">{_e(ins['message'])}</div>
    {detail_html}
  </div>
</div>""")
    return "".join(items)


def _build_charts(viz: Dict[str, Any]) -> str:
    sections_html = ""

    # Numeric overview
    if viz.get("numeric_overview"):
        sections_html += f'<div style="margin-bottom:20px">{_chart_img(viz["numeric_overview"], "Numeric Columns Overview (Normalised)")}</div>'

    # Histograms
    hists = viz.get("histograms", {})
    if hists:
        grid_items = "".join(_chart_img(b64, col) for col, b64 in hists.items())
        sections_html += f'<h3 style="margin:10px 0 14px;font-size:0.95rem;">Distribution Histograms</h3><div class="chart-grid">{grid_items}</div>'

    # Box plots
    boxes = viz.get("box_plots", {})
    if boxes:
        grid_items = "".join(_chart_img(b64, f"Box Plot — {col}") for col, b64 in boxes.items())
        sections_html += f'<h3 style="margin:20px 0 14px;font-size:0.95rem;">Box Plots (Outlier Visualisation)</h3><div class="chart-grid">{grid_items}</div>'

    # Category bars
    cats = viz.get("category_bars", {})
    if cats:
        grid_items = "".join(_chart_img(b64, f"Top Categories — {col}") for col, b64 in cats.items())
        sections_html += f'<h3 style="margin:20px 0 14px;font-size:0.95rem;">Categorical Distributions</h3><div class="chart-grid">{grid_items}</div>'

    # Time series
    ts = viz.get("time_series", {})
    if ts:
        grid_items = "".join(_chart_img(b64, key.replace("___", " vs ")) for key, b64 in ts.items())
        sections_html += f'<h3 style="margin:20px 0 14px;font-size:0.95rem;">Time Series</h3><div class="chart-grid">{grid_items}</div>'

    return sections_html or "<p style='color:var(--text-muted)'>No charts generated.</p>"


def _build_data_quality(profile: Dict[str, Any], viz: Dict[str, Any]) -> str:
    ds = profile.get("dataset", {})
    content = ""

    # Missing heatmap / bar chart
    missing_bar = viz.get("missing_bar")
    missing_heat = viz.get("missing_heatmap")
    if missing_bar or missing_heat:
        imgs = ""
        if missing_bar:
            imgs += _chart_img(missing_bar, "Missing Values by Column")
        if missing_heat:
            imgs += _chart_img(missing_heat, "Missing Values Matrix")
        content += f'<div class="chart-grid">{imgs}</div>'
    else:
        content += "<p style='color:var(--accent3)'>✅ No missing values detected!</p>"

    # Outlier summary table
    outliers = profile.get("outliers", {})
    if outliers:
        content += "<h3 style='margin:20px 0 10px;font-size:0.95rem;'>Outlier Summary (IQR Method)</h3>"
        content += "<table class='corr-table'><tr><th>Column</th><th>Outliers</th><th>%</th><th>Lower Fence</th><th>Upper Fence</th><th>Samples</th></tr>"
        for col, out in sorted(outliers.items(), key=lambda x: -x[1]["outlier_count"]):
            samples = ", ".join(str(v) for v in out["outlier_values"][:3])
            pct_cls = "corr-positive-strong" if out["outlier_pct"] >= 10 else ("corr-positive-mid" if out["outlier_pct"] >= 3 else "")
            content += (f"<tr><td>{_e(col)}</td>"
                        f"<td class='{pct_cls}'>{out['outlier_count']}</td>"
                        f"<td class='{pct_cls}'>{out['outlier_pct']:.1f}%</td>"
                        f"<td>{_fmt(out['lower_fence'])}</td>"
                        f"<td>{_fmt(out['upper_fence'])}</td>"
                        f"<td style='font-size:0.72rem;color:var(--text-muted)'>{_e(samples)}</td></tr>")
        content += "</table>"

    # Duplicate info
    dup = ds.get("duplicate_rows", 0)
    dup_pct = ds.get("duplicate_pct", 0)
    color = "var(--accent2)" if dup > 0 else "var(--accent3)"
    icon = "⚠️" if dup > 0 else "✅"
    content += f"<p style='margin-top:16px;color:{color}'>{icon} {dup:,} duplicate row(s) ({dup_pct:.1f}%)</p>"

    return content


def _nav_html() -> str:
    return """<nav>
  <div class="nav-section">Navigation</div>
  <ul>
    <li><a href="#overview">📊 Overview</a></li>
    <li><a href="#columns">📋 Columns</a></li>
    <li><a href="#correlation">🔗 Correlation</a></li>
    <li><a href="#visualisations">📈 Visualisations</a></li>
    <li><a href="#quality">🛡️ Data Quality</a></li>
    <li><a href="#insights">💡 Insights</a></li>
  </ul>
</nav>"""


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_report(
    profile: Dict[str, Any],
    insights: List[Dict[str, Any]],
    viz: Dict[str, Any],
    source_file: str = "dataset",
    output_path: str = "report.html",
) -> str:
    """Generate a self-contained HTML report and write it to *output_path*.

    Returns the path to the generated file.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ds = profile.get("dataset", {})
    rows = ds.get("row_count", 0)
    cols = ds.get("column_count", 0)

    corr_img = viz.get("correlation_heatmap", "")
    corr_section = ""
    if corr_img:
        corr_section = f'<div style="max-width:700px;margin:0 auto 20px">{_chart_img(corr_img, "Correlation Heatmap")}</div>'
    corr_section += _build_correlation(profile)

    insight_count = len(insights)
    critical_count = sum(1 for i in insights if i["severity"] >= 4)

    body_content = f"""
<header>
  <div class="header-title">
    <span>🔬</span>
    <div>
      <h1>Auto Data Profiler Report</h1>
      <div class="header-meta">
        {_e(source_file)} &nbsp;·&nbsp; {rows:,} rows × {cols} columns &nbsp;·&nbsp; Generated {_e(timestamp)}
        &nbsp;·&nbsp; {insight_count} insights
        {f'&nbsp;·&nbsp; <span style="color:#f85149">{critical_count} critical</span>' if critical_count else ''}
      </div>
    </div>
  </div>
  <button id="theme-btn">☀️ Light Mode</button>
</header>
{_nav_html()}
<main>
  {_section("overview",      "📊", "Dataset Overview",          _build_overview(profile))}
  {_section("columns",       "📋", "Column Deep Dive",          _build_columns(profile), collapsed=True)}
  {_section("correlation",   "🔗", "Correlation Analysis",      corr_section)}
  {_section("visualisations","📈", "Visualisations",            _build_charts(viz))}
  {_section("quality",       "🛡️", "Data Quality Report",       _build_data_quality(profile, viz))}
  {_section("insights",      "💡", "Auto-Generated Insights",   _build_insights(insights))}
</main>
<footer>Generated by <span>Auto Data Profiler</span> · {_e(timestamp)}</footer>
"""

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Data Profiler Report — {_e(source_file)}</title>
  <style>{_CSS}</style>
</head>
<body>
{body_content}
<script>{_JS}</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_doc)

    return output_path
