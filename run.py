"""Entry point: fetch City Heaven stats and write public JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pipeline.aggregate import aggregate
from scraper.client import HeavenClient
from scraper.fetch import fetch_all

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "public"
DOCS_DATA = ROOT / "docs" / "data"


def main() -> None:
    client = HeavenClient()
    try:
        raw = fetch_all(client)
    finally:
        client.close()

    payload = {
        "updated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "source": "https://www.cityheaven.net/",
        "disclaimer": "非公式の統計サイト。数値のみを集計し、画像・文章は転載していません。",
        "regions_target": ["tokyo", "aichi", "osaka"],
        **aggregate(raw),
    }

    for directory in (DATA_DIR, DOCS_DATA):
        directory.mkdir(parents=True, exist_ok=True)
        out = directory / "summary.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
