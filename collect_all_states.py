
from pathlib import Path
import csv
import re
import time

import requests
import osmium
import pandas as pd


BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OSM_DIR = DATA_DIR / "osm"
STATE_CSV_DIR = DATA_DIR / "state_csv"

OSM_DIR.mkdir(parents=True, exist_ok=True)
STATE_CSV_DIR.mkdir(parents=True, exist_ok=True)

STATES = {
    "Missouri": "missouri",
    "Kansas": "kansas",
    "Illinois": "illinois",
    "Indiana": "indiana",
    "Ohio": "ohio",
    "Tennessee": "tennessee",
    "North Carolina": "north-carolina",
    "South Carolina": "south-carolina",
    "Georgia": "georgia",
    "Arizona": "arizona",
    "Texas": "texas",
    "California": "california",
    "Nevada": "nevada",
    "Utah": "utah",
    "Colorado": "colorado",
    "Oregon": "oregon",
    "Washington": "washington",
}

BRANDS = {
    "In-N-Out": r"in[\s\-']*n[\s\-']*out",
    "McDonald's": r"mcdonald",
    "Five Guys": r"five\s*guys",
    "Shake Shack": r"shake\s*shack",
    "Whataburger": r"whataburger",
    "Culver's": r"culver",
    "Freddy's": r"freddy",
    "Steak 'n Shake": r"steak\s*['’]?\s*n\s*shake",
}

COLUMNS = [
    "osm_type", "osm_id", "name", "brand",
    "state_query", "latitude", "longitude",
    "city", "street", "postcode"
]


class RestaurantHandler(osmium.SimpleHandler):

    def __init__(self, state):
        super().__init__()
        self.state = state
        self.records = []

    def node(self, node):
        self.process(node, "node")

    def way(self, way):
        self.process(way, "way")

    def process(self, obj, osm_type):
        tags = obj.tags

        if tags.get("amenity") not in ("fast_food", "restaurant"):
            return

        name = tags.get("name", "")
        brand_tag = tags.get("brand", "")
        search_text = f"{name} {brand_tag}"

        matched_brand = None

        for brand, pattern in BRANDS.items():
            if re.search(pattern, search_text, re.IGNORECASE):
                matched_brand = brand
                break

        if matched_brand is None:
            return

        latitude = None
        longitude = None

        if osm_type == "node":
            if obj.location.valid():
                latitude = obj.location.lat
                longitude = obj.location.lon

        elif osm_type == "way":
            coords = [
                (n.location.lat, n.location.lon)
                for n in obj.nodes
                if n.location.valid()
            ]

            if coords:
                latitude = sum(p[0] for p in coords) / len(coords)
                longitude = sum(p[1] for p in coords) / len(coords)

        if latitude is None or longitude is None:
            return

        self.records.append({
            "osm_type": osm_type,
            "osm_id": obj.id,
            "name": name,
            "brand": matched_brand,
            "state_query": self.state,
            "latitude": latitude,
            "longitude": longitude,
            "city": tags.get("addr:city", ""),
            "street": tags.get("addr:street", ""),
            "postcode": tags.get("addr:postcode", "")
        })


def download_state(slug, output_file):
    url = (
        "https://download.geofabrik.de/"
        f"north-america/us/{slug}-latest.osm.pbf"
    )

    if output_file.exists() and output_file.stat().st_size > 0:
        print(f"Using existing file: {output_file.name}")
        return

    print(f"Downloading {slug}...")

    temp_file = output_file.with_suffix(".part")

    for attempt in range(3):
        try:
            with requests.get(url, stream=True, timeout=(30, 120)) as response:
                response.raise_for_status()

                with temp_file.open("wb") as f:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)

            temp_file.replace(output_file)
            print(f"Downloaded: {output_file.name}")
            return

        except requests.RequestException as exc:
            print(f"Attempt {attempt + 1} failed: {exc}")
            temp_file.unlink(missing_ok=True)
            time.sleep(5)

    raise RuntimeError(f"Failed to download {slug}")


def extract_state(state, pbf_file, csv_file):
    print(f"Extracting restaurants in {state}...")

    handler = RestaurantHandler(state)
    handler.apply_file(str(pbf_file), locations=True)

    with csv_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(handler.records)

    print(f"{state}: {len(handler.records):,} restaurants")


def combine_csv_files():
    frames = []

    for state, slug in STATES.items():
        csv_file = STATE_CSV_DIR / f"{slug}.csv"

        if csv_file.exists():
            frames.append(pd.read_csv(csv_file))

    if not frames:
        print("No state CSV files available.")
        return

    combined = pd.concat(frames, ignore_index=True)

    combined = combined.drop_duplicates(
        subset=["osm_type", "osm_id"]
    )

    output_file = DATA_DIR / "restaurants_osm.csv"
    combined.to_csv(output_file, index=False)

    print(f"\nCombined: {len(combined):,} restaurants")
    print(f"Saved to: {output_file}")


def main():
    print("In-N-Out Expansion: Multi-State Data Collection")

    for state, slug in STATES.items():
        pbf_file = OSM_DIR / f"{slug}-latest.osm.pbf"
        csv_file = STATE_CSV_DIR / f"{slug}.csv"

        if csv_file.exists():
            print(f"Skipping {state}: already extracted")
            continue

        try:
            download_state(slug, pbf_file)
            extract_state(state, pbf_file, csv_file)

            # Save progress after each state.
            combine_csv_files()

            # Delete downloaded raw data except Missouri.
            if state != "Missouri":
                pbf_file.unlink(missing_ok=True)

        except Exception as exc:
            print(f"WARNING: {state} failed: {exc}")

    combine_csv_files()
    print("\nFinished processing available states!")


if __name__ == "__main__":
    main()
