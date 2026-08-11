"""
Phase 3 — 30-Day Cost Projection Simulation

Simulates 30 days of production traffic through the AfyaPlus
backend, split 75% llama3.1 / 25% mistral (mirrors the brief's
75% gpt-4o-mini / 25% gpt-4o canary split), spread across the three
delivery channels (USSD, Mobile App, Web Portal).

Outputs (written to OUTPUT_DIR, each timestamped):
    cost_projection_30day_<ts>.csv   - one row per simulated request
    cost_by_feature_<ts>.csv         - total spend grouped by feature
    cost_by_model_<ts>.csv           - total spend grouped by model
"""

import os
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

from pricing import MODEL_PRICING, cost_per_request
from output_utils import resolve_output_dir

# ---------------------------------------------------------------
# Output directory
# ---------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = resolve_output_dir(Path(BASE_DIR) / "outputs", subfolder="cost")
print(f"OUTPUT_DIR = {OUTPUT_DIR}")

# ---------------------------------------------------------------
# Simulation parameters
# ---------------------------------------------------------------
np.random.seed(42)  # reproducible runs — remove/change to re-randomize

DAYS = 30
REQUESTS_PER_DAY = 1000

MODELS = list(MODEL_PRICING.keys())     # ["llama3.1", "mistral"]
MODEL_SPLIT = [0.75, 0.25]              # 75% / 25% canary split

FEATURES = ["USSD", "Mobile App", "Web Portal"]

records = []

for day in range(1, DAYS + 1):
    for _ in range(REQUESTS_PER_DAY):

        model = np.random.choice(MODELS, p=MODEL_SPLIT)
        feature = np.random.choice(FEATURES)

        # Input/output tokens simulated separately since they're
        # priced differently (see pricing.py) — this is more
        # realistic than a single flat "tokens" figure.
        input_tokens = int(np.random.randint(500, 2000))
        output_tokens = int(np.random.randint(100, 1000))

        cost = cost_per_request(model, input_tokens, output_tokens)

        records.append([
            day,
            model,
            feature,
            input_tokens,
            output_tokens,
            input_tokens + output_tokens,
            cost,
        ])

df = pd.DataFrame(
    records,
    columns=[
        "day",
        "model",
        "feature",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "cost_usd",
    ],
)

# ---------------------------------------------------------------
# Save outputs
# ---------------------------------------------------------------
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

results_csv = OUTPUT_DIR / f"cost_projection_30day_{timestamp}.csv"
df.to_csv(results_csv, index=False)
print(f"SUCCESS: {results_csv}")

feature_cost = (
    df.groupby("feature")["cost_usd"]
    .sum()
    .reset_index()
    .sort_values("cost_usd", ascending=False)
)
feature_csv = OUTPUT_DIR / f"cost_by_feature_{timestamp}.csv"
feature_cost.to_csv(feature_csv, index=False)
print(f"SUCCESS: {feature_csv}")

model_cost = (
    df.groupby("model")["cost_usd"]
    .sum()
    .reset_index()
    .sort_values("cost_usd", ascending=False)
)
model_csv = OUTPUT_DIR / f"cost_by_model_{timestamp}.csv"
model_cost.to_csv(model_csv, index=False)
print(f"SUCCESS: {model_csv}")

# ---------------------------------------------------------------
# Console report
# ---------------------------------------------------------------
print("\n" + "=" * 60)
print("30-DAY TOTAL SPEND BY MODEL")
print("=" * 60)
print(model_cost.to_string(index=False))

print("\n" + "=" * 60)
print("30-DAY TOTAL SPEND BY FEATURE")
print("=" * 60)
print(feature_cost.to_string(index=False))

print(
    f"\nGRAND TOTAL (30 days, {REQUESTS_PER_DAY} req/day, "
    f"{DAYS * REQUESTS_PER_DAY} requests): ${df['cost_usd'].sum():,.2f}"
)
