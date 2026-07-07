"""HTTP client for ZeroFox CTI APIs (token + paginated GET)."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from typing import Any
from urllib.parse import urljoin

import requests

JsonDict = dict[str, Any]
EpochFn = Callable[[str], float]


class ZeroFoxIntelClient:
    def __init__(
        self,
        api_base_url: str,
        username: str,
        password: str,
        *,
        proxies: dict[str, str] | None = None,
        timeout: int = 30,
        session: requests.Session | None = None,
    ) -> None:
        base = api_base_url.rstrip("/")
        self._base = base
        self._username = username
        self._password = password
        self._proxies = proxies or {}
        self._timeout = timeout
        self._session = session or requests.Session()

    def auth_token_url(self) -> str:
        return f"{self._base}/auth/token/"

    def get_access_token(self) -> str:
        url = self.auth_token_url()
        if not url.startswith("https"):
            msg = 'Auth URL must start with "https"'
            raise ValueError(msg)
        resp = self._session.post(
            url,
            json={"username": self._username, "password": self._password},
            proxies=self._proxies or None,
            timeout=self._timeout,
        )
        if not resp.ok:
            body_snippet = " ".join(resp.text[:300].split())
            raise RuntimeError(f"auth failed HTTP {resp.status_code}: {body_snippet}")
        resp.raise_for_status()
        body = resp.json()
        token = body.get("access")
        if not token:
            msg = f"token response missing access: {json.dumps(body)[:500]}"
            raise RuntimeError(msg)
        return str(token)

    def iter_cti_pages(
        self,
        first_url: str,
        params: dict[str, str] | None,
        *,
        access_token: str | None = None,
    ) -> Iterator[list[JsonDict]]:
        token = access_token or self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "zf-source": "Splunk",
        }
        url: str | None = first_url
        next_params = params
        while url:
            if not url.startswith("https"):
                msg = 'CTI URL must start with "https"'
                raise ValueError(msg)
            resp = self._session.get(
                url,
                params=next_params,
                headers=headers,
                proxies=self._proxies or None,
                timeout=self._timeout,
            )
            if not resp.ok:
                body_snippet = " ".join(resp.text[:300].split())
                raise RuntimeError(f"HTTP {resp.status_code}: {body_snippet}")
            resp.raise_for_status()
            body = resp.json()
            results = body.get("results") or []
            if not isinstance(results, list):
                msg = "CTI response results must be a list"
                raise TypeError(msg)
            yield [r for r in results if isinstance(r, dict)]
            next_url = body.get("next")
            url = str(next_url) if next_url else None
            next_params = None


def absolutize_url(api_base: str, path: str) -> str:
    return urljoin(api_base.rstrip("/") + "/", path.lstrip("/"))
