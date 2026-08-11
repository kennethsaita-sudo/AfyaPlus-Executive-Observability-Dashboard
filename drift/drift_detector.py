"""
Phase 2 — Statistical Drift Detection

For each production month (2, 3), compares that month's data against
Month 1 (the reference/baseline) in two ways:

  1. Evidently AI's DataDriftPreset -> an interactive HTML snapshot
     per month (the brief's required deliverable).
  2. A two-sample Kolmogorov-Smirnov test per tracked column (scipy)
     -> the authoritative source for drift_trend_table.csv and
     drift_alerts.json.

WHY scipy INSTEAD OF PARSING EVIDENTLY'S RESULT DICTIONARY:
Evidently's internal result/snapshot schema has changed significantly
across versions (this script targets 0.7.x's Dataset/DataDefinition/
Report API), so hardcoding a path into its internal structure here
would be fragile. A two-sample KS-test is a standard,
version-independent statistical drift test, so it keeps the alert
log reliable regardless of Evidently's API. Evidently is still used
for exactly what the brief asks for — the HTML snapshots — via its
documented top-level API, which is far more stable across versions
than its internal result structure.

If Evidently fails to import or errors during report generation
(e.g. an API mismatch for your installed version), the script keeps
going and still produces the trend table + alert log via scipy, so
one dependency issue doesn't block the rest of Phase 2.

Outputs:
    month1_report.html / month2_report.html / month3_report.html
    drift_trend_table.csv   - one row per month, mean of each metric
    drift_alerts.json       - first month + column where drift fired
"""

import json
import os
from pathlib import Path

import pandas as pd
from scipy import stats

from output_utils import resolve_output_dir, write_dataframe_csv

# ---------------------------------------------------------------
# Evidently import — guarded, since API paths have changed across
# evidently releases. Written against evidently 0.7.x's current API
# (Dataset/DataDefinition + Report([...]).run() returning a
# snapshot object). HTML reports are skipped (not the whole script)
# if this fails.
# ---------------------------------------------------------------
EVIDENTLY_AVAILABLE = True
try:
    from evidently import Dataset, DataDefinition, Report
    from evidently.presets import DataDriftPreset
except ImportError as e:
    EVIDENTLY_AVAILABLE = False
    print(
        "⚠️  Could not import Evidently AI (Dataset / DataDefinition / "
        "Report / DataDriftPreset).\n"
        "   HTML reports will be SKIPPED — the statistical drift trend\n"
        "   table and alert log will still be generated via scipy.\n"
        f"   Import error: {e}\n"
        "   Fix: `pip install evidently` (check `pip show evidently` — "
        "this script targets evidently 0.7.x's API; older/newer "
        "versions may use different import paths)."
    )

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = resolve_output_dir(Path(BASE_DIR) / "outputs", subfolder="drift")
print(f"OUTPUT_DIR = {OUTPUT_DIR}")

MONTHS = [1, 2, 3]
METRIC_COLUMNS = ["rouge_l", "latency_ms", "input_token_length"]
DRIFT_P_THRESHOLD = 0.05  # standard significance level for the KS test

reference = pd.read_csv(OUTPUT_DIR / "month1.csv")

# Evidently 0.7.x requires a DataDefinition describing column types.
# All three tracked metrics are numerical.
if EVIDENTLY_AVAILABLE:
    schema = DataDefinition(numerical_columns=METRIC_COLUMNS)
    reference_dataset = Dataset.from_pandas(reference, data_definition=schema)

trend_rows = []
first_alert = None  # will hold the FIRST (month, column) that drifted

for month in MONTHS:
    current = pd.read_csv(OUTPUT_DIR / f"month{month}.csv")

    trend_rows.append({
        "month": month,
        **{f"{col}_mean": current[col].mean() for col in METRIC_COLUMNS}
    })

    # -----------------------------------------------------------
    # Evidently HTML snapshot (required deliverable)
    # -----------------------------------------------------------
    if EVIDENTLY_AVAILABLE:
        try:
            current_dataset = Dataset.from_pandas(current, data_definition=schema)

            report = Report([DataDriftPreset()])
            # evidently 0.7.x: run(current_data, reference_data) —
            # positional, current FIRST, reference SECOND. run()
            # returns a snapshot object; save_html is called on
            # THAT, not on `report` itself (report is reusable/
            # stateless across runs in this version).
            snapshot = report.run(current_dataset, reference_dataset)

            html_path = OUTPUT_DIR / f"month{month}_report.html"
            snapshot.save_html(str(html_path))
            print(f"SUCCESS: {html_path}")
        except Exception as e:
            print(f"⚠️  Evidently report failed for month {month}: {e}")

    # -----------------------------------------------------------
    # KS-test drift check (authoritative for the alert log)
    # Month 1 IS the reference, so skip comparing it to itself —
    # that would trivially show p=1.0 / no drift and isn't a real
    # test.
    # -----------------------------------------------------------
    if month == 1:
        continue

    for col in METRIC_COLUMNS:
        stat, p_value = stats.ks_2samp(reference[col], current[col])
        drifted = p_value < DRIFT_P_THRESHOLD

        if drifted and first_alert is None:
            first_alert = {
                "month": month,
                "column": col,
                "ks_statistic": round(float(stat), 4),
                "p_value": round(float(p_value), 6),
                "test": "two-sample Kolmogorov-Smirnov",
                "threshold": DRIFT_P_THRESHOLD,
            }

# ---------------------------------------------------------------
# Save consolidated trend table (ONE file covering all 3 months,
# not three separate per-month files)
# ---------------------------------------------------------------
trend_df = pd.DataFrame(trend_rows)
trend_path = write_dataframe_csv(trend_df, OUTPUT_DIR / "drift_trend_table.csv")
print(f"SUCCESS: {trend_path}")

# ---------------------------------------------------------------
# Save alert log (previously missing entirely)
# ---------------------------------------------------------------
alert_log = {
    "first_drift_detected": first_alert is not None,
    "alert": first_alert,
    "checked_months": MONTHS,
    "checked_columns": METRIC_COLUMNS,
    "test": "two-sample Kolmogorov-Smirnov, each month vs. Month 1 baseline",
    "significance_threshold": DRIFT_P_THRESHOLD,
}

alerts_path = OUTPUT_DIR / "drift_alerts.json"
try:
    with open(alerts_path, "w", encoding="utf-8") as f:
        json.dump(alert_log, f, indent=2)
    print(f"SUCCESS: {alerts_path}")
except (PermissionError, OSError) as e:
    print(f"FAILED SAVE for {alerts_path}: {e}")
    fallback_dir = (
        Path("C:/Temp/afyaplus_outputs_fallback") if os.name == "nt"
        else Path("/tmp/afyaplus_outputs_fallback")
    )
    fallback_dir.mkdir(parents=True, exist_ok=True)
    fallback_path = fallback_dir / "drift_alerts.json"
    with open(fallback_path, "w", encoding="utf-8") as f:
        json.dump(alert_log, f, indent=2)
    print(f"SUCCESS (fallback): {fallback_path}")

# ---------------------------------------------------------------
# Console report
# ---------------------------------------------------------------
print("\n" + "=" * 60)
print("DRIFT TREND TABLE")
print("=" * 60)
print(trend_df.to_string(index=False))

print("\n" + "=" * 60)
print("ALERT LOG")
print("=" * 60)
print(json.dumps(alert_log, indent=2))
