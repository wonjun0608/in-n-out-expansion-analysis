
"""Download US place demographics and restaurant POIs.
In-N-Out Expansion Project
Run:
    python collect_data.py
"""

from pathlib import Path
import os
import time

import requests
import pandas as pd


# --------------------------------------------------
# Configuration
# --------------------------------------------------

OUT = Path(__file__).parent / "data"
OUT.mkdir(exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "CSE3104-student-project/1.0 (educational data collection)"
})

CENSUS_API_KEY = os.environ.get("CENSUS_API_KEY")

if not CENSUS_API_KEY:
    raise RuntimeError(
        "CENSUS_API_KEY is missing. "
        "Set it in your terminal before running this script."
    )


# --------------------------------------------------
# 1. Census Data Collection
# --------------------------------------------------

def fetch_census(year):
    """
    Download population and median household income
    for US places from the Census ACS 5-year API.
    """

    url = f"https://api.census.gov/data/{year}/acs/acs5"

    params = {
        "get": "NAME,B01003_001E,B19013_001E",
        "for": "place:*",
        "in": "state:*",
        "key": CENSUS_API_KEY
    }

    print(f"\nDownloading Census data for {year}...")

    response = SESSION.get(
        url,
        params=params,
        timeout=90
    )

    response.raise_for_status()

    # Check whether the Census API returned JSON.
    content_type = response.headers.get("Content-Type", "")

    if "json" not in content_type.lower():
        raise RuntimeError(
            f"Census API did not return JSON for {year}.\n"
            f"Final URL: {response.url.split('?')[0]}\n"
            f"Response: {response.text[:300]}"
        )

    rows = response.json()

    if not isinstance(rows, list) or len(rows) < 2:
        raise RuntimeError(
            f"Unexpected Census API response for {year}"
        )

    # Convert JSON response into a DataFrame.
    df = pd.DataFrame(
        rows[1:],
        columns=rows[0]
    )

    # Rename columns.
    df = df.rename(columns={
        "NAME": "city_state",
        "B01003_001E": "population",
        "B19013_001E": "median_household_income",
        "state": "state_fips",
        "place": "place_fips"
    })

    # Convert numeric columns.
    for col in ["population", "median_household_income"]:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

        # Census negative values can represent missing data.
        df.loc[df[col] < 0, col] = pd.NA

    # Add year.
    df.insert(0, "year", year)

    # Create unique geographic identifier.
    df["place_geoid"] = (
        df["state_fips"] + df["place_fips"]
    )

    # Save CSV.
    output_file = OUT / f"census_places_{year}.csv"

    df.to_csv(
        output_file,
        index=False
    )

    print(f"Census {year}: {len(df):,} places")
    print(f"Saved to: {output_file}")

    return df


# --------------------------------------------------
# 2. OpenStreetMap Restaurant Collection
# --------------------------------------------------

def fetch_restaurants():
    """
    Download fast-food restaurant locations
    from OpenStreetMap using the Overpass API.
    """

    states = [
        "Missouri",
    ]

    pattern = (
        "In-N-Out|McDonald|Five Guys|Shake Shack|"
        "Whataburger|Culver|Freddy|Steak.n.Shake"
    )

    records = []

    for state in states:

        print(f"\nDownloading restaurants in {state}...")

        query = """
        [out:json][timeout:60];

        (
            nwr["amenity"="fast_food"]
            ["name"~"McDonald",i]
            (38.55,-90.35,38.70,-90.15);
        );

        out center tags;
        """

        try:
            response = SESSION.post(
            "https://overpass.private.coffee/api/interpreter",
            data={"data": query},
            timeout=180
        )

            response.raise_for_status()

            data = response.json()

            for obj in data.get("elements", []):

                tags = obj.get("tags", {})

                center = obj.get("center", obj)

                records.append({
                    "osm_type": obj["type"],
                    "osm_id": obj["id"],
                    "name": tags.get("name"),
                    "brand": tags.get("brand"),
                    "state_query": state,
                    "latitude": center.get("lat"),
                    "longitude": center.get("lon"),
                    "city": tags.get("addr:city"),
                    "street": tags.get("addr:street"),
                    "postcode": tags.get("addr:postcode")
                })

            print(
                f"OSM {state}: downloaded; "
                f"running total {len(records):,}"
            )

        except (requests.RequestException, ValueError) as exc:
            print(f"WARNING: {state} failed: {exc}")

        # Avoid overwhelming the public API.
        time.sleep(3)

    # Convert records into DataFrame.
    df = pd.DataFrame(
        records,
        columns=[
            "osm_type",
            "osm_id",
            "name",
            "brand",
            "state_query",
            "latitude",
            "longitude",
            "city",
            "street",
            "postcode"
        ]
    )

    # Remove duplicate OSM objects.
    df = df.drop_duplicates(
        subset=["osm_type", "osm_id"]
    )

    # Save CSV.
    output_file = OUT / "restaurants_osm.csv"

    df.to_csv(
        output_file,
        index=False
    )

    print(
        f"\nOSM total: {len(df):,} "
        "restaurant features"
    )

    print(f"Saved to: {output_file}")

    return df


# --------------------------------------------------
# 3. Main
# --------------------------------------------------

def main():
    print("=" * 50)
    print("CSE 3104 - In-N-Out Expansion Project")
    print("=" * 50)

    # Census 2024 already downloaded
    # fetch_census(2024)

    # Temporarily skip 2023 due to API error
    # fetch_census(2023)

    # Download restaurant locations
    fetch_restaurants()

    print("\nData collection completed!")
    print(f"Output directory: {OUT}")


if __name__ == "__main__":
    main()
