import httpx

from scraper.client import HeavenClient
from scraper.config import BASE_URL, GENRES, REGIONS, Region
from scraper.parse import (
    ShopRecord,
    collect_area_codes_for_region,
    collect_area_list_paths,
    parse_prefecture_counts,
    parse_shop_list,
    parse_shop_list_page_links,
)


def _normalize_url(url: str) -> str:
    return url.split("?")[0]


def _merge_shops(target: dict[str, ShopRecord], shops: list[ShopRecord]) -> None:
    for shop in shops:
        key = _normalize_url(shop.url)
        shop.url = key
        if key not in target:
            target[key] = shop


def fetch_region_summary(client: HeavenClient, region: Region) -> tuple[dict, str]:
    html = client.get(f"{BASE_URL}/{region.slug}/")
    shop_count, girl_count = parse_prefecture_counts(html)
    summary = {
        "slug": region.slug,
        "name": region.name,
        "short": region.short,
        "shop_count": shop_count,
        "girl_count": girl_count,
    }
    return summary, html


def fetch_genre_shops(
    client: HeavenClient,
    region: Region,
    biz_id: str,
    pref_html: str,
    area_codes: list[str] | None = None,
) -> tuple[int, list[ShopRecord]]:
    shops_by_url: dict[str, ShopRecord] = {}
    list_paths = collect_area_list_paths(
        client, region.slug, biz_id, pref_html, BASE_URL, area_codes=area_codes
    )
    fetched_pages: set[str] = set()

    for path in list_paths:
        try:
            html = client.get(f"{BASE_URL}{path}")
        except httpx.HTTPStatusError:
            continue
        page_urls = [path] + [
            p for p in parse_shop_list_page_links(html, region.slug, path) if p != path
        ][:3]
        for page_path in page_urls:
            if page_path in fetched_pages:
                continue
            fetched_pages.add(page_path)
            try:
                if page_path != path:
                    html = client.get(f"{BASE_URL}{page_path}")
            except httpx.HTTPStatusError:
                continue
            result = parse_shop_list(html, region.slug)
            _merge_shops(shops_by_url, result.shops)

    return len(shops_by_url), list(shops_by_url.values())


def fetch_all(client: HeavenClient) -> dict:
    regions_data = []
    for region in REGIONS:
        summary, pref_html = fetch_region_summary(client, region)
        area_codes = collect_area_codes_for_region(client, region.slug, pref_html, BASE_URL)
        genres = []
        all_shops: list[ShopRecord] = []

        for biz_id, genre_name in GENRES.items():
            shop_count, shops = fetch_genre_shops(
                client, region, biz_id, pref_html, area_codes=area_codes
            )
            genres.append(
                {
                    "id": biz_id,
                    "name": genre_name,
                    "shop_count": shop_count,
                }
            )
            for shop in shops:
                shop.genre_label = shop.genre_label or genre_name
                all_shops.append(shop)

        regions_data.append(
            {
                **summary,
                "genres": genres,
                "shops": [
                    {
                        "name": s.name,
                        "url": s.url,
                        "genre": s.genre_label,
                        "review_count": s.review_count,
                        "min_minutes": s.min_minutes,
                        "min_price": s.min_price,
                    }
                    for s in all_shops
                ],
            }
        )

    return {"regions": regions_data}
