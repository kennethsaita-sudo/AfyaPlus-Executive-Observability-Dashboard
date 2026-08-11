"""
Phase 2 — Simulated 3-Month Production Traffic

Generates three synthetic monthly datasets (month1.csv..month3.csv)
with an intentional, gradual drift baked in across all three tracked
metrics, so drift_detector.py has something real to catch:

    - rouge_l:            slowly DECREASING (quality degrading)
    - latency_ms:         slowly INCREASING (system slowing down)
    - input_token_length: slowly INCREASING (prompts growing)

Month 1 acts as the reference/baseline that drift_detector.py
compares months 2 and 3 against.
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd

from output_utils import resolve_output_dir, write_dataframe_csv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = resolve_output_dir(Path(BASE_DIR) / "outputs", subfolder="drift")
print(f"OUTPUT_DIR = {OUTPUT_DIR}")

np.random.seed(42)  # reproducible runs — change/remove to re-randomize

SIZE = 1000

for month in range(1, 4):
    data = pd.DataFrame({
        "rouge_l": np.clip(
            np.random.normal(0.85 - (month * 0.05), 0.02, size=SIZE),
            0, 1
        ),
        "latency_ms": np.random.normal(
            700 + (month * 250), 50, size=SIZE
        ),
        "input_token_length": np.random.normal(
            120 + (month * 30), 10, size=SIZE
        ),
    })

    path = write_dataframe_csv(data, OUTPUT_DIR / f"month{month}.csv")

    print(
        f"SUCCESS: {path}  "
        f"(rouge_l~{data['rouge_l'].mean():.3f}, "
        f"latency~{data['latency_ms'].mean():.0f}ms, "
        f"input_tokens~{data['input_token_length'].mean():.0f})"
    )
