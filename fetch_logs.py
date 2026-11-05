import os
import sys
import time
import pathlib
import requests

TOKEN = os.environ.get("GITHUB_TOKEN")
if not TOKEN:
    sys.exit("Set GITHUB_TOKEN first.")

API = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
PER_REPO = 60
OUT = pathlib.Path("logs")
OUT.mkdir(exist_ok=True)


def get(url, **params):
    r = requests.get(url, headers=HEADERS, params=params, timeout=30)
    if r.headers.get("X-RateLimit-Remaining") == "0":
        sys.exit("GitHub rate limit reached. Wait an hour and run again.")
    return r


def fetch_repo(repo):
    saved = 0
    page = 1
    while saved < PER_REPO and page <= 10:
        r = get(f"{API}/repos/{repo}/actions/runs",
                status="failure", per_page=30, page=page)
        if r.status_code != 200:
            print(f"[{repo}] HTTP {r.status_code}")
            return saved
        runs = r.json().get("workflow_runs", [])
        if not runs:
            break
        for run in runs:
            jobs = get(f"{API}/repos/{repo}/actions/runs/{run['id']}/jobs",
                       filter="latest").json().get("jobs", [])
            for job in jobs:
                if job.get("conclusion") != "failure" or saved >= PER_REPO:
                    continue
                name = f"{repo.replace('/', '__')}__{job['id']}.txt"
                if (OUT / name).exists():
                    saved += 1
                    continue
                log = get(f"{API}/repos/{repo}/actions/jobs/{job['id']}/logs")
                if log.status_code != 200:
                    continue
                tail = log.text.splitlines()[-200:]
                (OUT / name).write_text("\n".join(tail), encoding="utf-8")
                saved += 1
                print(f"  [{repo}] saved {saved}/{PER_REPO}")
                time.sleep(0.3)
        page += 1
    return saved


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Pass repos as owner/name.")
    total = 0
    for repo in sys.argv[1:]:
        print(f"Starting {repo}")
        total += fetch_repo(repo)
    print(f"\nDone. Total logs in this run: {total}")
    print(f"Files in logs folder: {len(list(OUT.glob('*.txt')))}")