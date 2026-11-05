import os
import sys
import pathlib
import psycopg2

PASSWORD = os.environ.get("PGPASSWORD")
if not PASSWORD:
    sys.exit("Set PGPASSWORD first.")

LOG_DIR = pathlib.Path("logs")
files = sorted(LOG_DIR.glob("*.txt"))
print(f"Found {len(files)} files in the logs folder")
if not files:
    sys.exit("No log files found. Run fetch_logs.py first.")

# 1. Create the database if it does not exist
conn = psycopg2.connect(host="localhost", port=5432, user="postgres",
                        password=PASSWORD, dbname="postgres")
conn.autocommit = True
cur = conn.cursor()
cur.execute("SELECT 1 FROM pg_database WHERE datname = 'ci_logs'")
if not cur.fetchone():
    cur.execute("CREATE DATABASE ci_logs")
    print("Created database ci_logs")
conn.close()

# 2. Create the table
conn = psycopg2.connect(host="localhost", port=5432, user="postgres",
                        password=PASSWORD, dbname="ci_logs")
cur = conn.cursor()
cur.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id SERIAL PRIMARY KEY,
        repo TEXT NOT NULL,
        job_id BIGINT UNIQUE NOT NULL,
        log_text TEXT NOT NULL
    )
""")

# 3. Load the files
for f in files:
    stem, job_id = f.stem.rsplit("__", 1)
    repo = stem.replace("__", "/", 1)
    text = f.read_text(encoding="utf-8", errors="ignore").replace("\x00", "")
    cur.execute(
        "INSERT INTO logs (repo, job_id, log_text) VALUES (%s, %s, %s) "
        "ON CONFLICT (job_id) DO NOTHING",
        (repo, int(job_id), text),
    )
conn.commit()

cur.execute("SELECT repo, COUNT(*) FROM logs GROUP BY repo ORDER BY repo")
print("\nLogs stored per repo:")
for repo, n in cur.fetchall():
    print(f"  {repo}: {n}")
cur.execute("SELECT COUNT(*) FROM logs")
print(f"\nTotal rows in database: {cur.fetchone()[0]}")
conn.close()