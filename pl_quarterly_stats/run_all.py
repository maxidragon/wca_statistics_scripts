"""
Runs all analyses in one go, loading data once (faster than running scripts separately).

Usage:
  python run_all.py                # all time (from 2005)
  python run_all.py --last 5       # last 5 years
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import matplotlib
matplotlib.use("Agg")

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


def quarter_labels(df, year_col="year", quarter_col="quarter"):
    return df[year_col].astype(str) + " Q" + df[quarter_col].astype(str)


def save(name, suffix, bbox="tight" if False else None):
    path = OUT / f"{name}{suffix}.png"
    plt.savefig(path, dpi=150, bbox_inches=bbox)
    plt.close()


args = parse_args()
print("Loading data (this may take a moment)…")
comps_pl, att, persons, first_comp = load()
comps_pl, att, period_label, file_suffix = apply_filter(comps_pl, att, args)
YEAR_COLORS = make_year_colors(comps_pl["year"].unique())
n_years = comps_pl["year"].nunique()

print(f"  Period: {period_label}")
print(f"  Poland competitions: {len(comps_pl)}")
print(f"  Attendance records:  {len(att)}")

# ═══════════════════════════════════════════════════════════════════════════════
# COMPETITION TRENDS
# ═══════════════════════════════════════════════════════════════════════════════

q = comps_pl.groupby(["year", "quarter"]).size().reset_index(name="n")
q["label"] = quarter_labels(q)

fig, ax = plt.subplots(figsize=(14, 5))
ax.bar(q["label"], q["n"], color="#4C72B0")
ax.set(xlabel="Kwartał", ylabel="Liczba zawodów",
       title=f"Liczba zawodów WCA w Polsce per kwartał ({period_label})")
ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
plt.xticks(rotation=45, ha="right"); plt.tight_layout()
plt.savefig(OUT / f"1_comps_per_quarter{file_suffix}.png", dpi=150); plt.close()

fig, ax = plt.subplots(figsize=(12, 5))
for year, grp in comps_pl.groupby("year"):
    monthly = grp.groupby("month").size().reindex(range(1, 13), fill_value=0)
    ax.plot(monthly.index, monthly.values, marker="o",
            label=str(year), color=YEAR_COLORS.get(year))
ax.set_xticks(range(1, 13)); ax.set_xticklabels(MONTHS_PL)
ax.set(xlabel="Miesiąc", ylabel="Liczba zawodów",
       title=f"Liczba zawodów WCA w Polsce per miesiąc ({period_label})")
ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
ax.legend(title="Rok", ncol=max(1, n_years // 10))
ax.grid(axis="y", alpha=0.3); plt.tight_layout()
plt.savefig(OUT / f"2_comps_per_month_overlay{file_suffix}.png", dpi=150); plt.close()

fig, ax = plt.subplots(figsize=(12, 5))
for year, grp in comps_pl.groupby("year"):
    monthly = grp.groupby("month").size().reindex(range(1, 13), fill_value=0).cumsum()
    ax.plot(monthly.index, monthly.values, marker="o",
            label=str(year), color=YEAR_COLORS.get(year))
ax.set_xticks(range(1, 13)); ax.set_xticklabels(MONTHS_PL)
ax.set(xlabel="Miesiąc", ylabel="Łączna liczba zawodów (YTD)",
       title=f"Skumulowana liczba zawodów w Polsce – porównanie lat ({period_label})")
ax.legend(title="Rok", ncol=max(1, n_years // 10))
ax.grid(axis="y", alpha=0.3); plt.tight_layout()
plt.savefig(OUT / f"3_comps_ytd_overlay{file_suffix}.png", dpi=150); plt.close()

att_per_comp = (
    att.groupby("competition_id")["person_id"].nunique().reset_index(name="n")
    .merge(comps_pl[["id", "year", "quarter"]].rename(columns={"id": "competition_id"}),
           on="competition_id")
)
q_att = att_per_comp.groupby(["year", "quarter"])["n"].agg(mean="mean", median="median").reset_index()
q_att["label"] = quarter_labels(q_att)

fig, ax = plt.subplots(figsize=(14, 5))
ax.plot(q_att["label"], q_att["mean"],   marker="o", label="Średnia")
ax.plot(q_att["label"], q_att["median"], marker="s", linestyle="--", label="Mediana")
ax.set(xlabel="Kwartał", ylabel="Zawodnicy na zawodach",
       title=f"Średnia/mediana liczby zawodników na zawodach per kwartał ({period_label})")
plt.xticks(rotation=45, ha="right"); ax.legend(); ax.grid(axis="y", alpha=0.3); plt.tight_layout()
plt.savefig(OUT / f"4_attendance_per_comp_quarter{file_suffix}.png", dpi=150); plt.close()
print("✓ competition_trends (1–4)")

# ═══════════════════════════════════════════════════════════════════════════════
# COMPETITOR ACTIVITY
# ═══════════════════════════════════════════════════════════════════════════════

q_uniq = att.groupby(["year", "quarter"])["person_id"].nunique().reset_index(name="n")
q_uniq["label"] = quarter_labels(q_uniq)

fig, ax = plt.subplots(figsize=(14, 5))
ax.bar(q_uniq["label"], q_uniq["n"], color="#55A868")
ax.set(xlabel="Kwartał", ylabel="Unikalni zawodnicy",
       title=f"Liczba unikalnych zawodników w Polsce per kwartał ({period_label})")
ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
plt.xticks(rotation=45, ha="right"); plt.tight_layout()
plt.savefig(OUT / f"5_unique_competitors_per_quarter{file_suffix}.png", dpi=150); plt.close()

q_new_c = att[att.is_newcomer].groupby(["year", "quarter"])["person_id"].nunique().reset_index(name="newcomers")
q_ret_c = att[~att.is_newcomer].groupby(["year", "quarter"])["person_id"].nunique().reset_index(name="returning")
q_comp = q_new_c.merge(q_ret_c, on=["year", "quarter"], how="outer").fillna(0).sort_values(["year", "quarter"])
q_comp["label"] = quarter_labels(q_comp)

fig, ax = plt.subplots(figsize=(14, 5))
x = range(len(q_comp))
ax.bar(x, q_comp["returning"], label="Powracający", color="#4C72B0")
ax.bar(x, q_comp["newcomers"], bottom=q_comp["returning"], label="Nowicjusze", color="#DD8452")
ax.set_xticks(list(x)); ax.set_xticklabels(q_comp["label"], rotation=45, ha="right")
ax.set(ylabel="Zawodnicy",
       title=f"Nowicjusze vs powracający zawodnicy per kwartał ({period_label})")
ax.legend(); plt.tight_layout()
plt.savefig(OUT / f"6_new_vs_returning_per_quarter{file_suffix}.png", dpi=150); plt.close()

q_comp["pct_new"] = q_comp["newcomers"] / (q_comp["newcomers"] + q_comp["returning"]) * 100
fig, ax = plt.subplots(figsize=(14, 4))
ax.plot(list(x), q_comp["pct_new"], marker="o", color="#DD8452")
ax.axhline(q_comp["pct_new"].mean(), linestyle="--", color="gray",
           label=f"Średnia {q_comp['pct_new'].mean():.1f}%")
ax.set_xticks(list(x)); ax.set_xticklabels(q_comp["label"], rotation=45, ha="right")
ax.set(ylabel="% nowicjuszy", ylim=(0, 100),
       title=f"Udział nowicjuszy w łącznej liczbie zawodników per kwartał ({period_label})")
ax.legend(); ax.grid(axis="y", alpha=0.3); plt.tight_layout()
plt.savefig(OUT / f"7_pct_newcomers_per_quarter{file_suffix}.png", dpi=150); plt.close()

comps_per_person = (att.groupby(["person_id", "year"])["competition_id"]
                    .nunique().reset_index(name="n_comps"))
years = sorted(comps_per_person["year"].unique())
n_yr = len(years)
ncols = min(n_yr, 6)
nrows = (n_yr + ncols - 1) // ncols
fig, axes_grid = plt.subplots(nrows, ncols, figsize=(4 * ncols, 4 * nrows),
                               sharey=False, squeeze=False)
axes_flat = axes_grid.flatten()
for i, yr in enumerate(years):
    ax = axes_flat[i]
    data = comps_per_person[comps_per_person.year == yr]["n_comps"]
    ax.hist(data, bins=range(1, min(data.max() + 2, 21)), color="#4C72B0",
            edgecolor="white", align="left")
    med = data.median()
    ax.axvline(med, color="red", linestyle="--", label=f"Med: {med:.1f}")
    ax.set(title=str(yr), xlabel="Starty", ylabel="Zawodnicy")
    ax.legend(fontsize=8); ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
for ax in axes_flat[n_yr:]:
    ax.set_visible(False)
fig.suptitle(f"Rozkład liczby startów per zawodnik per rok ({period_label})", y=1.02)
plt.tight_layout()
plt.savefig(OUT / f"8_starts_per_person_per_year{file_suffix}.png", dpi=150, bbox_inches="tight")
plt.close()

quarters_active = (att.groupby(["person_id", "year"])["quarter"].nunique()
                   .reset_index(name="q_active"))
active = (quarters_active[quarters_active.q_active >= 3].groupby("year").size()
          .reset_index(name="n"))
fig, ax = plt.subplots(figsize=(max(8, n_yr * 0.6), 4))
ax.bar(active["year"].astype(str), active["n"], color="#C44E52")
ax.set(xlabel="Rok", ylabel="Zawodnicy",
       title=f"Zawodnicy aktywni w 3+ kwartałach danego roku ({period_label})")
ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
plt.xticks(rotation=45, ha="right"); plt.tight_layout()
plt.savefig(OUT / f"9_consistently_active_per_year{file_suffix}.png", dpi=150); plt.close()

med_trend = comps_per_person.groupby("year")["n_comps"].agg(
    mean="mean", median="median", q75=lambda x: x.quantile(0.75)
).reset_index()
fig, ax = plt.subplots(figsize=(max(8, n_yr * 0.6), 4))
ax.plot(med_trend["year"].astype(str), med_trend["mean"],   marker="o", label="Średnia")
ax.plot(med_trend["year"].astype(str), med_trend["median"], marker="s", linestyle="--", label="Mediana")
ax.plot(med_trend["year"].astype(str), med_trend["q75"],    marker="^", linestyle=":", label="75 percentyl")
ax.set(xlabel="Rok", ylabel="Starty per zawodnik",
       title=f"Aktywność zawodników w Polsce per rok ({period_label})")
ax.legend(); ax.grid(axis="y", alpha=0.3)
plt.xticks(rotation=45, ha="right"); plt.tight_layout()
plt.savefig(OUT / f"10_activity_trend_per_year{file_suffix}.png", dpi=150); plt.close()
print("✓ competitor_activity (5–10)")

# ═══════════════════════════════════════════════════════════════════════════════
# NEWCOMERS AND COHORTS
# ═══════════════════════════════════════════════════════════════════════════════

debuts = (
    att[att.is_newcomer][["person_id", "competition_id", "date", "year", "month", "quarter"]]
    .drop_duplicates("person_id")
    .rename(columns={"date": "debut_date", "year": "debut_year",
                     "month": "debut_month", "quarter": "debut_quarter"})
)

q_new_d = debuts.groupby(["debut_year", "debut_quarter"]).size().reset_index(name="newcomers")
q_new_d["label"] = q_new_d["debut_year"].astype(str) + " Q" + q_new_d["debut_quarter"].astype(str)

fig, ax = plt.subplots(figsize=(14, 5))
ax.bar(q_new_d["label"], q_new_d["newcomers"], color="#DD8452")
ax.set(xlabel="Kwartał debiutu", ylabel="Nowicjusze",
       title=f"Nowicjusze WCA w Polsce per kwartał – osoby debiutujące ({period_label})")
ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
plt.xticks(rotation=45, ha="right"); plt.tight_layout()
plt.savefig(OUT / f"11_newcomers_per_quarter{file_suffix}.png", dpi=150); plt.close()

debuts_with_month = att[att.is_newcomer][["person_id", "year", "month"]].drop_duplicates("person_id")
fig, ax = plt.subplots(figsize=(12, 5))
for year, grp in debuts_with_month.groupby("year"):
    monthly = grp.groupby("month").size().reindex(range(1, 13), fill_value=0)
    ax.plot(monthly.index, monthly.values, marker="o", label=str(year), color=YEAR_COLORS.get(year))
ax.set_xticks(range(1, 13)); ax.set_xticklabels(MONTHS_PL)
ax.set(xlabel="Miesiąc", ylabel="Nowicjusze",
       title=f"Nowicjusze WCA w Polsce per miesiąc ({period_label})")
ax.legend(title="Rok", ncol=max(1, n_years // 10))
ax.grid(axis="y", alpha=0.3); plt.tight_layout()
plt.savefig(OUT / f"12_newcomers_per_month_overlay{file_suffix}.png", dpi=150); plt.close()

followup = (
    att[att.person_id.isin(debuts.person_id)]
    .merge(debuts[["person_id", "debut_date", "debut_year", "debut_quarter"]], on="person_id")
)
followup["days_after"] = (followup["date"] - followup["debut_date"]).dt.days

retention_rows = []
for (yr, qt), cohort_debuts in debuts.groupby(["debut_year", "debut_quarter"]):
    n_total = len(cohort_debuts)
    pids = set(cohort_debuts.person_id)
    cohort_fu = followup[(followup.person_id.isin(pids)) & (followup.days_after > 0)]
    row = {"year": yr, "quarter": qt, "newcomers": n_total}
    for days, key in [(90, "3m"), (180, "6m"), (365, "12m")]:
        returned = cohort_fu[cohort_fu.days_after <= days]["person_id"].nunique()
        row[f"ret_{key}"] = returned
        row[f"pct_{key}"] = round(returned / n_total * 100, 1) if n_total else 0.0
    retention_rows.append(row)
ret = pd.DataFrame(retention_rows).sort_values(["year", "quarter"])
ret["label"] = ret["year"].astype(str) + " Q" + ret["quarter"].astype(str)

fig, ax = plt.subplots(figsize=(14, 5))
ax.plot(ret["label"], ret["pct_3m"],  marker="o", label="w ciągu 3 miesięcy")
ax.plot(ret["label"], ret["pct_6m"],  marker="s", label="w ciągu 6 miesięcy")
ax.plot(ret["label"], ret["pct_12m"], marker="^", label="w ciągu 12 miesięcy")
ax.set(xlabel="Kwartał debiutu", ylabel="% nowicjuszy którzy wrócili",
       title=f"Retencja nowicjuszy – % którzy wrócili na polskie zawody ({period_label})",
       ylim=(0, 100))
plt.xticks(rotation=45, ha="right"); ax.legend(); ax.grid(axis="y", alpha=0.3)
ax.annotate("⚠ Ostatnie kohorty mogą mieć niekompletne dane retencji 12m",
            xy=(0.99, 0.02), xycoords="axes fraction", ha="right", fontsize=8, color="gray")
plt.tight_layout()
plt.savefig(OUT / f"13_newcomer_retention_pct{file_suffix}.png", dpi=150); plt.close()

fig, ax = plt.subplots(figsize=(14, 5))
x = range(len(ret)); w = 0.25
ax.bar([i - w for i in x], ret["ret_3m"],  width=w, label="Wróciło w 3m",  color="#4C72B0")
ax.bar([i      for i in x], ret["ret_6m"],  width=w, label="Wróciło w 6m",  color="#55A868")
ax.bar([i + w for i in x], ret["ret_12m"], width=w, label="Wróciło w 12m", color="#8172B2")
ax.plot(x, ret["newcomers"], marker="o", color="black", linestyle="--", label="Łącznie nowicjuszy")
ax.set_xticks(list(x)); ax.set_xticklabels(ret["label"], rotation=45, ha="right")
ax.set(ylabel="Zawodnicy",
       title=f"Retencja nowicjuszy per kwartał – liczby bezwzględne ({period_label})")
ax.legend(); plt.tight_layout()
plt.savefig(OUT / f"14_newcomer_retention_abs{file_suffix}.png", dpi=150); plt.close()

return_counts = (
    followup[followup.days_after > 0].drop_duplicates(["person_id", "competition_id"])
    .groupby("person_id")["competition_id"].count().reset_index(name="returns")
)
never = pd.DataFrame({
    "person_id": list(set(debuts.person_id) - set(return_counts.person_id)),
    "returns": 0,
})
all_returns = pd.concat([return_counts, never], ignore_index=True)
n_never = (all_returns["returns"] == 0).sum()
n_total_ret = len(all_returns)

fig, ax = plt.subplots(figsize=(10, 4))
ax.hist(all_returns["returns"], bins=range(0, min(all_returns["returns"].max() + 2, 26)),
        color="#8172B2", edgecolor="white", align="left")
ax.axvline(0.5, color="red", linestyle="--", alpha=0.6)
ax.set(xlabel="Liczba kolejnych zawodów w Polsce po debiucie", ylabel="Zawodnicy",
       title=f"Ile razy wrócili nowicjusze? ({period_label})\n"
             f"Nigdy nie wróciło: {n_never}/{n_total_ret} ({n_never/n_total_ret*100:.1f}%)")
ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True)); plt.tight_layout()
plt.savefig(OUT / f"15_newcomer_return_distribution{file_suffix}.png", dpi=150); plt.close()

ret.to_csv(OUT / f"newcomer_cohort_summary{file_suffix}.csv", index=False)
print("✓ newcomer_cohorts (11–15)")

# ═══════════════════════════════════════════════════════════════════════════════
# RECURRING COMPETITION SERIES
# ═══════════════════════════════════════════════════════════════════════════════

comps_pl["series_name"] = (
    comps_pl["name"]
    .str.replace(r"\b\d{4}\b", "", regex=True)
    .str.strip()
    .str.replace(r"\s+", " ", regex=True)
)

att_per_comp_rec = (
    att.groupby("competition_id")["person_id"]
    .nunique()
    .reset_index(name="n_competitors")
)
comps_with_att = (
    comps_pl[["id", "name", "series_name", "year", "month", "city_name"]]
    .rename(columns={"id": "competition_id"})
    .merge(att_per_comp_rec, on="competition_id", how="left")
)
comps_with_att["n_competitors"] = comps_with_att["n_competitors"].fillna(0).astype(int)

years_per_series = comps_with_att.groupby("series_name")["year"].nunique()
rec = comps_with_att[comps_with_att.series_name.isin(years_per_series[years_per_series >= 3].index)].copy()

typical_month_rec = rec.groupby("series_name")["month"].median().round().astype(int)

def label_with_month(name):
    m = typical_month_rec.get(name)
    return f"{name} ({MONTHS_PL[m - 1]})" if m else name

pivot_rec = (
    rec.pivot_table(index="series_name", columns="year",
                    values="n_competitors", aggfunc="sum")
    .fillna(0)
    .astype(int)
)
pivot_rec.index = [label_with_month(n) for n in pivot_rec.index]
sort_key = pd.DataFrame({
    "editions": (pivot_rec > 0).sum(axis=1),
    "total":    pivot_rec.sum(axis=1),
}, index=pivot_rec.index)
pivot_rec = pivot_rec.loc[sort_key.sort_values(["editions", "total"], ascending=False).index]

hm = pivot_rec.head(30)
max_val = hm.values.max()
n_cols_hm = len(hm.columns)
fig, ax = plt.subplots(figsize=(max(10, n_cols_hm * 0.7), max(6, len(hm) * 0.42)))
im = ax.imshow(hm.values, aspect="auto", cmap="YlOrRd", vmin=0)
for i in range(len(hm)):
    for j in range(n_cols_hm):
        v = hm.iloc[i, j]
        text = str(v) if v > 0 else "—"
        color = "white" if v > max_val * 0.65 else ("black" if v > 0 else "#bbbbbb")
        ax.text(j, i, text, ha="center", va="center", fontsize=7.5, color=color)
ax.set_xticks(range(n_cols_hm)); ax.set_xticklabels(hm.columns, rotation=45, ha="right")
ax.set_yticks(range(len(hm))); ax.set_yticklabels(hm.index, fontsize=8)
plt.colorbar(im, ax=ax, label="Zawodnicy", shrink=0.55)
ax.set_title(f"Cykliczne zawody WCA w Polsce – frekwencja per edycja ({period_label})\n"
             "(w nawiasie typowy miesiąc rozgrywania)")
plt.tight_layout()
plt.savefig(OUT / f"16_recurring_series_heatmap{file_suffix}.png", dpi=150); plt.close()

top10_rec = pivot_rec.head(10)
fig, ax = plt.subplots(figsize=(12, 5))
for series_label, row in top10_rec.iterrows():
    valid = row[row > 0]
    short = series_label if len(series_label) <= 38 else series_label[:35] + "..."
    ax.plot(valid.index, valid.values, marker="o", label=short)
ax.set(xlabel="Rok", ylabel="Zawodnicy",
       title=f"Frekwencja na cyklicznych zawodach – top serie ({period_label})")
ax.legend(fontsize=7.5, loc="upper left", bbox_to_anchor=(1, 1))
ax.grid(axis="y", alpha=0.3); ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
plt.tight_layout()
plt.savefig(OUT / f"17_recurring_series_trend{file_suffix}.png", dpi=150, bbox_inches="tight")
plt.close()
pivot_rec.reset_index().rename(columns={"series_name": "series"}).to_csv(
    OUT / f"recurring_series{file_suffix}.csv", index=False
)
print("✓ recurring_series (16–17)")

print(f"\nAll charts saved to: {OUT}")
