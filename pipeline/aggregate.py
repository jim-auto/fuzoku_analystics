import statistics
from typing import Any


def _percentile(values: list[int], pct: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = int(round((len(ordered) - 1) * pct))
    return ordered[idx]


def _price_stats(prices: list[int]) -> dict[str, int | None]:
    if not prices:
        return {"count": 0, "min": None, "median": None, "p25": None, "p75": None, "max": None}
    return {
        "count": len(prices),
        "min": min(prices),
        "median": int(statistics.median(prices)),
        "p25": _percentile(prices, 0.25),
        "p75": _percentile(prices, 0.75),
        "max": max(prices),
    }


def aggregate(raw: dict) -> dict[str, Any]:
    regions_out = []
    comparison = []

    for region in raw["regions"]:
        prices = [s["min_price"] for s in region["shops"] if s.get("min_price")]
        reviews = [s["review_count"] for s in region["shops"] if s.get("review_count")]

        genre_breakdown = [
            {"id": g["id"], "name": g["name"], "shop_count": g["shop_count"]}
            for g in region["genres"]
        ]

        top_reviews = sorted(
            [s for s in region["shops"] if s.get("review_count")],
            key=lambda s: s["review_count"],
            reverse=True,
        )[:10]

        top_value = sorted(
            [s for s in region["shops"] if s.get("min_price") and s.get("review_count")],
            key=lambda s: s["review_count"] / max(s["min_price"], 1),
            reverse=True,
        )[:10]

        region_summary = {
            "slug": region["slug"],
            "name": region["name"],
            "short": region["short"],
            "shop_count": region["shop_count"],
            "girl_count": region["girl_count"],
            "girl_per_shop": round(region["girl_count"] / region["shop_count"], 1)
            if region.get("girl_count") and region.get("shop_count")
            else None,
            "genres": genre_breakdown,
            "price_stats": _price_stats(prices),
            "review_stats": {
                "count": len(reviews),
                "median": int(statistics.median(reviews)) if reviews else None,
                "max": max(reviews) if reviews else None,
            },
            "top_by_reviews": top_reviews,
            "top_by_value": top_value,
        }
        regions_out.append(region_summary)

        comparison.append(
            {
                "slug": region["slug"],
                "name": region["short"],
                "shop_count": region["shop_count"],
                "girl_count": region["girl_count"],
                "girl_per_shop": region_summary["girl_per_shop"],
                "median_price": region_summary["price_stats"]["median"],
                "genre_deli": next((g["shop_count"] for g in genre_breakdown if g["id"] == "biz6"), 0),
                "genre_soap": next((g["shop_count"] for g in genre_breakdown if g["id"] == "biz4"), 0),
            }
        )

    return {
        "regions": regions_out,
        "comparison": comparison,
    }
