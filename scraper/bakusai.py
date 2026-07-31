"""Bakusai thread-list scraper (metadata only, no post bodies)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

BAKUSAI_BASE = "https://bakusai.com"

BOARDS: dict[str, dict[str, str]] = {
    "tokyo": {
        "name": "東京",
        "list_url": f"{BAKUSAI_BASE}/thr_tl/acode=3/ctgid=103/bid=412/",
        "ctgid": "103",
        "bid": "412",
    },
    "osaka": {
        "name": "大阪",
        "list_url": f"{BAKUSAI_BASE}/thr_tl/acode=7/ctgid=103/bid=410/",
        "ctgid": "103",
        "bid": "410",
    },
    "aichi": {
        "name": "名古屋",
        "list_url": f"{BAKUSAI_BASE}/thr_tl/acode=5/ctgid=103/bid=472/",
        "ctgid": "103",
        "bid": "472",
    },
}


@dataclass
class BakusaiThread:
    title: str
    url: str
    views: int
    responses: int
    area: str | None


def _parse_count(raw: str) -> int:
    raw = raw.replace(",", "").strip()
    if raw.endswith("万"):
        return int(float(raw[:-1]) * 10_000)
    if "." in raw:
        return int(float(raw) * 10_000)
    return int(raw)


def _parse_area(title: str) -> str | None:
    m = re.search(r"【([^】]+)】", title)
    return m.group(1).strip() if m else None


def _normalize_shop_name(title: str) -> str:
    t = re.sub(r"【[^】]*】", "", title)
    t = re.sub(r"[①-⑳⓪-㊿]+", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:80]


def parse_thread_list(html: str, ctgid: str, bid: str) -> list[BakusaiThread]:
    soup = BeautifulSoup(html, "html.parser")
    needle = f"ctgid={ctgid}/bid={bid}/tid="
    rows: list[BakusaiThread] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if needle not in href:
            continue
        title = anchor.get_text(" ", strip=True)
        title = re.split(r"\s*閲覧数", title)[0].strip()
        title = re.sub(r"^\d+\s+", "", title)
        title = re.sub(r"\s*\d+\s*分前\s*$", "", title).strip()
        title = re.sub(r"\s+\d{1,3}\s*$", "", title).strip()
        if len(title) < 4:
            continue

        node = anchor.parent
        views = responses = None
        for _ in range(6):
            if node is None:
                break
            text = node.get_text(" ", strip=True)
            vm = re.search(r"閲覧数\s*([\d,.]+万?)", text)
            rm = re.search(r"レス数\s*([\d,.]+万?)", text)
            if vm and rm:
                views = _parse_count(vm.group(1))
                responses = _parse_count(rm.group(1))
                break
            node = node.parent

        if views is None or responses is None:
            continue

        url = BAKUSAI_BASE + href.split("/tp=")[0].rstrip("/") + "/"
        if url in seen:
            continue
        seen.add(url)

        rows.append(
            BakusaiThread(
                title=title,
                url=url,
                views=views,
                responses=responses,
                area=_parse_area(title),
            )
        )

    return rows


def analyze_threads(threads: list[BakusaiThread]) -> dict:
    if not threads:
        return {"thread_count": 0, "top_by_responses": [], "top_by_views": [], "area_stats": []}

    by_area: dict[str, list[BakusaiThread]] = {}
    for t in threads:
        key = t.area or "その他"
        by_area.setdefault(key, []).append(t)

    area_stats = sorted(
        [
            {
                "area": area,
                "thread_count": len(items),
                "total_responses": sum(t.responses for t in items),
                "median_responses": sorted(t.responses for t in items)[len(items) // 2],
            }
            for area, items in by_area.items()
        ],
        key=lambda x: x["total_responses"],
        reverse=True,
    )[:10]

    def as_dict(t: BakusaiThread) -> dict:
        return {
            "title": t.title,
            "shop_name": _normalize_shop_name(t.title),
            "url": t.url,
            "views": t.views,
            "responses": t.responses,
            "area": t.area,
        }

    top_resp = sorted(threads, key=lambda t: t.responses, reverse=True)[:15]
    top_views = sorted(threads, key=lambda t: t.views, reverse=True)[:10]

    return {
        "thread_count": len(threads),
        "total_responses": sum(t.responses for t in threads),
        "total_views": sum(t.views for t in threads),
        "top_by_responses": [as_dict(t) for t in top_resp],
        "top_by_views": [as_dict(t) for t in top_views],
        "area_stats": area_stats,
    }


def fetch_bakusai_board(client, slug: str) -> dict:
    board = BOARDS[slug]
    html = client.get(board["list_url"])
    threads = parse_thread_list(html, board["ctgid"], board["bid"])
    return {
        "slug": slug,
        "name": board["name"],
        "board_url": board["list_url"],
        **analyze_threads(threads),
    }


def fetch_all_bakusai(client) -> dict:
    regions = [fetch_bakusai_board(client, slug) for slug in BOARDS]
    return {
        "source": BAKUSAI_BASE,
        "note": "スレッド一覧のメタデータのみ（レス本文は取得・転載していません）",
        "regions": regions,
    }
