
from pathlib import Path
import csv
import re

import osmium


BASE_DIR = Path(__file__).parent
INPUT_FILE = BASE_DIR / "data/osm/missouri-latest.osm.pbf"
OUTPUT_FILE = BASE_DIR / "data/restaurants_osm.csv"

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


class RestaurantHandler(osmium.SimpleHandler):

    def __init__(self):
        super().__init__()
        self.records = []

    def node(self, node):
        self.process(node, "node")

    def way(self, way):
        self.process(way, "way")

    def process(self, obj, osm_type):
        tags = obj.tags

        # Include both fast-food and restaurant categories.
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
            # Use the average of available way-node coordinates.
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
            "state_query": "Missouri",
            "latitude": latitude,
            "longitude": longitude,
            "city": tags.get("addr:city", ""),
            "street": tags.get("addr:street", ""),
            "postcode": tags.get("addr:postcode", ""),
        })


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(INPUT_FILE)

    print("Reading Missouri OSM data...")

    handler = RestaurantHandler()

    # locations=True loads coordinates for way nodes.
    handler.apply_file(str(INPUT_FILE), locations=True)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    columns = [
        "osm_type", "osm_id", "name", "brand",
        "state_query", "latitude", "longitude",
        "city", "street", "postcode"
    ]

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(handler.records)

    print(f"Extracted {len(handler.records):,} restaurants")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
