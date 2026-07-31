"""Entry point: fetch City Heaven + Bakusai stats and write public JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pipeline.aggregate import aggregate
from pipeline.bakusai_match import cross_reference
from pipeline.history import (
    append_snapshot,
    build_trends,
    compact_snapshot,
    compute_changes,
)
from scraper.bakusai import fetch_all_bakusai
from scraper.client import HeavenClient
from scraper.fetch import fetch_all

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "public"
DOCS_DATA = ROOT / "docs" / "data"
HISTORY_PATH = ROOT / "data" / "history" / "index.json"


def main() -> None:
    client = HeavenClient()
    try:
        raw = fetch_all(client)
        bakusai = fetch_all_bakusai(client)
    finally:
        client.close()

    aggregated = aggregate(raw)
    snapshot = compact_snapshot(aggregated)
    snapshots = append_snapshot(HISTORY_PATH, snapshot)
    changes = compute_changes(snapshot, snapshots)
    trends = build_trends(snapshots)
    bakusai_cross = cross_reference(aggregated.get("regions", []), bakusai)

    payload = {
        "updated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "source": "https://www.cityheaven.net/",
        "disclaimer": "非公式の統計サイト。数値のみを集計し、画像・文章は転載していません。",
        "regions_target": ["tokyo", "aichi", "osaka"],
        **aggregated,
        "changes": changes,
        "trends": trends,
        "bakusai": bakusai,
        "bakusai_cross": bakusai_cross,
    }

    outputs = {
        DATA_DIR / "summary.json": payload,
        DOCS_DATA / "summary.json": payload,
        DOCS_DATA / "trends.json": trends,
    }
    for directory in (DATA_DIR, DOCS_DATA):
        directory.mkdir(parents=True, exist_ok=True)

    for path, data in outputs.items():
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
