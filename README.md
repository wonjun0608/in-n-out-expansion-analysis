# In-N-Out expansion: data collection starter

Run `pip install -r requirements.txt` and `python collect_data.py` from this folder. Files appear under `data/`.

- `census_places_2024.csv`: 2024 ACS 5-year place-level population and median household income (not the 2025 population estimates).
- `census_places_2023.csv`: 2023 ACS 5-year estimates; compare with 2024 cautiously because the 5-year windows overlap. Do not interpret the difference as a precise one-year growth rate.
- `restaurants_osm.csv`: OpenStreetMap points and polygon centers for selected chains in 17 states. This is an incomplete sample; not all restaurants have `amenity=fast_food` or a city address tag. Verify In-N-Out counts against its official locator.

Sources: https://api.census.gov/data/2024/acs/acs5.html ; https://overpass-turbo.eu/ ; https://locations.in-n-out.com/

**Important:** OSM restaurant locations are not automatically joined to Census place geographies. Use spatial joins to official Census place boundaries (or a documented geocoding method) rather than matching `addr:city` alone. Exclude non-city Census places if your analysis is city-only.

The collection script needs Internet access. It was not executed successfully in the ChatGPT sandbox because outbound DNS/network access is blocked. No data rows are fabricated.
