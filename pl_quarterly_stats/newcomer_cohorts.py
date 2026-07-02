"""
Newcomers and retention: newcomer counts per quarter, cohort analysis
(% returning within 3/6/12 months), distribution of return counts.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
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

# People whose global WCA debut took place at a Polish competition in the period
debuts = (
    att[att.is_newcomer][["person_id", "competition_id", "date", "year", "quarter"]]
    .drop_duplicates("person_id")
    .rename(columns={"date": "debut_date", "year": "debut_year", "quarter": "debut_quarter"})
)

# ── 1. Newcomers per quarter ─────────────────────────────────────────────────
q_new = (
    debuts.groupby(["debut_year", "debut_quarter"])
    .size()
    .reset_index(name="newcomers")
)
q_new["label"] = q_new["debut_year"].astype(str) + " Q" + q_new["debut_quarter"].astype(str)

fig, ax = plt.subplots(figsize=(14, 5))
ax.bar(q_new["label"], q_new["newcomers"], color="#DD8452")
ax.set_xlabel("Kwartał debiutu")
ax.set_ylabel("Nowicjusze")
ax.set_title(f"Nowicjusze WCA w Polsce per kwartał – osoby debiutujące ({period_label})")
ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
fig.savefig(OUT / f"11_newcomers_per_quarter{file_suffix}.png", dpi=150)
plt.close()

# ── 2. Newcomers per month – years overlaid ──────────────────────────────────
n_years = comps_pl["year"].nunique()
debuts_with_month = att[att.is_newcomer][["person_id", "year", "month"]].drop_duplicates("person_id")

fig, ax = plt.subplots(figsize=(12, 5))
for year, grp in debuts_with_month.groupby("year"):
    monthly = grp.groupby("month").size().reindex(range(1, 13), fill_value=0)
    ax.plot(monthly.index, monthly.values, marker="o",
            label=str(year), color=YEAR_COLORS.get(year))
ax.set_xticks(range(1, 13))
ax.set_xticklabels(MONTHS_PL)
ax.set_xlabel("Miesiąc")
ax.set_ylabel("Nowicjusze")
ax.set_title(f"Nowicjusze WCA w Polsce per miesiąc ({period_label})")
ax.legend(title="Rok", ncol=max(1, n_years // 10))
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
fig.savefig(OUT / f"12_newcomers_per_month_overlay{file_suffix}.png", dpi=150)
plt.close()

# ── 3. Cohort analysis – retention ───────────────────────────────────────────
followup = (
    att[att.person_id.isin(debuts.person_id)]
    .merge(debuts[["person_id", "debut_date", "debut_year", "debut_quarter"]], on="person_id")
)
followup["days_after"] = (followup["date"] - followup["debut_date"]).dt.days

retention_rows = []
for (yr, qt), cohort_debuts in debuts.groupby(["debut_year", "debut_quarter"]):
    n_total = len(cohort_debuts)
    pids = cohort_debuts.person_id
    cohort_fu = followup[
        (followup.person_id.isin(pids)) & (followup.days_after > 0)
    ]
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
ax.set_xlabel("Kwartał debiutu")
ax.set_ylabel("% nowicjuszy którzy wrócili")
ax.set_ylim(0, 100)
ax.set_title(f"Retencja nowicjuszy – % którzy wrócili na polskie zawody ({period_label})")
plt.xticks(rotation=45, ha="right")
ax.legend()
ax.grid(axis="y", alpha=0.3)
ax.annotate(
    "⚠ Ostatnie kohorty mogą mieć niekompletne dane retencji 12m",
    xy=(0.99, 0.02), xycoords="axes fraction", ha="right", fontsize=8, color="gray",
)
plt.tight_layout()
fig.savefig(OUT / f"13_newcomer_retention_pct{file_suffix}.png", dpi=150)
plt.close()

fig, ax = plt.subplots(figsize=(14, 5))
x = range(len(ret))
w = 0.25
ax.bar([i - w for i in x], ret["ret_3m"],  width=w, label="Wróciło w 3m",  color="#4C72B0")
ax.bar([i      for i in x], ret["ret_6m"],  width=w, label="Wróciło w 6m",  color="#55A868")
ax.bar([i + w for i in x], ret["ret_12m"], width=w, label="Wróciło w 12m", color="#8172B2")
ax.plot(x, ret["newcomers"], marker="o", color="black", linestyle="--", label="Łącznie nowicjuszy")
ax.set_xticks(list(x))
ax.set_xticklabels(ret["label"], rotation=45, ha="right")
ax.set_ylabel("Zawodnicy")
ax.set_title(f"Retencja nowicjuszy per kwartał – liczby bezwzględne ({period_label})")
ax.legend()
plt.tight_layout()
fig.savefig(OUT / f"14_newcomer_retention_abs{file_suffix}.png", dpi=150)
plt.close()

# ── 4. Distribution of return count per newcomer ─────────────────────────────
return_counts = (
    followup[followup.days_after > 0]
    .drop_duplicates(["person_id", "competition_id"])
    .groupby("person_id")["competition_id"]
    .count()
    .reset_index(name="returns")
)
never = pd.DataFrame({
    "person_id": list(set(debuts.person_id) - set(return_counts.person_id)),
    "returns": 0,
})
all_returns = pd.concat([return_counts, never], ignore_index=True)

n_never = (all_returns["returns"] == 0).sum()
n_total = len(all_returns)

fig, ax = plt.subplots(figsize=(10, 4))
max_bin = min(all_returns["returns"].max() + 2, 26)
ax.hist(all_returns["returns"], bins=range(0, max_bin),
        color="#8172B2", edgecolor="white", align="left")
ax.axvline(0.5, color="red", linestyle="--", alpha=0.6)
ax.set_xlabel("Liczba kolejnych zawodów w Polsce po debiucie")
ax.set_ylabel("Zawodnicy")
ax.set_title(
    f"Ile razy wrócili nowicjusze? ({period_label})\n"
    f"Nigdy nie wróciło: {n_never} / {n_total} ({n_never/n_total*100:.1f}%)"
)
ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
plt.tight_layout()
fig.savefig(OUT / f"15_newcomer_return_distribution{file_suffix}.png", dpi=150)
plt.close()

# ── 5. CSV cohort summary ─────────────────────────────────────────────────────
ret.to_csv(OUT / f"newcomer_cohort_summary{file_suffix}.csv", index=False)

print(f"Saved: 11–15 + CSV ({period_label})")
