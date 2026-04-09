"""
Bulk-load past the store shopping conversations into Mem0.

Mem0 extracts structured style preferences from raw conversation turns:
  "I always size up — I find fitted styles really uncomfortable"
  → "Customer sizes up, prefers relaxed fit"
  "I'm doing a lot of beach trips this summer, mostly casual"
  → "Customer shops for beach/resort casual occasion"

Run:
    python scripts/index_history.py
    python scripts/index_history.py --user alice
    python scripts/index_history.py --local
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Sample history ─────────────────────────────────────────────────────────────
# Needle-in-a-haystack: preference sessions interleaved with unrelated chats.
#
# Key preferences Mem0 should extract:
#   Size: M (but sizes up to L in fitted styles)
#   Fit: relaxed preferred, finds overly fitted uncomfortable
#   Occasion: casual/weekend, beach/resort, some cocktail events
#   Fabric: loves linen, avoids synthetic fabrics
#   Color: loves navy and stripes, avoids orange
#   Length: prefers midi or maxi dresses, not mini
#   Budget: comfortable up to ~$250 per item
#   Brands loved: the store private label, a brand

SAMPLE_HISTORY = [
    {
        "date": "2025-10-12",
        "description": "First visit — sizing and fit consultation",
        "turns": [
            {
                "role": "user",
                "content": "Hi, I'm new to the store. I'm not sure what size to get — I'm usually a medium but sizing feels inconsistent across brands.",
            },
            {
                "role": "assistant",
                "content": "Welcome! Sizing can definitely vary. Do you generally prefer a more fitted or relaxed look?",
            },
            {
                "role": "user",
                "content": "Relaxed, for sure. If something is too fitted I feel uncomfortable all day. I'd rather have a little room.",
            },
            {
                "role": "assistant",
                "content": "Totally understandable. For relaxed styles, a Medium usually works well. For anything described as 'fitted' in the product notes, sizing up to a Large gives you that comfort you're looking for.",
            },
            {
                "role": "user",
                "content": "Perfect, that's helpful. So M for relaxed cuts, L for anything fitted. Got it.",
            },
            {
                "role": "assistant",
                "content": "Exactly. And most the store pieces run true to size or slightly relaxed, so you're in good shape with that approach.",
            },
        ],
    },
    {
        "date": "2025-10-28",
        "description": "Unrelated conversation — book recommendation",
        "turns": [
            {
                "role": "user",
                "content": "Can you recommend a good novel to read this fall? I like character-driven stories.",
            },
            {
                "role": "assistant",
                "content": "For character-driven fiction, 'Tomorrow, and Tomorrow, and Tomorrow' by Gabrielle Zevin is excellent...",
            },
        ],
    },
    {
        "date": "2025-11-15",
        "description": "Fabric preferences and fabric avoidances",
        "turns": [
            {
                "role": "user",
                "content": "I'm shopping for some spring pieces. I know I want linen — I basically live in linen when it gets warm.",
            },
            {
                "role": "assistant",
                "content": "Linen is such a great warm-weather choice. Any fabrics you try to avoid?",
            },
            {
                "role": "user",
                "content": "Anything synthetic, honestly. Polyester makes me feel overheated and I can always tell when something isn't natural fiber.",
            },
            {
                "role": "assistant",
                "content": "Noted — linen, cotton, and natural fibers only. the store has a lot of linen and cotton pieces, especially in the spring collection.",
            },
            {
                "role": "user",
                "content": "Also I'm not a huge fan of cashmere — it's beautiful but it irritates my skin. Cotton or linen for me.",
            },
        ],
    },
    {
        "date": "2025-12-03",
        "description": "Occasion shopping — holiday cocktail party",
        "turns": [
            {
                "role": "user",
                "content": "I have a holiday cocktail party coming up and I need a dress. Something elegant but not too formal.",
            },
            {
                "role": "assistant",
                "content": "A midi dress in a festive fabric would be perfect for that. Any color preferences?",
            },
            {
                "role": "user",
                "content": "I love navy — it's my go-to. I also like deep jewel tones. I tend to stay away from orange, it's just not my color.",
            },
            {
                "role": "assistant",
                "content": "Navy is such a classic choice for cocktail events. We'll steer clear of orange.",
            },
            {
                "role": "user",
                "content": "And I really prefer midi or maxi length. I feel more comfortable and I think it looks more elegant. Mini dresses just aren't really my thing.",
            },
            {
                "role": "assistant",
                "content": "Midi or maxi, noted. A navy eyelet midi would be stunning for a holiday cocktail party.",
            },
            {
                "role": "user",
                "content": "That sounds perfect. I'm comfortable spending up to around $250 for something I'll wear multiple times.",
            },
        ],
    },
    {
        "date": "2026-01-20",
        "description": "Unrelated conversation — travel planning",
        "turns": [
            {
                "role": "user",
                "content": "I'm thinking about a trip to the Amalfi Coast this summer. Any tips?",
            },
            {
                "role": "assistant",
                "content": "Amalfi is stunning! Positano and Ravello are both beautiful bases. The shoulder season in late May or early September is ideal...",
            },
        ],
    },
    {
        "date": "2026-02-08",
        "description": "Beach vacation shopping — resort wear",
        "turns": [
            {
                "role": "user",
                "content": "I'm doing a beach trip in April — looking for some casual resort pieces. Not swimwear itself, just things to wear around the pool and for dinners.",
            },
            {
                "role": "assistant",
                "content": "Perfect — cover-ups, casual maxi dresses, and easy linen pieces. Any color or print preferences for the trip?",
            },
            {
                "role": "user",
                "content": "I love stripes — classic navy and white stripes especially. Very coastal. I also love anything in a solid linen.",
            },
            {
                "role": "assistant",
                "content": "Navy stripe linen is very much in the the store wheelhouse. That would work great from beach to dinner.",
            },
            {
                "role": "user",
                "content": "Exactly the vibe. Relaxed, classic, nothing too trendy. I'd rather buy something I'll wear for years.",
            },
            {
                "role": "assistant",
                "content": "Timeless over trendy — that fits perfectly with the the store ethos. A relaxed linen maxi and a stripe coverup would be a great starting point.",
            },
            {
                "role": "user",
                "content": "Yes. I've been really happy with the the store private label pieces I've bought. The quality is good for the price.",
            },
        ],
    },
    {
        "date": "2026-03-01",
        "description": "Unrelated conversation — dinner recipe",
        "turns": [
            {
                "role": "user",
                "content": "Do you have a good recipe for a simple dinner party main course?",
            },
            {
                "role": "assistant",
                "content": "A classic roast chicken is always impressive and simple. Or a braised short rib if you want something heartier...",
            },
        ],
    },
]


def index_history(user_id: str, use_local: bool = False):
    """Index all the store sample sessions into Mem0 for the given user."""

    if use_local:
        from mem0 import Memory
        path = os.getenv("LOCAL_MEMORY_PATH", "./data/local_memories")
        os.makedirs(path, exist_ok=True)
        client = Memory.from_config({
            "vector_store": {
                "provider": "faiss",
                "config": {"collection_name": "style_preferences", "path": path}
            }
        })
        add_fn = lambda turns: client.add(turns, user_id=user_id)
        list_fn = lambda: client.get_all(user_id=user_id)
    else:
        from mem0 import MemoryClient
        client = MemoryClient(api_key=os.environ["MEM0_API_KEY"])
        add_fn = lambda turns: client.add(turns, user_id=user_id)
        list_fn = lambda: client.get_all(user_id=user_id)

    print(f"Indexing {len(SAMPLE_HISTORY)} sessions for user '{user_id}'...\n")
    for session in SAMPLE_HISTORY:
        print(f"  [{session['date']}] {session['description']}")
        add_fn(session["turns"])

    print("\n✅ Done.")
    print("\nExtracted style preferences:")
    memories = list_fn()
    results = memories.get("results", memories) if isinstance(memories, dict) else memories
    for m in results:
        text = m.get("memory", m) if isinstance(m, dict) else m
        print(f"  - {text}")


def main():
    parser = argparse.ArgumentParser(description="Index the store history into Mem0")
    parser.add_argument("--user", default="user_123", help="User ID")
    parser.add_argument("--local", action="store_true", help="Use local FAISS")
    args = parser.parse_args()

    use_local = args.local or os.getenv("USE_LOCAL_MEMORY", "false").lower() == "true"

    if not use_local and not os.getenv("MEM0_API_KEY"):
        print("ERROR: MEM0_API_KEY not set.")
        print("  Option 1: set MEM0_API_KEY in .env (free at mem0.ai)")
        print("  Option 2: run with --local flag")
        sys.exit(1)

    index_history(user_id=args.user, use_local=use_local)


if __name__ == "__main__":
    main()
