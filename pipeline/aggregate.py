import statistics
from typing import Any

from pipeline.stats import (
    REVIEW_BUCKETS,
    PRICE_BUCKETS,
    dedupe_shops,
    genre_analysis,
    group_analysis,
    histogram,
    market_concentration,
    numeric_stats,
    parse_genre_label,
    shops_with_ppm,
)


def _insights_for_region(region: dict, all_medians: dict[str, int | None]) -> list[str]:
    insights: list[str] = []
    shops = dedupe_shops(region["shops"])
    price_median = numeric_stats([s["min_price"] for s in shops if s.get("min_price")]).get("median")
    review_median = numeric_stats([s["review_count"] for s in shops if s.get("review_count")]).get("median")
    coverage = region.get("coverage", {})

    if coverage.get("pct") is not None:
        insights.append(
            f"公式掲載 {coverage['official']:,} 店のうち {coverage['sampled']:,} 店をサンプリング（{coverage['pct']}%）"
        )

    if price_median and all_medians.get("price"):
        diff = price_median - all_medians["price"]
        if abs(diff) >= 1000:
            direction = "高め" if diff > 0 else "低め"
            insights.append(f"最低コース相場は3都市平均より {abs(diff):,}円{direction}（中央値 {price_median:,}円）")

    genres = region.get("genre_analysis") or []
    if genres:
        top_genre = max(genres, key=lambda g: g.get("sampled_count") or 0)
        insights.append(
            f"サンプル内では{top_genre['name']}が最多（{top_genre['sampled_count']}店・{top_genre['sample_pct']}%）"
        )

    areas = region.get("area_analysis") or []
    if areas:
        top_area = areas[0]
        insights.append(
            f"エリア別では「{top_area['name']}」の店舗密度が最高（{top_area['count']}店・中央値 {top_area.get('median_price', '—')}円）"
        )

    conc = region.get("market_concentration") or {}
    if conc.get("top5_share_pct"):
        insights.append(
            f"口コミ件数の上位5店で全体の {conc['top5_share_pct']}% を占有（集中度指標）"
        )

    if review_median:
        insights.append(f"口コミ件数の中央値は {int(review_median):,} 件（レビュー厚みの目安）")

    return insights


def _metro_insights(regions: list[dict]) -> list[str]:
    insights: list[str] = []
    if not regions:
        return insights

    by_price = sorted(
        [(r["short"], r["price_stats"].get("median")) for r in regions if r["price_stats"].get("median")],
        key=lambda x: x[1],
    )
    if len(by_price) >= 2:
        cheapest, expensive = by_price[0], by_price[-1]
        insights.append(f"相場最安は{cheapest[0]}（中央値 {cheapest[1]:,}円）、最高は{expensive[0]}（{expensive[1]:,}円）")

    by_girl = sorted(regions, key=lambda r: r.get("girl_per_shop") or 0, reverse=True)
    if by_girl:
        insights.append(
            f"在籍/店舗比は{by_girl[0]['short']}が最大（{by_girl[0].get('girl_per_shop')} 人/店）→ 選択肢の厚み"
        )

    total_official = sum(r.get("shop_count") or 0 for r in regions)
    total_sampled = sum(r.get("coverage", {}).get("sampled") or 0 for r in regions)
    if total_official:
        insights.append(f"3都市合計 {total_official:,} 店中 {total_sampled:,} 店を統計分析に使用")

    return insights


