import os, sys, psycopg2, mlflow
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import f1_score
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
print("Logs used:", len(texts), dict(Counter(labels)))

def tfidf():
    return TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=20000, sublinear_tf=True)

models = {
    "logistic_regression": make_pipeline(tfidf(), LogisticRegression(max_iter=1000, class_weight="balanced")),
    "lightgbm": make_pipeline(tfidf(), LGBMClassifier(n_estimators=200, learning_rate=0.1,
                num_leaves=15, min_child_samples=5, class_weight="balanced", verbose=-1)),
}
splits = min(5, min(Counter(labels).values()))
cv = StratifiedKFold(n_splits=splits, shuffle=True, random_state=42)

mlflow.set_tracking_uri("http://127.0.0.1:5000")
mlflow.set_experiment("ci-log-classifier")
classes = sorted(set(labels))
for name, model in models.items():
    pred = cross_val_predict(model, texts, labels, cv=cv)
    macro = f1_score(labels, pred, average="macro")
    per = f1_score(labels, pred, average=None, labels=classes)
    with mlflow.start_run(run_name=name):
        mlflow.log_param("model", name)
        mlflow.log_param("cv_folds", splits)
        mlflow.log_param("n_logs", len(texts))
        mlflow.log_metric("macro_f1", macro)
        for c, s in zip(classes, per):
            mlflow.log_metric("f1_" + c, s)
    print(name, "macro F1:", round(macro, 3), {c: round(s, 2) for c, s in zip(classes, per)})
