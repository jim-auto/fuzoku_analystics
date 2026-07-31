"""Snapshot history and week-over-week deltas."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

MAX_SNAPSHOTS = 52


def _capture_id() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def compact_snapshot(aggregated: dict[str, Any]) -> dict[str, Any]:
    regions = {}
    for region in aggregated.get("regions", []):
        top_shops = [
            {
                "url": s["url"],
                "name": s["name"],
                "review_count": s.get("review_count"),
            }
            for s in (region.get("top_by_reviews") or [])[:20]
        ]
        regions[region["slug"]] = {
            "shop_count": region.get("shop_count"),
            "girl_count": region.get("girl_count"),
            "sampled": region.get("coverage", {}).get("sampled"),
            "median_price": region.get("price_stats", {}).get("median"),
            "median_reviews": region.get("review_stats", {}).get("median"),
            "median_ppm": region.get("price_per_minute_stats", {}).get("median"),
            "genre_deli": next(
                (g["shop_count"] for g in region.get("genres", []) if g["id"] == "biz6"),
                None,
            ),
            "top_shops": top_shops,
        }
    return {
        "captured_at": _capture_id(),
        "date": date.today().isoformat(),
        "metro_median_price": aggregated.get("metro_overview", {})
        .get("metro_price_stats", {})
        .get("median"),
        "regions": regions,
    }


def load_history(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("snapshots", [])


def save_history(path: Path, snapshots: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    trimmed = snapshots[-MAX_SNAPSHOTS:]
    payload = json.dumps({"snapshots": trimmed}, ensure_ascii=False, indent=2)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)


def append_snapshot(path: Path, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    snapshots = load_history(path)
    snapshots.append(snapshot)
    save_history(path, snapshots)
    return snapshots[-MAX_SNAPSHOTS:]


def _delta(current: int | float | None, previous: int | float | None) -> int | float | None:
    if current is None or previous is None:
        return None
    return current - previous


def _review_movers(
    current_shops: list[dict],
    previous_shops: list[dict],
    limit: int = 5,
) -> list[dict[str, Any]]:
    prev_by_url = {s["url"]: s for s in previous_shops}
    movers = []
    for shop in current_shops:
        prev = prev_by_url.get(shop["url"])
        if not prev or shop.get("review_count") is None or prev.get("review_count") is None:
            continue
        diff = shop["review_count"] - prev["review_count"]
        if diff > 0:
            movers.append(
                {
                    "name": shop["name"],
                    "url": shop["url"],
                    "review_count": shop["review_count"],
                    "review_delta": diff,
                }
            )
    movers.sort(key=lambda m: m["review_delta"], reverse=True)
    return movers[:limit]


def _rank_changes(
    current_shops: list[dict],
    previous_shops: list[dict],
    limit: int = 5,
) -> list[dict[str, Any]]:
    prev_rank = {s["url"]: i + 1 for i, s in enumerate(previous_shops)}
    changes = []
    for i, shop in enumerate(current_shops[:20]):
        new_rank = i + 1
        old_rank = prev_rank.get(shop["url"])
        if old_rank is None:
            changes.append(
                {
                    "name": shop["name"],
                    "url": shop["url"],
                    "new_rank": new_rank,
                    "old_rank": None,
                    "rank_delta": None,
                    "label": "新規ランクイン",
                }
            )
        elif old_rank != new_rank:
            changes.append(
                {
                    "name": shop["name"],
                    "url": shop["url"],
                    "new_rank": new_rank,
                    "old_rank": old_rank,
                    "rank_delta": old_rank - new_rank,
                    "label": f"{old_rank}位→{new_rank}位",
                }
            )
    changes.sort(key=lambda c: (c.get("rank_delta") is not None, c.get("rank_delta") or 0), reverse=True)
    return changes[:limit]


def compute_changes(
    current: dict[str, Any],
    snapshots: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if len(snapshots) < 2:
        return None

    previous = snapshots[-2]

    try:
        prev_date = previous.get("date") or previous.get("captured_at", "")[:10]
        cur_date = current.get("date") or current.get("captured_at", "")[:10]
        since = datetime.strptime(prev_date, "%Y-%m-%d").date()
        until = datetime.strptime(cur_date, "%Y-%m-%d").date()
        days = (until - since).days
        if days == 0:
            days = 1
    except ValueError:
        days = None

    region_changes = []
    for slug, cur in current.get("regions", {}).items():
        prev = previous.get("regions", {}).get(slug, {})
        region_changes.append(
            {
                "slug": slug,
                "shop_count_delta": _delta(cur.get("shop_count"), prev.get("shop_count")),
                "girl_count_delta": _delta(cur.get("girl_count"), prev.get("girl_count")),
                "sampled_delta": _delta(cur.get("sampled"), prev.get("sampled")),
                "median_price_delta": _delta(cur.get("median_price"), prev.get("median_price")),
                "median_reviews_delta": _delta(cur.get("median_reviews"), prev.get("median_reviews")),
                "genre_deli_delta": _delta(cur.get("genre_deli"), prev.get("genre_deli")),
                "review_movers": _review_movers(
                    cur.get("top_shops", []),
                    prev.get("top_shops", []),
                ),
                "rank_changes": _rank_changes(
                    cur.get("top_shops", []),
                    prev.get("top_shops", []),
                ),
            }
        )

    return {
        "since": previous.get("captured_at") or previous.get("date"),
        "days": days,
        "metro_median_price_delta": _delta(
            current.get("metro_median_price"),
            previous.get("metro_median_price"),
        ),
        "regions": region_changes,
    }


def build_trends(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    """Compact time-series for charts."""
    if not snapshots:
        return {"dates": [], "series": {}}

    dates = [s.get("date") or (s.get("captured_at", "")[:10]) for s in snapshots]
    series: dict[str, dict[str, list]] = {
        slug: {
            "shop_count": [],
            "girl_count": [],
            "median_price": [],
            "median_reviews": [],
        }
        for slug in ("tokyo", "aichi", "osaka")
    }

    for snap in snapshots:
        for slug, metrics in series.items():
            region = snap.get("regions", {}).get(slug, {})
            for key in metrics:
                metrics[key].append(region.get(key))

    return {"dates": dates, "series": series}
