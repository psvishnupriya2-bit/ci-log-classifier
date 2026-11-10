import re

BOT = ["dependabot", "check_pr.py", "pr_quality", "pr_title:", "lock-threads",
       "backend subprocess exited"]
MISSING = ["modulenotfounderror", "no module named",
    "could not find a version that satisfies", "no matching distribution",
    "cannot find module", "unable to locate package",
    "package not found", "dependency resolution", "failed to install",
    "unsatisfiable", "could not solve", "packagesnotfounderror",
    "uv pip check", "pip check", "resolutionimpossible",
    "conflicting dependencies", "no solution found"]
INCOMPAT = r"found \d+ incompatibilit"
NETWORK = ["connection refused", "connection reset", "could not resolve host",
    "temporary failure in name resolution", "max retries exceeded", "connectionerror",
    "network is unreachable", "502 bad gateway", "503 service", "read timed out",
    "ssl: certificate", "failed to connect", "tls handshake", "unable to access",
    "could not download", "failed to download", "rate limit", "http error 5"]
TIMEOUT = ["timed out", "timeouterror", "exceeded the maximum execution time",
    "operation was canceled", "deadline exceeded", "was cancelled", "hung up"]
TEST = ["assertionerror", "short test summary info", "error collecting",
    "== failures ==", "tests failed", "failed tests", "test failed", "pytest",
    "test session starts", "unittest", "failures:", "traceback (most recent call last)",
    " passed", " failed,", "failed with code", "runtests", "ctest", "nose"]
LINT_WORDS = ("flake8", "ruff", "pylint", "eslint", "would reformat", "black --check",
    "isort", "mypy", "codespell", "trailing whitespace", "pre-commit",
    "cython-lint", "numpydoc", "docstring validation", "formatting check", "code style")
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


def has_any(tail, words):
    return any(w in tail for w in words)


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
    if has_any(tail, BOT):
        return "other"
    if has_any(tail, MISSING) or re.search(INCOMPAT, tail):
        return "missing_dependency"
    if has_any(tail, NETWORK):
        return "network_error"
    if has_any(tail, TIMEOUT):
        return "timeout"
    if lint_failure(lines):
        return "lint_error"
    if has_any(tail, TEST):
        return "test_failure"
    return "other"