import json
import os
import sys
import time

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB_DIR = os.path.join(APP_DIR, "lib")
sys.path.insert(0, LIB_DIR)

import requests
import splunk
from solnlib import splunkenv, log
from splunklib import client
from splunktaucclib.rest_handler import error

from ucc_utils import Util
from appdynamics_utils import normalize_controller_url


class AnalyticsService:
    """
    Client for the AppDynamics Analytics (Events) API.

    :param account: Splunk TA analytics account stanza name (used for config + credential lookup).
    :param session_key: Splunk session key for config and credential storage.
    :param source: Source name for events (default "appdynamics_analytics").
    :param splunk: Optional helper for log_exception and send_data when running in an input.
    :param duration: Time window in minutes for default start/end (default 15).
    :param external_logger: Optional logger; otherwise uses default.
    :param throw_exceptions: If True, raise on API errors; else log and return (default False).
    """

    logger = log.Logs().get_logger("appdynamics_analytics_service")

    def __init__(
        self,
        account,
        session_key,
        source="appdynamics_analytics",
        splunk=None,
        duration=15,
        external_logger=None,
        throw_exceptions=False,
    ):
        # Normalize account name: strip surrounding quotes/whitespace (SPL may pass "demo1" or 'demo1')
        self.account = (account or "").strip().strip('"').strip("'").strip() or account
        self.session_key = session_key
        self.source = source
        self.splunk = splunk
        self.proxies = Util.get_proxy(session_key)
        self.request_timeout = Util.get_timeout(session_key)
        self.verify_ssl = Util.get_verify_ssl(session_key)
        try:
            config = splunkenv.get_conf_stanza(
                "splunk_ta_appdynamics_analytics_account", self.account, Util.get_app_name(), session_key
            )
        except Exception as e:
            if type(e).__name__ == "ResourceNotFound":
                raise RuntimeError(
                    f"Analytics account '{self.account}' not found. "
                    "Create an Analytics Account in the TA (Setup → AppDynamics → Analytics Accounts) with this name. "
                    "This is separate from the Controller Account used for status/metrics."
                ) from None
            raise
        self.appd_account_name = config["appd_analytics_account_name"]
        self.duration = duration
        if external_logger:
            self.logger = external_logger
        if session_key is not None:
            self.logger = Util.apply_log_level(session_key, self.logger)
        self.throw_exceptions = throw_exceptions

        url = config.get("appd_analytics_endpoint")
        if url is None or url == "None":
            url = config.get("appd_onprem_analytics_url") or ""
        self.api_url = normalize_controller_url(url) if url else ""

        service = client.connect(token=session_key, app="Splunk_TA_AppDynamics")
        client_secret = None
        for storage_password in service.storage_passwords:
            username = storage_password.content.get("username") or ""
            if not username.startswith(self.account + "``splunk_cred_sep``1"):
                continue
            clear = storage_password.content.get("clear_password")
            if clear and "appd_analytics_secret" in clear:
                client_secret = json.loads(clear)["appd_analytics_secret"]
                break
        if not client_secret:
            raise RuntimeError(f"The Analytics Account Key was not found for account '{self.account}'")

        self.headers = {
            "X-Events-API-AccountName": self.appd_account_name,
            "X-Events-API-Key": client_secret,
            "Content-Type": "application/vnd.appd.events+json;v=2",
            "Accept": "application/vnd.appd.events+json;v=2",
        }

        # Per-instance result buffer (avoid mutable class default)
        self.data = []

        self.logger.info(
            "AnalyticsService Account: '%s' Account Name: %s", self.account, self.appd_account_name
        )

    def _map_fields_to_results(self, fields, result):
        mapped_result = {}
        self.logger.debug("Mapping %s to %s", fields, result)
        for i, field in enumerate(fields):
            field_label = field["label"]
            mapped_result[field_label] = result[i]
            self.logger.debug("Mapped field %s to %s", field_label, result[i])
        return mapped_result

    def _fetch_page(self, query, scroll_id, start, end, limit):
        """
        Fetch one page from the Analytics API. Returns (mapped_data, next_scroll_id).
        next_scroll_id is None when there is no more data or on error (mapped_data may be empty).
        """
        if start is None:
            start = int(time.time() * 1000) - (60000 * int(self.duration))
        if end is None:
            end = int(time.time() * 1000)
        if scroll_id is None:
            payload = {"label": f"{self.source}", "query": f"{query}", "mode": "scroll"}
        else:
            payload = {"label": f"{self.source}", "query": f"{query}", "mode": "scroll", "scrollid": f"{scroll_id}"}
        params = {"start": start, "end": end}
        if limit is not None:
            params["limit"] = limit

        try:
            response = requests.post(
                f"{self.api_url}/events/query",
                headers=self.headers,
                params=params,
                json=payload,
                verify=self.verify_ssl,
                timeout=float(self.request_timeout),
                proxies=self.proxies,
            )
        except Exception as e:
            if self.splunk is not None:
                self.splunk.log_exception(e)
            self.logger.error(
                "Current timeout is %s (seconds). Try again after increasing the request timeout value.",
                self.request_timeout,
            )
            if self.throw_exceptions:
                raise
            return [], None

        self.logger.info(
            "Request URL '%s' Response: %s (truncated)",
            response.request.url,
            (response.text or "")[:120],
        )
        if response.status_code >= 300:
            self.logger.error("Analytics API error: status %s. Response: %s (truncated)", response.status_code, (response.text or "")[:500])
            if self.throw_exceptions:
                raise error.RestError(response.status_code, f"Analytics Query failed: {response.status_code} - {response.text}")
            return [], None

        try:
            body = response.json()
        except Exception as e:
            self.logger.error("Invalid JSON response: %s", e)
            if self.throw_exceptions:
                raise
            return [], None
        if not body or not isinstance(body, list) or len(body) < 1:
            if not body or not isinstance(body, list):
                self.logger.warning("Analytics API returned unexpected body. type=%s len=%s", type(body).__name__, len(body) if body else 0)
            return [], None
        data = body[0]
        results_list = data.get("results") or []
        try:
            mapped_data = [self._map_fields_to_results(data["fields"], r) for r in results_list]
        except (KeyError, TypeError) as e:
            self.logger.error("Error processing Analytics API results: %s. Response keys: %s", e, list(data.keys()) if isinstance(data, dict) else "n/a")
            if self.throw_exceptions:
                raise
            mapped_data = []
        except Exception as e:
            self.logger.error("Error processing results: %s", e)
            if self.throw_exceptions:
                raise
            mapped_data = []

        for d in mapped_data:
            d["appdynamics_account"] = self.appd_account_name
        next_scroll_id = data.get("scrollid") if data.get("moreData") else None
        self.logger.info("Fetched page: %d records, moreData=%s", len(mapped_data), bool(next_scroll_id))
        return mapped_data, next_scroll_id

    def search_stream(self, query, start=None, end=None, limit=None, page_size=None):
        """
        Generator that yields one page of records at a time (for streaming to Splunk as soon as each page is available).
        Only pass limit to the API when the user explicitly sets a total cap. Otherwise we send no limit so the API
        returns its default page size and moreData/scroll_id for continuation; sending limit on the first request
        would cap the entire session at that number (e.g. 500 total).
        """
        scroll_id = None
        total = 0
        while True:
            batch, next_scroll_id = self._fetch_page(query, scroll_id, start, end, limit)
            if batch:
                total += len(batch)
                yield batch
            if next_scroll_id is None:
                break
            scroll_id = next_scroll_id
        self.logger.info("search_stream finished: %d total records yielded", total)

    def search(self, query, scroll_id=None, start=None, end=None, limit=None):
        """Fetch all pages and either send_data (mod input) or append to self.data for get_data()."""
        if start is None:
            start = int(time.time() * 1000) - (60000 * int(self.duration))
        if end is None:
            end = int(time.time() * 1000)
        batch, next_scroll_id = self._fetch_page(query, scroll_id, start, end, limit)
        for d in batch:
            self.logger.info("data: %s", d)
            if self.splunk is not None:
                self.splunk.send_data(self.source, d)
            else:
                self.data.append(d)
        if next_scroll_id is not None:
            self.search(query, scroll_id=next_scroll_id, start=start, end=end, limit=limit)

    def get_data(self):
        data = self.data
        self.data = []
        return data
