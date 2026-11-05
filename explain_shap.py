import os, sys, numpy as np, psycopg2, shap
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

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

Xt, Xe, yt, ye = train_test_split(texts, labels, test_size=0.2, stratify=labels, random_state=42)
vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=20000, sublinear_tf=True)
Xtr = vec.fit_transform(Xt)
clf = LogisticRegression(max_iter=1000, class_weight="balanced").fit(Xtr, yt)
names = vec.get_feature_names_out()

samples = []
for c in clf.classes_:
    for t, l in zip(Xe, ye):
        if l == c:
            samples.append((c, t))
            break
Xs = vec.transform([s[1] for s in samples]).toarray()
probs = clf.predict_proba(Xs)
sv = shap.LinearExplainer(clf, Xtr.toarray()).shap_values(Xs)

def contrib(i, k):
    if isinstance(sv, list):
        return np.asarray(sv[k][i]).ravel()
    a = np.asarray(sv)
    return a[i, :, k] if a.ndim == 3 else a[i]

for i, (true_label, _) in enumerate(samples):
    k = int(probs[i].argmax())
    c = contrib(i, k)
    top = [j for j in c.argsort()[::-1] if Xs[i, j] > 0][:6]
    print("\n" + "=" * 60)
    print("True cause:     ", true_label)
    print("Predicted cause:", clf.classes_[k], "| confidence:", round(float(probs[i, k]), 2))
    print("Words that drove it:", ", ".join(names[j] for j in top))
