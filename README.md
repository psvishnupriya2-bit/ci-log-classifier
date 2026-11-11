# CI Log Classifier

When a CI build fails, this project reads the end of the failure log and says why it failed.

Live demo: https://ci-log-classifier.onrender.com/ (free server, the first visit can take about 50 seconds to wake up)

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

## Results on the first labels (5-fold cross-validation, 328 logs; retrained scores are in the update at the end)

| Model | Macro F1 | test_failure | other | lint_error | missing_dependency |
|---|---|---|---|---|---|
| TF-IDF + logistic regression | 0.894 | 0.97 | 0.94 | 0.87 | 0.80 |
| TF-IDF + LightGBM | 0.873 | 0.98 | 0.98 | 0.93 | 0.60 |
| Small PyTorch network | 0.925 | 0.99 | 0.98 | 0.95 | 0.78 |

Logs per cause: test_failure 196, other 91, lint_error 30, missing_dependency 11.

Logistic regression is served live. PyTorch scored highest (0.925), but the gap is small on 328 logs, and logistic regression is light enough for a free server and easy to explain. The words shown on the page are the TF-IDF weight times the model coefficient. SHAP was used offline (explain_shap.py) to check the explanations.

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



## Hand check of the labels

I labeled 29 logs by hand and the keyword rules agreed with me on 21 of them (72%). Per cause: lint_error 4 of 4, other 6 of 7, test_failure 7 of 9, missing_dependency 4 of 9. The rules often miss dependency conflicts and package downloads that time out. This is a small sample, and I skipped logs whose cause was not visible in the stored lines, so treat 72% as a rough estimate. The model scores above show how well the model reproduces the rule labels, not how well it finds the true cause. Rewriting the missing_dependency rules and labeling more logs is the next improvement.

## Update: improved labeling rules

The hand check showed the first rules were weakest on missing_dependency (4 of 9 right). Reading the disagreements, I fixed three problems: bot jobs (Dependabot, pull-request checks) were counted as missing_dependency, version conflicts such as "pytest-asyncio requires pytest<10" were missed, and two of my own hand labels were typos.

On the same 29 hand-labeled logs, agreement went from 22 of 29 (76%) to 28 of 29 (97%). This 97% is not a real accuracy, because I wrote the new rules after reading these exact logs. Accuracy on unseen logs is lower, and I have not measured it yet.

After relabeling (test_failure 189, other 108, lint_error 33, missing_dependency 13, timeout 1, network_error 1), I retrained: logistic regression macro F1 0.937 and LightGBM 0.939. These scores use the new labels and cannot be compared with the table above, which uses the old labels. The PyTorch model was not rerun. The live page uses the retrained logistic regression model.

The live missing-package example gives the right cause but only 47% confidence, and its top words include a package name (openblas32) from repeated numpy logs. With 13 training logs for this cause, the model has partly learned that name.

Next step: label about 15 new logs the rules have never seen, to get an honest accuracy.




