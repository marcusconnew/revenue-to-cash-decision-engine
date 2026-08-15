"""
Week 6 Capstone — B2B Revenue-to-Cash Early Warning and Decision Engine
Phase 1: minimal Streamlit deployment proof.

Purpose (charter v1.0.1, §10 Phase 1, acceptance test T5.1):
confirm that the repository, the pinned dependency set and Streamlit
Community Cloud all cooperate before any pipeline work begins.

Every number on this page is dummy data. No model, no pipeline, no
synthetic data pack exists yet. The §6 page structure is stubbed only so
that Phase 6 extends this file rather than replacing it.

All smoke checks are wrapped so that a dependency failure is *reported*
rather than crashing the app — a crashed app would fail T5.1 without
telling us which dependency caused it.
"""

from __future__ import annotations

import importlib.metadata as metadata
import platform
import sys
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

APP_VERSION = "phase1-0.1.0"
CHARTER_VERSION = "v1.0.1 (frozen 7 August 2026)"

REQUIRED_PACKAGES = [
    "streamlit",
    "pandas",
    "numpy",
    "statsmodels",
    "scikit-learn",
    "xgboost",
    "plotly",
    "openpyxl",
]

st.set_page_config(
    page_title="Revenue-to-Cash Decision Engine — deployment proof",
    page_icon="•",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Dummy data (Phase 1 only — replaced by the §4 synthetic pack in Phase 3)
# ---------------------------------------------------------------------------

@st.cache_data
def dummy_revenue_history() -> pd.Series:
    """84 months of plausible-looking dummy revenue, Jan 2019 – Dec 2025.

    Deliberately simple and deterministic. This is not the synthetic
    data-generating process; that is defined in Phase 3 to the §4 contract.
    """
    rng = np.random.default_rng(20260807)
    index = pd.date_range("2019-01-01", "2025-12-01", freq="MS")
    trend = np.linspace(1_800_000, 2_950_000, len(index))
    seasonal = 180_000 * np.sin(np.arange(len(index)) * 2 * np.pi / 12)
    noise = rng.normal(0, 70_000, len(index))
    return pd.Series((trend + seasonal + noise).round(0), index=index, name="dummy_revenue")


# ---------------------------------------------------------------------------
# Environment and dependency checks
# ---------------------------------------------------------------------------

def environment_report() -> pd.DataFrame:
    rows = []
    for package in REQUIRED_PACKAGES:
        try:
            rows.append({"Package": package, "Version": metadata.version(package), "Status": "OK"})
        except Exception as exc:  # noqa: BLE001 — report, never crash
            rows.append({"Package": package, "Version": "—", "Status": f"NOT FOUND ({exc.__class__.__name__})"})
    return pd.DataFrame(rows)


def check_holt_winters(series: pd.Series) -> dict:
    """Fit is the point, not the import. Holt-Winters at seasonal period 12."""
    try:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fit = ExponentialSmoothing(
                series.astype(float),
                trend="add",
                seasonal="add",
                seasonal_periods=12,
                initialization_method="estimated",
            ).fit()
            forecast = fit.forecast(12)
        return {
            "check": "statsmodels — Holt-Winters fit and 12-month forecast",
            "status": "PASS",
            "detail": f"12 points returned, first = {forecast.iloc[0]:,.0f}",
        }
    except Exception as exc:  # noqa: BLE001
        return {"check": "statsmodels — Holt-Winters", "status": "FAIL", "detail": f"{exc.__class__.__name__}: {exc}"}


def check_xgboost() -> dict:
    """XGBoost is the dependency most likely to fail on a slim container."""
    try:
        import xgboost as xgb
        from sklearn.metrics import mean_absolute_error

        rng = np.random.default_rng(7)
        x = rng.normal(size=(240, 4))
        y = 45 + 6 * x[:, 0] - 3 * x[:, 1] + rng.normal(0, 2, 240)
        model = xgb.XGBRegressor(n_estimators=40, max_depth=3, learning_rate=0.15, verbosity=0)
        model.fit(x[:200], y[:200])
        mae = mean_absolute_error(y[200:], model.predict(x[200:]))
        return {
            "check": "xgboost — regressor fit and predict",
            "status": "PASS",
            "detail": f"holdout MAE {mae:.2f} on dummy features",
        }
    except Exception as exc:  # noqa: BLE001
        return {"check": "xgboost", "status": "FAIL", "detail": f"{exc.__class__.__name__}: {exc}"}


def check_sarimax(series: pd.Series) -> dict:
    """Heaviest fit in the planned stack — the resource-limit canary."""
    try:
        from statsmodels.tsa.statespace.sarimax import SARIMAX

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fit = SARIMAX(
                series.astype(float),
                order=(1, 1, 1),
                seasonal_order=(1, 1, 0, 12),
                enforce_stationarity=False,
                enforce_invertibility=False,
            ).fit(disp=False)
            forecast = fit.forecast(12)
        return {
            "check": "statsmodels — SARIMA fit and 12-month forecast",
            "status": "PASS",
            "detail": f"12 points returned, first = {forecast.iloc[0]:,.0f}",
        }
    except Exception as exc:  # noqa: BLE001
        return {"check": "statsmodels — SARIMA", "status": "FAIL", "detail": f"{exc.__class__.__name__}: {exc}"}


def check_plotly() -> dict:
    try:
        import plotly.graph_objects as go

        go.Figure(data=go.Scatter(x=[1, 2, 3], y=[1, 4, 9]))
        return {"check": "plotly — figure construction", "status": "PASS", "detail": "figure built"}
    except Exception as exc:  # noqa: BLE001
        return {"check": "plotly", "status": "FAIL", "detail": f"{exc.__class__.__name__}: {exc}"}


def check_openpyxl() -> dict:
    try:
        import io

        buffer = io.BytesIO()
        pd.DataFrame({"month": ["2025-01"], "actual_revenue": [1_000_000]}).to_excel(buffer, index=False)
        round_trip = pd.read_excel(io.BytesIO(buffer.getvalue()))
        return {
            "check": "openpyxl — Excel write and read round trip",
            "status": "PASS",
            "detail": f"{len(round_trip)} row returned",
        }
    except Exception as exc:  # noqa: BLE001
        return {"check": "openpyxl", "status": "FAIL", "detail": f"{exc.__class__.__name__}: {exc}"}


# ---------------------------------------------------------------------------
# Page 1 — Decision (structure only; numbers are placeholders)
# ---------------------------------------------------------------------------

history = dummy_revenue_history()

st.warning(
    "**Phase 1 deployment proof — dummy data.** No pipeline, no model and no synthetic "
    "data pack exist yet. Every figure below is a placeholder proving layout and "
    "dependency availability only.",
    icon="⚠",
)

st.title("B2B Revenue-to-Cash Early Warning and Decision Engine")
st.caption(
    f"Charter {CHARTER_VERSION} · app {APP_VERSION} · "
    f"rendered {datetime.now().strftime('%d %B %Y %H:%M')}"
)

decision_tab, evidence_tab, confidence_tab, assurance_tab = st.tabs(
    ["1 · Decision", "2 · Evidence", "3 · Confidence", "4 · Technical assurance"]
)

with decision_tab:
    st.subheader("Decision status: placeholder — no model has run")
    st.markdown(
        "**Recommendation.** Placeholder text. In the completed build this sentence is "
        "produced by Agent C and states what management should approve, reject or investigate."
    )

    a, b, c, d = st.columns(4)
    a.metric("Expected 2026 revenue", "AED 0", help="Placeholder")
    b.metric("Expected closing cash", "AED 0", help="Placeholder")
    c.metric("Lowest cash month", "—", help="Placeholder")
    d.metric("Funding requirement", "AED 0", help="Placeholder")

    st.divider()
    st.markdown("#### Scenario controls")
    st.caption(
        "Controls sit below the answer, per §6. Wiring is inert in Phase 1 — moving a "
        "slider changes nothing, because there is nothing behind it yet."
    )
    s1, s2, s3 = st.columns(3)
    s1.slider("Revenue growth (%)", -20, 20, 0, disabled=True)
    s2.slider("Billing latency (days)", 0, 60, 15, disabled=True)
    s3.slider("Collection delay (days)", 0, 90, 30, disabled=True)

with evidence_tab:
    st.subheader("Evidence — structure only")
    st.caption("Dummy series, Jan 2019 – Dec 2025. Chart titles state conclusions in the completed build.")
    st.line_chart(history)

with confidence_tab:
    st.subheader("Confidence and limitations — structure only")
    st.markdown(
        "- Decision-status labels by component — Phase 7\n"
        "- Assumptions register — Phase 7\n"
        "- Right-censoring disclosure (§4.6) — Phase 3 onward\n"
        "- Known limitations — Phase 8"
    )

with assurance_tab:
    st.subheader("Technical assurance")
    st.markdown(
        f"**Runtime.** Python {platform.python_version()} · {sys.platform}  \n"
        "This tab is the actual Phase 1 test. Everything else on the page is scaffolding."
    )

    st.markdown("##### Installed dependency versions")
    st.dataframe(environment_report(), hide_index=True, width="stretch")
    st.caption(
        "Once T5.1 passes, pin these exact versions in requirements.txt — that pinned set "
        "becomes the reproducibility baseline supporting T3.6."
    )

    st.markdown("##### Dependency smoke checks")
    st.caption("Imports are not enough. These fit the models the charter actually specifies.")

    if st.button("Run smoke checks", type="primary"):
        with st.spinner("Fitting Holt-Winters, XGBoost, SARIMA…"):
            results = [
                check_holt_winters(history),
                check_xgboost(),
                check_sarimax(history),
                check_plotly(),
                check_openpyxl(),
            ]
        frame = pd.DataFrame(results).rename(
            columns={"check": "Check", "status": "Status", "detail": "Detail"}
        )
        st.dataframe(frame, hide_index=True, width="stretch")

        failures = frame[frame["Status"] == "FAIL"]
        if failures.empty:
            st.success("All checks passed. T5.1 satisfied once this page is reachable at a live URL.")
        else:
            st.error(
                f"{len(failures)} check(s) failed. Record as a technical blocker before "
                "proceeding to Phase 3."
            )
    else:
        st.info("Checks run on demand to keep first paint fast on Community Cloud.")
