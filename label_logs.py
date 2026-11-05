import os, re, sys, psycopg2

PASSWORD = os.environ.get("PGPASSWORD")
if not PASSWORD:
    sys.exit("Set PGPASSWORD first.")

BEFORE_LINT = [
    ("missing_dependency", ["modulenotfounderror", "no module named",
        "could not find a version that satisfies", "no matching distribution",
        "cannot find module", "unable to locate package",
        "package not found", "dependency resolution", "failed to install",
        "unsatisfiable", "could not solve", "packagesnotfounderror"]),
    ("network_error", ["connection refused", "connection reset", "could not resolve host",
        "temporary failure in name resolution", "max retries exceeded", "connectionerror",
        "network is unreachable", "502 bad gateway", "503 service", "read timed out",
        "ssl: certificate", "failed to connect", "tls handshake", "unable to access",
        "could not download", "failed to download", "rate limit", "http error 5"]),
    ("timeout", ["timed out", "timeouterror", "exceeded the maximum execution time",
        "operation was canceled", "deadline exceeded", "was cancelled", "hung up"]),
]
AFTER_LINT = [
    ("test_failure", ["assertionerror", "short test summary info", "error collecting",
        "== failures ==", "tests failed", "failed tests", "test failed", "pytest",
        "test session starts", "unittest", "failures:", "traceback (most recent call last)",
        " passed", " failed,", "failed with code", "runtests", "ctest", "nose"]),
]
LINT_WORDS = ("flake8", "ruff", "pylint", "eslint", "would reformat", "black --check",
              "isort", "mypy", "codespell", "trailing whitespace", "pre-commit",
              "cython-lint", "numpydoc", "docstring validation", "formatting check",
              "code style")
LINT_FAIL = ("error", "would reformat", "found", "failed", "fail", "violation",
             "issue", "problem")
SUCCESS = ("no problems", "no issues", "all checks passed", "passed", "success",
           "0 errors", "no errors")
NOISE_START = ("using cached", "collecting ", "downloading ", "requirement already satisfied",
               "installing collected", "successfully installed", "obtaining ",
               "building wheel", "preparing metadata")

def strip_line(l):
    l = re.sub(r"(\x1b)?\[[0-9;]*m", "", l)
    return re.sub(r"^\d{4}-\d{2}-\d{2}T[\d:.]+Z ?", "", l)

def noisy(l):
    s = l.strip().lower()
    return s.startswith(NOISE_START) or ".whl" in s

def lint_failure(lines):
    for l in lines:
        low = l.lower()
        if any(s in low for s in SUCCESS):
            continue
        if any(w in low for w in LINT_WORDS) and any(f in low for f in LINT_FAIL):
            return True
    return False

def label(text):
    lines = [strip_line(l) for l in text.splitlines()[-120:]]
    lines = [l for l in lines if not l.startswith("FAILED ") and not noisy(l)]
    tail = "\n".join(lines).lower()
    for name, words in BEFORE_LINT:
        if any(w in tail for w in words):
            return name
    if lint_failure(lines):
        return "lint_error"
    for name, words in AFTER_LINT:
        if any(w in tail for w in words):
            return name
    return "other"

conn = psycopg2.connect(host="localhost", port=5432, user="postgres",
                        password=PASSWORD, dbname="ci_logs")
cur = conn.cursor()
cur.execute("SELECT id, log_text FROM logs")
rows = cur.fetchall()
print("Labeling", len(rows), "logs...")
for log_id, text in rows:
    cur.execute("UPDATE logs SET label = %s WHERE id = %s", (label(text), log_id))
conn.commit()
cur.execute("SELECT label, COUNT(*) FROM logs GROUP BY label ORDER BY COUNT(*) DESC")
print("\nLabel counts:")
for name, n in cur.fetchall():
    print(" ", name + ":", n)
conn.close()
