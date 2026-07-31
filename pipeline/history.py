"""Snapshot history and week-over-week deltas."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

MAX_SNAPSHOTS = 52


def _today_str() -> str:
    return date.today().isoformat()


def compact_snapshot(aggregated: dict[str, Any]) -> dict[str, Any]:
    regions = {}
    for region in aggregated.get("regions", []):
        top_shops = [
            {
                "url": s["url"],
                "name": s["name"],
                "review_count": s.get("review_count"),
            }
            for s in (region.get("top_by_reviews") or [])[:15]
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
        "date": _today_str(),
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
    path.write_text(
        json.dumps({"snapshots": trimmed}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def append_snapshot(path: Path, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    snapshots = load_history(path)
    snapshots = [s for s in snapshots if s.get("date") != snapshot["date"]]
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


def compute_changes(
    current: dict[str, Any],
    snapshots: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if len(snapshots) < 2:
        return None

    previous = snapshots[-2]
    if previous.get("date") == current.get("date"):
        previous = snapshots[-3] if len(snapshots) >= 3 else None
    if not previous:
        return None

    try:
        since = datetime.strptime(previous["date"], "%Y-%m-%d").date()
        until = datetime.strptime(current["date"], "%Y-%m-%d").date()
        days = (until - since).days
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
            }
        )

    return {
        "since": previous["date"],
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

    dates = [s["date"] for s in snapshots]
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
