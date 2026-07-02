"""Shared CLI argument parsing and period-filtering helpers for all pl_quarterly_stats scripts."""
import argparse
import matplotlib.pyplot as plt


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--last", type=int, default=None, metavar="N",
        help="Last N years of Polish WCA data, e.g. --last 1, --last 5 (default: all time)",
    )
    args = p.parse_args()
    if args.last is not None and args.last < 1:
        p.error("--last must be a positive integer")
    return args


def apply_filter(comps_pl, att, args):
    """
    Optionally restrict comps_pl and att to the last N years.
    Returns (comps_pl, att, period_label, file_suffix).
    """
    if args.last is not None:
        max_year = int(comps_pl["year"].max())
        since = max_year - args.last + 1
        comps_pl = comps_pl[comps_pl["year"] >= since].copy()
        att = att[att["competition_id"].isin(comps_pl["id"])].copy()

    yr_min = int(comps_pl["year"].min())
    yr_max = int(comps_pl["year"].max())
    period_label = f"{yr_min}–{yr_max}"
    file_suffix = f"_last{args.last}y" if args.last is not None else "_all"

    return comps_pl, att, period_label, file_suffix


def make_year_colors(years):
    """Return a dict mapping each year to a distinct matplotlib color."""
    years = sorted(set(int(y) for y in years))
    palette = list(plt.cm.tab20.colors) if len(years) > 10 else list(plt.cm.tab10.colors)
    return {yr: palette[i % len(palette)] for i, yr in enumerate(years)}
