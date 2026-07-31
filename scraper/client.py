import time

import httpx

from scraper.config import REQUEST_DELAY_SEC, USER_AGENT


class HeavenClient:
    def __init__(self) -> None:
        self._last_request = 0.0
        self._client = httpx.Client(
            headers={"User-Agent": USER_AGENT, "Accept-Language": "ja,en;q=0.5"},
            follow_redirects=True,
            timeout=30.0,
        )

    def get(self, url: str) -> str:
        elapsed = time.monotonic() - self._last_request
        if elapsed < REQUEST_DELAY_SEC:
            time.sleep(REQUEST_DELAY_SEC - elapsed)
        response = self._client.get(url)
        self._last_request = time.monotonic()
        response.raise_for_status()
        return response.content.decode("utf-8", "replace")

    def close(self) -> None:
        self._client.close()
