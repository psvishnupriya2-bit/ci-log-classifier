import os
import sys
import psycopg2

PASSWORD = os.environ.get("PGPASSWORD")
if not PASSWORD:
    sys.exit("Set PGPASSWORD first.")

conn = psycopg2.connect(host="localhost", port=5432, user="postgres",
                        password=PASSWORD, dbname="ci_logs")
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM logs")
print("Total logs:", cur.fetchone()[0])

cur.execute("SELECT id, repo, log_text FROM logs WHERE label = 'other' "
            "ORDER BY random() LIMIT 8")
for log_id, repo, text in cur.fetchall():
    print("\n" + "=" * 70)
    print(f"id {log_id}  |  {repo}")
    hits = [l for l in text.splitlines()
            if any(w in l.lower() for w in ("error", "fail", "exception", "denied"))
            and "##[group]" not in l]
    for l in hits[-6:]:
        print("   ", l[:160])
conn.close()