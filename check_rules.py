import os, sys, csv, psycopg2
from collections import Counter
from rules import label

PASSWORD = os.environ.get("PGPASSWORD")
if not PASSWORD:
    sys.exit("Set PGPASSWORD first.")
FIX = {98: "missing_dependency", 233: "other"}
conn = psycopg2.connect(host="localhost", port=5432, user="postgres",
                        password=PASSWORD, dbname="ci_logs")
cur = conn.cursor()
n = old_ok = new_ok = 0
by, ok, bad = Counter(), Counter(), []
with open("labels_manual.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        i = int(r["id"])
        mine = FIX.get(i, r["my_label"])
        cur.execute("SELECT log_text FROM logs WHERE id = %s", (i,))
        new = label(cur.fetchone()[0])
        if new in ("timeout", "network_error"):
            new = "other"
        n += 1
        old_ok += r["rule_label"] == mine
        new_ok += new == mine
        by[mine] += 1
        ok[mine] += new == mine
        if new != mine:
            bad.append((i, new, mine))
print("Logs:", n, "(2 typos corrected: ids 98 and 233)")
print("Old rules agree:", old_ok, "of", n, "=", round(100 * old_ok / n), "%")
print("New rules agree:", new_ok, "of", n, "=", round(100 * new_ok / n), "%")
for k in by:
    print(" ", k, ":", ok[k], "of", by[k])
print("Still wrong (id, rules said, you said):", bad)
conn.close()