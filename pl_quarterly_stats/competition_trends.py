"""
Competition counts and attendance: per quarter, per month (years overlaid),
mean/median competitors per competition.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from loader import load
from _period import parse_args, apply_filter, make_year_colors

OUT = Path(__file__).parent / "output"
OUT.mkdir(exist_ok=True)

MONTHS_PL = ["Sty", "Lut", "Mar", "Kwi", "Maj", "Cze",
             "Lip", "Sie", "Wrz", "Paź", "Lis", "Gru"]

args = parse_args()
print("Loading data…")
comps_pl, att, persons, first_comp = load()
comps_pl, att, period_label, file_suffix = apply_filter(comps_pl, att, args)
YEAR_COLORS = make_year_colors(comps_pl["year"].unique())
print(f"  Period: {period_label}  |  competitions: {len(comps_pl)}")

# ── 1. Competitions per quarter ──────────────────────────────────────────────
q = comps_pl.groupby(["year", "quarter"]).size().reset_index(name="n")
q["label"] = q["year"].astype(str) + " Q" + q["quarter"].astype(str)

fig, ax = plt.subplots(figsize=(14, 5))
ax.bar(q["label"], q["n"], color="#4C72B0")
ax.set_xlabel("Kwartał")
ax.set_ylabel("Liczba zawodów")
ax.set_title(f"Liczba zawodów WCA w Polsce per kwartał ({period_label})")
ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
fig.savefig(OUT / f"1_comps_per_quarter{file_suffix}.png", dpi=150)
plt.close()

# ── 2. Competitions per month – years overlaid ───────────────────────────────
n_years = comps_pl["year"].nunique()
fig, ax = plt.subplots(figsize=(12, 5))
for year, grp in comps_pl.groupby("year"):
    monthly = grp.groupby("month").size().reindex(range(1, 13), fill_value=0)
    ax.plot(monthly.index, monthly.values, marker="o",
            label=str(year), color=YEAR_COLORS.get(year))
ax.set_xticks(range(1, 13))
ax.set_xticklabels(MONTHS_PL)
ax.set_xlabel("Miesiąc")
ax.set_ylabel("Liczba zawodów")
ax.set_title(f"Liczba zawodów WCA w Polsce per miesiąc ({period_label})")
ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
ax.legend(title="Rok", ncol=max(1, n_years // 10))
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
fig.savefig(OUT / f"2_comps_per_month_overlay{file_suffix}.png", dpi=150)
plt.close()

# ── 3. Cumulative competition count per year (YTD) ───────────────────────────
fig, ax = plt.subplots(figsize=(12, 5))
for year, grp in comps_pl.groupby("year"):
    monthly = grp.groupby("month").size().reindex(range(1, 13), fill_value=0).cumsum()
    ax.plot(monthly.index, monthly.values, marker="o",
            label=str(year), color=YEAR_COLORS.get(year))
ax.set_xticks(range(1, 13))
ax.set_xticklabels(MONTHS_PL)
ax.set_xlabel("Miesiąc")
ax.set_ylabel("Łączna liczba zawodów (YTD)")
ax.set_title(f"Skumulowana liczba zawodów w Polsce – porównanie lat ({period_label})")
ax.legend(title="Rok", ncol=max(1, n_years // 10))
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
fig.savefig(OUT / f"3_comps_ytd_overlay{file_suffix}.png", dpi=150)
plt.close()

# ── 4. Mean/median attendance per competition per quarter ────────────────────
att_per_comp = (
    att.groupby("competition_id")["person_id"]
    .nunique()
    .reset_index(name="n_competitors")
    .merge(
        comps_pl[["id", "year", "quarter"]].rename(columns={"id": "competition_id"}),
        on="competition_id",
    )
)
q_att = (
    att_per_comp.groupby(["year", "quarter"])["n_competitors"]
    .agg(mean="mean", median="median")
    .reset_index()
)
q_att["label"] = q_att["year"].astype(str) + " Q" + q_att["quarter"].astype(str)

fig, ax = plt.subplots(figsize=(14, 5))
ax.plot(q_att["label"], q_att["mean"], marker="o", label="Średnia")
ax.plot(q_att["label"], q_att["median"], marker="s", linestyle="--", label="Mediana")
ax.set_xlabel("Kwartał")
ax.set_ylabel("Zawodnicy na zawodach")
ax.set_title(f"Średnia/mediana liczby zawodników na zawodach per kwartał ({period_label})")
plt.xticks(rotation=45, ha="right")
ax.legend()
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
fig.savefig(OUT / f"4_attendance_per_comp_quarter{file_suffix}.png", dpi=150)
plt.close()

print(f"Saved: 1–4 ({period_label})")
