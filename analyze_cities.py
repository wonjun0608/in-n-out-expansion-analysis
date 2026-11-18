
import sqlite3
import pandas as pd

DB_FILE = "data/in_n_out.db"

QUERY = """
SELECT
    c.city_state,
    c.population,
    c.median_household_income,
    c.total_restaurants,
    COALESCE(c.restaurants_in_n_out, 0) AS in_n_out_count
FROM cities AS c
WHERE c.population >= 100000
  AND COALESCE(c.restaurants_in_n_out, 0) = 0
  AND c.median_household_income > 0
ORDER BY c.population DESC
LIMIT 20;
"""

with sqlite3.connect(DB_FILE) as conn:
    results = pd.read_sql_query(QUERY, conn)

print("\n=== POTENTIAL IN-N-OUT EXPANSION CITIES ===")
print(results.to_string(index=False))
