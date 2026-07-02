"""
Competitor activity: unique competitors per quarter, newcomers vs returning,
distribution of starts per person per year, consistently active (3+ quarters in a year).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from loader import load
from _period import parse_args, apply_filter

OUT = Path(__file__).parent / "output"
OUT.mkdir(exist_ok=True)

args = parse_args()
print("Loading data…")
comps_pl, att, persons, first_comp = load()
comps_pl, att, period_label, file_suffix = apply_filter(comps_pl, att, args)
print(f"  Period: {period_label}  |  competitions: {len(comps_pl)}")

# ── 1. Unique competitors per quarter ────────────────────────────────────────
q_uniq = att.groupby(["year", "quarter"])["person_id"].nunique().reset_index(name="n")
q_uniq["label"] = q_uniq["year"].astype(str) + " Q" + q_uniq["quarter"].astype(str)

fig, ax = plt.subplots(figsize=(14, 5))
ax.bar(q_uniq["label"], q_uniq["n"], color="#55A868")
ax.set_xlabel("Kwartał")
ax.set_ylabel("Unikalni zawodnicy")
ax.set_title(f"Liczba unikalnych zawodników w Polsce per kwartał ({period_label})")
ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
fig.savefig(OUT / f"5_unique_competitors_per_quarter{file_suffix}.png", dpi=150)
plt.close()

# ── 2. Newcomers vs returning competitors per quarter (stacked bar) ──────────
q_new = (att[att.is_newcomer].groupby(["year", "quarter"])["person_id"]
         .nunique().reset_index(name="newcomers"))
q_ret = (att[~att.is_newcomer].groupby(["year", "quarter"])["person_id"]
         .nunique().reset_index(name="returning"))

q_comp = q_new.merge(q_ret, on=["year", "quarter"], how="outer").fillna(0)
q_comp["label"] = q_comp["year"].astype(str) + " Q" + q_comp["quarter"].astype(str)
q_comp = q_comp.sort_values(["year", "quarter"])

fig, ax = plt.subplots(figsize=(14, 5))
x = range(len(q_comp))
ax.bar(x, q_comp["returning"], label="Powracający", color="#4C72B0")
ax.bar(x, q_comp["newcomers"], bottom=q_comp["returning"],
       label="Nowicjusze", color="#DD8452")
ax.set_xticks(list(x))
ax.set_xticklabels(q_comp["label"], rotation=45, ha="right")
ax.set_ylabel("Zawodnicy")
ax.set_title(f"Nowicjusze vs powracający zawodnicy per kwartał ({period_label})")
ax.legend()
plt.tight_layout()
fig.savefig(OUT / f"6_new_vs_returning_per_quarter{file_suffix}.png", dpi=150)
plt.close()

# ── 3. Share of newcomers in total competitors per quarter ───────────────────
q_comp["pct_new"] = q_comp["newcomers"] / (q_comp["newcomers"] + q_comp["returning"]) * 100

fig, ax = plt.subplots(figsize=(14, 4))
ax.plot(list(x), q_comp["pct_new"], marker="o", color="#DD8452")
ax.axhline(q_comp["pct_new"].mean(), linestyle="--", color="gray",
           label=f"Średnia {q_comp['pct_new'].mean():.1f}%")
ax.set_xticks(list(x))
ax.set_xticklabels(q_comp["label"], rotation=45, ha="right")
ax.set_ylabel("% nowicjuszy")
ax.set_ylim(0, 100)
ax.set_title(f"Udział nowicjuszy w łącznej liczbie zawodników per kwartał ({period_label})")
ax.legend()
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
fig.savefig(OUT / f"7_pct_newcomers_per_quarter{file_suffix}.png", dpi=150)
plt.close()

# ── 4. Distribution of starts per person per year ────────────────────────────
comps_per_person = (
    att.groupby(["person_id", "year"])["competition_id"]
    .nunique()
    .reset_index(name="n_comps")
)
years = sorted(comps_per_person["year"].unique())
n = len(years)
ncols = min(n, 6)
nrows = (n + ncols - 1) // ncols

fig, axes_grid = plt.subplots(nrows, ncols,
                               figsize=(4 * ncols, 4 * nrows),
                               sharey=False, squeeze=False)
axes_flat = axes_grid.flatten()
for i, yr in enumerate(years):
    ax = axes_flat[i]
    data = comps_per_person[comps_per_person.year == yr]["n_comps"]
    max_bin = min(data.max() + 2, 21)
    ax.hist(data, bins=range(1, max_bin), color="#4C72B0", edgecolor="white", align="left")
    med = data.median()
    ax.axvline(med, color="red", linestyle="--", label=f"Med: {med:.1f}")
    ax.set_title(str(yr))
    ax.set_xlabel("Starty")
    ax.set_ylabel("Zawodnicy")
    ax.legend(fontsize=8)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
for ax in axes_flat[n:]:
    ax.set_visible(False)
fig.suptitle(f"Rozkład liczby startów per zawodnik per rok ({period_label})", y=1.02)
plt.tight_layout()
fig.savefig(OUT / f"8_starts_per_person_per_year{file_suffix}.png", dpi=150, bbox_inches="tight")
plt.close()

# ── 5. Consistently active: competed in 3+ quarters in a year ────────────────
quarters_active = (
    att.groupby(["person_id", "year"])["quarter"]
    .nunique()
    .reset_index(name="quarters_active")
)
active = (
    quarters_active[quarters_active.quarters_active >= 3]
    .groupby("year")
    .size()
    .reset_index(name="n")
)

fig, ax = plt.subplots(figsize=(max(8, len(years) * 0.6), 4))
ax.bar(active["year"].astype(str), active["n"], color="#C44E52")
ax.set_xlabel("Rok")
ax.set_ylabel("Zawodnicy")
ax.set_title(f"Zawodnicy aktywni w 3+ kwartałach danego roku ({period_label})")
ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
fig.savefig(OUT / f"9_consistently_active_per_year{file_suffix}.png", dpi=150)
plt.close()

# ── 6. Median starts per year – trend ────────────────────────────────────────
med_trend = comps_per_person.groupby("year")["n_comps"].agg(
    mean="mean", median="median", q75=lambda x: x.quantile(0.75)
).reset_index()

fig, ax = plt.subplots(figsize=(max(8, len(years) * 0.6), 4))
ax.plot(med_trend["year"].astype(str), med_trend["mean"],   marker="o", label="Średnia")
ax.plot(med_trend["year"].astype(str), med_trend["median"], marker="s", linestyle="--", label="Mediana")
ax.plot(med_trend["year"].astype(str), med_trend["q75"],    marker="^", linestyle=":", label="75 percentyl")
ax.set_xlabel("Rok")
ax.set_ylabel("Starty per zawodnik")
ax.set_title(f"Aktywność zawodników w Polsce per rok ({period_label})")
ax.legend()
ax.grid(axis="y", alpha=0.3)
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
fig.savefig(OUT / f"10_activity_trend_per_year{file_suffix}.png", dpi=150)
plt.close()

print(f"Saved: 5–10 ({period_label})")
