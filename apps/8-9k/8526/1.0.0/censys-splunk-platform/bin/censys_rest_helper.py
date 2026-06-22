import traceback
import time
import json
import requests
from dateutil import parser
from requests.adapters import HTTPAdapter, Retry

from common.consts import PROTOCOL, Endpoints, Rest, VERIFY_SSL
from common.config_manager import get_proxy_data, is_true
import common.proxy as proxy
from utils import get_splunk_version, get_python_version, get_censys_version

Unprocessable_Entity_MSG = "Unprocessable Entity."


class RestHelper:
    """Rest Helper Class."""

    def __init__(self, censys_config, logger) -> None:
        """Rest Helper Class Constructor."""
        self.censys_config = censys_config
        self.logger = logger
        self.session_key = censys_config.get("session_key")
        self.api_key = self.censys_config.get("api_key", "").strip()
        self.org_id = self.censys_config.get("org_id", "").strip()
        self.proxy_settings = None
        proxy_data = get_proxy_data(logger, self.session_key)
        if proxy_data and is_true(proxy_data.get("proxy_enabled")):
            self.proxy_settings = proxy.get_proxies(proxy_data)
        self.verify = VERIFY_SSL
        self.session = self.__get_session()

    def get(self, endpoint, timeout=Rest.REQUEST_TIMEOUT, retry=True, params=None):
        """Get API call to Censys."""
        try:
            start_time = time.time()
            full_url = f"{PROTOCOL}{Endpoints.CENSYS_SERVER_ADDRESS}{endpoint}"
            session = self.session if retry else self.__get_session(retries=0)

            self.logger.debug(
                f"message=HttpRequest | type=Get, endpoint={endpoint}, timeout={timeout}, retry={retry}, "
                f"verify={self.verify}, proxy={bool(self.proxy_settings)}, params={params}, initiating..."
            )

            response = session.get(full_url, timeout=timeout, params=params)

            self.logger.info(
                f"message=HttpRequest | type=Get, url={endpoint}, status={response.status_code},"
                f" time_taken={time.time() - start_time}"
            )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.ProxyError as e:
            error_msg = "Please verify the configured proxy."
            self.logger.exception(f"message=HttpRequest_error | {error_msg} {e}")
            raise type(e)(error_msg) from None

        except requests.exceptions.SSLError as e:
            error_msg = (
                "Please verify the SSL certificate for the provided configuration."
            )
            self.logger.exception(f"message=HttpRequest_error | {error_msg}: {e}")
            raise type(e)(error_msg) from None

        except requests.exceptions.ConnectionError as e:
            error_msg = "Could not connect to the server."
            self.logger.exception(f"message=HttpRequest_error | {error_msg}: {e}")
            raise type(e)(error_msg) from None

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            if status_code == 401:
                error_msg = "Please verify the provided credentials."
                self.logger.exception(f"message=HttpRequest_error | {error_msg}: {e}")
                raise type(e)(error_msg) from None

            if status_code == 403:
                error_msg = "Insufficient permission to perform this action."
                self.logger.exception(f"message=HttpRequest_error | {error_msg}: {e}")
                raise type(e)(error_msg) from None

            if status_code == 422:
                response_text = json.loads(response.text)
                error = response_text.get("errors", [Unprocessable_Entity_MSG])[0]
                error_msg = error.get("message", Unprocessable_Entity_MSG)
                self.logger.exception(f"message=HttpRequest_error | {error_msg}: {e}")
                raise type(e)(error_msg) from None

            if status_code == 429:
                error_msg = "Censys API Limit Exceeded."
                self.logger.exception(f"message=HttpRequest_error | {error_msg}: {e}")
                raise type(e)(error_msg) from None

            self.logger.exception(
                f"message=HttpRequest_error | HttpRequest Failed: {e}"
            )
            raise
        except Exception as e:
            self.logger.exception(
                f"message=HttpRequest_error | HttpRequest Failed: {e}"
            )
            self.logger.exception(
                f"message=HttpRequest_error | HttpRequest Failed: {traceback.format_exc()}"
            )
            raise

    def post(
        self,
        endpoint,
        timeout=Rest.REQUEST_TIMEOUT,
        retry=True,
        params=None,
        payload=None,
    ):
        """Post API call to Censys."""
        try:
            start_time = time.time()
            full_url = f"{PROTOCOL}{Endpoints.CENSYS_SERVER_ADDRESS}{endpoint}"
            session = self.session if retry else self.__get_session(retries=0)

            self.logger.debug(
                f"message=HttpRequest | type=Post, endpoint={endpoint}, timeout={timeout}, retry={retry}, "
                f"verify={self.verify}, proxy={bool(self.proxy_settings)}, params={params},"
                f" payload={payload} initiating..."
            )

            response = session.post(
                full_url, timeout=timeout, json=payload, params=params
            )

            self.logger.info(
                f"message=HttpRequest | type=Post, url={endpoint}, status={response.status_code},"
                f" time_taken={time.time() - start_time}"
            )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.ProxyError as e:
            error_msg = "Please verify the configured proxy."
            self.logger.exception(f"message=HttpRequest_error | {error_msg} {e}")
            raise type(e)(error_msg) from None

        except requests.exceptions.SSLError as e:
            error_msg = (
                "Please verify the SSL certificate for the provided configuration."
            )
            self.logger.exception(f"message=HttpRequest_error | {error_msg}: {e}")
            raise type(e)(error_msg) from None

        except requests.exceptions.ConnectionError as e:
            error_msg = (
                "Could not connect to the server. Please verify the provided credentials"
                " or proxy configurations."
            )
            self.logger.exception(f"message=HttpRequest_error | {error_msg}: {e}")
            raise type(e)(error_msg) from None

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            if status_code == 401:
                error_msg = "Please verify the provided credentials."
                self.logger.exception(f"message=HttpRequest_error | {error_msg}: {e}")
                raise type(e)(error_msg) from None

            if status_code == 403:
                error_msg = "Insufficient permission to perform this action."
                self.logger.exception(f"message=HttpRequest_error | {error_msg}: {e}")
                raise type(e)(error_msg) from None

            if status_code == 422:
                response_text = json.loads(response.text)
                error = response_text.get("errors", [Unprocessable_Entity_MSG])[0]
                error_msg = error.get("message", Unprocessable_Entity_MSG)
                self.logger.exception(f"message=HttpRequest_error | {error_msg}: {e}")
                raise type(e)(error_msg) from None

            if status_code == 429:
                error_msg = "Censys API Limit Exceeded."
                self.logger.exception(f"message=HttpRequest_error | {error_msg}: {e}")
                raise type(e)(error_msg) from None

            self.logger.exception(
                f"message=HttpRequest_error | HttpRequest Failed: {e}"
            )
            raise
        except Exception as e:
            self.logger.exception(
                f"message=HttpRequest_error | HttpRequest Failed: {e}"
            )
            self.logger.exception(
                f"message=HttpRequest_error | HttpRequest Failed: {traceback.format_exc()}"
            )
            raise

    def __get_session(
        self,
        retries=3,
        backoff_factor=60,
        status_forcelist=Rest.STATUS_FORCELIST,
        method_whitelist=["GET", "POST", "HEAD"],
    ):
        """
        Create and return a session object with retry mechanism.

        :param retries: Maximum number of retries to attempt
        :param backoff_factor: Backoff factor used to calculate time between retries. e.g. For 10 - 5, 10, 20, 40,...
        :param status_forcelist: A tuple containing the response status codes that should trigger a retry.
        :param method_whiltelist: HTTP methods on which retry will be performed.

        :return: Session Object
        """
        session = requests.Session()

        session.verify = self.verify
        session.proxies = self.proxy_settings
        session.headers["Content-Type"] = "application/json; charset=utf8"
        session.headers.update({"Authorization": "Bearer {}".format(self.api_key)})

        splunk_version = get_splunk_version(self.session_key)
        python_version = get_python_version()
        censys_version = get_censys_version()
        ts = time.time()
        user_agent = f"CensysSplunk/{censys_version} (Splunk/{splunk_version}; Python/{python_version}; ts={ts})"
        session.headers.update(
            {
                "User-Agent": user_agent
            }
        )

        if retries == 0:
            return session

        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            method_whitelist=method_whitelist,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def get_enriched_host(self, host_value, org_id, at_time=""):
        """Get enriched host."""
        try:
            self.logger.info("message=fetch_data | Fetching Enriched Host.")
            params = {"organization_id": org_id}
            if at_time:
                at_time = at_time.strip()
                params.update({"at_time": at_time})

            response = self.get(
                endpoint=Endpoints.CENSYS_ENRICHED_HOST.format(host_value),
                params=params,
            )

            return response
        except Exception:
            self.logger.error(
                "message=fetch_data_error | Error occured while getting Enriched Host data: {}".format(
                    traceback.format_exc()
                )
            )
            return None

    def get_enriched_web_property(self, web_property_value, org_id, port, at_time=""):
        """Get enriched web property."""
        try:
            web_property = web_property_value + ":" + port
            self.logger.info("message=fetch_data | Fetching Enriched Web Property.")
            params = {"organization_id": org_id}
            if at_time:
                at_time = at_time.strip()
                params.update({"at_time": at_time})
            response = self.get(
                endpoint=Endpoints.CENSYS_ENRICHED_WEB_PROPERTY.format(web_property),
                params=params,
            )

            return response
        except Exception:
            self.logger.error(
                "message=fetch_data_error | Error occured while getting Enriched Web Property data: {}".format(
                    traceback.format_exc()
                )
            )
            return None

    def get_enriched_certificate(self, certificate_value, org_id):
        """Get enriched certificate."""
        try:
            self.logger.info("message=fetch_data | Fetching Enriched Certificate.")
            params = {"organization_id": org_id}
            response = self.get(
                endpoint=Endpoints.CENSYS_ENRICHED_CERTIFICATE.format(
                    certificate_value
                ),
                params=params,
            )

            return response
        except Exception:
            self.logger.error(
                "message=fetch_data_error | Error occured while getting Enriched Certificate data: {}".format(
                    traceback.format_exc()
                )
            )
            return None

    def get_host_event_history(
        self, host_value, org_id, start_time, end_time, max_pages=10
    ):
        """Get host event history with pagination support.

        Args:
            host_value: Host IP or hostname
            org_id: Organization ID
            start_time: Start time in RFC3339 format (e.g., 2025-01-01T00:00:00Z)
            end_time: End time in RFC3339 format (e.g., 2025-01-01T00:00:00Z)
            max_pages: Maximum number of pages to fetch (default: 10)

        Returns:
            Combined results from all pages
        """
        response = {"failed": True}
        combined_results = None
        try:
            self.logger.info("message=fetch_data | Fetching Host Event History.")

            # Format end_time for comparison if needed
            original_end_time = end_time
            try:
                # Use dateutil parser which handles various time formats
                end_time_dt = parser.parse(end_time)
                # Convert to epoch time (seconds since 1970-01-01)
                end_time_epoch = end_time_dt.timestamp()
                self.logger.debug(
                    f"message=fetch_data_debug | Parsed end_time: {end_time} to epoch: {end_time_epoch}"
                )
            except Exception as e:
                self.logger.warning(
                    f"message=fetch_data_warning | Error parsing end_time format: {end_time}. Error: {str(e)}"
                )
                end_time_epoch = None

            # Initial API call
            params = {
                "organization_id": org_id,
                "start_time": start_time,
                "end_time": end_time,
            }

            response = self.get(
                endpoint=Endpoints.CENSYS_HOST_EVENT_HISTORY.format(host_value),
                params=params,
            )

            if not response or not response.get("result"):
                self.logger.warning(
                    "message=fetch_data_warning | No event history found."
                )
                return response

            # Check if there's a scanned_to field indicating more data
            scanned_to = response.get("result", {}).get("scanned_to", "")
            if not scanned_to:
                self.logger.info(
                    "message=fetch_data_info | No scanned_to field found, no pagination needed."
                )
                return response

            # Initialize combined results
            combined_results = response
            all_events = response.get("result", {}).get("events", [])
            page_count = 1

            # Format scanned_to for comparison using dateutil parser and convert to epoch time
            try:
                # Use dateutil parser which handles various time formats
                scanned_to_dt = parser.parse(scanned_to)
                # Convert to epoch time (seconds since 1970-01-01)
                scanned_to_epoch = scanned_to_dt.timestamp()
                self.logger.debug(
                    f"message=fetch_data_debug | Parsed scanned_to: {scanned_to} to epoch: {scanned_to_epoch}"
                )
            except Exception as e:
                self.logger.warning(
                    f"message=fetch_data_warning | Error parsing scanned_to format: {scanned_to}. Error: {str(e)}"
                )
                scanned_to_epoch = None

            # Check if we need to fetch more pages
            need_more_pages = False

            # Compare timestamps using epoch time if both are valid
            if (
                end_time_epoch is not None
                and scanned_to_epoch is not None
                and scanned_to_epoch >= end_time_epoch
            ):
                need_more_pages = True
            elif end_time_epoch is None or scanned_to_epoch is None:
                # If we can't compare as epoch time, fall back to string comparison
                need_more_pages = scanned_to >= original_end_time

            # Fetch additional pages up to max_pages
            while need_more_pages and page_count < max_pages:
                self.logger.debug(
                    f"message=fetch_data_info | Fetching event history data for page {page_count + 1}"
                )

                # Update end_time to scanned_to for next request
                params["end_time"] = original_end_time
                params["start_time"] = scanned_to

                # Make API call with updated time range
                page_response = self.get(
                    endpoint=Endpoints.CENSYS_HOST_EVENT_HISTORY.format(host_value),
                    params=params,
                )

                if not page_response or not page_response.get("result"):
                    self.logger.warning(
                        f"message=fetch_data_warning | Failed to fetch page {page_count + 1}."
                    )
                    break

                # Get events from this page
                page_events = page_response.get("result", {}).get("events", [])
                if not page_events:
                    self.logger.info(
                        "message=fetch_data_info | No more events available."
                    )
                    break

                all_events.extend(page_events)

                # Update scanned_to for next iteration
                scanned_to = page_response.get("result", {}).get("scanned_to")
                if not scanned_to:
                    self.logger.info(
                        "message=fetch_data_info | No more scanned_to field, pagination complete."
                    )
                    break

                # Format new scanned_to for comparison using dateutil parser and convert to epoch time
                try:
                    # Use dateutil parser which handles various time formats
                    scanned_to_dt = parser.parse(scanned_to)
                    # Convert to epoch time (seconds since 1970-01-01)
                    scanned_to_epoch = scanned_to_dt.timestamp()
                    self.logger.debug(
                        f"message=fetch_data_debug | Parsed scanned_to: {scanned_to} to epoch: {scanned_to_epoch}"
                    )
                except Exception as e:
                    self.logger.warning(
                        f"message=fetch_data_warning | Error parsing scanned_to format: {scanned_to}. Error: {str(e)}"
                    )
                    scanned_to_epoch = None

                # Check if we need to fetch more pages
                if (
                    end_time_epoch is not None
                    and scanned_to_epoch is not None
                    and scanned_to_epoch >= end_time_epoch
                ):
                    need_more_pages = True
                elif end_time_epoch is None or scanned_to_epoch is None:
                    # If we can't compare as epoch time, fall back to string comparison
                    need_more_pages = scanned_to >= original_end_time
                else:
                    need_more_pages = False

                page_count += 1

            # Update combined results with all events
            if page_count > 1:
                self.logger.info(
                    f"message=fetch_data_info | Combined {page_count} pages with {len(all_events)} total events."
                )
                combined_results["result"]["events"] = all_events

            return combined_results

        except Exception as e:
            if combined_results:
                return combined_results
            e_str = str(e)
            self.logger.error(
                "message=fetch_data_error | Error occured while getting Host Event History data: {}".format(
                    traceback.format_exc()
                )
            )
            if e_str:
                response.update({"err_message": e_str})
            return response

    def initiate_rescan(self, org_id, service_obj, web_origin_obj):
        """Initiate a new rescan."""
        try:
            self.logger.info("message=fetch_data | Initiating a new Rescan.")
            params = {"organization_id": org_id}
            if service_obj:
                payload = {"target": {"service_id": service_obj}}
                response = self.post(
                    endpoint=Endpoints.CENSYS_INITIATE_NEW_RESCAN,
                    params=params,
                    payload=payload,
                )
            else:
                payload = {"target": {"web_origin": web_origin_obj}}
                response = self.post(
                    endpoint=Endpoints.CENSYS_INITIATE_NEW_RESCAN,
                    params=params,
                    payload=payload,
                )

            return response
        except Exception:
            self.logger.error(
                "message=fetch_data_error | Error occured while initiating a new Rescan: {}".format(
                    traceback.format_exc()
                )
            )
            return None

    def get_current_scan_status(self, scan_id, org_id):
        """Get scan status."""
        try:
            self.logger.info("message=fetch_data | Fetching Current Status of a Scan.")
            params = {"organization_id": org_id}
            response = self.get(
                endpoint=Endpoints.CENSYS_SCAN_STATUS.format(scan_id), params=params
            )

            return response
        except Exception:
            self.logger.error(
                "message=fetch_data_error | Error occured while getting Current Status of a Scan: {}".format(
                    traceback.format_exc()
                )
            )
            return None

    def get_value_counts(self, org_id, field_value_pairs_object, query_value):
        """Get value count."""
        try:
            self.logger.info("message=fetch_data | Retrieve value count.")
            params = {"organization_id": org_id}
            payload = {
                "and_count_conditions": [field_value_pairs_object],
                "query": query_value,
            }
            response = self.post(
                endpoint=Endpoints.CENSYS_RETRIEVE_VALUE_COUNT,
                params=params,
                payload=payload,
            )
            return response
        except Exception:
            self.logger.error(
                "message=fetch_data_error | Error occured while getting value count: {}".format(
                    traceback.format_exc()
                )
            )
            return None

    def run_search_query(self, org_id, query, max_pages=10):
        """Run search query with pagination support.

        Args:
            org_id: Organization ID
            query: Query string
            max_pages: Maximum number of pages to fetch (default: 10)

        Returns:
            Combined results from all pages
        """
        response = {"failed": True}
        combined_results = None
        try:
            self.logger.info("message=fetch_data | Run search Query.")
            params = {"organization_id": org_id}
            payload = {
                "fields": [
                    "host.ip",
                    "host.service_count",
                    "host.services.port",
                    "host.services.protocol",
                    "host.services.transport_protocol",
                    "host.labels.value",
                    "host.services.labels.value",
                    "host.services.threats.name",
                    "host.services.vulns.name",
                    "host.services.scan_time",
                    "host.dns.names",
                    "host.dns.forward_dns.names",
                    "host.dns.reverse_dns.names",
                    "host.whois.network.name",
                    "host.whois.network.cidrs",
                    "host.autonomous_system.name",
                    "host.autonomous_system.asn",
                    "host.location.city",
                    "host.location.province",
                    "host.location.postal_code",
                    "host.location.country",
                    "host.location.country_code",
                    "host.location.continent",
                    "host.location.coordinates.latitude",
                    "host.location.coordinates.longitude",
                    "web.hostname",
                    "web.port",
                    "web.endpoints.endpoint_type",
                    "web.endpoints.path",
                    "web.labels",
                    "web.threats.name",
                    "web.vulns.name",
                    "web.scan_time",
                    "web.software.vendor",
                    "web.software.product",
                    "web.software.version",
                    "web.cert.fingerprint_sha256",
                    "web.cert.parsed.subject_dn",
                    "web.cert.parsed.issuer_dn",
                    "web.cert.parsed.subject.common_name",
                    "web.cert.parsed.validity_period.not_before",
                    "web.cert.parsed.validity_period.not_after",
                    "web.cert.parsed.signature.self_signed",
                    "cert.fingerprint_sha256",
                    "cert.parsed.subject_dn",
                    "cert.parsed.issuer_dn",
                    "cert.parsed.subject.common_name",
                    "cert.parsed.validity_period.not_before",
                    "cert.parsed.validity_period.not_after",
                    "cert.parsed.signature.self_signed",
                    "cert.valid_to",
                    "cert.self_signed",
                ],
                "query": query,
            }

            # Initial API call without page token
            response = self.post(
                endpoint=Endpoints.CENSYS_RUN_SEARCH_QUERY,
                params=params,
                payload=payload,
            )

            if not response or not response.get("result"):
                self.logger.warning(
                    "message=fetch_data_warning | No results found for query."
                )
                return response

            # Check if there are more pages
            next_page_token = response.get("result", {}).get("next_page_token")
            if not next_page_token:
                self.logger.info("message=fetch_data_info | No more pages available.")
                return response

            # Initialize combined results
            combined_results = response
            all_hits = response.get("result", {}).get("hits", [])
            page_count = 1

            # Fetch additional pages up to max_pages
            while next_page_token and page_count < max_pages:
                self.logger.debug(
                    f"message=fetch_data_info | Fetching data for page {page_count + 1}"
                )

                # Add page token to payload
                payload["page_token"] = next_page_token

                # Make API call with page token
                page_response = self.post(
                    endpoint=Endpoints.CENSYS_RUN_SEARCH_QUERY,
                    params=params,
                    payload=payload,
                )

                if not page_response or not page_response.get("result"):
                    self.logger.warning(
                        f"message=fetch_data_warning | Failed to fetch page {page_count + 1}."
                    )
                    break

                # Get hits from this page
                page_hits = page_response.get("result", {}).get("hits", [])
                all_hits.extend(page_hits)

                # Update next page token
                next_page_token = page_response.get("result", {}).get(
                    "next_page_token", ""
                )
                page_count += 1

                if not next_page_token:
                    self.logger.info(
                        "message=fetch_data_info | No more pages available."
                    )
                    break

            # Update combined results with all hits
            if page_count > 1:
                self.logger.info(
                    f"message=fetch_data_info | Combined {page_count} pages with {len(all_hits)} total hits."
                )
                combined_results["result"]["hits"] = all_hits
            return combined_results

        except Exception as e:
            if combined_results:
                return combined_results
            e_str = str(e)
            self.logger.error(
                "message=fetch_data_error | Error occured while running search query: {}".format(
                    traceback.format_exc()
                )
            )
            if e_str:
                response.update({"err_message": e_str})
            return response
