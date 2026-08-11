import os
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import ollama

from evaluation_data import evaluation_dataset
from metrics import bleu_score, rouge_l, token_f1
from llm_judge import judge


# =====================================================
# BASE DIRECTORY
# =====================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

print(f"BASE_DIR = {BASE_DIR}")


# =====================================================
# OUTPUT DIRECTORY RESOLVER
# =====================================================
# Troubleshooting found that on this machine, Windows Defender's
# "Controlled Folder Access" (confirmed via testing, personal
# non-domain laptop) blocks writes under %LOCALAPPDATA%\Temp
# specifically — even a bare `open()` call, not just pandas — while
# C:\Temp remains fully writable every time it's been tested. So
# C:\Temp is now the PRIMARY target, not a last-resort fallback.

import uuid


def _real_write_test(candidate: Path) -> None:
    """Do a write that actually exercises real file creation (open,
    write, flush, fsync, close), not just a trivial touch — trivial
    writes have been seen to slip through Controlled Folder Access
    even when real writes are blocked.
    """
    probe = candidate / f".write_test_{uuid.uuid4().hex}.tmp"
    with open(probe, "w", encoding="utf-8", newline="") as f:
        f.write("col_a,col_b\n1,2\n" * 50)
        f.flush()
        os.fsync(f.fileno())
    probe.unlink()


def resolve_output_dir(preferred: Path) -> Path:
    """Return a directory we can actually write CSVs to.

    C:\\Temp is tried FIRST — confirmed reliable on this machine.
    %LOCALAPPDATA%\\Temp is deliberately NOT used as a candidate here,
    since it was confirmed blocked even for plain open() calls.
    `preferred` (the project's own outputs folder) is tried as a
    secondary option in case Controlled Folder Access gets disabled
    or reconfigured later.
    """

    candidates = []
    if os.name == "nt":
        candidates.append(Path("C:/Temp/afyaplus_outputs"))
    candidates.append(preferred)

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            _real_write_test(candidate)

            if candidate != preferred:
                print(
                    f"\n⚠️  NOTE: Writing output to:\n    {candidate}\n"
                    f"   instead of the project folder:\n    {preferred}\n"
                    f"   This is a deliberate workaround for Windows "
                    f"Defender's 'Controlled Folder Access' (or similar "
                    f"policy) blocking writes inside the project folder. "
                    f"See notes at the bottom of this script to fix it "
                    f"permanently and restore the original output "
                    f"location.\n"
                )

            return candidate

        except (PermissionError, OSError) as e:
            print(f"Cannot write to {candidate}: {e}")
            continue

    raise RuntimeError(
        "No writable output directory found. Tried: "
        + ", ".join(str(c) for c in candidates)
    )


OUTPUT_DIR = resolve_output_dir(Path(BASE_DIR) / "outputs")
print(f"OUTPUT_DIR = {OUTPUT_DIR}")


# =====================================================
# QUALITY GATE
# =====================================================

def check_quality_gate(
    rouge_l_score,
    token_f1_score,
    alignment_score
):
    if (
        rouge_l_score >= 0.70
        and token_f1_score >= 0.70
        and alignment_score >= 4.0
    ):
        return "PASS"

    return "FAIL"


# =====================================================
# MODELS
# =====================================================

models = [
    "llama3.1:8b",
    "mistral"
]


# =====================================================
# EVALUATION LOOP
# =====================================================

results = []

for model in models:

    print("\n" + "=" * 60)
    print(f"Evaluating {model}")
    print("=" * 60)

    for row in evaluation_dataset:

        question = row["question"]
        reference = row["clinical_reference"]
        feature = row["feature"]

        try:

            response = ollama.chat(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": question
                    }
                ]
            )

            answer = response["message"]["content"]

            bleu = bleu_score(
                reference,
                answer
            )

            rouge = rouge_l(
                reference,
                answer
            )

            f1 = token_f1(
                reference,
                answer
            )

            judge_scores = judge(
                reference,
                answer
            )

            quality_status = check_quality_gate(
                rouge,
                f1,
                judge_scores["alignment"]
            )

            results.append(
                {
                    "model": model,
                    "feature": feature,
                    "question": question,
                    "reference": reference,
                    "answer": answer,
                    "bleu": bleu,
                    "rouge_l": rouge,
                    "token_f1": f1,
                    "correctness": judge_scores["correctness"],
                    "groundedness": judge_scores["groundedness"],
                    "relevance": judge_scores["relevance"],
                    "helpfulness": judge_scores["helpfulness"],
                    "alignment": judge_scores["alignment"],
                    "quality_status": quality_status
                }
            )

            print(f"✓ {question}")

        except Exception as e:

            print(f"✗ {question}")
            print(f"ERROR: {e}")


