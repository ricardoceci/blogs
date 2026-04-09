"""
Shopping Companion — Core agent logic.

Exposes ShoppingCompanion class with three methods:
  identify_preferences()  → Stage 1: retrieve from Mem0, return string
  save_correction()       → persist user correction back to Mem0
  find_products()         → Stage 2: search catalog, return recommendation

No input() calls — all interaction is handled by the caller (app.py or CLI).

Store: the store (your-store.myshopify.com) — classic American women's clothing and lifestyle.
Key preferences tracked: size, fit, occasion, style, fabric, color, length, budget.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

from strands import Agent
from strands.models import BedrockModel
from strands_tools import mem0_memory

from tools.product_tools import get_product_tools, get_product_backend
from tools.budget_tools import verify_bundle_budget

# ── Model ──────────────────────────────────────────────────────────────────────

def _make_model():
    return BedrockModel(
        model_id=os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-20250514-v1:0"),
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
    )


# ── System prompts ─────────────────────────────────────────────────────────────

STAGE1_SYSTEM_PROMPT = """
You are a personal styling assistant for a women's clothing and lifestyle store.

Before searching for any product, retrieve the customer's past style preferences
from memory using the mem0_memory tool.

Key preferences to look for:
  - Size: XS / S / M / L / XL / XXL (note: fit can vary by brand and style)
  - Fit preference: fitted, relaxed, oversized, true-to-size
  - Occasion: casual, office/work, cocktail party, wedding guest, beach/resort,
              black tie, weekend, night out, sport
  - Style sensibility: classic/preppy, bohemian, minimalist, trendy, feminine
  - Fabric preferences: linen (loves/avoids), cashmere, cotton, silk, seersucker
  - Color/print preferences: loves stripes, loves florals, avoids bold prints,
                              prefers neutrals, loves navy, avoids orange, etc.
  - Dress length preference: mini, midi, maxi, or no preference
  - Brands to avoid or prefer
  - Budget range if mentioned

Process:
1. Call mem0_memory with action="retrieve" using the shopping query as search term
2. Call mem0_memory with action="list" if results seem incomplete
3. Compile findings as "attribute: value" pairs — be specific and useful
4. Present to the customer and ask for confirmation

Guidelines:
- "Size: M, prefers relaxed fit — finds fitted styles uncomfortable" is useful
- "Likes nice clothes" is not
- Flag conflicts (e.g. two different sizes across sessions)
- If no relevant memories exist, say so clearly — never invent preferences
- End with: "Do these look right? Feel free to confirm or correct anything."
"""

STAGE2_SYSTEM_PROMPT_SHOPIFY = """
You are a personal styling assistant connected to a live Shopify store catalog.

Given a shopping query and confirmed customer preferences, find the best matching item(s).

Guidance:
- Always match size exactly as specified — never suggest "size up" unless
  the customer has previously mentioned fit issues
- Occasion match is critical: never recommend a cocktail dress for a casual weekend
- For fabric: if a customer avoids a fabric, do not recommend it even if search
  returns it as a top result
- Respect stated budget ranges
- For bundle/outfit requests: use verify_bundle_budget to confirm total fits budget

Process:
1. Use search_shop_catalog with the query AND pass confirmed preferences as the
   "context" parameter for better ranking.
   Example: context="size M, relaxed fit, midi length, linen, coastal casual, navy"
2. Verify style, occasion, fabric, and size availability for each candidate
3. Never recommend a product you haven't verified
4. For outfit bundles: verify combined price fits budget if stated

Recommendation format:
- Lead with why this item matches the customer's specific confirmed preferences
- Call out any preference you could not satisfy and why
- End with: RECOMMENDATION: variant_id
  or for outfits: RECOMMENDATION: variant_id_1, variant_id_2
"""

STAGE2_SYSTEM_PROMPT_LOCAL = """
You are a personal styling assistant with access to a local sample catalog.

Given a shopping query and confirmed customer preferences, find the best matching item(s).

Guidance:
- Match size, occasion, fabric, and style to confirmed preferences exactly
- Never recommend a fabric or occasion type the customer has said to avoid
- For outfit bundles: use verify_bundle_budget to confirm total fits budget

Process:
1. Use product_search with the main query + key preference terms
2. For each candidate, call product_view to verify size availability, occasion
   suitability, fabric, and style against confirmed preferences
3. Never recommend without verifying via product_view

Recommendation format:
- Explain how each item matches the confirmed preferences specifically
- Flag any preference you could not satisfy
- End with: RECOMMENDATION: product_id
  or for outfits: RECOMMENDATION: product_id_1, product_id_2
