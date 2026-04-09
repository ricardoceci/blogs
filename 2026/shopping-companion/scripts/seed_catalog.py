"""
Generate a sample product catalog inspired by the store (your-store.myshopify.com).

the store is a classic American women's clothing and lifestyle brand known for
timeless, preppy, and occasion-ready pieces.

Categories covered:
  - Dresses (maxi, midi, mini — various occasions)
  - Tops (polo, blouse, tee, tank)
  - Sweaters & knitwear (cashmere, cardigan, pullover)
  - Bottoms (pants, skirts, shorts)
  - Swimwear & coverups
  - Accessories

Run: python scripts/seed_catalog.py
"""

import json
from pathlib import Path
from collections import Counter

PRODUCTS = [

    # ── Dresses ───────────────────────────────────────────────────────────────

    {
        "id": "dress_clementine_maxi",
        "name": "Clementine Maxi Dress — Orange Linen",
        "category": "dresses",
        "price": 198.00,
        "description": "orange linen maxi dress relaxed fit casual weekend resort beach vacation spring summer midi maxi long",
        "attributes": {
            "length": "maxi",
            "fabric": "100% linen",
            "fit": "relaxed",
            "occasion": ["casual", "beach/resort", "weekend"],
            "color": "orange",
            "print": "solid",
            "neckline": "v-neck",
            "sleeve": "sleeveless",
        },
        "options": {"sizes": ["XS", "S", "M", "L", "XL"]},
        "brand": "the store",
        "in_stock": True,
    },
    {
        "id": "dress_delaney_navy_eyelet",
        "name": "Delaney Dress — Navy Eyelet",
        "category": "dresses",
        "price": 228.00,
        "description": "navy eyelet midi dress fitted cocktail party wedding guest daytime elegant classic preppy cotton",
        "attributes": {
            "length": "midi",
            "fabric": "cotton eyelet",
            "fit": "fitted",
            "occasion": ["cocktail party", "wedding guest", "daytime elegance"],
            "color": "navy",
            "print": "eyelet",
            "neckline": "square neck",
            "sleeve": "sleeveless",
        },
        "options": {"sizes": ["XS", "S", "M", "L", "XL", "XXL"]},
        "brand": "the store",
        "in_stock": True,
    },
    {
        "id": "dress_delaney_raspberry",
        "name": "Delaney Dress — Raspberry Organza",
        "category": "dresses",
        "price": 228.00,
        "description": "raspberry organza midi dress fitted cocktail party wedding guest feminine elegant pink red",
        "attributes": {
            "length": "midi",
            "fabric": "organza",
            "fit": "fitted",
            "occasion": ["cocktail party", "wedding guest", "black tie"],
            "color": "raspberry",
            "print": "solid",
            "neckline": "square neck",
            "sleeve": "sleeveless",
        },
        "options": {"sizes": ["XS", "S", "M", "L", "XL"]},
        "brand": "the store",
        "in_stock": True,
    },
    {
        "id": "dress_hailey_linen_maxi",
        "name": "Hailey Maxi Dress — Ocean Mist Colorblock Linen",
        "category": "dresses",
        "price": 218.00,
        "description": "linen maxi dress colorblock ocean blue casual resort beach vacation relaxed spring summer long",
        "attributes": {
            "length": "maxi",
            "fabric": "100% linen",
            "fit": "relaxed",
            "occasion": ["casual", "beach/resort", "weekend"],
            "color": "ocean mist / blue colorblock",
            "print": "colorblock",
            "neckline": "scoop neck",
            "sleeve": "sleeveless",
        },
        "options": {"sizes": ["XS", "S", "M", "L", "XL"]},
        "brand": "the store",
        "in_stock": True,
    },
    {
        "id": "dress_yvette_mini_gingham",
        "name": "Yvette Mini Dress — Mocha Gingham",
        "category": "dresses",
        "price": 178.00,
        "description": "mini dress gingham mocha brown cotton casual weekend daytime short fitted fun playful",
        "attributes": {
            "length": "mini",
            "fabric": "cotton",
            "fit": "fitted",
            "occasion": ["casual", "weekend", "night out"],
            "color": "mocha / brown",
            "print": "gingham",
            "neckline": "v-neck",
            "sleeve": "short sleeve",
        },
        "options": {"sizes": ["XS", "S", "M", "L", "XL"]},
        "brand": "the store",
        "in_stock": True,
    },
    {
        "id": "dress_nicola_embellished",
        "name": "Nicola Dress — Winter White Embellished",
        "category": "dresses",
        "price": 298.00,
        "description": "white embellished midi dress elegant black tie cocktail formal occasion wedding guest special event",
        "attributes": {
            "length": "midi",
            "fabric": "embellished fabric blend",
            "fit": "fitted",
            "occasion": ["black tie", "cocktail party", "wedding guest"],
            "color": "winter white",
            "print": "embellished",
            "neckline": "halter",
            "sleeve": "sleeveless",
        },
        "options": {"sizes": ["XS", "S", "M", "L"]},
        "brand": "the store",
        "in_stock": True,
    },
    {
        "id": "dress_zacara_seersucker",
        "name": "Zacara Dress — Brown Gingham Seersucker",
        "category": "dresses",
        "price": 188.00,
        "description": "seersucker midi dress brown gingham casual daytime preppy classic cotton spring summer",
        "attributes": {
            "length": "midi",
            "fabric": "cotton seersucker",
            "fit": "relaxed",
            "occasion": ["casual", "daytime elegance", "weekend"],
            "color": "brown / gingham",
            "print": "gingham seersucker",
            "neckline": "collared",
            "sleeve": "short sleeve",
        },
        "options": {"sizes": ["XS", "S", "M", "L", "XL", "XXL"]},
        "brand": "the store",
        "in_stock": True,
    },
    {
        "id": "dress_may_polo_green",
        "name": "May Polo Dress — Green Pique",
        "category": "dresses",
        "price": 158.00,
        "description": "polo dress green pique cotton sport casual weekend preppy sport label collared",
        "attributes": {
            "length": "mini",
            "fabric": "cotton pique",
            "fit": "relaxed",
            "occasion": ["casual", "sport", "weekend"],
            "color": "green",
            "print": "solid",
            "neckline": "polo/collared",
            "sleeve": "short sleeve",
        },
        "options": {"sizes": ["XS", "S", "M", "L", "XL"]},
        "brand": "Sport Label",
        "in_stock": True,
    },

    # ── Tops ─────────────────────────────────────────────────────────────────

    {
        "id": "top_caroline_polo_white",
        "name": "Caroline Polo — Classic White",
        "category": "tops",
        "price": 88.00,
        "description": "polo shirt white cotton pique classic preppy casual sport office weekend versatile",
        "attributes": {
            "fabric": "cotton pique",
            "fit": "relaxed",
            "occasion": ["casual", "office", "weekend", "sport"],
            "color": "white",
            "print": "solid",
            "sleeve": "short sleeve",
        },
        "options": {"sizes": ["XS", "S", "M", "L", "XL", "XXL"]},
        "brand": "the store",
        "in_stock": True,
    },
    {
        "id": "top_ryan_tee_navy",
        "name": "Ryan Tee — Navy",
        "category": "tops",
        "price": 58.00,
        "description": "navy tee t-shirt cotton casual everyday wardrobe staple basic top",
        "attributes": {
            "fabric": "cotton",
            "fit": "relaxed",
            "occasion": ["casual", "weekend"],
            "color": "navy",
            "print": "solid",
            "sleeve": "short sleeve",
        },
        "options": {"sizes": ["XS", "S", "M", "L", "XL", "XXL"]},
        "brand": "the store",
        "in_stock": True,
    },
    {
        "id": "top_isla_stripe_jacket",
        "name": "Isla Stripe Loren Jacket",
        "category": "tops",
        "price": 248.00,
        "description": "stripe blazer jacket linen cotton casual preppy coastal smart casual office work",
        "attributes": {
            "fabric": "linen-cotton blend",
            "fit": "relaxed",
            "occasion": ["office", "casual", "daytime elegance"],
            "color": "blue and white stripe",
            "print": "stripe",
            "sleeve": "long sleeve",
        },
        "options": {"sizes": ["XS", "S", "M", "L", "XL"]},
        "brand": "the store",
        "in_stock": True,
    },

    # ── Sweaters ──────────────────────────────────────────────────────────────

    {
        "id": "sweater_campbell_cashmere",
        "name": "Campbell Pullover — Ivory Cashmere",
        "category": "sweaters",
        "price": 298.00,
        "description": "cashmere pullover sweater ivory cream classic cozy luxury soft layering fall winter",
        "attributes": {
            "fabric": "100% cashmere",
            "fit": "relaxed",
            "occasion": ["casual", "office", "weekend"],
            "color": "ivory",
            "print": "solid",
            "sleeve": "long sleeve",
            "neckline": "crewneck",
        },
        "options": {"sizes": ["XS", "S", "M", "L", "XL"]},
        "brand": "The Luxe Label",
        "in_stock": True,
    },
    {
        "id": "sweater_cady_quarter_zip",
        "name": "Cady Quarter Zip — Navy",
        "category": "sweaters",
        "price": 148.00,
        "description": "quarter zip pullover sweater navy sporty casual preppy cotton blend sport store",
        "attributes": {
            "fabric": "cotton blend",
            "fit": "relaxed",
            "occasion": ["casual", "sport", "weekend"],
            "color": "navy",
            "print": "solid",
            "sleeve": "long sleeve",
        },
        "options": {"sizes": ["XS", "S", "M", "L", "XL", "XXL"]},
        "brand": "the store",
        "in_stock": True,
    },

    # ── Bottoms ───────────────────────────────────────────────────────────────

    {
        "id": "pants_millie_white",
        "name": "Millie Pant — White",
        "category": "bottoms",
        "price": 128.00,
        "description": "white pants wide leg casual relaxed spring summer cotton linen office weekend",
        "attributes": {
            "fabric": "cotton blend",
            "fit": "wide leg / relaxed",
            "occasion": ["casual", "office", "weekend"],
            "color": "white",
            "print": "solid",
            "length": "full length",
        },
        "options": {"sizes": ["XS", "S", "M", "L", "XL", "XXL"]},
        "brand": "the store",
        "in_stock": True,
    },
    {
        "id": "shorts_isla_archer",
        "name": "Isla Stripe Archer Short",
        "category": "bottoms",
        "price": 128.00,
        "description": "stripe shorts bermuda navy white casual preppy beach resort weekend summer linen cotton",
        "attributes": {
            "fabric": "linen-cotton blend",
            "fit": "relaxed",
            "occasion": ["casual", "beach/resort", "weekend"],
            "color": "navy and white stripe",
            "print": "stripe",
            "length": "bermuda",
        },
        "options": {"sizes": ["XS", "S", "M", "L", "XL"]},
        "brand": "the store",
        "in_stock": True,
    },

    # ── Swimwear ──────────────────────────────────────────────────────────────

    {
        "id": "swim_caftan_stripe",
        "name": "Cardigan Caftan — Blue Stripe",
        "category": "swimwear",
        "price": 168.00,
        "description": "caftan cover up beach resort pool stripe blue white swimwear coverup linen casual",
        "attributes": {
            "fabric": "linen blend",
            "fit": "oversized/caftan",
            "occasion": ["beach/resort", "casual"],
            "color": "blue stripe",
            "print": "stripe",
            "sleeve": "long sleeve open front",
        },
        "options": {"sizes": ["XS/S", "M/L", "XL/XXL"]},
        "brand": "Beach Label",
        "in_stock": True,
    },
]


def main():
    output_path = Path("data/products.json")
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(PRODUCTS, f, indent=2, ensure_ascii=False)

    print(f"✅ Seeded {len(PRODUCTS)} products → {output_path}")
    print("\nCategories:")
    cats = Counter(p["category"] for p in PRODUCTS)
    for cat, count in cats.items():
        print(f"  {cat}: {count} products")


if __name__ == "__main__":
    main()
