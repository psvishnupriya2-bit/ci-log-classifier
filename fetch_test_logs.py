import os
import sys
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
TARGET = 10
OUT = pathlib.Path("sample_logs")
OUT.mkdir(exist_ok=True)


def get(url, **params):
    return requests.get(url, headers=HEADERS, params=params, timeout=30)


def main(repos):
    saved, expired, errors = 0, 0, 0
    for repo in repos:
        if saved >= TARGET:
            break
        r = get(f"{API}/repos/{repo}/actions/runs", status="failure", per_page=10)
        if r.status_code != 200:
            print(f"[{repo}] cannot list runs: HTTP {r.status_code}")
            errors += 1
            continue
        runs = r.json().get("workflow_runs", [])
        print(f"[{repo}] {len(runs)} failed runs found")
        for run in runs:
            if saved >= TARGET:
                break
            jobs = get(f"{API}/repos/{repo}/actions/runs/{run['id']}/jobs",
                       filter="latest").json().get("jobs", [])
            for job in jobs:
                if job.get("conclusion") != "failure" or saved >= TARGET:
                    continue


                