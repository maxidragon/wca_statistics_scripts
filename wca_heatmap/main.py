from pathlib import Path
import numpy as np
import pandas as pd
import folium
from folium.plugins import HeatMap
from sklearn.cluster import DBSCAN

DATA = Path(__file__).parent.parent / "wca-export"
YEAR = 2025
COUNTRY = "Poland"

# --- wczytanie ---
comps   = pd.read_csv(DATA / "WCA_export_competitions.tsv", sep="\t", low_memory=False)
results = pd.read_csv(DATA / "WCA_export_results.tsv",      sep="\t", low_memory=False)
persons = pd.read_csv(DATA / "WCA_export_persons.tsv",      sep="\t", low_memory=False)

# Persons.subid=1 to aktualny rekord
persons = persons[persons.sub_id == 1][["wca_id", "name", "country_id"]] \
            .rename(columns={"wca_id": "person_id", "country_id": "person_country"})

pl_comps = comps[
    (comps.country_id == COUNTRY) &
    (comps.year       == YEAR)    &
    (comps.cancelled  == 0)       &
    (comps.latitude_microdegrees.notna()) & (comps.longitude_microdegrees.notna())
].copy()
pl_comps["lat"] = pl_comps["latitude_microdegrees"]  / 1e6
pl_comps["lon"] = pl_comps["longitude_microdegrees"] / 1e6
pl_comps = pl_comps[["id", "cell_name", "city_name", "lat", "lon"]] \
             .rename(columns={"id": "competition_id"})

att = (results[results.competition_id.isin(pl_comps.competition_id)]
       [["competition_id", "person_id"]]
       .drop_duplicates()
       .merge(pl_comps, on="competition_id")
       .merge(persons,  on="person_id"))

print(f"Zawody: {pl_comps.shape[0]}, starty: {att.shape[0]}, "
      f"unikalnych zawodników: {att.person_id.nunique()}")

# =================== WARIANT 1 ===================
v1 = (att.groupby(["competition_id", "cell_name", "lat", "lon"])
         .person_id.nunique().reset_index(name="n"))

m1 = folium.Map(location=[52.0, 19.3], zoom_start=6, tiles="cartodbpositron")
HeatMap(v1[["lat", "lon", "n"]].values.tolist(), radius=28, blur=22).add_to(m1)
for _, r in v1.iterrows():
    folium.CircleMarker([r.lat, r.lon], radius=3, color="#333",
        popup=f"{r.cell_name}: {r.n}").add_to(m1)
m1.save(Path(__file__).parent / "heatmap_v1_sumarycznie.html")

# =================== WARIANT 2 ===================
att_pl = att[att.person_country == COUNTRY].copy()

def max_pairwise_km(lats, lons):
    if len(lats) < 2: return 0.0
    lat = np.radians(lats); lon = np.radians(lons)
    dlat = lat[:, None] - lat[None, :]
    dlon = lon[:, None] - lon[None, :]
    a = np.sin(dlat/2)**2 + np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin(dlon/2)**2
    return float(6371.0 * 2 * np.arcsin(np.sqrt(a)).max())

coords_rad = np.radians(pl_comps[["lat", "lon"]].values)
labels = DBSCAN(eps=50/6371.0, min_samples=1, metric="haversine").fit_predict(coords_rad)
pl_comps["region"] = labels
att_pl = att_pl.merge(pl_comps[["competition_id", "region"]], on="competition_id")

person_stats = (att_pl.groupby("person_id")
                .apply(lambda g: pd.Series({
                    "n_starts":  len(g),
                    "n_regions": g.region.nunique(),
                    "spread_km": max_pairwise_km(g.lat.values, g.lon.values),
                }))
                .reset_index())

MAX_SPREAD_KM = 250
MAX_REGIONS   = 3

locals_ids = person_stats[
    (person_stats.spread_km <= MAX_SPREAD_KM) &
    (person_stats.n_regions <= MAX_REGIONS)
].person_id

print(f"Lokalsi: {len(locals_ids)} / {len(person_stats)} "
      f"(odsianych {len(person_stats) - len(locals_ids)})")
print("Top 10 globtroterów wg spread:")
print(person_stats.sort_values("spread_km", ascending=False)
      .merge(persons, on="person_id").head(10)[["name", "n_starts", "n_regions", "spread_km"]])

att_locals = att_pl[att_pl.person_id.isin(locals_ids)]

v2 = (att_locals.groupby(["competition_id", "cell_name", "lat", "lon"])
                .person_id.nunique().reset_index(name="n"))

m2 = folium.Map(location=[52.0, 19.3], zoom_start=6, tiles="cartodbpositron")
HeatMap(v2[["lat", "lon", "n"]].values.tolist(), radius=28, blur=22).add_to(m2)
for _, r in v2.iterrows():
    folium.CircleMarker([r.lat, r.lon], radius=3, color="#333",
        popup=f"{r.cell_name}: {r.n}").add_to(m2)
m2.save(Path(__file__).parent / "heatmap_v2_lokalsi.html")

region_centroids = (pl_comps.groupby("region")[["lat", "lon"]].mean().reset_index())
v2_reg = (att_locals.groupby("region").person_id.nunique()
          .reset_index(name="n").merge(region_centroids, on="region"))
print("\nUnikalni lokalsi per region:")
print(v2_reg.sort_values("n", ascending=False))
