"""
Phase 3 — Structural Savings Analysis

Required output: "Structural Savings Analysis: dollar reduction from
routing to the lowest-cost model that clears quality gates."

This is the one piece that ties Phase 3 (cost) back to Phase 1
(quality). For each clinical feature, it:
    1. Reads the latest quality_gate_*.csv produced by
       evaluation/evaluate.py
    2. Finds which model(s) PASS the quality gate for that feature
    3. Picks the cheapest PASSing model
    4. Compares its cost against a "no cost-aware routing" baseline
       (always using the most expensive available model)
    5. Projects the resulting $ savings over 30 days of traffic

Outputs:
    routing_recommendation_<ts>.csv         - per-feature routing decision
    structural_savings_summary_<ts>.csv     - same, + 30-day $ projection
"""

import os
import tempfile
from pathlib import Path
from datetime import datetime

import pandas as pd

from pricing import MODEL_PRICING, cost_per_request
from output_utils import resolve_output_dir, find_latest_file

# ---------------------------------------------------------------
# Output directory
# ---------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = Path(BASE_DIR).parent  # .../AfyaPlus Executive Observability Dashboard

OUTPUT_DIR = resolve_output_dir(Path(BASE_DIR) / "outputs", subfolder="cost")
print(f"OUTPUT_DIR = {OUTPUT_DIR}")

# ---------------------------------------------------------------
# Locate the latest Phase 1 quality gate CSV
# ---------------------------------------------------------------
# evaluate.py's own output can itself have fallen back to temp (see
# its resolve_output_dir), so we search everywhere it could plausibly
# have landed rather than hardcoding one path.
search_dirs = [
    PROJECT_ROOT / "evaluation" / "outputs",
    PROJECT_ROOT / "evaluation" / "_fallback_outputs",
    PROJECT_ROOT / "evaluation" / "outputs_old",
    PROJECT_ROOT / "evaluation" / "results",
    Path(tempfile.gettempdir()) / "afyaplus_outputs",
    Path(tempfile.gettempdir()) / "afyaplus_outputs_fallback",
    Path("C:/Temp/afyaplus_outputs"),
]

quality_gate_path = find_latest_file(search_dirs, "quality_gate_*.csv")

if quality_gate_path is None:
    raise FileNotFoundError(
        "Could not find a quality_gate_*.csv from evaluate.py.\n"
        "Run evaluation/evaluate.py first so Phase 1 results exist.\n"
        "Searched:\n" + "\n".join(f"  {d}" for d in search_dirs)
    )

print(f"Using quality gate file: {quality_gate_path}")
quality_df = pd.read_csv(quality_gate_path)

required_cols = {"model", "feature", "quality_status"}
missing = required_cols - set(quality_df.columns)
if missing:
    raise ValueError(
        f"{quality_gate_path.name} is missing expected column(s): "
        f"{missing}. Check evaluate.py's quality_csv output format."
    )

# ---------------------------------------------------------------
# Per-request cost assumption used to RANK models for routing
# ---------------------------------------------------------------
# NOTE: uses representative average token counts, not per-request
# tokens from any single simulated request, since routing decisions
# are made per FEATURE (a design-time choice), not per individual
# request at runtime.
AVG_INPUT_TOKENS = 1000
AVG_OUTPUT_TOKENS = 300

model_avg_cost = {
    model: cost_per_request(model, AVG_INPUT_TOKENS, AVG_OUTPUT_TOKENS)
    for model in MODEL_PRICING
}

# Baseline = always route to the most expensive model available,
# i.e. what you'd pay with NO cost-aware routing at all.
baseline_model = max(model_avg_cost, key=model_avg_cost.get)
baseline_cost = model_avg_cost[baseline_model]

# ---------------------------------------------------------------
# Determine the cheapest PASSing model per feature
# ---------------------------------------------------------------
rows = []
features = sorted(quality_df["feature"].unique())

for feature in features:
    feature_rows = quality_df[quality_df["feature"] == feature]
    passing = feature_rows[feature_rows["quality_status"] == "PASS"]

    if passing.empty:
        rows.append([
            feature,
            "NONE",
            None,
            baseline_model,
            baseline_cost,
            0.0,
            0.0,
            "NO MODEL CLEARS QUALITY GATE for this feature — "
            "route to human-in-the-loop review, not the cheapest model.",
        ])
        continue

    passing_models = [m for m in passing["model"].unique() if m in model_avg_cost]

    if not passing_models:
        rows.append([
            feature,
            "NONE",
            None,
            baseline_model,
            baseline_cost,
            0.0,
            0.0,
            "Passing model(s) found but not present in pricing.py — "
            "add pricing for: " + ", ".join(passing["model"].unique()),
        ])
        continue

    cheapest_model = min(passing_models, key=lambda m: model_avg_cost[m])
    cheapest_cost = model_avg_cost[cheapest_model]

    savings_per_request = baseline_cost - cheapest_cost
    savings_pct = (
        (savings_per_request / baseline_cost * 100) if baseline_cost else 0.0
    )

    rows.append([
        feature,
        cheapest_model,
        cheapest_cost,
        baseline_model,
        baseline_cost,
        savings_per_request,
        savings_pct,
        "Route to cheapest model clearing the quality gate.",
    ])

routing_df = pd.DataFrame(
    rows,
    columns=[
        "feature",
        "recommended_model",
        "recommended_cost_per_request_usd",
        "baseline_model",
        "baseline_cost_per_request_usd",
        "savings_per_request_usd",
        "savings_pct",
        "note",
    ],
)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

routing_path = OUTPUT_DIR / f"routing_recommendation_{timestamp}.csv"
routing_df.to_csv(routing_path, index=False)
print(f"SUCCESS: {routing_path}")

print("\n" + "=" * 60)
print("ROUTING RECOMMENDATION BY FEATURE")
print("=" * 60)
print(routing_df.to_string(index=False))

# ---------------------------------------------------------------
# Project savings over 30 days
# ---------------------------------------------------------------
# Requests are assumed split evenly across the features observed in
# the quality gate file, since evaluate.py's dataset doesn't carry
# real production volume figures. Adjust REQUESTS_PER_DAY / DAYS to
# match simulate_costs.py if you change those there.
REQUESTS_PER_DAY = 1000
DAYS = 30
TOTAL_REQUESTS = REQUESTS_PER_DAY * DAYS

n_features = max(len(features), 1)
requests_per_feature = TOTAL_REQUESTS / n_features

routing_df["projected_requests_30day"] = requests_per_feature
routing_df["projected_savings_30day_usd"] = (
    routing_df["savings_per_request_usd"] * routing_df["projected_requests_30day"]
)

summary_path = OUTPUT_DIR / f"structural_savings_summary_{timestamp}.csv"
routing_df.to_csv(summary_path, index=False)
print(f"SUCCESS: {summary_path}")

total_savings = routing_df["projected_savings_30day_usd"].sum()

print("\n" + "=" * 60)
print("30-DAY STRUCTURAL SAVINGS PROJECTION")
print("=" * 60)
print(routing_df.to_string(index=False))

print(
    f"\nBaseline (no cost-aware routing): always use {baseline_model} "
    f"(${baseline_cost:.6f}/request)"
)
print(f"TOTAL PROJECTED 30-DAY STRUCTURAL SAVINGS: ${total_savings:,.2f}")
