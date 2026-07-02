"""
Recurring competition series: WCA competitions in Poland that take place under the
same name across multiple years, compared by attendance per edition.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
from loader import load
from _period import parse_args, apply_filter

OUT = Path(__file__).parent / "output"
OUT.mkdir(exist_ok=True)

MONTHS_PL = ["Sty", "Lut", "Mar", "Kwi", "Maj", "Cze",
             "Lip", "Sie", "Wrz", "Paź", "Lis", "Gru"]

args = parse_args()
print("Loading data...")
comps_pl, att, persons, first_comp = load()
comps_pl, att, period_label, file_suffix = apply_filter(comps_pl, att, args)
print(f"  Period: {period_label}  |  competitions: {len(comps_pl)}")

# Attendance per competition
att_per_comp = (
    att.groupby("competition_id")["person_id"]
    .nunique()
    .reset_index(name="n_competitors")
)

# Strip 4-digit years from competition names to identify recurring series
comps_pl["series_name"] = (
    comps_pl["name"]
    .str.replace(r"\b\d{4}\b", "", regex=True)
    .str.strip()
    .str.replace(r"\s+", " ", regex=True)
)

comps_with_att = (
    comps_pl[["id", "name", "series_name", "year", "month", "city_name"]]
    .rename(columns={"id": "competition_id"})
    .merge(att_per_comp, on="competition_id", how="left")
)
comps_with_att["n_competitors"] = comps_with_att["n_competitors"].fillna(0).astype(int)

# Keep only series that appeared in 3+ different years
years_per_series = comps_with_att.groupby("series_name")["year"].nunique()
recurring_names = years_per_series[years_per_series >= 3].index

rec = comps_with_att[comps_with_att.series_name.isin(recurring_names)].copy()

# Typical month per series (for axis labels)
typical_month = rec.groupby("series_name")["month"].median().round().astype(int)

def label_with_month(name):
    m = typical_month.get(name)
    return f"{name} ({MONTHS_PL[m - 1]})" if m else name

# Pivot: series × year, value = attendance
pivot = (
    rec.pivot_table(index="series_name", columns="year",
                    values="n_competitors", aggfunc="sum")
    .fillna(0)
    .astype(int)
)
pivot.index = [label_with_month(n) for n in pivot.index]

# Sort: most editions first, then highest total attendance
sort_key = pd.DataFrame({
    "editions": (pivot > 0).sum(axis=1),
    "total":    pivot.sum(axis=1),
}, index=pivot.index)
pivot = pivot.loc[sort_key.sort_values(["editions", "total"], ascending=False).index]

# ── 1. Heatmap: series × year ─────────────────────────────────────────────────
MAX_SERIES = 30
hm = pivot.head(MAX_SERIES)
max_val = hm.values.max()
n_cols = len(hm.columns)

fig, ax = plt.subplots(figsize=(max(10, n_cols * 0.7), max(6, len(hm) * 0.42)))
im = ax.imshow(hm.values, aspect="auto", cmap="YlOrRd", vmin=0)

for i in range(len(hm)):
    for j in range(n_cols):
        v = hm.iloc[i, j]
        text = str(v) if v > 0 else "—"
        color = "white" if v > max_val * 0.65 else ("black" if v > 0 else "#bbbbbb")
        ax.text(j, i, text, ha="center", va="center", fontsize=7.5, color=color)

ax.set_xticks(range(n_cols))
ax.set_xticklabels(hm.columns, rotation=45, ha="right")
ax.set_yticks(range(len(hm)))
ax.set_yticklabels(hm.index, fontsize=8)
plt.colorbar(im, ax=ax, label="Zawodnicy", shrink=0.55)
ax.set_title(
    f"Cykliczne zawody WCA w Polsce – frekwencja per edycja ({period_label})\n"
    "(w nawiasie typowy miesiąc rozgrywania)"
)
plt.tight_layout()
fig.savefig(OUT / f"16_recurring_series_heatmap{file_suffix}.png", dpi=150)
plt.close()

# ── 2. Line chart: top 10 series attendance trend ─────────────────────────────
top10 = pivot.head(10)

fig, ax = plt.subplots(figsize=(12, 5))
for series_label, row in top10.iterrows():
    valid = row[row > 0]
    short = series_label if len(series_label) <= 38 else series_label[:35] + "..."
    ax.plot(valid.index, valid.values, marker="o", label=short)

ax.set_xlabel("Rok")
ax.set_ylabel("Zawodnicy")
ax.set_title(f"Frekwencja na cyklicznych zawodach – top serie ({period_label})")
ax.legend(fontsize=7.5, loc="upper left", bbox_to_anchor=(1, 1))
ax.grid(axis="y", alpha=0.3)
ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
plt.tight_layout()
fig.savefig(OUT / f"17_recurring_series_trend{file_suffix}.png", dpi=150, bbox_inches="tight")
plt.close()

# ── CSV export ─────────────────────────────────────────────────────────────────
pivot.reset_index().rename(columns={"series_name": "series"}).to_csv(
    OUT / f"recurring_series{file_suffix}.csv", index=False
)

print(f"Saved: 16–17 + CSV ({period_label})")
