# 🔬 Auto Data Profiler & Visualization Engine

> **One command. Instant insights. Beautiful reports.**
>
> Drop any CSV or JSON file and get a fully interactive HTML report packed with statistics, visualizations, anomaly detection, and plain-English insights — no configuration needed.

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/deps-pandas%20numpy%20matplotlib%20seaborn-green.svg)](#)

---

## ✨ Features

| Feature | Description |
|---|---|
| 🧠 **Smart Type Detection** | Automatically classifies columns as numeric, categorical, datetime, text, or boolean |
| 📊 **Rich Statistics** | Mean, median, std, percentiles, skewness, kurtosis, top-categories, datetime ranges, text lengths |
| 🔗 **Correlation Analysis** | Pearson correlation matrix with highlighted strong pairs (|r| > 0.7) |
| 🚨 **Outlier Detection** | IQR-based outlier detection with counts, percentages, and example values |
| 💡 **Auto Insights** | Plain-English insights ranked by severity (Critical / High / Medium / Low) |
| 📈 **Rich Visualizations** | Histograms, box plots, heatmaps, bar charts, time series — all embedded as base64 |
| 🖥️ **Beautiful HTML Report** | Self-contained single-file report with dark/light theme, smooth animations, collapsible sections |
| 🎨 **Colorful Terminal** | ANSI-colored progress output with summary stats right in your terminal |
| 📂 **Flexible Input** | CSV, JSON, or piped stdin |

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run on the included demo dataset

```bash
python analyze.py sample_data.csv
```

### 3. Open the report

```bash
# Linux/macOS
open report.html

# Windows
start report.html
```

---

## 📖 Usage

```bash
# Analyse a CSV file
python analyze.py your_data.csv

# Analyse a JSON file
python analyze.py your_data.json

# Custom output path
python analyze.py your_data.csv --output my_report.html

# Pipe data from stdin
cat data.csv | python analyze.py -

# Skip HTML report (terminal output only)
python analyze.py your_data.csv --no-report

# Quiet mode (no progress output)
python analyze.py your_data.csv --quiet
```

---

## 🗂️ Project Structure

```
NewCodetry/
├── analyze.py           # 🚀 Main CLI entry point
├── profiler.py          # 🧠 Data profiling engine
├── visualizer.py        # 📈 Visualization generator (base64 PNG)
├── insights.py          # 💡 Insight generator
├── report_generator.py  # 🖥️  HTML report builder
├── sample_data.csv      # 🛸 Demo dataset (space missions)
├── requirements.txt     # 📦 Python dependencies
└── README.md            # 📖 This file
```

---

## 🛸 Demo Dataset

`sample_data.csv` contains **~130 rows** of fictional and real space mission data including:

- **Numeric columns**: crew size, mission duration, budget, distance, payload mass, success rate
- **Categorical columns**: agency, destination, mission status, commander
- **Datetime column**: launch date
- **Text column**: mission notes
- **Intentional missing values & outliers** to showcase the tool's detection capabilities

---

## ⚙️ How It Works

```
 CSV / JSON
     │
     ▼
 profiler.py ──────► Column type detection
                      Per-column statistics
                      Dataset-level stats
                      Correlation matrix
                      Outlier detection (IQR)
     │
     ├──► visualizer.py ──► Matplotlib / Seaborn charts
     │                       encoded as base64 PNG
     │
     ├──► insights.py ───► Plain-English insights
     │                       ranked by severity
     │
     └──► report_generator.py ──► Self-contained HTML
                                    dark/light theme
                                    collapsible sections
                                    all images inline
```

---

## 📦 Dependencies

```
pandas>=1.3.0
numpy>=1.21.0
matplotlib>=3.4.0
seaborn>=0.11.0
```

All standard, widely-available Python packages. No external services or API keys required.

---

## 🛠️ Technical Notes

- **Python 3.8+ compatible**
- Graceful error handling for bad files, empty datasets, and parsing failures
- The HTML report is **fully self-contained** — share it as a single file with no external dependencies
- Visualizations use a **non-interactive Matplotlib backend** (Agg) — no display needed
- Terminal output uses **ANSI escape codes** (auto-disabled when not writing to a TTY)

---

*Made with ❤️ and a lot of 🛸 space data*