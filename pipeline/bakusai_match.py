"""Cross-reference City Heaven shops with Bakusai thread titles."""

from __future__ import annotations

import re
from typing import Any


def _norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9\u3040-\u30ff\u4e00-\u9fff]", "", s)
    return s


def cross_reference(heaven_regions: list[dict], bakusai: dict) -> list[dict[str, Any]]:
    results = []
    bakusai_by_slug = {r["slug"]: r for r in bakusai.get("regions", [])}

    for region in heaven_regions:
        slug = region["slug"]
        b = bakusai_by_slug.get(slug)
        if not b:
            continue

        shop_index = []
        for shop in region.get("top_by_reviews", [])[:20]:
            name = _norm(shop.get("name", ""))
            if len(name) < 2:
                continue
            shop_index.append({**shop, "_norm": name})

        threads = b.get("top_by_responses", [])
        matched = []
        heaven_only = []
        bakusai_only = []

        used_threads = set()
        for shop in shop_index:
            hit = None
            for i, thread in enumerate(threads):
                tn = _norm(thread.get("shop_name", ""))
                if len(tn) >= 3 and (tn in shop["_norm"] or shop["_norm"] in tn):
                    hit = thread
                    used_threads.add(i)
                    break
            if hit:
                matched.append(
                    {
                        "name": shop["name"],
                        "heaven_url": shop["url"],
                        "heaven_reviews": shop.get("review_count"),
                        "bakusai_url": hit["url"],
                        "bakusai_responses": hit["responses"],
                        "bakusai_views": hit["views"],
                    }
                )
            else:
                heaven_only.append({"name": shop["name"], "heaven_reviews": shop.get("review_count")})

        for i, thread in enumerate(threads[:10]):
            if i not in used_threads:
                bakusai_only.append(
                    {
                        "title": thread["title"],
                        "responses": thread["responses"],
                        "url": thread["url"],
                    }
                )

        results.append(
            {
                "slug": slug,
                "name": region["short"],
                "matched_count": len(matched),
                "matched": matched[:8],
                "heaven_top_not_on_bakusai": heaven_only[:5],
                "bakusai_hot_not_in_heaven_top": bakusai_only[:5],
            }
        )

    return results
