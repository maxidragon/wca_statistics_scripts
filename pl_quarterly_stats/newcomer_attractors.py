"""
Newcomer attractors: which competitions, cities, months, and event mixes
attract the most newcomers?

Usage:
  python newcomer_attractors.py                # all time
  python newcomer_attractors.py --last 5       # last 5 years
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import pandas as pd
from loader import load
from _period import parse_args, apply_filter, make_year_colors

OUT = Path(__file__).parent / "output"
OUT.mkdir(exist_ok=True)

MONTHS_PL = ["Sty", "Lut", "Mar", "Kwi", "Maj", "Cze",
             "Lip", "Sie", "Wrz", "Paź", "Lis", "Gru"]

EVENT_NAMES = {
    "333": "3x3x3", "222": "2x2x2", "444": "4x4x4", "555": "5x5x5",
    "666": "6x6x6", "777": "7x7x7", "333bf": "3x3 Blindfolded",
    "333oh": "3x3 One-Handed", "clock": "Clock", "minx": "Megaminx",
    "pyram": "Pyraminx", "skewb": "Skewb", "sq1": "Square-1",
    "444bf": "4x4 Blindfolded", "555bf": "5x5 Blindfolded",
    "333mbf": "Multi-Blind", "333ft": "3x3 With Feet",
}

args = parse_args()
print("Loading data...")
comps_pl, att, persons, first_comp = load()
comps_pl, att, period_label, file_suffix = apply_filter(comps_pl, att, args)
YEAR_COLORS = make_year_colors(comps_pl["year"].unique())
print(f"  Period: {period_label}  |  competitions: {len(comps_pl)}  |  attendance rows: {len(att)}")

# Per-competition newcomer stats
comp_stats = (
    att.groupby("competition_id")
    .agg(total=("person_id", "nunique"), newcomers=("is_newcomer", "sum"))
    .reset_index()
)
comp_stats["pct_newcomers"] = comp_stats["newcomers"] / comp_stats["total"] * 100

comp_stats = comp_stats.merge(
    comps_pl[["id", "name", "city_name", "year", "month",
              "latitude_microdegrees", "longitude_microdegrees", "event_specs"]]
    .rename(columns={"id": "competition_id"}),
    on="competition_id",
)

year_legend = [
    mpatches.Patch(color=c, label=str(y))
    for y, c in YEAR_COLORS.items()
    if y in comp_stats["year"].unique()
]

def save(name):
    path = OUT / f"{name}{file_suffix}.png"
    plt.savefig(path, dpi=150)
    plt.close()
    return path.name

saved = []

# ── 1. Top competitions by absolute newcomer count ────────────────────────────
TOP_N = 20
top_abs = comp_stats.nlargest(TOP_N, "newcomers").sort_values("newcomers")

fig, ax = plt.subplots(figsize=(12, 7))
bars = ax.barh(top_abs["name"], top_abs["newcomers"],
               color=top_abs["year"].map(YEAR_COLORS))
ax.bar_label(bars, padding=3, fontsize=8)
ax.set_xlabel("Liczba nowicjuszy")
ax.set_title(f"Top {TOP_N} zawodów z największą liczbą nowicjuszy WCA ({period_label})")
ax.legend(handles=year_legend, title="Rok", loc="lower right")
plt.tight_layout()
saved.append(save("18_top_comps_by_newcomers"))

# ── 2. Top competitions by newcomer % (min 30 total competitors) ──────────────
MIN_COMPETITORS = 30
top_pct = (
    comp_stats[comp_stats.total >= MIN_COMPETITORS]
    .nlargest(TOP_N, "pct_newcomers")
    .sort_values("pct_newcomers")
)

fig, ax = plt.subplots(figsize=(12, 7))
bars = ax.barh(top_pct["name"], top_pct["pct_newcomers"],
               color=top_pct["year"].map(YEAR_COLORS))
ax.bar_label(bars, fmt="%.1f%%", padding=3, fontsize=8)
ax.set_xlabel("% nowicjuszy")
ax.set_title(
    f"Top {TOP_N} zawodów z największym udziałem nowicjuszy "
    f"(min. {MIN_COMPETITORS} zawodników, {period_label})"
)
ax.legend(handles=year_legend, title="Rok", loc="lower right")
plt.tight_layout()
saved.append(save("19_top_comps_by_newcomer_pct"))

# ── 3. Geographic bubble chart ────────────────────────────────────────────────
comp_stats["lat"] = comp_stats["latitude_microdegrees"] / 1e6
comp_stats["lon"] = comp_stats["longitude_microdegrees"] / 1e6

city_geo = (
    comp_stats.groupby("city_name")
    .agg(
        total_newcomers=("newcomers", "sum"),
        avg_newcomers=("newcomers", "mean"),
        n_comps=("competition_id", "nunique"),
        lat=("lat", "mean"),
        lon=("lon", "mean"),
    )
    .reset_index()
)

fig, ax = plt.subplots(figsize=(10, 9))
sc = ax.scatter(
    city_geo["lon"], city_geo["lat"],
    s=city_geo["total_newcomers"] * 2.5,
    c=city_geo["avg_newcomers"],
    cmap="YlOrRd", alpha=0.75, edgecolors="#555555", linewidths=0.5,
)
plt.colorbar(sc, ax=ax, label="Śr. nowicjuszy na zawodach", shrink=0.6)
for _, row in city_geo.nlargest(20, "total_newcomers").iterrows():
    ax.annotate(
        row["city_name"], (row["lon"], row["lat"] + 0.06),
        fontsize=7, ha="center", va="bottom",
    )
ax.set_xlabel("Długość geograficzna")
ax.set_ylabel("Szerokość geograficzna")
ax.set_title(
    f"Nowicjusze WCA w Polsce – rozkład geograficzny ({period_label})\n"
    "Rozmiar: łączna liczba nowicjuszy  |  Kolor: średnia na zawodach"
)
plt.tight_layout()
saved.append(save("20_newcomers_geo_bubble"))

# ── 4. Newcomers by calendar month ───────────────────────────────────────────
monthly = (
    comp_stats.groupby("month")
    .agg(avg_count=("newcomers", "mean"), avg_pct=("pct_newcomers", "mean"))
    .reset_index()
)

fig, ax1 = plt.subplots(figsize=(12, 5))
ax2 = ax1.twinx()
ax1.bar(monthly["month"], monthly["avg_count"], color="#DD8452", alpha=0.75,
        label="Śr. liczba nowicjuszy")
ax2.plot(monthly["month"], monthly["avg_pct"], marker="o", color="#4C72B0",
         linewidth=2, label="Śr. % nowicjuszy")
ax1.set_xticks(range(1, 13))
ax1.set_xticklabels(MONTHS_PL)
ax1.set_ylabel("Śr. liczba nowicjuszy na zawodach", color="#DD8452")
ax2.set_ylabel("Śr. % nowicjuszy", color="#4C72B0")
ax1.set_title(f"Kiedy przyjeżdżają nowicjusze? Wzorzec miesięczny ({period_label})")
h1, l1 = ax1.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, loc="upper left")
plt.tight_layout()
saved.append(save("21_newcomers_by_month"))

# ── 5. WCA events vs. average newcomer % ─────────────────────────────────────
comp_events = (
    comp_stats[["competition_id", "pct_newcomers", "event_specs"]]
    .dropna(subset=["event_specs"])
    .assign(event_list=lambda df: df["event_specs"].str.split())
    .explode("event_list")
    .rename(columns={"event_list": "event_id"})
    .dropna(subset=["event_id"])
)

overall_avg = comp_stats["pct_newcomers"].mean()

event_avg = (
    comp_events.groupby("event_id")
    .agg(avg_pct=("pct_newcomers", "mean"), n_comps=("competition_id", "nunique"))
    .reset_index()
    .sort_values("avg_pct", ascending=True)
)
event_avg["event_name"] = event_avg["event_id"].map(EVENT_NAMES).fillna(event_avg["event_id"])

fig, ax = plt.subplots(figsize=(10, max(5, len(event_avg) * 0.42)))
colors_ev = ["#55A868" if v >= overall_avg else "#DD8452" for v in event_avg["avg_pct"]]
bars = ax.barh(event_avg["event_name"], event_avg["avg_pct"], color=colors_ev)
ax.axvline(overall_avg, color="gray", linestyle="--",
           label=f"Średnia wszystkich zawodów ({overall_avg:.1f}%)")
ax.bar_label(bars, fmt="%.1f%%", padding=3, fontsize=8)
ax.set_xlabel("Śr. % nowicjuszy na zawodach oferujących tę konkurencję")
ax.set_title(
    f"Udział nowicjuszy wg oferowanych konkurencji ({period_label})\n"
    "Zielony = powyżej średniej, pomarańczowy = poniżej"
)
ax.legend()
plt.tight_layout()
saved.append(save("22_newcomers_by_event"))

print("Saved: " + ", ".join(saved))