"""


# ── ShoppingCompanion class ────────────────────────────────────────────────────

class ShoppingCompanion:
    """
    Stateless agent wrapper. Each method call is independent.
    Session state is managed by the caller (app.py).
    """

    def __init__(self):
        self._model = _make_model()

    def identify_preferences(self, user_id: str, query: str) -> str:
        """
        Stage 1: Retrieve past preferences from Mem0 for this user and query.
        Returns a formatted string summarising found preferences + confirmation ask.
        """
        agent = Agent(
            model=self._model,
            system_prompt=STAGE1_SYSTEM_PROMPT,
            tools=[mem0_memory],
        )
        result = agent(
            f"user_id: {user_id}\n"
            f"Shopping request: {query}\n\n"
            f"Retrieve this customer's style preferences relevant to this request."
        )
        return str(result)

    def process_confirmation(
        self,
        user_id: str,
        identified_preferences: str,
        user_response: str,
    ) -> str:
        """
        Let the agent decide whether the user's response contains actual
        preference corrections/updates worth saving to memory.

        If the response is just a confirmation ("looks perfect", "yes", "ok"),
        the agent does nothing and returns the original preferences unchanged.

        If the response contains new or corrected information, the agent
        updates Mem0 and returns the merged preference string for Stage 2.
        """
        agent = Agent(
            model=self._model,
            system_prompt="""
You are managing a customer's style preference memory for a shopping assistant.

You are given:
- The preferences already identified from memory
- The customer's response after reviewing them

Your job:
1. Decide if the response contains actual new or corrected preference information.
   - Corrections/updates: "Actually I'm a L now", "I prefer maxi not midi",
     "I hate floral prints", "my budget is $200", "I moved to size 12"
   - Just confirmations: "looks good", "perfect", "yes", "that's right",
     "correct", "all good", or anything that doesn't change the preferences

2. If it's a correction or new information:
   - Use mem0_memory with action="store" to save ONLY the new/changed facts
   - Return the full updated preference list (original + corrections merged)

3. If it's just a confirmation:
   - Do NOT call mem0_memory at all
   - Return the original preferences unchanged

Always end your response with the final confirmed preference list in
"attribute: value" format, ready to pass to the product search stage.
""",
            tools=[mem0_memory],
        )
        result = agent(
            f"user_id: {user_id}\n\n"
            f"Identified preferences:\n{identified_preferences}\n\n"
            f"Customer response: {user_response}"
        )
        return str(result)

    def find_products(
        self,
        user_id: str,
        query: str,
        confirmed_preferences: str,
        bundle: bool = False,
    ) -> str:
        """
        Stage 2: Search the product catalog with confirmed preferences.
        Returns a recommendation string including RECOMMENDATION: variant_id.
        """
        backend = get_product_backend()
        product_tools, mcp_client = get_product_tools()

        stage2_tools = list(product_tools)
        if bundle:
            stage2_tools.append(verify_bundle_budget)

        prompt = (
            STAGE2_SYSTEM_PROMPT_SHOPIFY
            if backend == "shopify"
            else STAGE2_SYSTEM_PROMPT_LOCAL
        )

        query_text = (
            f"Shopping request: {query}\n\n"
            f"Confirmed customer preferences:\n{confirmed_preferences}\n\n"
            f"Find the best matching item(s) and verify all preference attributes."
        )

        if mcp_client is not None:
            with mcp_client:
                # list_tools_sync() must be called inside the context manager —
                # the connection isn't open until we enter the with block
                stage2_tools = mcp_client.list_tools_sync()
                if bundle:
                    stage2_tools = list(stage2_tools) + [verify_bundle_budget]
                agent = Agent(model=self._model, system_prompt=prompt, tools=stage2_tools)
                result = agent(query_text)
        else:
            agent = Agent(model=self._model, system_prompt=prompt, tools=stage2_tools)
            result = agent(query_text)

        return str(result)


def save_session(user_id: str, turns: list[dict]):
    """
    Save a completed conversation session to Mem0.
    Call this after a full Stage 1 → Stage 2 cycle to update the user's profile.
    Mem0 handles deduplication and preference updates automatically.
    """
    use_local = os.getenv("USE_LOCAL_MEMORY", "false").lower() == "true"

    if use_local:
        from mem0 import Memory
        path = os.getenv("LOCAL_MEMORY_PATH", "./data/local_memories")
        os.makedirs(path, exist_ok=True)
        Memory.from_config({
            "vector_store": {
                "provider": "faiss",
                "config": {"collection_name": "style_preferences", "path": path}
            }
        }).add(turns, user_id=user_id)
    else:
        from mem0 import MemoryClient
        MemoryClient(api_key=os.environ["MEM0_API_KEY"]).add(turns, user_id=user_id)
