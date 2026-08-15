"""
B2B Revenue-to-Cash Early Warning and Decision Engine — deployed application.

Charter deliverable 5, §6. Decision-first: the answer is at the top, controls
sit below it. Acceptance tests T5.1–T5.3.

Reads a decision pack exported by the pipeline. The app recomputes the cash
roll-forward live so the sliders move numbers, narrative and actions together
(T5.2), but it never refits a model — model selection is frozen in Phase 4.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

HERE = Path(__file__).parent
CHARTER = "v1.0.1 (frozen 7 August 2026)"

st.set_page_config(page_title="Revenue-to-Cash Decision Engine",
                   page_icon="•", layout="wide")


@st.cache_data
def load_pack() -> dict:
    return json.loads((HERE / "decision_pack.json").read_text())


@st.cache_data
def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(HERE / f"{name}.csv")


PACK = load_pack()
MONTHS = list(PACK["forecast_revenue"])          # Jan-Dec 2026, the reporting window
HORIZON = PACK["horizon"]                        # Jan 2026 - Dec 2027, the arithmetic window


def shift_receipts(base: dict, extra_days: float) -> pd.Series:
    """Move receipts by `extra_days`, splitting across month boundaries.

    Boundary handling is deliberately asymmetric, because the two ends mean
    different things:

      RIGHT  cash pushed past the end of the arithmetic horizon (December
             2027) is dropped -- it arrives in 2028, beyond anything the
             scenario needs to represent. Cash landing in 2027 is retained by
             the horizon and simply falls outside the 2026 reporting window
             when the projection is cropped.
      LEFT   cash pulled before January 2026 is FLOORED into January, never
             discarded. Opening AR is known outstanding at 31 December 2025,
             so no scenario can make it collect earlier than the forecast
             start; and 2026 revenue cannot be collected before it is earned.

    An earlier version discarded both ends. A -15 day collection scenario
    therefore destroyed AED 1.75m of the AED 6.69m opening-AR book, making the
    optimistic case look worse than the base case for a reason with no
    financial meaning.

    Shifts run across the FULL Jan-2026 to Dec-2027 horizon, then the cash
    projection is cropped to 2026. Shifting an already-cropped 2026 schedule
    was the second half of the same defect: AED 9.46m of 2026 revenue collects
    in 2027, and a faster-collection scenario must be able to pull part of that
    tail back into December rather than being told 2026 receipts are fixed.
    """
    values = pd.Series(base, dtype=float)
    if extra_days == 0:
        return values
    whole, fraction = divmod(extra_days / 30.4375, 1.0)
    whole = int(whole)
    out = pd.Series(0.0, index=values.index)
    last = len(out) - 1
    for i, amount in enumerate(values):
        for target, share in ((i + whole, 1 - fraction), (i + whole + 1, fraction)):
            if share == 0:
                continue
            if target < 0:
                out.iloc[0] += amount * share          # floored at forecast start
            elif target <= last:
                out.iloc[target] += amount * share
            # target > last: beyond December 2027, i.e. 2028 or later, which is
            # further out than any scenario needs to represent
    return out


def project(revenue_change: float, collection_delay: float, billing_delay: float,
            cost_change: float, buffer: float, ar_case: str,
            distribution: bool, relocation: bool) -> pd.DataFrame:
    receipts_key = ("ar_base_ext" if ar_case == "Base — stale AR excluded"
                    else "ar_upside_ext")

    # Segment-wise receipt projection computed by the pipeline over the extended
    # horizon, scaled for the revenue lever and shifted for the timing levers.
    # Reconstructing the lag here with an approximate constant made the app
    # disagree with the analysis it is supposed to present.
    new_business = shift_receipts(
        {m: v * (1 + revenue_change) for m, v in PACK["new_business_receipts_ext"].items()},
        billing_delay + collection_delay)
    ar = shift_receipts(PACK[receipts_key], collection_delay)

    # Crop to the 2026 reporting window only after the arithmetic is done.
    new_business = new_business.iloc[:len(MONTHS)]
    ar = ar.iloc[:len(MONTHS)]

    costs = pd.Series(PACK["operating_costs"], dtype=float) * (1 + cost_change)
    committed = pd.Series(PACK["committed"], dtype=float).copy()
    if not distribution:
        committed.iloc[4] = max(committed.iloc[4] - 1_127_219.91, 0.0)
    if relocation:
        for i in range(1, 10):
            committed.iloc[i] += 379_446.11

    frame = pd.DataFrame({"receipts": new_business.to_numpy() + ar.to_numpy(),
                          "operating_costs": costs.to_numpy(),
                          "committed_payments": committed.to_numpy()}, index=MONTHS)
    frame["net"] = frame["receipts"] - frame["operating_costs"] - frame["committed_payments"]
    frame["opening_cash"] = PACK["opening_cash"] + frame["net"].cumsum().shift(1).fillna(0.0)
    frame["closing_cash"] = frame["opening_cash"] + frame["net"]
    frame["shortfall"] = (buffer - frame["closing_cash"]).clip(lower=0.0)
    return frame


def aed(value: float) -> str:
    return f"AED {value:,.0f}"


# ---------------------------------------------------------------------------

st.title("B2B Revenue-to-Cash Early Warning and Decision Engine")
st.caption(f"Harbourline Technical Services LLC (synthetic) · charter {CHARTER} · "
           "seasonal naïve revenue model · segment-median collection model")

decision, evidence, confidence, assurance = st.tabs(
    ["1 · Decision", "2 · Evidence", "3 · Confidence", "4 · Technical assurance"])

# Presets are explicit Session State updates so switching back to Base genuinely
# restores the scenario controls. Streamlit widgets otherwise preserve their
# existing state across reruns, which can make a changed slider survive a preset switch.
PRESETS = {
    "Base": {"revenue_pct": 0, "collection_delay": 0, "billing_delay": 0,
             "cost_pct": 0, "buffer_m": PACK["buffer"] / 1e6},
    "Upside": {"revenue_pct": 5, "collection_delay": -15, "billing_delay": 0,
               "cost_pct": -2, "buffer_m": PACK["buffer"] / 1e6},
    "Downside": {"revenue_pct": -5, "collection_delay": 30, "billing_delay": 0,
                 "cost_pct": 5, "buffer_m": PACK["buffer"] / 1e6},
}


def apply_preset(name: str) -> None:
    for key, value in PRESETS[name].items():
        st.session_state[key] = value
    st.session_state["active_preset"] = name


def mark_custom() -> None:
    st.session_state["active_preset"] = "Custom"


for _key, _value in PRESETS["Base"].items():
    if _key not in st.session_state:
        st.session_state[_key] = _value
if "active_preset" not in st.session_state:
    st.session_state["active_preset"] = "Base"


with st.sidebar:
    st.markdown("### Scenario controls")

    p1, p2, p3 = st.columns(3)
    p1.button("Base", on_click=apply_preset, args=("Base",))
    p2.button("Upside", on_click=apply_preset, args=("Upside",))
    p3.button("Downside", on_click=apply_preset, args=("Downside",))
    st.caption(f"Active scenario: **{st.session_state['active_preset']}**")
    st.caption("Preset buttons reset the scenario controls below. Plan assumptions remain separate.")

    # Percentage sliders use whole percentage points for display (e.g. 5 = +5%),
    # then convert back to decimals for the calculation.
    revenue_pct = st.slider("Revenue growth", -20, 20, step=1, key="revenue_pct",
                            format="%+d%%", on_change=mark_custom)
    collection_delay = st.slider("Collection delay (days)", -30, 90, step=5,
                                 key="collection_delay", on_change=mark_custom)
    billing_delay = st.slider("Billing latency change (days)", -15, 60, step=5,
                              key="billing_delay", on_change=mark_custom)
    cost_pct = st.slider("Operating cost change *(assumption)*", -10, 20, step=1,
                         key="cost_pct", format="%+d%%", on_change=mark_custom,
                         help="Baseline AED 32.42m is the 2025 profile carried forward. "
                              "No approved 2026 budget exists. +5% moves the funding "
                              "requirement to AED 0.81m.")
    buffer_m = st.slider("Minimum cash buffer (AED m)", 1.0, 6.0, step=0.25,
                         key="buffer_m", on_change=mark_custom)

    revenue_change = revenue_pct / 100.0
    cost_change = cost_pct / 100.0
    buffer = buffer_m * 1e6

    st.markdown("### Plan assumptions")
    st.caption("**These are assumptions, not approved plan.** The base case breaches the "
               "buffer by only about AED 0.10m, so each one can change the decision.")
    distribution = st.checkbox("Founder distribution taken *(assumption)*", value=True,
                               help="Discretionary. Set at the 2021–24 median, AED 1.13m. "
                                    "Deferring it removes the base shortfall.")
    relocation = st.checkbox("Relocation programme repeats *(assumption)*", value=False,
                             help="Observed Feb–Oct 2025 only, AED 3.42m. Treated as "
                                  "non-recurring. If it repeats, funding rises to AED 2.02m.")
    ar_case = st.radio("Opening AR treatment",
                       ["Base — stale AR excluded", "Upside — validated recovery"],
                       help="The upside assumes stale balances are validated as collectable. "
                            "It improves the economics; it does not improve the evidence, so "
                            "the decision status is unchanged.")

frame = project(revenue_change, collection_delay, billing_delay, cost_change,
                buffer, ar_case, distribution, relocation)
funding = float(frame["shortfall"].max())
lowest = float(frame["closing_cash"].min())
lowest_month = frame["closing_cash"].idxmin()
months_below = int((frame["closing_cash"] < buffer).sum())

# Decision status is governed by EVIDENCE QUALITY, not by scenario economics.
# While the opening-AR integrity gate is unresolved, no combination of sliders
# may promote the status to an approval. Improving the modelled outcome does
# not improve what we know.
GATE_UNRESOLVED = PACK["gate"]["status"] != "RECONCILED"
DECISION_STATUS = ("Further validation required" if GATE_UNRESOLVED
                   else "Use for planning")

with decision:
    st.subheader(f"Decision status: {DECISION_STATUS}")
    if funding <= 0:
        headline = (f"On these assumptions the plan holds the {aed(buffer)} buffer in every "
                    f"month of 2026, with {aed(lowest - buffer)} of headroom at its tightest "
                    f"({lowest_month}).")
    elif funding < 500_000:
        headline = (f"The plan **breaches the {aed(buffer)} buffer by {aed(funding)} in "
                    f"{lowest_month}** — it sits on the limit rather than above it, and small "
                    "changes in costs or collection timing move it materially.")
    else:
        headline = (f"Management should secure **{aed(funding)}** of liquidity headroom "
                    f"to protect the buffer, tightest in {lowest_month}.")
    st.markdown(f"**Recommendation.** {headline} "
                f"{aed(PACK['gate']['unreconciled_exposure'])} of cash-application exposure "
                "remains unreconciled, so opening receivables require validation before "
                "any collection of stale balances is relied upon.")

    a, b, c, d = st.columns(4)
    a.metric("2026 revenue", aed(sum(PACK["forecast_revenue"].values()) * (1 + revenue_change)))
    b.metric("Closing cash, Dec", aed(frame["closing_cash"].iloc[-1]))
    c.metric("Lowest cash", aed(lowest), lowest_month, delta_color="off")
    d.metric("Funding requirement", aed(funding),
             f"{months_below} month(s) below buffer",
             delta_color="inverse" if funding else "off")

    figure = go.Figure()
    figure.add_bar(x=MONTHS, y=frame["closing_cash"], name="Closing cash",
                   marker_color=["#c0392b" if v < buffer else "#2c7873"
                                 for v in frame["closing_cash"]])
    figure.add_hline(y=buffer, line_dash="dash", line_color="#c0392b",
                     annotation_text=f"Minimum buffer {aed(buffer)}")
    if months_below == 0:
        chart_title = (f"Plan stays above the {aed(buffer)} buffer — minimum headroom "
                       f"{aed(lowest - buffer)} in {lowest_month}")
    else:
        chart_title = (f"Plan breaches the {aed(buffer)} buffer by {aed(funding)} in "
                       f"{lowest_month} ({months_below} month(s) below)")
    figure.update_layout(
        title=chart_title,
        height=330, margin=dict(t=44, b=8), showlegend=False, yaxis_title="AED")
    st.plotly_chart(figure, width="stretch")

    st.markdown("#### Three priority actions")
    st.table(pd.DataFrame([
        {"#": 1, "Action": "Confirm whether the relocation programme repeats and whether "
                           "the founder distribution is taken",
         "Financial effect": "Spans nil to AED 2.02m", "Owner": "CEO / Board",
         "Deadline": "Before plan approval"},
        {"#": 2, "Action": "Reconcile cash application and aged receivables",
         "Financial effect": f"{aed(PACK['gate']['unreconciled_exposure'])} unreconciled",
         "Owner": "Finance Manager", "Deadline": "31 Jan 2026"},
        {"#": 3, "Action": "Supply an approved 2026 operating-cost budget",
         "Financial effect": "5% cost increase moves requirement to AED 0.81m",
         "Owner": "CFO", "Deadline": "28 Feb 2026"},
    ]).set_index("#"))

    st.warning(
        f"**The base number is not the finding — its fragility is.** At {aed(funding)} the plan "
        "is effectively at the liquidity limit. A 30-day collection delay takes the requirement "
        "to **AED 3.57m**; operating costs 10% above assumption take it to **AED 1.52m**; a "
        f"repeat of the relocation programme takes it to **AED 2.02m**. {aed(PACK['gate']['unreconciled_exposure'])} "
        "of receivables exposure is still unreconciled.\n\n*Figures in bold are **base-case reference "
        "sensitivities**, each measured from default settings. They are not recalculated from "
        "your current scenario — move one slider at a time to see its effect live.*", icon="⚠")

    st.info("**Escalation triggers.** Collection delay beyond 30 days · operating costs "
            "more than 5% above assumption · relocation programme confirmed · "
            "cash-application reconciliation not complete by 31 January.")

    with st.expander("Monthly projection for this scenario"):
        table = frame[["receipts", "operating_costs", "committed_payments",
                       "opening_cash", "closing_cash", "shortfall"]].round(0)
        st.dataframe(table, width="stretch")
        st.caption("Every figure on this page, including the recommendation and the four "
                   "metrics above, derives from this single scenario result.")

with evidence:
    history = load_csv("history")
    trend = go.Figure()
    trend.add_scatter(x=history["month"], y=history["actual_revenue"], name="Actual",
                      line=dict(color="#2c7873"))
    trend.add_scatter(x=history["month"], y=history["budget_revenue"], name="Budget",
                      line=dict(color="#999", dash="dot"))
    trend.add_scatter(x=MONTHS,
                      y=[v * (1 + revenue_change) for v in PACK["forecast_revenue"].values()],
                      name="2026 forecast", line=dict(color="#c0392b", dash="dash"))
    trend.update_layout(title="The 2026 forecast repeats 2025 — the selected model assumes no growth",
                        height=340, margin=dict(t=44, b=8), yaxis_title="AED")
    st.plotly_chart(trend, width="stretch")

    st.markdown("##### Government-linked work is 31% of value but collects 98 days out")
    st.dataframe(load_csv("segment_receipt_projection"), hide_index=True, width="stretch")

    st.markdown("##### Two management choices move the answer more than trading does")
    st.dataframe(load_csv("plan_assumption_sensitivity"), hide_index=True, width="stretch")

with confidence:
    gate = PACK["gate"]
    st.error(f"**Opening AR integrity gate: {gate['status']}.** "
             f"{aed(gate['unreconciled_exposure'])} of cash-application exposure — "
             f"{gate['exposure_share_of_book']:.0%} of the apparent "
             f"{aed(PACK['ar_book'])} receivables book.")
    st.markdown(
        f"The receipt ledger falls {aed(gate['reconciliation_exception'])} short of recorded "
        f"cash, and {aed(gate['unapplied_cash'])} of cash cannot be matched to an invoice. "
        "Some invoices shown as outstanding **may already have been paid**, in which case "
        "that cash is already inside opening cash and must not be forecast again.\n\n"
        f"Consequently {aed(PACK['stale_held_back'])} of stale balances is **held back from "
        "the base case — not written off**, and remains collectable subject to validation.")

    st.markdown("##### Decision status by component")
    st.table(pd.DataFrame([
        {"Component": "Revenue forecast", "Status": "Use with caution",
         "Basis": "Seasonal naïve selected on frozen rules; SARIMA beat it on the 2025 holdout"},
        {"Component": "Collection timing", "Status": "Use with caution",
         "Basis": "Segment median; cannot predict an on-time payment, so aggregate use only"},
        {"Component": "Opening receivables", "Status": "Do not use unvalidated",
         "Basis": "Integrity gate UNRECONCILED"},
        {"Component": "Operating costs", "Status": "Assumption",
         "Basis": "2025 profile carried forward; no approved 2026 budget"},
        {"Component": "Cash roll-forward", "Status": "Reliable",
         "Basis": "Arithmetic reconciles exactly; controls C5.1–C5.7 pass"},
    ]).set_index("Component"))

    st.markdown("##### Known limitations")
    st.markdown(
        "- The revenue model recorded 9.21% WAPE on the 2025 holdout; SARIMA performed better at 5.04%.\n"
        "- 286 invoices are right-censored and excluded, biasing collection history toward "
        "faster payers.\n"
        "- The collection model predicts every invoice late; it is unsuitable for invoice-level "
        "classification.\n"
        "- Operating costs are an assumption, not an approved budget.")

with assurance:
    st.markdown("##### Model selection — both challengers lost to a pre-registered threshold")
    st.dataframe(load_csv("revenue_selection_record"), hide_index=True, width="stretch")
    st.dataframe(load_csv("invoice_selection_record"), hide_index=True, width="stretch")
    st.caption("Thresholds fixed 7 August 2026, before any model ran, and not revisited.")

    st.markdown("##### Backtests")
    st.dataframe(load_csv("revenue_backtest"), hide_index=True, width="stretch")
    st.dataframe(load_csv("invoice_bakeoff"), hide_index=True, width="stretch")

    st.markdown("##### Leakage audit and data quality")
    st.dataframe(load_csv("leakage_audit"), hide_index=True, width="stretch")
    st.dataframe(load_csv("row_accounting"), hide_index=True, width="stretch")
    st.dataframe(load_csv("data_quality_summary"), hide_index=True, width="stretch")

    st.markdown("##### 2026 plan assumptions")
    st.dataframe(load_csv("plan_assumptions_2026"), hide_index=True, width="stretch")