def aggregate(raw: dict) -> dict[str, Any]:
    regions_out: list[dict] = []
    comparison: list[dict] = []

    for region in raw["regions"]:
        shops = dedupe_shops(region["shops"])
        prices = [s["min_price"] for s in shops if s.get("min_price")]
        reviews = [s["review_count"] for s in shops if s.get("review_count")]
        ppms = [
            s["min_price"] / s["min_minutes"]
            for s in shops
            if s.get("min_price") and s.get("min_minutes")
        ]

        official = region.get("shop_count") or 0
        sampled = len(shops)
        coverage_pct = round(sampled / official * 100, 1) if official else None

        genre_breakdown = [
            {"id": g["id"], "name": g["name"], "shop_count": g["shop_count"]}
            for g in region["genres"]
        ]

        top_reviews = sorted(
            [s for s in shops if s.get("review_count")],
            key=lambda s: s["review_count"],
            reverse=True,
        )[:10]

        top_value = sorted(
            shops_with_ppm(shops),
            key=lambda s: (s.get("review_count") or 0) / max(s.get("min_price") or 1, 1),
            reverse=True,
        )[:10]

        area_analysis = group_analysis(
            shops,
            key_fn=lambda s: parse_genre_label(s.get("genre", "")).get("area"),
            min_count=3,
            limit=10,
        )
        subgenre_analysis = group_analysis(
            shops,
            key_fn=lambda s: parse_genre_label(s.get("genre", "")).get("subgenre"),
            min_count=3,
            limit=8,
        )

        region_summary: dict[str, Any] = {
            "slug": region["slug"],
            "name": region["name"],
            "short": region["short"],
            "shop_count": region["shop_count"],
            "girl_count": region["girl_count"],
            "girl_per_shop": round(region["girl_count"] / region["shop_count"], 1)
            if region.get("girl_count") and region.get("shop_count")
            else None,
            "genres": genre_breakdown,
            "coverage": {
                "official": official,
                "sampled": sampled,
                "pct": coverage_pct,
            },
            "price_stats": numeric_stats(prices),
            "price_per_minute_stats": numeric_stats(ppms),
            "review_stats": numeric_stats(reviews),
            "price_histogram": histogram(prices, PRICE_BUCKETS),
            "review_histogram": histogram(reviews, REVIEW_BUCKETS),
            "genre_analysis": genre_analysis(shops, region["genres"]),
            "area_analysis": area_analysis,
            "subgenre_analysis": subgenre_analysis,
            "market_concentration": market_concentration(shops),
            "top_by_reviews": top_reviews,
            "top_by_value": [
                {
                    "name": s["name"],
                    "url": s["url"],
                    "genre": s.get("genre"),
                    "review_count": s.get("review_count"),
                    "min_minutes": s.get("min_minutes"),
                    "min_price": s.get("min_price"),
                    "price_per_minute": s.get("price_per_minute"),
                }
                for s in top_value
            ],
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
                "mean_price": region_summary["price_stats"]["mean"],
                "median_ppm": region_summary["price_per_minute_stats"]["median"],
                "median_reviews": region_summary["review_stats"]["median"],
                "genre_deli": next((g["shop_count"] for g in genre_breakdown if g["id"] == "biz6"), 0),
                "genre_soap": next((g["shop_count"] for g in genre_breakdown if g["id"] == "biz4"), 0),
                "coverage_pct": coverage_pct,
                "top5_review_share": region_summary["market_concentration"].get("top5_share_pct"),
            }
        )

    all_prices = [
        s["min_price"]
        for region in raw["regions"]
        for s in dedupe_shops(region["shops"])
        if s.get("min_price")
    ]
    metro_median_price = int(statistics.median(all_prices)) if all_prices else None

    for region in regions_out:
        shops_raw = next(r["shops"] for r in raw["regions"] if r["slug"] == region["slug"])
        region["insights"] = _insights_for_region({**region, "shops": shops_raw}, {"price": metro_median_price})

    metro_overview = {
        "total_official_shops": sum(r.get("shop_count") or 0 for r in regions_out),
        "total_sampled_shops": sum(r["coverage"]["sampled"] for r in regions_out),
        "metro_price_stats": numeric_stats(all_prices),
        "insights": _metro_insights(regions_out),
    }

    return {
        "metro_overview": metro_overview,
        "regions": regions_out,
        "comparison": comparison,
    }
