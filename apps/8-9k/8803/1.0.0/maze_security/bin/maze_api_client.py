import gzip
import json
import time
import urllib.error
import urllib.request

VERSION = "1.0.0"
HTTP_TIMEOUT = 30


class SplunkLogAdapter:
    """Adapts Splunk EventWriter.log(severity, msg) to standard logger interface."""

    def __init__(self, ew_log):
        self._log = ew_log

    def warning(self, msg, *args):
        self._log("WARNING", msg % args if args else msg)

    def info(self, msg, *args):
        self._log("INFO", msg % args if args else msg)

    def error(self, msg, *args):
        self._log("ERROR", msg % args if args else msg)


class MazeAPIClient:

    def __init__(self, base_url, api_key, logger=None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.logger = SplunkLogAdapter(logger) if callable(logger) else logger
        self.max_retries = 3

    def _request(self, method, path, body=None):
        url = f"{self.base_url}{path}"
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"MazeSplunkApp/{VERSION}",
        }

        data = json.dumps(body).encode("utf-8") if body else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        for attempt in range(self.max_retries):
            try:
                with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    retry_after = int(e.headers.get("Retry-After", 60))
                    if self.logger:
                        self.logger.warning(
                            "Rate limited, retrying in %d seconds", retry_after
                        )
                    time.sleep(retry_after)
                    continue
                if e.code >= 500 and attempt < self.max_retries - 1:
                    wait = 2 ** (attempt + 1)
                    if self.logger:
                        self.logger.warning(
                            "Server error %d, retrying in %d seconds", e.code, wait
                        )
                    time.sleep(wait)
                    continue
                raise

        raise RuntimeError(f"Max retries exceeded for {method} {path}")

    def search_investigations(
        self, updated_from=None, updated_to=None, cursor=None, limit=100
    ):
        body = {"limit": limit}
        if updated_from:
            body["updated_from"] = updated_from
        if updated_to:
            body["updated_to"] = updated_to
        if cursor:
            body["cursor"] = cursor
        return self._request("POST", "/v1/investigations/search", body)

    def search_investigations_all(self, updated_from=None, updated_to=None):
        cursor = None
        while True:
            resp = self.search_investigations(
                updated_from=updated_from,
                updated_to=updated_to,
                cursor=cursor,
                limit=1000,
            )
            yield from resp["data"]
            if not resp.get("has_more"):
                break
            cursor = resp.get("next_cursor")

    def list_daily_exports(self):
        return self._request("GET", "/v1/investigations/exports/daily")

    def get_daily_export(self, export_id):
        return self._request(
            "GET", f"/v1/investigations/exports/daily/{export_id}"
        )

    def download_export_file(self, download_url):
        req = urllib.request.Request(
            download_url,
            headers={"User-Agent": f"MazeSplunkApp/{VERSION}"},
        )
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            compressed = resp.read()
        decompressed = gzip.decompress(compressed)
        for line in decompressed.decode("utf-8").strip().split("\n"):
            if line:
                yield json.loads(line)
