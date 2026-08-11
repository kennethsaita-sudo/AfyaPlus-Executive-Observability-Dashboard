"""
Phase 3 — Cost-Per-Request Comparison Across Prompt Configurations

Required output: "Cost-Per-Request Comparison: gpt-4o-mini vs. gpt-4o
across prompt configurations" (substituted here with llama3.1 /
mistral — see pricing.py's note on this).

Compares the cost of a single request under two prompt strategies —
a verbose Chain-of-Thought system prompt vs. a short direct prompt —
for each model, holding the average model *response* length constant.
This isolates the savings that come purely from trimming the SYSTEM
PROMPT, independent of the 30-day traffic mix simulated in
simulate_costs.py.

Outputs:
    cost_per_request_by_prompt_config_<ts>.csv  - long-form comparison
    prompt_config_savings_summary_<ts>.csv      - per-model $ / % savings
"""

import os
from pathlib import Path
from datetime import datetime

import pandas as pd

from pricing import MODEL_PRICING, PROMPT_CONFIGS, cost_per_request
from output_utils import resolve_output_dir

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = resolve_output_dir(Path(BASE_DIR) / "outputs", subfolder="cost")
print(f"OUTPUT_DIR = {OUTPUT_DIR}")

# Held constant across configs so the comparison isolates the
# system-prompt token savings rather than mixing in response-length
# variance.
AVG_OUTPUT_TOKENS = 300

rows = []
for model in MODEL_PRICING:
    for config_name, prompt_tokens in PROMPT_CONFIGS.items():
        cost = cost_per_request(
            model,
            input_tokens=prompt_tokens,
            output_tokens=AVG_OUTPUT_TOKENS,
        )
        rows.append([model, config_name, prompt_tokens, AVG_OUTPUT_TOKENS, cost])

df = pd.DataFrame(
    rows,
    columns=[
        "model",
        "prompt_config",
        "prompt_tokens",
        "output_tokens",
        "cost_per_request_usd",
    ],
)

# Per-model savings summary: CoT cost vs. direct-prompt cost
pivot = df.pivot(
    index="model", columns="prompt_config", values="cost_per_request_usd"
)
pivot["savings_per_request_usd"] = (
    pivot["cot_system_prompt"] - pivot["direct_prompt"]
)
pivot["savings_pct"] = (
    pivot["savings_per_request_usd"] / pivot["cot_system_prompt"] * 100
)
pivot = pivot.reset_index()

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

comparison_path = OUTPUT_DIR / f"cost_per_request_by_prompt_config_{timestamp}.csv"
df.to_csv(comparison_path, index=False)
print(f"SUCCESS: {comparison_path}")

summary_path = OUTPUT_DIR / f"prompt_config_savings_summary_{timestamp}.csv"
pivot.to_csv(summary_path, index=False)
print(f"SUCCESS: {summary_path}")

print("\n" + "=" * 60)
print("COST PER REQUEST BY PROMPT CONFIGURATION")
print("=" * 60)
print(df.to_string(index=False))

print("\n" + "=" * 60)
print("PER-REQUEST SAVINGS: CoT PROMPT -> DIRECT PROMPT")
print("=" * 60)
print(pivot.to_string(index=False))
