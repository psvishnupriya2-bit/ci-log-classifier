import os, sys, joblib, psycopg2
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

PASSWORD = os.environ.get("PGPASSWORD")
if not PASSWORD:
    sys.exit("Set PGPASSWORD first.")
conn = psycopg2.connect(host="localhost", port=5432, user="postgres",
                        password=PASSWORD, dbname="ci_logs")
cur = conn.cursor()
cur.execute("SELECT clean_text, label FROM logs WHERE clean_text IS NOT NULL AND label IS NOT NULL")
rows = cur.fetchall()
conn.close()

seen, texts, labels = set(), [], []
for t, l in rows:
    if t in seen:
        continue
    seen.add(t)
    texts.append(t)
    labels.append("other" if l in ("timeout", "network_error") else l)

model = make_pipeline(
    TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=20000, sublinear_tf=True),
    LogisticRegression(max_iter=1000, class_weight="balanced"),
)
model.fit(texts, labels)
joblib.dump(model, "model.joblib")
print("Trained on", len(texts), "logs")
print("Causes:", list(model.classes_))
print("Saved model.joblib")