# =====================================================
# DATAFRAME
# =====================================================

df = pd.DataFrame(results)

print("\nRows Collected:", len(df))

if len(df) == 0:
    raise ValueError(
        "No evaluation results generated. Check that Ollama is running "
        "and that both models are pulled (`ollama list`)."
    )

# ====================================================
# OUTPUT FILE PATHS
# ====================================================

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

results_csv = OUTPUT_DIR / f"test_results_{timestamp}.csv"
judge_csv = OUTPUT_DIR / f"judge_scores_{timestamp}.csv"
quality_csv = OUTPUT_DIR / f"quality_gate_{timestamp}.csv"
summary_csv = OUTPUT_DIR / f"model_summary_{timestamp}.csv"
aggregation_csv = OUTPUT_DIR / f"gate_aggregation_{timestamp}.csv"

print("\nOUTPUT FILES")
print(results_csv)
print(judge_csv)
print(quality_csv)
print(summary_csv)
print(aggregation_csv)


# =====================================================
# SAFE CSV WRITER
# =====================================================

def _dataframe_to_csv_string(dataframe) -> str:
    """Render the dataframe to CSV entirely in memory (no file I/O
    at all here) — this is just pandas' own CSV-formatting logic
    with no path involved, so it can never hit a permissions error.
    """
    return dataframe.to_csv(index=False)


def _write_text_bypassing_pandas_io(csv_text: str, filepath: Path) -> None:
    """Write CSV text using a bare built-in `open()` call instead of
    pandas' `to_csv(path, ...)`.

    Root cause found in testing: pandas' `to_csv(path)` opens the
    file through its own internal `io.common.get_handle()` code
    path. On this machine, something (endpoint security software —
    Controlled Folder Access or similar) blocks THAT specific call
    pattern with PermissionError, even in folders where a plain
    `open()`/`write()`/`close()` call succeeds every time (verified
    repeatedly during troubleshooting). Using plain `open()` here
    sidesteps pandas' internal handle-opening logic entirely.
    """
    # utf-8-sig = UTF-8 with a BOM, so Excel opens accented/special
    # characters correctly — matches the encoding the old code asked
    # pandas for, just applied manually here instead.
    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        f.write(csv_text)


def write_csv_text(dataframe, filepath):

    filepath = Path(filepath)

    print("\n" + "=" * 60)
    print("SAVE ATTEMPT")
    print("=" * 60)

    print(f"File: {filepath}")
    print(f"Type: {type(dataframe)}")

    try:
        print(f"Rows: {len(dataframe)}")
        print(f"Columns: {list(dataframe.columns)}")
    except Exception as e:
        print(f"DATAFRAME ERROR: {e}")

    # Build the CSV content in memory FIRST — this step never
    # touches the filesystem, so it can't be the thing that fails.
    csv_text = _dataframe_to_csv_string(dataframe)

    try:

        _write_text_bypassing_pandas_io(csv_text, filepath)

        print(f"SUCCESS: {filepath}")

    except (PermissionError, OSError) as e:

        # Last-ditch fallback: if something changes mid-run (e.g. a
        # cloud sync client grabs a lock) and OUTPUT_DIR becomes
        # unwritable partway through, drop this specific file next
        # to the script under a "_fallback" folder instead of dying.
        print("\nFAILED SAVE — retrying in fallback location")
        print(f"File: {filepath}")
        print(f"Exception Type: {type(e).__name__}")
        print(f"Exception: {e}")

        # IMPORTANT: this must be OUTSIDE the project folder tree.
        # A fallback under BASE_DIR would hit the exact same
        # Controlled-Folder-Access block that caused this except
        # branch to run in the first place.
        # IMPORTANT: must NOT be under %LOCALAPPDATA%\Temp — that
        # path is confirmed blocked on this machine even for plain
        # open() calls. C:\Temp is confirmed reliable instead.
        fallback_dir = Path("C:/Temp/afyaplus_outputs_fallback") if os.name == "nt" \
            else Path("/tmp/afyaplus_outputs_fallback")
        fallback_dir.mkdir(parents=True, exist_ok=True)
        fallback_path = fallback_dir / filepath.name

        _write_text_bypassing_pandas_io(csv_text, fallback_path)

        print(f"SUCCESS (fallback): {fallback_path}")


