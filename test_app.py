from fastapi.testclient import TestClient
from app import app

client = TestClient(app)
CAUSES = {"test_failure", "missing_dependency", "lint_error", "other"}


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_home_page_loads():
    r = client.get("/")
    assert r.status_code == 200
    assert "Classify" in r.text


def test_classify_returns_expected_fields():
    log = "=== FAILURES ===\nAssertionError: assert 3 == 4\nFAILED tests/test_a.py::test_x"
    r = client.post("/classify", json={"log": log})
    assert r.status_code == 200
    d = r.json()
    assert d["cause"] in CAUSES
    assert 0.0 <= d["confidence"] <= 1.0
    assert isinstance(d["words"], list)
    assert set(d["probs"]) == CAUSES


def test_empty_log_is_handled():
    r = client.post("/classify", json={"log": "   "})
    assert r.status_code == 200
    assert r.json()["cause"] == "other"
    assert r.json()["confidence"] == 0.0


def test_missing_log_field_rejected():
    r = client.post("/classify", json={})
    assert r.status_code == 422
