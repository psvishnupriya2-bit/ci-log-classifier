import joblib
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from logclean import clean

model = joblib.load("model.joblib")
vec = model.steps[0][1]
clf = model.steps[1][1]
names = vec.get_feature_names_out()

app = FastAPI(title="CI Log Classifier")


class Req(BaseModel):
    log: str


@app.get("/", response_class=HTMLResponse)
def home():
    with open("index.html", encoding="utf-8") as f:
        return f.read()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/classify")
def classify(req: Req):
    lines = req.log.splitlines()[-200:]
    cleaned = clean("\n".join(lines))
    if not cleaned.strip():
        return {"cause": "other", "confidence": 0.0, "words": [], "probs": {}}
    x = vec.transform([cleaned])
    probs = clf.predict_proba(x)[0]
    k = int(probs.argmax())
    contrib = x.toarray()[0] * clf.coef_[k]
    top = [j for j in contrib.argsort()[::-1] if contrib[j] > 0][:8]
    return {
        "cause": str(clf.classes_[k]),
        "confidence": round(float(probs[k]), 3),
        "words": [str(names[j]) for j in top],
        "probs": {str(c): round(float(p), 3) for c, p in zip(clf.classes_, probs)},
    }
