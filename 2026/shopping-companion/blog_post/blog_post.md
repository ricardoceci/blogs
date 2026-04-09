# Memory-Aware Shopping Agents with Strands Agents and Mem0

*A research paper from Alibaba proposes a two-stage e-commerce agent that remembers customer preferences across sessions. In this post, you learn how to build it as a working chat app using Strands Agents, Amazon Bedrock, Mem0, and the Shopify Storefront Model Context Protocol (MCP).*

---

## Why e-commerce agents forget everything

Most e-commerce chatbots have goldfish memory.

A customer tells your assistant: *"I'm a size M, I hate synthetic fabrics, my budget is around $200."* Three sessions later, they're back. The bot asks again. This is not only a UX annoyance. It's a conversion problem. And it's entirely avoidable.

A paper published in March 2026, [Shopping Companion (arXiv:2603.14864)](https://arxiv.org/abs/2603.14864) from Alibaba's international commerce team, tackles this directly. The researchers build a large language model (LLM) agent that remembers customer preferences across sessions, retrieves them before searching, and asks the customer to confirm before recommending anything.

---

## What the paper proposes

The core idea is splitting the agent into two stages instead of one.

**Stage 1, Preference Identification:** Before touching the catalog, the agent reads past conversation history and extracts implicit style preferences: size, fit, occasion, fabric aversions, color preferences, and budget. It surfaces a summary and asks the customer to confirm. They can correct anything before the search starts.

**Stage 2, Shopping Assistance:** With confirmed preferences in hand, the agent searches the catalog and verifies each candidate before recommending. For outfit bundles, it coordinates across products and validates budget math. The paper trains the whole pipeline end-to-end with reinforcement learning (RL). Their fine-tuned 4B model reaches 84% success on single-product tasks, surpassing GPT-4o (72%). You don't need to replicate the RL training. The inference architecture is fully buildable today.

---

## Architecture

![Architecture diagram](https://raw.githubusercontent.com/ricardoceci/blogs/2026/shopping-companion/images/animation.svg)

**Stack:**

| Component | Service | Cost |
|---|---|---|
| LLM | Amazon Bedrock Claude Sonnet 4 | Pay per token |
| Embeddings | Amazon Bedrock Titan Embed v2 (via Mem0) | Pay per token |
| Cross-session memory | Mem0 free tier | Free |
| Product catalog | Shopify Storefront MCP | Free, no auth |
| Chat server | FastAPI + uvicorn | Free |
| Agent framework | Strands Agents (open source) | Free |

---

## Stage 1: Cross-session memory with AWS Strands Agents and Mem0

The paper externalizes memory into retrievable records injected into generation at runtime. In this implementation, Mem0 handles extraction, deduplication, storage, and semantic retrieval, using Amazon Bedrock Titan Embed v2 as the embedding model.

`mem0_memory` ships as a built-in tool in `strands-agents-tools`, which means Stage 1 is a single-tool agent:

```python
# agents/shopping_companion.py
from strands_tools import mem0_memory

def identify_preferences(self, user_id: str, query: str) -> str:
    agent = Agent(
        model=self._model,
        system_prompt=STAGE1_SYSTEM_PROMPT,
        tools=[mem0_memory],
    )
    return str(agent(
        f"user_id: {user_id}\n"
        f"Shopping request: {query}\n\n"
        f"Retrieve this customer's style preferences relevant to this request."
    ))
```

Before this can work, you need to index past conversations. Mem0 extracts structured facts from raw turns automatically:

```python
from mem0 import MemoryClient

client = MemoryClient(api_key=os.environ["MEM0_API_KEY"])

turns = [
    {"role": "user", "content": "I always size up. I find fitted styles uncomfortable."},
    {"role": "assistant", "content": "Good to know. Sizing up for relaxed fit."},
    {"role": "user", "content": "I basically live in linen when it gets warm."},
    {"role": "assistant", "content": "Linen it is. Any fabrics to avoid?"},
    {"role": "user", "content": "Anything synthetic. Polyester makes me overheat."},
]

client.add(turns, user_id="user_123")

# Mem0 extracts:
# - "Customer sizes up, prefers relaxed fit"
# - "Customer prefers linen fabric"
# - "Customer avoids synthetic / polyester fabrics"
```

Five raw turns become three clean, queryable facts. Deduplication is automatic: running twice won't create duplicates, and when a customer says "actually I moved to size L last month," Mem0 updates the existing fact rather than adding a contradiction. According to the Mem0 paper, this approach delivers 91% lower latency and 90% lower token cost compared to full-context approaches, with 26% better accuracy on the LOCOMO memory benchmark than OpenAI's memory system.

---

## Stage 2: Live catalog search via the Shopify Storefront MCP

The paper implements `product_search` and `product_view` as tools over a BM25 (Best Match 25) index. In this implementation, those tools come directly from the store via the Shopify Storefront MCP, so the catalog is always live: real prices, real stock, real variants.

Every Shopify store exposes a public MCP endpoint at `https://{store}.myshopify.com/api/mcp`. No OAuth or API key is required. The endpoint is open by design for storefront interactions. Strands has native MCP support:

```python
# tools/product_tools.py
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamable_http_client

def get_shopify_mcp_client():
    endpoint = f"https://{os.environ['SHOPIFY_STORE_DOMAIN']}/api/mcp"
    # MCPClient requires a transport callable, not a url= keyword argument
    return MCPClient(lambda: streamable_http_client(endpoint))
```

`list_tools_sync()` must be called inside the context manager. The connection is not open until you enter it. This is where Stage 2 runs:

```python
# agents/shopping_companion.py
def find_products(self, user_id, query, confirmed_preferences, bundle=False) -> str:
    _, mcp_client = get_product_tools()
    with mcp_client:
        # connection is open here — fetch tools and run agent
        tools = mcp_client.list_tools_sync()
        agent = Agent(model=self._model, system_prompt=STAGE2_PROMPT, tools=tools)
        return str(agent(
            f"Query: {query}\n\n"
            f"Confirmed preferences:\n{confirmed_preferences}"
        ))
```

The store's native `search_shop_catalog` tool accepts a `context` parameter. This is how confirmed preferences flow from Stage 1 into the catalog search:

```
search_shop_catalog(
  query="maxi dress",
  context="size M, relaxed fit, linen only, midi or maxi, avoids orange"
)
```

---

## The user intervention loop: the detail that matters most

The paper explicitly models user intervention as a first-class part of the architecture. After Stage 1 retrieves preferences, the agent surfaces them for confirmation before Stage 2 runs. The customer can correct anything.

This implementation adds one critical refinement: once you confirm preferences in a session, they persist for all follow-up requests. Stage 1 only runs once, on the first message of a new session. The distinction between `pending_preferences` (pre-confirmation) and `confirmed_preferences` (persisted for the session) is what makes this work:

```python
# app.py
if session["state"] == "awaiting_query":

    # Preferences already confirmed earlier in this session:
    # skip Stage 1 and go straight to product search
    if session["confirmed_preferences"] is not None:
        recommendation = companion.find_products(
            user_id=session["user_id"],
            query=req.message,
            confirmed_preferences=session["confirmed_preferences"],
        )
        return ChatResponse(reply=recommendation, stage=2, ...)

    # First request in session: run Stage 1
    preferences = companion.identify_preferences(...)
    session["pending_preferences"] = preferences
    session["state"] = "awaiting_confirmation"
    return ChatResponse(reply=preferences, state="awaiting_confirmation", stage=1, ...)

elif session["state"] == "awaiting_confirmation":
    confirmed = companion.process_confirmation(
        user_id=session["user_id"],
        identified_preferences=session["pending_preferences"],
        user_response=req.message.strip(),
    )
    session["confirmed_preferences"] = confirmed  # persists for whole session
    session["state"] = "awaiting_query"

    recommendation = companion.find_products(...)
    return ChatResponse(reply=recommendation, stage=2, ...)
```

The `process_confirmation` method delegates the correction-vs-confirmation decision to the agent itself. The agent has the full context of what was identified and what the customer said, which is exactly the kind of reasoning LLMs handle well. If the response is "looks perfect," nothing gets saved to Mem0. If it's "actually I moved to size L," the new fact gets stored and confirmed preferences are updated before Stage 2 runs.

The resulting conversation flow:

```
Turn 1: "I need a dress for a wedding"
  → Stage 1 runs, retrieves: size M, midi/maxi, linen, avoids orange
  → "Do these look right?"

Turn 2: "Looks perfect"
  → Stage 2 runs, returns dress recommendation
  → confirmed_preferences saved to session

Turn 3: "I liked that one. Can you find a blazer to go with it?"
  → confirmed_preferences already in session
  → Stage 1 SKIPPED, Stage 2 runs directly

Turn 4: "What about shoes?"
  → Stage 1 still SKIPPED, Stage 2 runs with same preferences
```

---

## What to build next

The paper's main result is a 4B model that outperforms GPT-4o. This comes from RL training with a dual reward: one for how well Stage 1 extracted preferences, one for whether Stage 2's recommendation was correct. A third tool-wise reward scores each individual tool call, not only the final result. This significantly improves credit assignment in multi-turn interactions and also reduces response verbosity, because the model learns that unnecessary tool calls are penalized.

Replicating that training requires labeled trajectories and GPU compute. What you get from [this repo](https://github.com/ricardoceci/blogs/tree/main/2026/shopping-companion) is the full inference architecture running with Claude Sonnet 4 zero-shot. It works well in practice and gives you a production-ready foundation to layer the training on top of later.

---

## Get started

```bash
pip install strands-agents "strands-agents-tools[mem0-memory]" \
    rank_bm25 fastapi uvicorn boto3 python-dotenv mem0ai
```

```bash
# .env
AWS_DEFAULT_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-20250514-v1:0
MEM0_API_KEY=your-mem0-api-key
MEM0_LLM_MODEL=anthropic.claude-3-5-haiku-20241022-v1:0
MEM0_EMBEDDER_MODEL=amazon.titan-embed-text-v2:0
PRODUCT_BACKEND=shopify
SHOPIFY_STORE_DOMAIN=your-store.myshopify.com
```

```bash
python scripts/index_history.py   # seed sample conversation history into Mem0
python app.py                     # start server at http://localhost:8000
```

The sample history includes preference sessions interleaved with unrelated conversations. This mirrors the paper's "needle in a haystack" setup, so the agent has to retrieve the right preferences from across multiple sessions.

---

## Frequently asked questions

**Does this work with any Shopify store?**
Yes. Every Shopify store has a public MCP endpoint at `https://{store}.myshopify.com/api/mcp` enabled by default since the Summer 2025 Edition.

**What happens if a customer has no memory yet?**
Stage 1 returns an empty preference list and tells the customer so. Stage 2 runs with whatever the customer provides in that first message.

**Can I use a model other than Claude Sonnet 4?**
Yes. Strands Agents is model-agnostic. Replace `BedrockModel` with `AnthropicModel` or `OpenAIModel` in one line.

**Do I need GPU compute to run this?**
No. This implementation runs entirely on API calls to Amazon Bedrock and Mem0. The RL training from the original paper requires GPU compute, but that is not part of this repo.

**Is Mem0 free?**
Mem0 has a free tier at [mem0.ai](https://mem0.ai). You can also run it self-hosted with a local FAISS backend by setting `USE_LOCAL_MEMORY=true` in your `.env` file.

---

## References

- [Shopping Companion (arXiv:2603.14864)](https://arxiv.org/abs/2603.14864)
- [Strands Agents SDK](https://strandsagents.com)
- [Shopify Storefront MCP documentation](https://shopify.dev/docs/apps/build/storefront-mcp/servers/storefront)
- [AWS and Mem0 partnership announcement](https://mem0.ai/blog/aws-and-mem0-partner-to-bring-persistent-memory-to-next-gen-ai-agents-with-strands)
- [Mem0 paper (arXiv:2504.19413)](https://arxiv.org/abs/2504.19413)
- [GitHub repo](https://github.com/ricardoceci/blogs/tree/main/2026/shopping-companion)

