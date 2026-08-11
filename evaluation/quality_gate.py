# quality_gate.py

import pandas as pd

# =====================================================
# QUALITY THRESHOLDS
# =====================================================

ROUGE_THRESHOLD = 0.70
TOKEN_F1_THRESHOLD = 0.70
ALIGNMENT_THRESHOLD = 4.0


# =====================================================
# FUNCTION USED BY evaluate.py
# =====================================================

def check_quality_gate(
    rouge_l_score,
    token_f1_score,
    alignment_score
):
    """
    Returns PASS or FAIL
    """

    if (
        rouge_l_score >= ROUGE_THRESHOLD
        and token_f1_score >= TOKEN_F1_THRESHOLD
        and alignment_score >= ALIGNMENT_THRESHOLD
    ):
        return "PASS"

    return "FAIL"


# =====================================================
# RUN REPORT ONLY IF CSV EXISTS
# =====================================================

if __name__ == "__main__":

    try:

        df = pd.read_csv(
            "full_evaluation_results.csv"
        )

        summary = (
            df.groupby(
                ["model", "feature"]
            )
            .agg({
                "bleu": "mean",
                "rouge_l": "mean",
                "token_f1": "mean",
                "correctness": "mean",
                "groundedness": "mean",
                "relevance": "mean",
                "helpfulness": "mean",
                "alignment": "mean"
            })
            .reset_index()
        )

        summary["status"] = summary.apply(
            lambda row: check_quality_gate(
                row["rouge_l"],
                row["token_f1"],
                row["alignment"]
            ),
            axis=1
        )

        summary.to_csv(
            "quality_gate_results.csv",
            index=False
        )

        executive_view = summary[
            [
                "model",
                "feature",
                "rouge_l",
                "token_f1",
                "alignment",
                "status"
            ]
        ]

        executive_view.to_csv(
            "quality_gate_executive_view.csv",
            index=False
        )

        print("\nQUALITY GATE RESULTS")
        print(executive_view)

        print("\nGenerated:")
        print("quality_gate_results.csv")
        print("quality_gate_executive_view.csv")

    except FileNotFoundError:

        print(
            "\nfull_evaluation_results.csv not found."
        )
        print(
            "Run evaluate.py first."
        )
        