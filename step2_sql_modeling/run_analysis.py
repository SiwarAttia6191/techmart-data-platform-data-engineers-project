"""
Step 2 - run_analysis.py
--------------------------
Splits analysis_queries.sql into its individual statements (on the
'-- Qn:' comment markers) and runs each one against db/techmart.db,
printing a small formatted result table. This is just a convenience
runner so you can `python3 run_analysis.py` and see every business
question answered without opening a SQL client.

Usage:
    python3 step2_sql_modeling/run_analysis.py
"""
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db" / "techmart.db"
SQL_PATH = Path(__file__).resolve().parent / "analysis_queries.sql"


def split_queries(sql_text: str):
    """Split the file into (label, query) pairs on '-- Qn: ...' headers."""
    chunks = re.split(r"(?m)^-- (Q\d+:.*)$", sql_text)
    # chunks[0] is leading boilerplate before Q1; skip it
    pairs = []
    for i in range(1, len(chunks), 2):
        label = chunks[i].strip()
        query = chunks[i + 1].strip().strip(";")
        if query:
            pairs.append((label, query))
    return pairs


def print_table(cursor, rows, max_rows=10):
    cols = [d[0] for d in cursor.description]
    print(" | ".join(cols))
    print("-" * (len(" | ".join(cols))))
    for row in rows[:max_rows]:
        print(" | ".join(str(v) for v in row))
    if len(rows) > max_rows:
        print(f"... ({len(rows) - max_rows} more rows)")


def main():
    if not DB_PATH.exists():
        raise SystemExit("db/techmart.db not found -- run step2_sql_modeling/seed_data.py first.")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    sql_text = SQL_PATH.read_text()
    for label, query in split_queries(sql_text):
        print(f"\n=== {label} ===")
        cur.execute(query)
        rows = cur.fetchall()
        print_table(cur, rows)

    conn.close()


if __name__ == "__main__":
    main()
