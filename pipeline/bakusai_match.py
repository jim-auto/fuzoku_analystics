"""Cross-reference City Heaven shops with Bakusai thread titles."""

from __future__ import annotations

import json
import re
import statistics
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

_ALIASES_PATH = Path(__file__).resolve().parent / "shop_aliases.json"


@lru_cache(maxsize=1)
def _alias_config() -> dict:
    if not _ALIASES_PATH.exists():
        return {"strip_patterns": [], "token_aliases": {}}
    return json.loads(_ALIASES_PATH.read_text(encoding="utf-8"))


def _strip_noise(s: str) -> str:
    cfg = _alias_config()
    for pattern in cfg.get("strip_patterns", []):
        s = re.sub(pattern, " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", _strip_noise(s)).lower()
    s = re.sub(r"[^a-z0-9\u3040-\u30ff\u4e00-\u9fff]", "", s)
    return s


def _expand_tokens(tokens: set[str]) -> set[str]:
    cfg = _alias_config()
    aliases: dict[str, list[str]] = cfg.get("token_aliases", {})
    expanded = set(tokens)
    for token in list(tokens):
        for alias in aliases.get(token, []):
            expanded.add(_norm(alias))
        for canonical, alist in aliases.items():
            canon = _norm(canonical)
            if token == canon or token in {_norm(a) for a in alist}:
                expanded.add(canon)
                for a in alist:
                    expanded.add(_norm(a))
    return {t for t in expanded if len(t) >= 2}


def _tokens(s: str) -> set[str]:
    s = _norm(s)
    parts = re.findall(r"[\u4e00-\u9fff]+|[a-z0-9]+", s)
    base = {p for p in parts if len(p) >= 2}
    return _expand_tokens(base)


def match_score(name_a: str, name_b: str) -> float:
    ta, tb = _tokens(name_a), _tokens(name_b)
    if not ta or not tb:
        na, nb = _norm(name_a), _norm(name_b)
        if len(na) >= 3 and len(nb) >= 3 and (na in nb or nb in na):
            return 0.75
        return 0.0
    inter = len(ta & tb)
    if inter == 0:
        return 0.0
    score = inter / min(len(ta), len(tb))
    if inter >= 2:
        score = min(1.0, score + 0.1)
    return score


def _find_heaven_shop(
    thread_name: str,
    heaven_shops: list[dict],
    threshold: float = 0.45,
) -> dict | None:
    if not thread_name:
        return None
    best = None
    best_score = threshold
    for shop in heaven_shops:
        score = match_score(thread_name, shop.get("name", ""))
        if score > best_score:
            best_score = score
            best = shop
    return best


def _find_best_thread(
    shop_name: str,
    threads: list[dict],
    threshold: float = 0.45,
) -> dict | None:
    if not shop_name:
        return None
    best = None
    best_score = threshold
    for thread in threads:
        score = max(
            match_score(shop_name, thread.get("shop_name", "")),
            match_score(shop_name, thread.get("title", "")),
        )
        if score > best_score:
            best_score = score
            best = thread
    return best


def cross_reference(heaven_regions: list[dict], bakusai: dict) -> list[dict[str, Any]]:
    results = []
    bakusai_by_slug = {r["slug"]: r for r in bakusai.get("regions", [])}

    for region in heaven_regions:
        slug = region["slug"]
        b = bakusai_by_slug.get(slug)
        if not b:
            continue

        all_threads = b.get("threads") or b.get("top_by_responses", [])
        heaven_top = region.get("top_by_reviews", [])[:20]
        heaven_pool = region.get("match_pool") or heaven_top
        heaven_median = (
            int(statistics.median([s["review_count"] for s in heaven_top if s.get("review_count")]))
            if heaven_top
            else 0
        )

        matched = []
        heaven_high_bakusai_low = []
        used_urls: set[str] = set()

        for shop in heaven_top:
            hit = _find_best_thread(shop.get("name", ""), all_threads)
            reviews = shop.get("review_count") or 0
            if hit:
                used_urls.add(hit["url"])
                resp = hit.get("responses") or 0
                matched.append(
                    {
                        "name": shop["name"],
                        "heaven_url": shop["url"],
                        "heaven_reviews": reviews,
                        "bakusai_url": hit["url"],
                        "bakusai_responses": resp,
                        "bakusai_views": hit.get("views"),
                        "match_score": round(
                            max(
                                match_score(shop["name"], hit.get("shop_name", "")),
                                match_score(shop["name"], hit.get("title", "")),
                            ),
                            2,
                        ),
                    }
                )
            elif reviews >= heaven_median:
                heaven_high_bakusai_low.append(
                    {
                        "name": shop["name"],
                        "heaven_reviews": reviews,
                        "bakusai_responses": 0,
                        "heaven_url": shop["url"],
                        "note": "爆サイスレ未検出（表記差 or 話題薄）",
                    }
                )

        all_responses = [t.get("responses") or 0 for t in all_threads]
        board_median = int(statistics.median(all_responses)) if all_responses else 0
        threshold = max(board_median * 0.4, 500)

        for item in matched:
            if item["heaven_reviews"] >= heaven_median and item["bakusai_responses"] < threshold:
                heaven_high_bakusai_low.append(
                    {
                        "name": item["name"],
                        "heaven_reviews": item["heaven_reviews"],
                        "bakusai_responses": item["bakusai_responses"],
                        "heaven_url": item["heaven_url"],
                        "note": "CH口コミは多いが爆サイでの話題は相対的に少ない",
                    }
                )

        bakusai_hot_heaven_quiet = []
        for thread in sorted(all_threads, key=lambda t: t.get("responses") or 0, reverse=True)[:20]:
            if thread["url"] in used_urls:
                continue
            if not _find_heaven_shop(
                thread.get("shop_name") or thread.get("title", ""), heaven_pool
            ):
                bakusai_hot_heaven_quiet.append(
                    {
                        "title": thread.get("title"),
                        "responses": thread.get("responses"),
                        "url": thread.get("url"),
                        "note": "爆サイで話題だがCH口コミ上位50外",
                    }
                )

        results.append(
            {
                "slug": slug,
                "name": region["short"],
                "matched_count": len(matched),
                "matched": matched[:12],
                "heaven_high_bakusai_low": heaven_high_bakusai_low[:8],
                "bakusai_hot_heaven_quiet": bakusai_hot_heaven_quiet[:8],
            }
        )

    return results
