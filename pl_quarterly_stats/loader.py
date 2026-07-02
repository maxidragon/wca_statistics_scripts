from pathlib import Path
import pandas as pd

DATA = Path(__file__).parent.parent / "wca-export"
COUNTRY = "Poland"


def load():
    comps = pd.read_csv(DATA / "WCA_export_competitions.tsv", sep="\t", low_memory=False)
    results = pd.read_csv(DATA / "WCA_export_results.tsv", sep="\t", low_memory=False)
    persons = pd.read_csv(DATA / "WCA_export_persons.tsv", sep="\t", low_memory=False)

    persons = (
        persons[persons.sub_id == 1][["wca_id", "name", "country_id"]]
        .rename(columns={"wca_id": "person_id", "country_id": "person_country"})
    )

    comps["date"] = pd.to_datetime(
        dict(year=comps.year, month=comps.month, day=comps.day)
    )

    comps_pl = comps[
        (comps.country_id == COUNTRY)
        & (comps.cancelled == 0)
    ].copy()
    comps_pl["quarter"] = ((comps_pl["month"] - 1) // 3 + 1).astype(int)

    # First WCA competition ever for each person (globally, all history)
    comp_dates = comps[["id", "date"]].rename(columns={"id": "competition_id"})
    first_comp = (
        results[["competition_id", "person_id"]]
        .drop_duplicates()
        .merge(comp_dates, on="competition_id")
        .groupby("person_id")["date"]
        .min()
        .reset_index()
        .rename(columns={"date": "first_comp_date"})
    )

    att = (
        results[results.competition_id.isin(comps_pl.id)][
            ["competition_id", "person_id", "person_country_id"]
        ]
        .drop_duplicates(["competition_id", "person_id"])
        .merge(
            comps_pl[
                [
                    "id", "date", "year", "month", "quarter",
                    "city_name", "latitude_microdegrees", "longitude_microdegrees",
                ]
            ].rename(columns={"id": "competition_id"}),
            on="competition_id",
        )
        .merge(first_comp, on="person_id")
    )
    att["is_newcomer"] = att["date"] == att["first_comp_date"]

    return comps_pl, att, persons, first_comp
