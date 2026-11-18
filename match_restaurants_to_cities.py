
from pathlib import Path
import pandas as pd
import geopandas as gpd

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

RESTAURANTS_FILE = DATA_DIR / "restaurants_osm.csv"
BOUNDARY_FILE = DATA_DIR / "boundaries/tl_2024_29_place.zip"
OUTPUT_FILE = DATA_DIR / "missouri_restaurants_matched.csv"


def main():
    # Load only Missouri restaurants.
    restaurants = pd.read_csv(RESTAURANTS_FILE)
    restaurants = restaurants[
        restaurants["state_query"] == "Missouri"
    ].copy()

    print(f"Missouri restaurants: {len(restaurants)}")

    # Convert latitude/longitude to geographic points.
    points = gpd.GeoDataFrame(
        restaurants,
        geometry=gpd.points_from_xy(
            restaurants["longitude"],
            restaurants["latitude"]
        ),
        crs="EPSG:4326"
    )

    # Load Census place boundaries.
    cities = gpd.read_file(BOUNDARY_FILE)

    # Ensure both datasets use the same coordinate system.
    cities = cities.to_crs(points.crs)

    cities = cities[
        ["GEOID", "NAME", "geometry"]
    ].rename(columns={
        "GEOID": "place_geoid",
        "NAME": "census_city"
    })

    # Match each restaurant to the Census place containing it.
    matched = gpd.sjoin(
        points,
        cities,
        how="left",
        predicate="within"
    )

    matched = matched.drop(
        columns=["geometry", "index_right"]
    )

    matched.to_csv(OUTPUT_FILE, index=False)

    print(f"Total restaurants: {len(matched)}")
    print(
        "Matched to Census places:",
        matched["place_geoid"].notna().sum()
    )
    print(
        "Unmatched:",
        matched["place_geoid"].isna().sum()
    )

    print("\nSample results:")
    print(
        matched[
            ["name", "brand", "census_city", "place_geoid"]
        ].head(10)
    )

    print(f"\nSaved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
