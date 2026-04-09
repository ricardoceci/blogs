"""
Budget validation tool for add-on deals (multi-product bundles with vouchers).

Implements the "add-on deals" task from the paper, where the agent must verify
that a bundle of products satisfies budget + voucher constraints before recommending.

Uses a specialized sub-agent so the math check is isolated and the prompt stays clean.
"""

import json
import os
from strands import Agent, tool
from strands.models import BedrockModel

_model = BedrockModel(
    model_id=os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-20250514-v1:0"),
    region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
)

_BUDGET_SYSTEM_PROMPT = """
You are a budget constraint checker for an e-commerce shopping agent.

Given a list of products and voucher rules, calculate the exact final price
and return ONLY a valid JSON object — no explanation, no markdown, no code fences.

Required schema:
{
  "feasible": <bool>,
  "total_before_discount": <float>,
  "total_after_discount": <float>,
  "savings": <float>,
  "voucher_applied": <bool>,
  "reason": <string>
}

Rules:
- voucher_applied is true only if total_before_discount >= voucher_threshold
- If voucher is not applied, total_after_discount == total_before_discount
- feasible is true only if total_after_discount <= budget
- reason should explain the calculation clearly in one sentence
"""


@tool
def verify_bundle_budget(
    products: list[dict],
    budget: float,
    voucher_discount: float,
    voucher_threshold: float,
) -> dict:
    """
    Verify if a product bundle fits within budget after applying a voucher.

    Use this for any multi-product recommendation before presenting it to the user.
    A bundle that exceeds the budget must NOT be recommended.

    Args:
        products: List of products, each with 'id', 'name', and 'price'.
        budget: Maximum total spend the user can make.
        voucher_discount: Discount as decimal (e.g. 0.20 for 20% off).
        voucher_threshold: Minimum order subtotal to activate the voucher.

    Returns:
        Dict with feasible (bool), total_before_discount, total_after_discount,
        savings, voucher_applied (bool), and reason (explanation string).
    """
    agent = Agent(model=_model, system_prompt=_BUDGET_SYSTEM_PROMPT)

    result = agent(
        f"Products: {json.dumps(products)}\n"
        f"Voucher: {voucher_discount * 100:.0f}% off on orders >= ${voucher_threshold}\n"
        f"User budget: ${budget}\n\n"
        f"Calculate and return JSON only."
    )

    try:
        raw = str(result).strip()
        # Strip any accidental markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except (json.JSONDecodeError, IndexError):
        return {
            "feasible": False,
            "total_before_discount": 0.0,
            "total_after_discount": 0.0,
            "savings": 0.0,
            "voucher_applied": False,
            "reason": "Could not parse budget calculation result.",
        }
