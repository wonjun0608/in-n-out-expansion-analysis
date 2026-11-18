
from pathlib import Path
import pandas as pd

DATA_DIR = Path("data")

CENSUS_FILE = DATA_DIR / "census_places_2024.csv"
RESTAURANTS_FILE = DATA_DIR / "restaurants_with_cities.csv"
OUTPUT_FILE = DATA_DIR / "city_analysis.csv"


def main():
    # Load Census and restaurant datasets.
    census = pd.read_csv(
        CENSUS_FILE,
        dtype={"place_geoid": str}
    )

    restaurants = pd.read_csv(
        RESTAURANTS_FILE,
        dtype={"place_geoid": str}
    )

    # Keep restaurants that were matched to a Census place.
    matched = restaurants.dropna(
        subset=["place_geoid"]
    ).copy()

    # Count restaurants by city and brand.
    counts = (
        matched.groupby(["place_geoid", "brand"])
        .size()
        .unstack(fill_value=0)
    )

    # Make brand columns easier to identify.
    counts.columns = [
        "restaurants_" + name.lower()
        .replace("'", "")
        .replace("-", "_")
        .replace(" ", "_")
        for name in counts.columns
    ]

    counts = counts.reset_index()

    # Join restaurant counts with Census demographics.
    cities = census.merge(
        counts,
        on="place_geoid",
        how="left",
        validate="one_to_one"
    )

    restaurant_columns = [
        col for col in cities.columns
        if col.startswith("restaurants_")
    ]

    cities[restaurant_columns] = (
        cities[restaurant_columns]
        .fillna(0)
        .astype(int)
    )

    # Total number of tracked restaurants in each city.
    cities["total_restaurants"] = (
        cities[restaurant_columns].sum(axis=1)
    )

    # Save the analysis dataset.
    cities.to_csv(OUTPUT_FILE, index=False)

    print("=== CITY ANALYSIS ===")
    print("Total Census places:", len(cities))
    print(
        "Cities with tracked restaurants:",
        (cities["total_restaurants"] > 0).sum()
    )

    print("\nSample:")
    print(
        cities[
            [
                "city_state",
                "population",
                "median_household_income",
                "total_restaurants"
            ]
        ].head(10)
    )

    print("\nSaved to:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
