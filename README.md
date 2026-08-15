# B2B Revenue-to-Cash Early Warning and Decision Engine

Week 6 Capstone, AI in Finance — Mastery level.
Specification: `project_charter_v1.0.1_FROZEN.md`. The charter governs; this repo implements it.

**Current state: Phase 1 — deployment proof only.** No pipeline, no models, no synthetic data pack. Every figure in the app is a placeholder.

---

## What Phase 1 proves

Charter §10 Phase 1, acceptance test **T5.1 — deploys on Community Cloud, live URL loads.**

The app does slightly more than load. The Technical assurance tab reports installed versions and, on demand, *fits* the models the charter specifies rather than merely importing them:

| Check | Why it is here |
|---|---|
| Holt-Winters fit and 12-month forecast | §5.1 challenger 1 |
| SARIMA fit and 12-month forecast | §5.1 challenger 2 — heaviest fit, the resource-limit canary |
| XGBoost fit and predict | §5.2 challenger; most likely dependency to fail on a slim container |
| Plotly figure construction | §6 charting |
| openpyxl Excel round trip | §4 messy source-file ingestion |

A hello-world would pass T5.1 and leave the real risk — dependency resolution and memory headroom on Community Cloud — undiscovered until Phase 6. Every check is wrapped so a failure is reported on the page instead of crashing the app.

---

## Runbook

1. Create a **public** GitHub repository. Community Cloud can deploy private repos, but public removes an authorisation variable from a test whose only job is removing variables.
2. Commit these five files at the repository root: `app.py`, `requirements.txt`, `packages.txt`, `README.md`, `.gitignore`. Only the first three are needed for the deployment itself; the README is retained as submission evidence. If your device will not save a leading-dot filename, upload the rest and create `.gitignore` in GitHub via **Add file → Create new file**.
3. At share.streamlit.io, sign in with GitHub, then **Create app → Deploy a public app from GitHub**. Repository, branch `main`, main file path `app.py`. If **Advanced settings** offers a Python version, choose 3.11 or 3.12 — the newest release can run ahead of the statsmodels and XGBoost wheel builds, and a wheel-availability failure would misdiagnose as a stack problem.
4. Watch the build log. First build takes several minutes — XGBoost and statsmodels wheels are large.
5. When the app loads, open **4 · Technical assurance** and press **Run smoke checks**.

**T5.1 passes when** the live URL loads and all five smoke checks report PASS.

Record the live URL and the date. Screenshot the version table and the check results — that screenshot is evidence for deliverable 5 and for Loom 3:00–4:00.

---

## After it passes

Replace the floors in `requirements.txt` with the exact versions shown on the Technical assurance tab, commit, and redeploy. That pinned set is the reproducibility baseline behind **T3.6**.

Versions tested locally on 8 August 2026:

```
streamlit 1.61.1   pandas 2.3.3     numpy 2.5.1
statsmodels 0.14.6 scikit-learn 1.9.0  xgboost 3.4.0
plotly 6.9.0       openpyxl 3.1.5
```

Community Cloud resolves against its own Python build, so its numbers may differ. Its numbers are the ones to pin.

---

## If it fails

Do not adjust scope. Record the failure and its cause; a genuine technical blocker is the only basis for a charter change, logged as v1.0.2.

| Symptom | Likely cause | Fix |
|---|---|---|
| `libgomp.so.1: cannot open shared object file` | XGBoost needs OpenMP | Already handled by `packages.txt`. Confirm it is at the repo root and spelled exactly. |
| Build times out or app restarts during smoke checks | Memory ceiling reached on the SARIMA fit | Genuine blocker. Options: shorten the fitted series, or drop SARIMA to import-only in the app and run it in the notebook. Charter §5.1 permits SARIMA "where justified" — a Community Cloud memory ceiling is a justification for excluding it, and must be recorded as such, not left silent. |
| Dependency resolution fails | Version conflict between floors | Pin the locally tested set above and retry. |
| App loads but tabs are blank | Streamlit version older than tab support | Raise the `streamlit` floor. |

---

## Structure note

The four tabs mirror charter §6 (Decision, Evidence, Confidence, Technical assurance) so that Phase 6 extends this file rather than replacing it. The decision sits above the scenario controls, which are present but disabled — there is nothing behind them yet, and an inert control that appears to work would be worse than one that plainly does not.

---

## Not in this repo yet

Phases 3–8: synthetic data pack (§4), pipeline class, model selection (§5), revenue-to-cash integration, agent challenge chain (§1.4). The §3.3 backlog stays a backlog.
