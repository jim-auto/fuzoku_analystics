"""Bakusai snapshot history and response deltas."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

MAX_SNAPSHOTS = 52


def compact_bakusai(bakusai: dict[str, Any]) -> dict[str, Any]:
    regions: dict[str, Any] = {}
    for region in bakusai.get("regions", []):
        threads = {}
        for thread in region.get("threads", []):
            threads[thread["url"]] = {
                "title": thread.get("title"),
                "responses": thread.get("responses"),
                "views": thread.get("views"),
            }
        regions[region["slug"]] = {"thread_count": region.get("thread_count"), "threads": threads}
    return {
        "captured_at": datetime.now().replace(microsecond=0).isoformat(),
        "regions": regions,
    }


def load_history(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("snapshots", [])


def append_snapshot(path: Path, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    path.parent.mkdir(parents=True, exist_ok=True)
    snapshots = load_history(path)
    snapshots.append(snapshot)
    snapshots = snapshots[-MAX_SNAPSHOTS:]
    payload = json.dumps({"snapshots": snapshots}, ensure_ascii=False, indent=2)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)
    return snapshots


def compute_bakusai_changes(current: dict[str, Any], snapshots: list[dict[str, Any]]) -> dict[str, Any] | None:
    if len(snapshots) < 2:
        return None
    previous = snapshots[-2]
    since = previous.get("captured_at")
    region_changes = []

    for slug, cur in current.get("regions", {}).items():
        prev = previous.get("regions", {}).get(slug, {})
        prev_threads = prev.get("threads", {})
        movers = []
        for url, thread in cur.get("threads", {}).items():
            old = prev_threads.get(url)
            if not old:
                continue
            delta = thread["responses"] - old.get("responses", 0)
            if delta > 0:
                movers.append(
                    {
                        "title": thread.get("title"),
                        "url": url,
                        "responses": thread["responses"],
                        "response_delta": delta,
                    }
                )
        movers.sort(key=lambda m: m["response_delta"], reverse=True)
        region_changes.append({"slug": slug, "response_movers": movers[:8]})

    return {"since": since, "regions": region_changes}


def build_bakusai_trends(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    if not snapshots:
        return {"dates": [], "series": {}}

    dates = [s.get("captured_at", "")[:10] for s in snapshots]
    series: dict[str, dict[str, list]] = {
        slug: {"thread_count": [], "total_responses": []}
        for slug in ("tokyo", "aichi", "osaka")
    }

    for snap in snapshots:
        for slug, metrics in series.items():
            region = snap.get("regions", {}).get(slug, {})
            metrics["thread_count"].append(region.get("thread_count"))
            total = sum(t.get("responses", 0) for t in region.get("threads", {}).values())
            metrics["total_responses"].append(total)

    return {"dates": dates, "series": series}
