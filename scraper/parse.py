import re
from dataclasses import dataclass, field

import httpx
from bs4 import BeautifulSoup


@dataclass
class ShopRecord:
    name: str
    url: str
    genre_label: str
    review_count: int | None
    min_minutes: int | None
    min_price: int | None


@dataclass
class GenrePageResult:
    total_count: int | None
    shops: list[ShopRecord] = field(default_factory=list)


def parse_prefecture_counts(html: str) -> tuple[int | None, int | None]:
    soup = BeautifulSoup(html, "html.parser")
    nums = [int(n.get_text(strip=True)) for n in soup.select("span.num") if n.get_text(strip=True).isdigit()]
    if len(nums) >= 2:
        return nums[0], nums[1]
    return None, None


def parse_genre_total(html: str) -> int | None:
    match = re.search(r"全\s*(\d+)\s*件", html)
    if match:
        return int(match.group(1))
    return None


def _card_text(title_div) -> str:
    node = title_div
    for _ in range(6):
        if node is None:
            break
        text = node.get_text(" ", strip=True)
        if "口コミ:" in text:
            return text
        node = node.parent
    return title_div.get_text(" ", strip=True)


def parse_area_genre_links(html: str, region_slug: str, biz_id: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    pattern = re.compile(rf"^/{region_slug}/.+/shop-list/{biz_id}/?$")
    links: list[str] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].split("?")[0]
        if not pattern.match(href):
            continue
        if href in seen:
            continue
        seen.add(href)
        links.append(href)
    return links


def parse_area_codes(html: str, region_slug: str) -> list[str]:
    """Extract sub-area codes (e.g. A1317) linked from prefecture / hub pages."""
    soup = BeautifulSoup(html, "html.parser")
    pattern = re.compile(rf"^/{region_slug}/([A-Z]\d{{3,5}})/")
    codes: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].split("?")[0]
        match = pattern.match(href)
        if match:
            codes.add(match.group(1))
    return sorted(codes)


def parse_shop_list_page_links(html: str, region_slug: str, path: str) -> list[str]:
    """Discover paginated shop-list URLs for the same area/genre."""
    soup = BeautifulSoup(html, "html.parser")
    base = path.split("?")[0]
    pages: set[str] = {path.split("?")[0]}
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].split("#")[0]
        if not href.startswith(f"/{region_slug}/"):
            continue
        if not href.split("?")[0].startswith(base.rstrip("/")):
            continue
        if "shop-list" not in href:
            continue
        pages.add(href.split("?")[0] if "?" not in href else href)
    return sorted(pages)


def _fetch_html(client, url: str) -> str | None:
    try:
        return client.get(url)
    except httpx.HTTPStatusError:
        return None


def collect_area_codes_for_region(
    client,
    region_slug: str,
    pref_html: str,
    base_url: str,
) -> list[str]:
    """Collect sub-area codes once per prefecture (shared across genres)."""
    seed_html: list[str] = [pref_html]
    codes: set[str] = set()

    for hub_path in (f"/{region_slug}/shop-list/", f"/{region_slug}/region/shop-list/"):
        hub_html = _fetch_html(client, f"{base_url}{hub_path}")
        if hub_html:
            seed_html.append(hub_html)

    for html in seed_html:
        codes.update(parse_area_codes(html, region_slug))

    default_biz = "biz6"
    index_html = _fetch_html(client, f"{base_url}/{region_slug}/shop-list/{default_biz}/")
    if index_html:
        seed_html.append(index_html)
        codes.update(parse_area_codes(index_html, region_slug))

    return sorted(codes)[:80]


def collect_area_list_paths(
    client,
    region_slug: str,
    biz_id: str,
    pref_html: str,
    base_url: str,
    area_codes: list[str] | None = None,
) -> list[str]:
    """Gather sub-area shop-list URLs from prefecture top, hubs, and area codes."""
    default = f"/{region_slug}/shop-list/{biz_id}/"
    seen: set[str] = set()
    paths: list[str] = []

    def add(path: str) -> None:
        clean = path.split("?")[0]
        if clean not in seen:
            seen.add(clean)
            paths.append(clean)

    for path in parse_area_genre_links(pref_html, region_slug, biz_id):
        add(path)

    index_html = _fetch_html(client, f"{base_url}{default}")
    if index_html:
        for path in parse_area_genre_links(index_html, region_slug, biz_id):
            add(path)

    region_hub = f"/{region_slug}/region/shop-list/{biz_id}/"
    hub_html = _fetch_html(client, f"{base_url}{region_hub}")
    if hub_html:
        for path in parse_area_genre_links(hub_html, region_slug, biz_id):
            add(path)

    codes = area_codes if area_codes is not None else parse_area_codes(pref_html, region_slug)
    for code in codes:
        add(f"/{region_slug}/{code}/shop-list/{biz_id}/")

    add(default)
    return paths


def parse_shop_list(html: str, region_slug: str) -> GenrePageResult:
    soup = BeautifulSoup(html, "html.parser")
    total = parse_genre_total(html)
    shops: list[ShopRecord] = []

    for title_div in soup.select("div.shop_title"):
        name_el = title_div.select_one("a.shop_title_shop")
        genre_el = title_div.select_one(".shop_title_gyousyu")
        if not name_el:
            continue

        href = name_el.get("href", "").split("?")[0]
        if href and not href.startswith("http"):
            href = f"https://www.cityheaven.net{href}"

        card_text = _card_text(title_div)
        review_match = re.search(r"口コミ:(\d+)件", card_text)
        price_match = re.search(r"(\d+)分(\d+)円", card_text)

        shops.append(
            ShopRecord(
                name=name_el.get_text(strip=True),
                url=href,
                genre_label=genre_el.get_text(strip=True) if genre_el else "",
                review_count=int(review_match.group(1)) if review_match else None,
                min_minutes=int(price_match.group(1)) if price_match else None,
                min_price=int(price_match.group(2)) if price_match else None,
            )
        )

    return GenrePageResult(total_count=total, shops=shops)
