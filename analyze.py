#!/usr/bin/env python3
"""
analyze.py — Main CLI Entry Point for the Auto Data Profiler & Visualization Engine

Usage:
    python analyze.py your_data.csv
    python analyze.py your_data.json
    cat data.csv | python analyze.py -          # read from stdin

Options:
    --no-report     Skip HTML report generation
    --output FILE   Custom output HTML path (default: report.html)
    --quiet         Suppress progress output
"""

import argparse
import io
import json
import os
import sys
import time
from typing import Optional

import pandas as pd


# ---------------------------------------------------------------------------
# ANSI colour helpers
# ---------------------------------------------------------------------------

class _C:
    """ANSI colour codes. Disabled automatically when not writing to a TTY."""
    _USE = sys.stdout.isatty() or os.environ.get("FORCE_COLOR", "")

    RESET  = "\033[0m"   if _USE else ""
    BOLD   = "\033[1m"   if _USE else ""
    DIM    = "\033[2m"   if _USE else ""

    RED    = "\033[91m"  if _USE else ""
    GREEN  = "\033[92m"  if _USE else ""
    YELLOW = "\033[93m"  if _USE else ""
    BLUE   = "\033[94m"  if _USE else ""
    MAGENTA= "\033[95m"  if _USE else ""
    CYAN   = "\033[96m"  if _USE else ""
    WHITE  = "\033[97m"  if _USE else ""


def _c(text: str, *codes: str) -> str:
    if not codes:
        return text
    return "".join(codes) + str(text) + _C.RESET


def _banner() -> None:
    print(_c("""
╔══════════════════════════════════════════════════════════╗
║   🔬  Auto Data Profiler & Visualization Engine 🔬       ║
║       Automatic insights · Beautiful reports              ║
╚══════════════════════════════════════════════════════════╝
""", _C.CYAN, _C.BOLD))


def _step(icon: str, msg: str, quiet: bool = False) -> None:
    if not quiet:
        print(f"  {icon}  {_c(msg, _C.WHITE)}", flush=True)


def _ok(icon: str, msg: str, quiet: bool = False) -> None:
    if not quiet:
        print(f"  {icon}  {_c(msg, _C.GREEN)}", flush=True)


def _warn(msg: str) -> None:
    print(f"  {_c('⚠️', _C.YELLOW)}  {_c(msg, _C.YELLOW)}", flush=True, file=sys.stderr)


def _err(msg: str) -> None:
    print(f"  {_c('❌', _C.RED)}  {_c(msg, _C.RED, _C.BOLD)}", flush=True, file=sys.stderr)


def _separator(quiet: bool = False) -> None:
    if not quiet:
        print(_c("  " + "─" * 56, _C.DIM))


def _progress(label: str, quiet: bool = False) -> float:
    if not quiet:
        print(f"  ⏳  {_c(label + ' ...', _C.DIM)}", end="", flush=True)
    return time.time()


def _done(t0: float, quiet: bool = False) -> None:
    elapsed = time.time() - t0
    if not quiet:
        print(_c(f"  ✓  done ({elapsed:.2f}s)", _C.GREEN))


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data(source: str) -> pd.DataFrame:
    """Load a CSV or JSON file (or '-' for stdin) into a DataFrame."""
    if source == "-":
        raw = sys.stdin.read()
        # Try CSV first, then JSON
        try:
            return pd.read_csv(io.StringIO(raw))
        except Exception:
            pass
        try:
            return pd.read_json(io.StringIO(raw))
        except Exception as exc:
            raise ValueError(f"Could not parse stdin as CSV or JSON: {exc}") from exc

    if not os.path.exists(source):
        raise FileNotFoundError(f"File not found: {source!r}")

    ext = os.path.splitext(source)[1].lower()
    if ext == ".json":
        return pd.read_json(source)
    # Default: CSV (also handles .tsv, .txt with comma delimiter)
    try:
        return pd.read_csv(source)
    except Exception as exc:
        raise ValueError(f"Could not read CSV file {source!r}: {exc}") from exc


# ---------------------------------------------------------------------------
# Pretty terminal summary
# ---------------------------------------------------------------------------

