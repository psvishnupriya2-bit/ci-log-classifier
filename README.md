# CI Log Classifier

When a CI build fails, this project reads the end of the failure log and says why it failed.

Live demo: PASTE-YOUR-ONRENDER-LINK-HERE (free server, the first visit can take about 50 seconds to wake up)

## What it does

- Input: the last lines of a failed build log.
- Output: the most likely cause, a confidence score and the words that drove the answer.
- Causes: test_failure, missing_dependency, lint_error, other.

## How it works

1. Download failed-job logs from the GitHub API (7 public repos: pandas, scikit-learn, numpy, flask, requests, pytest, django).
2. Keep the last 200 lines of each log and store them in Postgres (345 logs, 328 after removing duplicates).
3. Clean the text: remove timestamps, hashes, paths, numbers and boilerplate lines such as pip downloads and Docker cleanup.
4. Label each log with keyword rules.
5. Train and compare models with 5-fold cross-validation, tracked in MLflow.
6. Serve the logistic regression model with FastAPI, packaged in Docker, tested with pytest and GitHub Actions, deployed on Render.

## Results (5-fold cross-validation, 328 logs)

| Model | Macro F1 | test_failure | other | lint_error | missing_dependency |
|---|---|---|---|---|---|
| TF-IDF + logistic regression | 0.894 | 0.97 | 0.94 | 0.87 | 0.80 |
| TF-IDF + LightGBM | 0.873 | 0.98 | 0.98 | 0.93 | 0.60 |
| Small PyTorch network | see MLflow | | | | |

Logs per cause: test_failure 196, other 91, lint_error 30, missing_dependency 11.

Logistic regression is served live: best macro F1, light enough for a free server, and its predictions are easy to explain. The words shown on the page are the TF-IDF weight times the model coefficient. SHAP was used offline (explain_shap.py) to check the explanations.

## Honest limits

- GitHub gives no failure-cause labels. The labels come from keyword rules, so part of the score is the model learning those rules. A hand-checked sample is still needed to measure how accurate the rules are.
- missing_dependency has only 11 logs, so its score is unreliable. lint_error has only 30.
- timeout and network_error had 1 log each, so they were merged into other.
- Logs expire after about 90 days, so only recent failures can be downloaded.
- The logs come from large open-source projects. The model may do worse on logs from other kinds of projects.
- Early versions had labeling mistakes (lint tools that passed were counted as lint failures). Fixing them lowered the scores, and the numbers above are the corrected ones.

## Run it locally

Install the requirements, then start the service with uvicorn:

    pip install -r requirements.txt
    python -m uvicorn app:app --port 8000

Open http://127.0.0.1:8000 in a browser. Run the tests with: python -m pytest -q

## Tools

Python, Postgres, GitHub API, scikit-learn, LightGBM, PyTorch, MLflow, SHAP, FastAPI, Docker, pytest, GitHub Actions, Render.
