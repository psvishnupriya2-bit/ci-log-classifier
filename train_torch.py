import os, sys, numpy as np, psycopg2, torch, mlflow
from torch import nn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import f1_score

torch.manual_seed(42)
np.random.seed(42)
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
classes = sorted(set(labels))
y = np.array([classes.index(l) for l in labels])
print("Logs used:", len(texts))

pred = np.zeros(len(y), dtype=int)
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
for tr, te in cv.split(texts, y):
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=5000, sublinear_tf=True)
    Xtr = torch.tensor(vec.fit_transform([texts[i] for i in tr]).toarray(), dtype=torch.float32)
    Xte = torch.tensor(vec.transform([texts[i] for i in te]).toarray(), dtype=torch.float32)
    ytr = torch.tensor(y[tr])
    counts = np.bincount(y[tr], minlength=len(classes))
    w = torch.tensor(len(tr) / (len(classes) * np.maximum(counts, 1)), dtype=torch.float32)
    net = nn.Sequential(nn.Linear(Xtr.shape[1], 64), nn.ReLU(), nn.Dropout(0.3),
                        nn.Linear(64, len(classes)))
    opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-4)
    loss_fn = nn.CrossEntropyLoss(weight=w)
    for epoch in range(60):
        net.train()
        perm = torch.randperm(len(tr))
        for i in range(0, len(tr), 32):
            idx = perm[i:i + 32]
            opt.zero_grad()
            loss_fn(net(Xtr[idx]), ytr[idx]).backward()
            opt.step()
    net.eval()
    with torch.no_grad():
        pred[te] = net(Xte).argmax(1).numpy()

macro = f1_score(y, pred, average="macro")
per = f1_score(y, pred, average=None, labels=list(range(len(classes))))
mlflow.set_tracking_uri("http://127.0.0.1:5000")
mlflow.set_experiment("ci-log-classifier")
with mlflow.start_run(run_name="pytorch_mlp"):
    mlflow.log_param("model", "pytorch_mlp")
    mlflow.log_param("cv_folds", 5)
    mlflow.log_param("n_logs", len(texts))
    mlflow.log_metric("macro_f1", macro)
    for c, s in zip(classes, per):
        mlflow.log_metric("f1_" + c, float(s))
print("pytorch_mlp macro F1:", round(macro, 3), {c: round(float(s), 2) for c, s in zip(classes, per)})
