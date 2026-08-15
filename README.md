# Revenue-to-Cash Decision Engine — deployed application

Charter deliverable 5, §6. Deploy `app.py` on Streamlit Community Cloud from
this folder (Python 3.12, as pinned in Phase 1).

The app reads `decision_pack.json` and the exported CSVs. It recomputes the cash
roll-forward live so sliders move numbers, narrative and actions together, but
it **never refits a model** — selection was frozen in Phase 4.

Base settings reproduce the repository figures exactly: funding requirement
AED 103,461, lowest cash AED 2.90m in May 2026.

Regenerate the pack after any pipeline change, or the app will present stale
numbers.

## Acceptance

**T5.2 — automated.** `python -m tests.test_app` — **7/7 pass**. Covers default parity to
repository output, six reference sensitivities, combined multi-lever scenarios,
reset-to-default parity, single-source-of-truth, the decision-status invariant, and
timing-boundary conservation.

**T5.1 and T5.3 — manual, require the deployed app.**

| | Step |
|---|---|
| T5.1 | Push this folder to the existing GitHub repo (replacing the Phase 1 shell), redeploy, confirm the live URL opens the real app — decision status and four metrics, not the dummy-data banner. |
| T5.3 | At a normal laptop viewport, confirm status, recommendation and all four metrics are visible before scrolling. Screenshot as submission evidence. |

`decision_pack.json` must be regenerated after any pipeline change, or the app
will present stale numbers.
