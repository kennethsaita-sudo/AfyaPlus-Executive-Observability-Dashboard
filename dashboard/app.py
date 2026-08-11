"""
Phase 4 — AfyaPlus Executive Observability Dashboard

Serves a single unified monitoring console with the four sections
required by the brief:
    1. System Health        - live UP/DOWN status + quality failure count
    2. Feature Quality Matrix - quality scores per feature + model routing
    3. Drift Vector Status   - summary of the current month's drift report
    4. Budget Capital Utilisation - spend vs. daily/monthly caps

Plus a /metrics endpoint exposing Prometheus-scrapeable output.

Run with:
    uvicorn app:app --reload
Then open http://127.0.0.1:8000/dashboard
"""

import json
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Gauge, generate_latest

from data_sources import find_latest

app = FastAPI(title="AfyaPlus Executive Observability Dashboard")

DASHBOARD_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=DASHBOARD_DIR / "static"), name="static")
templates = Jinja2Templates(directory=DASHBOARD_DIR / "templates")

# ---------------------------------------------------------------
# Budget caps — no figures were specified in the brief, so these
# are ASSUMED placeholder values. Document/adjust them for your
# actual deployment before treating the utilisation % as real.
# ---------------------------------------------------------------
DAILY_BUDGET_CAP_USD = 5.00
MONTHLY_BUDGET_CAP_USD = 100.00


@app.get("/")
def root():
    return {"status": "UP"}


# ---------------------------------------------------------------
# Data loading — each section is independent, so one missing file
# doesn't take down the whole dashboard. Every loader returns a
# dict with an "available" flag the template checks.
# ---------------------------------------------------------------

def load_quality_data():
    path = find_latest("quality_gate_*.csv")
    if path is None:
        return {"available": False, "path": None}

    df = pd.read_csv(path)
    return {
        "available": True,
        "path": str(path),
        "rows": df.to_dict(orient="records"),
        "total_evaluated": len(df),
        "fail_count": int((df["quality_status"] == "FAIL").sum()),
        "pass_count": int((df["quality_status"] == "PASS").sum()),
    }


def load_routing_data():
    # Prefer the fuller structural_savings_summary (has 30-day
    # projections); fall back to the plain routing_recommendation
    # if savings_analysis.py hasn't been run with that step yet.
    path = find_latest("structural_savings_summary_*.csv", phase_subfolder="cost")
    if path is None:
        path = find_latest("routing_recommendation_*.csv", phase_subfolder="cost")
    if path is None:
        return {"available": False, "path": None}

    df = pd.read_csv(path)
    return {
        "available": True,
        "path": str(path),
        "rows": df.to_dict(orient="records"),
    }


def load_drift_data():
    trend_path = find_latest("drift_trend_table.csv", phase_subfolder="drift")
    alerts_path = find_latest("drift_alerts.json", phase_subfolder="drift")

    if trend_path is None and alerts_path is None:
        return {"available": False}

    result = {"available": True}

    if trend_path is not None:
        trend_df = pd.read_csv(trend_path)
        result["trend_rows"] = trend_df.to_dict(orient="records")
        result["latest_month"] = trend_df.to_dict(orient="records")[-1] if len(trend_df) else None
        result["trend_path"] = str(trend_path)
    else:
        result["trend_rows"] = []
        result["latest_month"] = None

    if alerts_path is not None:
        with open(alerts_path, "r", encoding="utf-8") as f:
            result["alert_log"] = json.load(f)
        result["alerts_path"] = str(alerts_path)
    else:
        result["alert_log"] = None

    return result


def load_cost_data():
    path = find_latest("cost_projection_30day_*.csv", phase_subfolder="cost")
    if path is None:
        return {"available": False}

    df = pd.read_csv(path)
    total_30day = float(df["cost_usd"].sum())
    daily_avg = total_30day / 30 if len(df) else 0.0

    daily_pct = min(100.0, (daily_avg / DAILY_BUDGET_CAP_USD) * 100) if DAILY_BUDGET_CAP_USD else 0
    monthly_pct = min(100.0, (total_30day / MONTHLY_BUDGET_CAP_USD) * 100) if MONTHLY_BUDGET_CAP_USD else 0

    return {
        "available": True,
        "path": str(path),
        "total_30day_usd": round(total_30day, 2),
        "daily_avg_usd": round(daily_avg, 2),
        "daily_cap_usd": DAILY_BUDGET_CAP_USD,
        "monthly_cap_usd": MONTHLY_BUDGET_CAP_USD,
        "daily_pct": round(daily_pct, 1),
        "monthly_pct": round(monthly_pct, 1),
        "daily_over_cap": daily_avg > DAILY_BUDGET_CAP_USD,
        "monthly_over_cap": total_30day > MONTHLY_BUDGET_CAP_USD,
    }


@app.get("/dashboard")
def dashboard(request: Request):
    quality = load_quality_data()
    routing = load_routing_data()
    drift = load_drift_data()
    cost = load_cost_data()

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "quality": quality,
            "routing": routing,
            "drift": drift,
            "cost": cost,
        },
    )


# ---------------------------------------------------------------
# Prometheus metrics endpoint
# ---------------------------------------------------------------
@app.get("/metrics")
def metrics():
    registry = CollectorRegistry()

    up_gauge = Gauge(
        "afyaplus_up", "Whether the dashboard service is up (1=up)", registry=registry
    )
    up_gauge.set(1)

    quality = load_quality_data()
    if quality["available"]:
        Gauge(
            "afyaplus_quality_gate_pass_total",
            "Number of model/feature pairs that PASSed the quality gate",
            registry=registry,
        ).set(quality["pass_count"])

        Gauge(
            "afyaplus_quality_gate_fail_total",
            "Number of model/feature pairs that FAILed the quality gate",
            registry=registry,
        ).set(quality["fail_count"])

    cost = load_cost_data()
    if cost["available"]:
        Gauge(
            "afyaplus_cost_30day_usd",
            "Projected 30-day spend in USD",
            registry=registry,
        ).set(cost["total_30day_usd"])

        Gauge(
            "afyaplus_cost_daily_avg_usd",
            "Average daily spend in USD",
            registry=registry,
        ).set(cost["daily_avg_usd"])

        Gauge(
            "afyaplus_budget_daily_utilisation_pct",
            "Daily budget utilisation as a percentage of the cap",
            registry=registry,
        ).set(cost["daily_pct"])

        Gauge(
            "afyaplus_budget_monthly_utilisation_pct",
            "Monthly budget utilisation as a percentage of the cap",
            registry=registry,
        ).set(cost["monthly_pct"])

    drift = load_drift_data()
    if drift["available"] and drift.get("alert_log"):
        drift_detected_gauge = Gauge(
            "afyaplus_drift_detected",
            "Whether drift has been detected (1=yes, 0=no)",
            registry=registry,
        )
        drift_detected_gauge.set(1 if drift["alert_log"].get("first_drift_detected") else 0)

    return Response(content=generate_latest(registry), media_type=CONTENT_TYPE_LATEST)
