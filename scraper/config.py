from dataclasses import dataclass


@dataclass(frozen=True)
class Region:
    slug: str
    name: str
    short: str


REGIONS: list[Region] = [
    Region("tokyo", "東京都", "東京"),
    Region("aichi", "愛知県", "名古屋"),
    Region("osaka", "大阪府", "大阪"),
]

GENRES: dict[str, str] = {
    "biz1": "ヘルス",
    "biz4": "ソープ",
    "biz5": "ホテヘル",
    "biz6": "デリヘル",
    "biz7": "エステ",
}

BASE_URL = "https://www.cityheaven.net"
USER_AGENT = "fuzoku-analystics/0.1 (+https://github.io/fuzoku_analystics; stats-only)"
REQUEST_DELAY_SEC = 1.0
