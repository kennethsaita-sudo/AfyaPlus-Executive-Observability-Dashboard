"""
Phase 3 — Token pricing and prompt-configuration constants.

Prices are $ PER TOKEN (not per 1M tokens), so downstream cost
calculations are a simple multiplication: cost = tokens * price.

NOTE ON ASSUMPTIONS:
This capstone's evaluation pipeline uses Ollama's local models
(llama3.1:8b, mistral) rather than OpenAI's gpt-4o-mini / gpt-4o, per
the course's stated option to substitute Ollama. Local models have no
real per-token cloud bill of their own, so the rates below are
ASSUMED, chosen to mirror the relative price gap between a small/fast
model and a larger/more expensive one (roughly matching the public
gpt-4o-mini vs. gpt-4o pricing ratio at the time of writing). Document
this substitution explicitly in your README / executive summary so
graders don't read the numbers as real OpenAI billing data.
"""

MODEL_PRICING = {
    "llama3.1": {
        "input": 0.00000015,   # ~ $0.15 / 1M tokens  (mini-equivalent)
        "output": 0.00000060,  # ~ $0.60 / 1M tokens
    },
    "mistral": {
        "input": 0.0000025,    # ~ $2.50 / 1M tokens  (larger-equivalent)
        "output": 0.0000100,   # ~ $10.00 / 1M tokens
    },
}

# Two system-prompt configurations for the cost-per-request
# comparison required by Phase 3 ("gpt-4o-mini vs. gpt-4o across
# prompt configurations" in the brief — substituted with our models).
# Token counts here are SYSTEM PROMPT overhead only.
PROMPT_CONFIGS = {
    "cot_system_prompt": 200,  # verbose chain-of-thought style prompt
    "direct_prompt": 30,       # short, direct instruction prompt
}


def cost_per_request(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return the dollar cost of a single request for `model`.

    Raises KeyError if `model` isn't in MODEL_PRICING — this is
    intentional so a typo'd model name fails loudly instead of
    silently producing $0.00 costs.
    """
    rates = MODEL_PRICING[model]
    return (
        input_tokens * rates["input"]
        + output_tokens * rates["output"]
    )