def _print_summary(profile: dict, insights: list, quiet: bool) -> None:
    if quiet:
        return
    ds = profile.get("dataset", {})
    col_types = profile.get("col_types", {})

    print()
    _separator(quiet)
    print(_c("  📊  Dataset Summary", _C.CYAN, _C.BOLD))
    _separator(quiet)
    rows = ds.get("row_count", 0)
    cols = ds.get("column_count", 0)
    mem  = ds.get("memory_human", "—")
    dups = ds.get("duplicate_rows", 0)
    miss = ds.get("total_missing_pct", 0)

    print(f"     Rows          : {_c(f'{rows:,}', _C.WHITE, _C.BOLD)}")
    print(f"     Columns       : {_c(str(cols), _C.WHITE, _C.BOLD)}")
    print(f"     Memory        : {_c(mem, _C.WHITE)}")
    print(f"     Duplicate rows: {_c(str(dups), _C.YELLOW if dups else _C.GREEN)}")
    print(f"     Missing data  : {_c(f'{miss:.1f}%', _C.YELLOW if miss > 5 else _C.GREEN)}")

    # Column type breakdown
    type_counts: dict = {}
    for t in col_types.values():
        type_counts[t] = type_counts.get(t, 0) + 1
    print()
    print(_c("     Column Types:", _C.DIM))
    type_colors = {"numeric": _C.GREEN, "categorical": _C.BLUE, "datetime": _C.YELLOW,
                   "text": _C.MAGENTA, "boolean": _C.CYAN, "unknown": _C.DIM}
    for t, cnt in sorted(type_counts.items()):
        col_str = _c(f"  {t:<14} {cnt}", type_colors.get(t, _C.WHITE))
        print(f"       {col_str}")

    # Top insights
    if insights:
        print()
        _separator(quiet)
        print(_c(f"  💡  Top Insights ({len(insights)} total)", _C.CYAN, _C.BOLD))
        _separator(quiet)
        severity_color = {4: _C.RED, 3: _C.YELLOW, 2: _C.BLUE, 1: _C.GREEN}
        for ins in insights[:8]:
            sev_c = severity_color.get(ins["severity"], _C.WHITE)
            label = ins["severity_label"].split(" ", 1)[0]  # just the emoji
            print(f"     {label}  {_c(ins['message'], sev_c)}")
            if ins.get("detail"):
                print(f"         {_c(ins['detail'], _C.DIM)}")
        if len(insights) > 8:
            print(_c(f"       ... and {len(insights) - 8} more in the HTML report.", _C.DIM))

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Auto Data Profiler & Visualization Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("file", help="Path to CSV/JSON file, or '-' to read from stdin")
    parser.add_argument("--no-report", action="store_true", help="Skip HTML report generation")
    parser.add_argument("--output", default="report.html", metavar="FILE",
                        help="Output HTML file path (default: report.html)")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress progress output")
    args = parser.parse_args()

    if not args.quiet:
        _banner()

    # ---- Load data ----
    _step("📂", f"Loading data from {args.file!r}", args.quiet)
    try:
        t0 = time.time()
        df = load_data(args.file)
        elapsed = time.time() - t0
        _ok("✅", f"Loaded {len(df):,} rows × {len(df.columns)} columns in {elapsed:.2f}s", args.quiet)
    except (FileNotFoundError, ValueError) as exc:
        _err(str(exc))
        return 1

    if df.empty:
        _err("Dataset is empty — nothing to profile.")
        return 1

    # ---- Profile ----
    t0 = _progress("Running data profiler", args.quiet)
    try:
        import profiler
        profile = profiler.profile(df)
    except Exception as exc:
        print()
        _err(f"Profiling failed: {exc}")
        return 1
    _done(t0, args.quiet)

    # ---- Insights ----
    t0 = _progress("Generating insights", args.quiet)
    try:
        import insights as insights_mod
        all_insights = insights_mod.generate_insights(profile)
    except Exception as exc:
        print()
        _err(f"Insights generation failed: {exc}")
        all_insights = []
    _done(t0, args.quiet)

    # ---- Pretty terminal output ----
    _print_summary(profile, all_insights, args.quiet)

    # ---- Visualisations + HTML report ----
    if not args.no_report:
        t0 = _progress("Generating visualisations", args.quiet)
        try:
            import visualizer
            col_types = profile.get("col_types", {})
            viz = visualizer.generate_all(df, col_types)
        except Exception as exc:
            print()
            _warn(f"Visualisation step failed (report will have no charts): {exc}")
            viz = {}
        _done(t0, args.quiet)

        t0 = _progress("Building HTML report", args.quiet)
        try:
            import report_generator
            out_path = report_generator.generate_report(
                profile=profile,
                insights=all_insights,
                viz=viz,
                source_file=args.file,
                output_path=args.output,
            )
        except Exception as exc:
            print()
            _err(f"Report generation failed: {exc}")
            return 1
        _done(t0, args.quiet)

        abs_path = os.path.abspath(out_path)
        if not args.quiet:
            print(_c(f"  📄  Report saved → {abs_path}", _C.GREEN, _C.BOLD))
            size_kb = os.path.getsize(abs_path) / 1024
            print(_c(f"       File size: {size_kb:.1f} KB", _C.DIM))
            print()

    if not args.quiet:
        print(_c("  🚀  Analysis complete!", _C.CYAN, _C.BOLD))
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
