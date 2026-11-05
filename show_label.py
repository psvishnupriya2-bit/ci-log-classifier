import os, sys, psycopg2

PASSWORD = os.environ.get("PGPASSWORD")
if not PASSWORD:
    sys.exit("Set PGPASSWORD first.")
LABEL = sys.argv[1]
WORDS = {
    "missing_dependency": ["modulenotfounderror", "no module named",
        "could not find a version that satisfies", "no matching distribution",
        "cannot find module", "unable to locate package", "importerror: cannot import",
        "package not found", "dependency resolution", "failed to install",
        "unsatisfiable", "could not solve", "packagesnotfounderror"],
    "lint_error": ["flake8", "ruff", "pylint", "eslint", "would reformat",
        "black --check", "isort", "mypy", "codespell", "trailing whitespace",
        "pre-commit", "cython-lint", "numpydoc", "docstring validation",
        "formatting check", "code style"],
}
words = WORDS.get(LABEL, [])
conn = psycopg2.connect(host="localhost", port=5432, user="postgres",
                        password=PASSWORD, dbname="ci_logs")
cur = conn.cursor()
cur.execute("SELECT id, repo, log_text FROM logs WHERE label = %s ORDER BY random() LIMIT 6", (LABEL,))
for log_id, repo, text in cur.fetchall():
    print("\n" + "=" * 60)
    print("id", log_id, "|", repo)
    lines = text.splitlines()[-120:]
    shown = 0
    for l in lines:
        if any(w in l.lower() for w in words):
            print("  MATCH:", l[29:190])
            shown += 1
            if shown == 2:
                break
    print("  LAST LINE:", lines[-1][29:190] if lines else "")
conn.close()
