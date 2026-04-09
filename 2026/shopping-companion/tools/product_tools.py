"""
Product tools for Stage 2 of the shopping agent.

Two backends available — set PRODUCT_BACKEND in .env:

  shopify (default)
    Connects to the Shopify Storefront MCP server for a real store.
    Requires SHOPIFY_STORE_DOMAIN (e.g. your-store.myshopify.com).
    No auth needed — the endpoint is public per Shopify's docs.
    Catalog is always live: real prices, real stock, real variants.

  local
    Falls back to a local JSON catalog + rank_bm25.
    Useful for demos, testing, or stores not on Shopify.
    Requires running: python scripts/seed_catalog.py

The agent (shopping_companion.py) calls get_product_tools() to get
the right tool set at runtime — Stage 2 never needs to know which
backend is active.
"""

import json
import os
from pathlib import Path


# ── Backend: Shopify Storefront MCP ──────────────────────────────────────────

def get_shopify_mcp_client():
    """
    Returns a connected Strands MCPClient for the Shopify Storefront MCP.

    Endpoint format: https://{shop}.myshopify.com/api/mcp
    No authentication required (Shopify public storefront).

    The client exposes the store's native tools directly to the agent:
      - search_shop_catalog: full-text + semantic search over live catalog
      - get_product_by_id: full product detail including variants and pricing
      - (plus any other tools the store exposes via tools/list)
    """
    from strands.tools.mcp import MCPClient
    from mcp.client.streamable_http import streamable_http_client

    store_domain = os.environ.get("SHOPIFY_STORE_DOMAIN", "").strip()
    if not store_domain:
        raise ValueError(
            "SHOPIFY_STORE_DOMAIN not set. "
            "Add it to .env (e.g. your-store.myshopify.com)"
        )

    # Normalize — accept both with and without https://
    if store_domain.startswith("https://"):
        store_domain = store_domain[8:]

    endpoint = f"https://{store_domain}/api/mcp"
    return MCPClient(lambda: streamable_http_client(endpoint))


# ── Backend: Local BM25 ───────────────────────────────────────────────────────

def get_local_tools():
    """
    Returns (product_search, product_view) tools backed by a local JSON
    catalog and rank_bm25. Used for testing or non-Shopify stores.
    """
    from strands import tool
    from rank_bm25 import BM25Okapi

    catalog_path = Path(os.getenv("CATALOG_PATH", "data/products.json"))
    if not catalog_path.exists():
        raise FileNotFoundError(
            f"Catalog not found at {catalog_path}. "
            "Run: python scripts/seed_catalog.py"
        )

    with open(catalog_path) as f:
        products = json.load(f)

    tokenized = [p["description"].lower().split() for p in products]
    bm25 = BM25Okapi(tokenized)
    by_id = {p["id"]: p for p in products}

    @tool
    def product_search(
        query: str,
        price_max: float = None,
        category: str = None
    ) -> list[dict]:
        """
        Search products by natural language query using BM25 ranking.
        Returns top 10 candidates. Always verify with product_view before
        recommending.

        Args:
            query: Natural language search (e.g. 'carbon plate running shoe EU 43').
            price_max: Optional maximum price filter.
            category: Optional category filter.
        """
        scores = bm25.get_scores(query.lower().split())
        ranked = sorted(
            [(i, s) for i, s in enumerate(scores) if s > 0],
            key=lambda x: x[1], reverse=True
        )[:20]
        results = [products[i] for i, _ in ranked]

        if price_max is not None:
            results = [p for p in results if float(p.get("price", 0)) <= price_max]
        if category:
            results = [p for p in results
                       if p.get("category", "").lower() == category.lower()]

        return [
            {
                "id": p["id"],
                "name": p["name"],
                "category": p.get("category", ""),
                "price": p["price"],
                "short_description": p["description"][:120],
            }
            for p in results[:10]
        ]

    @tool
    def product_view(product_id: str) -> dict:
        """
        Get full specifications, options, and price of a product.
        Always call this before recommending — verify ALL preference attributes.

        Args:
            product_id: Product ID from product_search results.
        """
        product = by_id.get(product_id)
        if not product:
            return {"error": f"Product '{product_id}' not found."}
        return product

    return product_search, product_view


# ── Public interface ──────────────────────────────────────────────────────────

def get_product_backend() -> str:
    """Returns the active backend: 'shopify' or 'local'."""
    return os.getenv("PRODUCT_BACKEND", "shopify").lower()


def get_product_tools():
    """
    Returns (tools, mcp_client_or_none) for the active backend.

    For the Shopify backend, tools is an empty list — the caller MUST
    call mcp_client.list_tools_sync() inside the with mcp_client: block,
    because the connection isn't open until the context manager is entered:

        tools, mcp_client = get_product_tools()
        with mcp_client:
            stage2_tools = mcp_client.list_tools_sync()
            agent = Agent(tools=stage2_tools, ...)
            result = agent(query)

    For the local backend, mcp_client is None and tools is ready to use.
    """
    backend = get_product_backend()

    if backend == "shopify":
        mcp_client = get_shopify_mcp_client()
        # tools fetched inside the context manager by the caller
        return [], mcp_client
    else:
        product_search, product_view = get_local_tools()
        return [product_search, product_view], None
