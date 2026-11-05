import os, sys, psycopg2
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import f1_score, classification_report
from lightgbm import LGBMClassifier

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
print("Logs used:", len(texts))
print("Per cause:", dict(Counter(labels)))

def tfidf():
    return TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=20000, sublinear_tf=True)

models = {
    "logistic_regression": make_pipeline(tfidf(), LogisticRegression(max_iter=1000, class_weight="balanced")),
    "lightgbm": make_pipeline(tfidf(), LGBMClassifier(n_estimators=200, learning_rate=0.1,
                num_leaves=15, min_child_samples=5, class_weight="balanced", verbose=-1)),
}
splits = min(5, min(Counter(labels).values()))
cv = StratifiedKFold(n_splits=splits, shuffle=True, random_state=42)

for name, model in models.items():
    pred = cross_val_predict(model, texts, labels, cv=cv)
    print("\n" + "=" * 60)
    print(name, "| macro F1:", round(f1_score(labels, pred, average="macro"), 3))
    print(classification_report(labels, pred, zero_division=0))

lr = models["logistic_regression"].fit(texts, labels)
names = lr.steps[0][1].get_feature_names_out()
clf = lr.steps[1][1]
print("Top words per cause (logistic regression):")
for i, c in enumerate(clf.classes_):
    top = clf.coef_[i].argsort()[-8:][::-1]
    print(" ", c, "->", ", ".join(names[j] for j in top))
