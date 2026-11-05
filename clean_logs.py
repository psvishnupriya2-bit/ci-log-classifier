import os, re, sys, psycopg2

PASSWORD = os.environ.get("PGPASSWORD")
if not PASSWORD:
    sys.exit("Set PGPASSWORD first.")

NOISE = ("using cached", "collecting ", "downloading ", "requirement already satisfied",
         "installing collected", "successfully installed", "obtaining ", "building wheel",
         "preparing metadata", "hint:", "##[group]", "##[endgroup]", "##[command]",
         "stop and remove container", "remove container network", "cleaning up orphan",
         "post job cleanup", "from https", "remote:", "* [new", "to https",
         "git version", "deleting", "temporarily overriding", "adding repository")

def clean(text):
    kept = []
    for line in text.splitlines():
        l = re.sub(r"^\d{4}-\d{2}-\d{2}T[\d:.]+Z ?", "", line)
        l = re.sub(r"(\x1b)?\[[0-9;]*m", "", l).strip()
        low = l.lower()
        if not low or low.startswith(NOISE) or ".whl" in low:
            continue
        kept.append(l)
    text = "\n".join(kept)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"(?<!\w)(?:[A-Za-z]:\\|\.{0,2}/|~/)[\w\-.@+/\\]+", " ", text)
    text = re.sub(r"\b[0-9a-f]{7,64}\b", " ", text)
    text = re.sub(r"\b\d+(\.\d+)*\b", " ", text)
    lines = []
    for line in text.lower().splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)

conn = psycopg2.connect(host="localhost", port=5432, user="postgres",
                        password=PASSWORD, dbname="ci_logs")
cur = conn.cursor()
cur.execute("ALTER TABLE logs ADD COLUMN IF NOT EXISTS clean_text TEXT")
conn.commit()
cur.execute("SELECT id, log_text FROM logs")
rows = cur.fetchall()
print("Cleaning", len(rows), "logs...")
for log_id, text in rows:
    cur.execute("UPDATE logs SET clean_text = %s WHERE id = %s", (clean(text), log_id))
conn.commit()
print("Done.")
conn.close()
