# llm_judge.py

import json
import ollama


def judge(reference, answer):
    """
    LLM-as-a-Judge evaluation.

    Returns:
        {
            "correctness": int,
            "groundedness": int,
            "relevance": int,
            "helpfulness": int,
            "alignment": int
        }
    """

    prompt = f"""
You are a clinical AI evaluator.

Reference Answer:
{reference}

Generated Answer:
{answer}

Rate the generated answer from 1 to 5 on:

1. correctness
2. groundedness
3. relevance
4. helpfulness
5. alignment

Return ONLY valid JSON.

Example:

{{
    "correctness": 4,
    "groundedness": 4,
    "relevance": 4,
    "helpfulness": 4,
    "alignment": 4
}}
"""

    try:

        response = ollama.chat(
            model="llama3.1:8b",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        content = response["message"]["content"]

        # Extract JSON portion if model adds text
        start = content.find("{")
        end = content.rfind("}") + 1

        if start == -1 or end == 0:
            raise ValueError("No JSON found in response")

        content = content[start:end]

        scores = json.loads(content)

        required_keys = [
            "correctness",
            "groundedness",
            "relevance",
            "helpfulness",
            "alignment"
        ]

        for key in required_keys:
            if key not in scores:
                raise KeyError(f"Missing key: {key}")

        return scores

    except Exception as e:

        print(f"Judge Error: {e}")

        # Safe fallback
        return {
            "correctness": 3,
            "groundedness": 3,
            "relevance": 3,
            "helpfulness": 3,
            "alignment": 3
        }


# Optional test
if __name__ == "__main__":

    result = judge(
        "Patients should seek professional medical advice.",
        "You should contact your healthcare provider for guidance."
    )

    print(result)