import math
import re
import statistics
from typing import Any, Callable


PRICE_BUCKETS: list[tuple[int, int, str]] = [
    (0, 10_000, "〜1万円"),
    (10_000, 15_000, "1〜1.5万"),
    (15_000, 20_000, "1.5〜2万"),
    (20_000, 30_000, "2〜3万"),
    (30_000, 50_000, "3〜5万"),
    (50_000, math.inf, "5万円〜"),
]

REVIEW_BUCKETS: list[tuple[int, int, str]] = [
    (0, 100, "〜100"),
    (100, 500, "100〜500"),
    (500, 2_000, "500〜2千"),
    (2_000, 10_000, "2千〜1万"),
    (10_000, math.inf, "1万〜"),
]


def percentile(values: list[int | float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = (len(ordered) - 1) * pct
    lower = int(math.floor(idx))
    upper = int(math.ceil(idx))
    if lower == upper:
        return float(ordered[lower])
    weight = idx - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def numeric_stats(values: list[int | float]) -> dict[str, int | float | None]:
    if not values:
        return {
            "count": 0,
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "stdev": None,
            "p25": None,
            "p75": None,
        }
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": round(statistics.mean(values), 1),
        "median": int(statistics.median(values)),
        "stdev": round(statistics.stdev(values), 1) if len(values) > 1 else 0.0,
        "p25": int(percentile(values, 0.25) or 0),
        "p75": int(percentile(values, 0.75) or 0),
    }


def histogram(
    values: list[int | float],
    buckets: list[tuple[int, int, str]],
) -> list[dict[str, Any]]:
    if not values:
        return [{"label": label, "count": 0, "pct": 0.0} for _, _, label in buckets]
    total = len(values)
    result = []
    for low, high, label in buckets:
        count = sum(1 for v in values if low <= v < high)
        result.append({"label": label, "count": count, "pct": round(count / total * 100, 1)})
    return result


def parse_genre_label(label: str) -> dict[str, str | None]:
    match = re.match(r"^([^(（]+)(?:[（(]([^/／]+)[/／]([^)）]+)[)）])?", label)
    if match:
        return {
            "biz": match.group(1).strip() or None,
            "subgenre": match.group(2).strip() if match.group(2) else None,
            "area": match.group(3).strip() if match.group(3) else None,
        }
    return {"biz": label or None, "subgenre": None, "area": None}


def dedupe_shops(shops: list[dict]) -> list[dict]:
    by_url: dict[str, dict] = {}
    for shop in shops:
        url = shop.get("url", "")
        if url and url not in by_url:
            by_url[url] = shop
    return list(by_url.values())


def shops_with_ppm(shops: list[dict]) -> list[dict]:
    enriched = []
    for shop in shops:
        if shop.get("min_price") and shop.get("min_minutes"):
            ppm = shop["min_price"] / shop["min_minutes"]
            enriched.append({**shop, "price_per_minute": round(ppm, 1)})
    return enriched


def group_analysis(
    shops: list[dict],
    key_fn: Callable[[dict], str | None],
    min_count: int = 3,
    limit: int = 12,
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict]] = {}
    for shop in shops:
        key = key_fn(shop)
        if not key:
            continue
        groups.setdefault(key, []).append(shop)

    total = sum(len(v) for v in groups.values())
    rows = []
    for name, items in groups.items():
        if len(items) < min_count:
            continue
        prices = [s["min_price"] for s in items if s.get("min_price")]
        reviews = [s["review_count"] for s in items if s.get("review_count")]
        rows.append(
            {
                "name": name,
                "count": len(items),
                "pct": round(len(items) / total * 100, 1) if total else 0,
                "median_price": int(statistics.median(prices)) if prices else None,
                "median_reviews": int(statistics.median(reviews)) if reviews else None,
                "mean_price": round(statistics.mean(prices), 0) if prices else None,
            }
        )

    rows.sort(key=lambda r: r["count"], reverse=True)
    return rows[:limit]


def market_concentration(shops: list[dict]) -> dict[str, float | None]:
    reviews = sorted(
        [s["review_count"] for s in shops if s.get("review_count")],
        reverse=True,
    )
    if not reviews:
        return {"top5_share_pct": None, "top10_share_pct": None, "total_reviews": 0}
    total = sum(reviews)
    top5 = sum(reviews[:5])
    top10 = sum(reviews[:10])
    return {
        "top5_share_pct": round(top5 / total * 100, 1),
        "top10_share_pct": round(top10 / total * 100, 1),
        "total_reviews": total,
    }


def genre_analysis(shops: list[dict], genres: list[dict]) -> list[dict[str, Any]]:
    total_sampled = len(shops)
    rows = []
    for genre in genres:
        genre_shops = [
            s for s in shops if parse_genre_label(s.get("genre", "")).get("biz") == genre["name"]
        ]
        prices = [s["min_price"] for s in genre_shops if s.get("min_price")]
        reviews = [s["review_count"] for s in genre_shops if s.get("review_count")]
        ppms = [
            s["min_price"] / s["min_minutes"]
            for s in genre_shops
            if s.get("min_price") and s.get("min_minutes")
        ]
        rows.append(
            {
                "id": genre["id"],
                "name": genre["name"],
                "listed_count": genre["shop_count"],
                "sampled_count": len(genre_shops),
                "sample_pct": round(len(genre_shops) / total_sampled * 100, 1) if total_sampled else 0,
                "median_price": int(statistics.median(prices)) if prices else None,
                "median_reviews": int(statistics.median(reviews)) if reviews else None,
                "median_ppm": round(statistics.median(ppms), 1) if ppms else None,
            }
        )
    return rows


def build_price_heatmap(
    shops: list[dict],
    top_areas: int = 8,
    min_count: int = 2,
) -> dict[str, Any]:
    """Area × business-type median price matrix for heatmap display."""
    from collections import defaultdict

    cells: dict[tuple[str, str], list[int]] = defaultdict(list)
    area_counts: dict[str, int] = defaultdict(int)
    biz_types: set[str] = set()

    for shop in shops:
        parsed = parse_genre_label(shop.get("genre", ""))
        area, biz = parsed.get("area"), parsed.get("biz")
        price = shop.get("min_price")
        if not area or not biz or not price:
            continue
        area_counts[area] += 1
        cells[(area, biz)].append(price)
        biz_types.add(biz)

    areas = [
        name
        for name, _ in sorted(area_counts.items(), key=lambda x: x[1], reverse=True)
        if area_counts[name] >= min_count
    ][:top_areas]
    biz_list = sorted(biz_types)

    matrix: list[list[int | None]] = []
    for area in areas:
        row: list[int | None] = []
        for biz in biz_list:
            prices = cells.get((area, biz), [])
            row.append(int(statistics.median(prices)) if len(prices) >= min_count else None)
        matrix.append(row)

    return {"areas": areas, "biz_types": biz_list, "matrix": matrix}
