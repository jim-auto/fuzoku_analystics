import re
from dataclasses import dataclass, field

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


def collect_area_list_paths(
    client,
    region_slug: str,
    biz_id: str,
    pref_html: str,
    base_url: str,
) -> list[str]:
    """Gather sub-area shop-list URLs from prefecture top and genre index page."""
    default = f"/{region_slug}/shop-list/{biz_id}/"
    seen: set[str] = set()
    paths: list[str] = []

    def add(path: str) -> None:
        if path not in seen:
            seen.add(path)
            paths.append(path)

    for path in parse_area_genre_links(pref_html, region_slug, biz_id):
        add(path)

    index_html = client.get(f"{base_url}{default}")
    for path in parse_area_genre_links(index_html, region_slug, biz_id):
        add(path)

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
