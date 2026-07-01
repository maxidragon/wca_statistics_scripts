import csv
import mysql.connector
import os
from pathlib import Path

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="wca_statistics"
)

cur = conn.cursor(dictionary=True)

YEAR = 2024

cur.execute("""
    SELECT id, name
    FROM competitions
    WHERE YEAR(end_date)=%s AND country_id="Poland"
""", (YEAR, ))

comps = cur.fetchall()

rows = []

for comp in comps:
    comp_id = comp["id"]

    cur.execute(f"""
        WITH FirstCompetition AS (
            SELECT r.person_id, MIN(c.start_date) AS firstCompDate
            FROM results r
            JOIN competitions c ON r.competition_id=c.id
            GROUP BY r.person_id
        ),
        Newbies AS (
            SELECT DISTINCT r.person_id
            FROM results r
            JOIN competitions c ON r.competition_id=c.id
            JOIN FirstCompetition fc ON r.person_id=fc.person_id
            WHERE c.id="{comp_id}"
            AND c.start_date=fc.firstCompDate
        )
        SELECT person_id, COUNT(DISTINCT competition_id) AS comps
        FROM results
        WHERE person_id IN (SELECT person_id FROM Newbies)
        GROUP BY person_id
    """)

    newbies = cur.fetchall()
    total_new = len(newbies)
    returned = sum(1 for n in newbies if n["comps"] > 1)
    print(f"{comp_id}: {total_new} newcomers, {returned} returned")

    rows.append([comp_id, comp["name"], total_new, returned])

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)

with open(output_dir / "returning_newcomers_by_year_in_poland.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["competition_id", "competition_name", "newcomers", "returned_newcomers"])
    w.writerows(rows)

cur.close()
conn.close()
