# WCA Statistics Scripts

Analysis and visualisation scripts for Polish WCA speedcubing data, based on the
official WCA export TSV files.

---

## Setup

### 1. WCA export data

Download the latest export from https://www.worldcubeassociation.org/export/results
and extract it into a folder named `wca-export/` at the project root:

```
wca_statistics_scripts/
└── wca-export/
    ├── WCA_export_competitions.tsv
    ├── WCA_export_results.tsv
    ├── WCA_export_persons.tsv
    └── ...
```

### 2. Python environment

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Project structure

```
wca_statistics_scripts/
├── wca-export/                          # WCA TSV data (gitignored)
├── requirements.txt
│
├── pl_quarterly_stats/                  # Main analysis suite (22 charts)
│   ├── run_all.py                       #   Run all charts in one go
│   ├── competition_trends.py            #   Charts 1–4
│   ├── competitor_activity.py           #   Charts 5–10
│   ├── newcomer_cohorts.py              #   Charts 11–15
│   ├── recurring_series.py              #   Charts 16–17
│   ├── newcomer_attractors.py           #   Charts 18–22 (standalone only)
│   ├── loader.py                        #   Shared data loader
│   ├── _period.py                       #   Shared CLI / period-filter helper
│   ├── STATISTICS.txt                   #   Description of all 22 charts
│   └── output/                          #   Generated charts (gitignored)
│
├── wca_heatmap/
│   └── main.py                          # Folium heatmap (HTML output)
│
└── returning_newcomers_by_year_in_poland/
    └── main.py                          # Returning newcomers (requires MySQL)
```

---

## pl_quarterly_stats — main analysis suite

### Run everything at once

```bash
# All available history (Poland WCA started in 2005)
python pl_quarterly_stats/run_all.py

# Last N years only
python pl_quarterly_stats/run_all.py --last 5    # 2022–2026
python pl_quarterly_stats/run_all.py --last 10   # 2016–2026
python pl_quarterly_stats/run_all.py --last 1    # current year only
```

Charts 1–17 are generated. Output files include the period in their name so
multiple runs do not overwrite each other:

| Mode | File suffix | Example |
|------|-------------|---------|
| All time | `_all` | `1_comps_per_quarter_all.png` |
| Last 5 years | `_last5y` | `1_comps_per_quarter_last5y.png` |
| Last 1 year | `_last1y` | `1_comps_per_quarter_last1y.png` |

### Run individual scripts

Each script accepts the same `--last N` flag and produces only its own charts:

```bash
python pl_quarterly_stats/competition_trends.py           # charts 1–4
python pl_quarterly_stats/competition_trends.py --last 5

python pl_quarterly_stats/competitor_activity.py          # charts 5–10
python pl_quarterly_stats/competitor_activity.py --last 3

python pl_quarterly_stats/newcomer_cohorts.py             # charts 11–15
python pl_quarterly_stats/newcomer_cohorts.py --last 5

python pl_quarterly_stats/recurring_series.py             # charts 16–17
python pl_quarterly_stats/recurring_series.py --last 10
```

### newcomer_attractors (standalone only)

Charts 18–22 are not part of `run_all.py` and must be run separately:

```bash
python pl_quarterly_stats/newcomer_attractors.py          # all time
python pl_quarterly_stats/newcomer_attractors.py --last 5
```

### Charts overview

See `pl_quarterly_stats/STATISTICS.txt` for detailed descriptions of all 22 charts.

| # | Script | What it shows |
|---|--------|---------------|
| 1 | competition_trends | Competitions per quarter |
| 2 | competition_trends | Competitions per month, years overlaid |
| 3 | competition_trends | Cumulative competitions YTD |
| 4 | competition_trends | Mean/median attendance per competition per quarter |
| 5 | competitor_activity | Unique competitors per quarter |
| 6 | competitor_activity | Newcomers vs returning (stacked bar) |
| 7 | competitor_activity | % newcomers per quarter |
| 8 | competitor_activity | Starts per person per year (histograms) |
| 9 | competitor_activity | Competitors active in 3+ quarters per year |
| 10 | competitor_activity | Activity trend: mean / median / 75th pct per year |
| 11 | newcomer_cohorts | Newcomers per quarter (debuts only) |
| 12 | newcomer_cohorts | Newcomers per month, years overlaid |
| 13 | newcomer_cohorts | Cohort retention % (3 / 6 / 12 months) |
| 14 | newcomer_cohorts | Cohort retention absolute numbers |
| 15 | newcomer_cohorts | Distribution of return count per newcomer |
| 16 | recurring_series | Recurring series heatmap (series × year) |
| 17 | recurring_series | Top recurring series attendance trend |
| 18 | newcomer_attractors | Top competitions by newcomer count |
| 19 | newcomer_attractors | Top competitions by newcomer % |
| 20 | newcomer_attractors | Geographic bubble chart of newcomers |
| 21 | newcomer_attractors | Newcomers by calendar month |
| 22 | newcomer_attractors | Average newcomer % by WCA event offered |

---

## wca_heatmap

Generates two interactive HTML heatmaps of Polish competitors' locations using Folium:

- `heatmap_v1_sumarycznie.html` — all Polish competitors
- `heatmap_v2_lokalsi.html` — only competitors who debuted locally (DBSCAN cluster)

Edit `YEAR` at the top of the script to change the target year.

```bash
python wca_heatmap/main.py
```

Output HTML files are written next to the script (gitignored).

---

## returning_newcomers_by_year_in_poland

Requires a local MySQL database loaded with WCA data. Edit the connection
parameters and `YEAR` at the top of the script.

```bash
python returning_newcomers_by_year_in_poland/main.py
```

---

## Notes

- **Data freshness**: re-download `wca-export/` whenever you want up-to-date results.
- **`is_newcomer` flag**: a competitor is marked as a newcomer when the Polish competition
  they attended was their very first WCA competition globally (not just in Poland).
  This is computed from the full WCA history regardless of the `--last` filter.
- **`--last N` edge cases**: if `N` exceeds the available history, the script quietly
  uses all available data (the earliest Polish WCA competition was in 2005).