# =====================================================
# FULL RESULTS
# =====================================================

write_csv_text(
    df,
    results_csv
)


# =====================================================
# LLM JUDGE RESULTS
# =====================================================

judge_df = df[
    [
        "model",
        "feature",
        "correctness",
        "groundedness",
        "relevance",
        "helpfulness",
        "alignment"
    ]
]

write_csv_text(
    judge_df,
    judge_csv
)


# =====================================================
# QUALITY GATE RESULTS
# =====================================================

quality_df = df[
    [
        "model",
        "feature",
        "rouge_l",
        "token_f1",
        "alignment",
        "quality_status"
    ]
]

write_csv_text(
    quality_df,
    quality_csv
)


# =====================================================
# MODEL SUMMARY
# =====================================================

summary = (
    df.groupby(
        ["model", "feature"]
    )
    .mean(numeric_only=True)
    .reset_index()
)

write_csv_text(
    summary,
    summary_csv
)


# =====================================================
# AGGREGATION
# =====================================================

gate_summary = (
    df.groupby(
        ["model", "feature", "quality_status"]
    )
    .size()
    .reset_index(name="count")
)

write_csv_text(
    gate_summary,
    aggregation_csv
)

# =====================================================
# REPORT
# =====================================================

print("\n")
print("=" * 60)
print("MODEL COMPARISON SUMMARY")
print("=" * 60)

print(summary)

print("\n")
print("=" * 60)
print("QUALITY GATE SUMMARY")
print("=" * 60)

print(gate_summary)

print("\n")
print("=" * 60)
print("EVALUATION COMPLETE")
print("=" * 60)

print(f"Rows Evaluated: {len(df)}")
print(f"Models Tested: {df['model'].nunique()}")
print(f"Features Tested: {df['feature'].nunique()}")
print(f"Questions Evaluated: {df['question'].nunique()}")

print("\nGenerated Files:")
print(results_csv)
print(judge_csv)
print(quality_csv)
print(summary_csv)
print(aggregation_csv)

# =====================================================
# NOTE ON THE PERMISSION ERRORS SEEN DURING TROUBLESHOOTING:
#
# It turned out to be more specific than "this folder is blocked."
# A plain `open(path, "w")` call succeeded every single time, in
# every folder tested (project folder, system Temp, even a fresh
# fallback folder) — but pandas' own `dataframe.to_csv(path)` failed
# with PermissionError in ALL of those same folders. That points to
# endpoint security software (Controlled Folder Access or similar)
# blocking pandas' internal file-opening code path specifically,
# not the folder location itself.
#
# Fix applied: `write_csv_text()` now builds the CSV as a string in
# memory using pandas (`dataframe.to_csv(index=False)`, no path —
# this never touches disk) and then writes that string out with a
# bare `open()`/`.write()` call, which has been reliable throughout
# testing. This should work regardless of which folder OUTPUT_DIR
# resolves to.
#
# If you still see failures after this change, it likely means even
# plain `open()` writes are now being blocked too (a stricter policy
# than what was seen during troubleshooting) — in that case, check:
#   1. Windows Security -> Virus & threat protection -> Ransomware
#      protection -> Controlled folder access -> "Allow an app"
#      -> add your venv's python.exe (exact path from `Get-Command
#      python` while your venv is active)
#   2. Whether this is a managed/work device with additional
#      endpoint security (CrowdStrike, Sophos, etc.) that your IT
#      admin would need to whitelist python.exe for
# =====================================================
