
from pathlib import Path
import sqlite3
import pandas as pd

DATA_DIR = Path("data")
DB_FILE = DATA_DIR / "in_n_out.db"

STATE_FIPS = {
    "29", "20", "17", "18", "39", "47",
    "37", "45", "13", "04", "48", "06",
    "32", "49", "08", "41", "53"
}


def main():
    cities = pd.read_csv(
        DATA_DIR / "city_analysis.csv",
        dtype={"place_geoid": str, "state_fips": str}
    )

    restaurants = pd.read_csv(
        DATA_DIR / "restaurants_with_cities.csv",
        dtype={"place_geoid": str}
    )

    # Restrict the analysis to our 17 collected states.
    cities["state_fips"] = cities["state_fips"].str.zfill(2)
    cities = cities[
        cities["state_fips"].isin(STATE_FIPS)
    ].copy()

    # Keep only restaurants with matched Census places.
    matched_restaurants = restaurants.dropna(
        subset=["place_geoid"]
    ).copy()

    # Create a separate table for restaurant brands.
    chains = pd.DataFrame({
        "brand": sorted(restaurants["brand"].dropna().unique())
    })
    chains.insert(0, "chain_id", range(1, len(chains) + 1))

    matched_restaurants = matched_restaurants.merge(
        chains, on="brand", how="left", validate="many_to_one"
    )

    with sqlite3.connect(DB_FILE) as conn:
        cities.to_sql(
            "cities", conn, if_exists="replace", index=False
        )

        chains.to_sql(
            "chains", conn, if_exists="replace", index=False
        )

        matched_restaurants.to_sql(
            "restaurants", conn, if_exists="replace", index=False
        )

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cities_geoid "
            "ON cities(place_geoid)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_restaurants_geoid "
            "ON restaurants(place_geoid)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_restaurants_chain "
            "ON restaurants(chain_id)"
        )

        for table in ["cities", "chains", "restaurants"]:
            count = conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
            print(f"{table}: {count} rows")

    print(f"\nDatabase saved to: {DB_FILE}")


if __name__ == "__main__":
    main()
