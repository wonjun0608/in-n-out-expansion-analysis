
from pathlib import Path
import pandas as pd
import geopandas as gpd
import requests

DATA_DIR = Path("data")
BOUNDARY_DIR = DATA_DIR / "boundaries"
OUTPUT_FILE = DATA_DIR / "restaurants_with_cities.csv"

STATE_FIPS = {
    "Missouri": "29",
    "Kansas": "20",
    "Illinois": "17",
    "Indiana": "18",
    "Ohio": "39",
    "Tennessee": "47",
    "North Carolina": "37",
    "South Carolina": "45",
    "Georgia": "13",
    "Arizona": "04",
    "Texas": "48",
    "California": "06",
    "Nevada": "32",
    "Utah": "49",
    "Colorado": "08",
    "Oregon": "41",
    "Washington": "53",
}


def download_boundary(state_fips):
    BOUNDARY_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"tl_2024_{state_fips}_place.zip"
    path = BOUNDARY_DIR / filename

    if path.exists():
        return path

    url = (
        "https://www2.census.gov/geo/tiger/TIGER2024/"
        f"PLACE/{filename}"
    )

    print(f"Downloading {filename}...")

    response = requests.get(url, timeout=120)
    response.raise_for_status()
    path.write_bytes(response.content)

    return path


def main():
    restaurants = pd.read_csv(
        DATA_DIR / "restaurants_osm.csv"
    )

    all_results = []

    for state, fips in STATE_FIPS.items():
        print(f"\nProcessing {state}...")

        subset = restaurants[
            restaurants["state_query"] == state
        ].copy()

        if subset.empty:
            continue

        boundary_file = download_boundary(fips)

        cities = gpd.read_file(boundary_file)
        cities = cities.to_crs("EPSG:4326")

        cities = cities[
            ["GEOID", "NAME", "geometry"]
        ].rename(columns={
            "GEOID": "place_geoid",
            "NAME": "census_city"
        })

        points = gpd.GeoDataFrame(
            subset,
            geometry=gpd.points_from_xy(
                subset["longitude"],
                subset["latitude"]
            ),
            crs="EPSG:4326"
        )

        matched = gpd.sjoin(
            points,
            cities,
            how="left",
            predicate="within"
        )

        matched = matched.drop(
            columns=["geometry", "index_right"]
        )

        all_results.append(matched)

        count = matched["place_geoid"].notna().sum()
        print(f"Matched: {count}/{len(matched)}")

    combined = pd.concat(
        all_results,
        ignore_index=True
    )

    combined.to_csv(OUTPUT_FILE, index=False)

    print("\n=== FINAL RESULTS ===")
    print("Total restaurants:", len(combined))
    print(
        "Matched:",
        combined["place_geoid"].notna().sum()
    )
    print(
        "Unmatched:",
        combined["place_geoid"].isna().sum()
    )
    print("Saved to:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
