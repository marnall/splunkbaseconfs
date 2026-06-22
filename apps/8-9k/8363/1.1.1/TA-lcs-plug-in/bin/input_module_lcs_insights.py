# encoding = utf-8

import import_declare_test  # noqa: F401
import json
import logging
import time
import datetime
from datetime import timezone
import traceback
from typing import Generator, Optional, Tuple

import requests
from solnlib import conf_manager, log
from splunklib import modularinput as smi

ADDON_NAME = "TA-lcs-plug-in"


def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


def get_account_clientid(session_key: str, account_name: str):
    """Retrieve the Client ID from the account configuration."""
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-lcs_plug_in_account",
    )
    account_conf_file = cfm.get_conf("lcs_plug_in_account")
    return account_conf_file.get(account_name).get("clientid")


def get_account_secret(session_key: str, account_name: str):
    """Retrieve the Client Secret from the account configuration."""
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-lcs_plug_in_account",
    )
    account_conf_file = cfm.get_conf("lcs_plug_in_account")
    return account_conf_file.get(account_name).get("secret")


class RateLimiter:
    """Manages API call rate limits (per second and per day) with UTC timezone."""

    def __init__(self, calls_per_second: int, calls_per_day: int, logger: logging.Logger):
        self.calls_per_second = calls_per_second
        self.calls_per_day = calls_per_day
        self.logger = logger

        self.second_timestamps = []
        self.daily_call_count = 0
        self.last_reset_day = datetime.datetime.now(timezone.utc).date()

    def _clean_second_timestamps(self):
        """Remove timestamps older than 1 second."""
        now = time.time()
        self.second_timestamps = [t for t in self.second_timestamps if now - t < 1.0]

    def _check_and_reset_daily_count(self):
        """Reset daily count if new day (UTC)."""
        today_utc = datetime.datetime.now(timezone.utc).date()
        if today_utc != self.last_reset_day:
            self.logger.info(
                f"Daily API call count reset (UTC): {self.daily_call_count} calls made on {self.last_reset_day}"
            )
            self.daily_call_count = 0
            self.last_reset_day = today_utc

    def wait_for_api_call(self):
        """Wait if necessary to respect rate limits."""
        self._check_and_reset_daily_count()

        if self.daily_call_count >= self.calls_per_day:
            self.logger.error(
                f"Daily API call limit of {self.calls_per_day} reached. No more calls will be made today."
            )
            raise Exception(f"Daily API call limit of {self.calls_per_day} reached.")

        self._clean_second_timestamps()

        if len(self.second_timestamps) >= self.calls_per_second:
            wait_time = 1.0 - (time.time() - self.second_timestamps[0])
            if wait_time > 0:
                self.logger.debug(f"Rate limit: waiting {wait_time:.3f}s")
                time.sleep(wait_time)
                self._clean_second_timestamps()

        self.second_timestamps.append(time.time())
        self.daily_call_count += 1
        self.logger.debug(
            f"API call made. Daily count: {self.daily_call_count}, Second count: {len(self.second_timestamps)}"
        )


def get_jwt(
    logger: logging.Logger,
    server: str,
    client_id: str,
    client_secret: str,
    rate_limiter: RateLimiter,
    max_retries: int = 3,
) -> Tuple[str, int]:
    """Obtain JWT with retry logic.

    Returns:
        tuple: (access_token, expires_in_seconds)
    """
    url = f"https://{server}/torii-auth/v1/token"
    data = {
        "grantType": "client_credentials",
        "clientId": client_id,
        "secret": client_secret,
        "scope": "api.bcs.manage",
    }
    headers = {"Content-Type": "application/json"}

    for attempt in range(max_retries):
        try:
            rate_limiter.wait_for_api_call()
            logger.debug(f"Requesting JWT from {url} (attempt {attempt + 1}/{max_retries})")

            resp = requests.post(
                url=url,
                data=json.dumps(data),
                headers=headers,
                verify=True,
                timeout=120,
            )
            resp.raise_for_status()

            response_data = resp.json()
            access_token = response_data.get("accessToken")
            expires_in = response_data.get("expiresIn", 3200)

            logger.debug(f"JWT obtained successfully, expires in {expires_in} seconds")
            return access_token, expires_in

        except Exception as err:
            if attempt < max_retries - 1:
                wait_time = 2**attempt
                logger.warning(
                    f"JWT request failed (attempt {attempt + 1}/{max_retries}): {err}. " f"Retrying in {wait_time}s..."
                )
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to obtain JWT after {max_retries} attempts: {err}")
                raise


def get_all_items(
    logger: logging.Logger,
    url: str,
    headers: dict,
    rate_limiter: RateLimiter,
    url_params: Optional[dict] = None,
    max_retries: int = 3,
    jwt_refresh_callback=None,
) -> Generator[dict, None, None]:
    """Fetch all items from paginated API with retry logic.

    Args:
        jwt_refresh_callback: Optional function to refresh JWT on 401 errors.
                             Should return new headers dict.
    """
    offset = 0
    total = float("inf")
    params = url_params.copy() if url_params else {}
    page_count = 0

    while offset < total:
        params["offset"] = offset
        page_count += 1

        for attempt in range(max_retries):
            try:
                rate_limiter.wait_for_api_call()
                logger.debug(
                    f"Fetching page {page_count} from {url} with offset={offset} "
                    f"(attempt {attempt + 1}/{max_retries})"
                )

                response = requests.get(
                    url=url,
                    params=params,
                    headers=headers,
                    verify=True,
                    timeout=120,
                )
                response.raise_for_status()
                break

            except Exception as err:
                error_str = str(err)
                is_401 = "401" in error_str or "Unauthorized" in error_str

                if is_401 and jwt_refresh_callback and attempt < max_retries - 1:
                    logger.warning(f"JWT expired (401) on page {page_count}. Refreshing token...")
                    headers = jwt_refresh_callback()
                    logger.info("JWT refreshed, retrying page...")
                    continue

                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Page {page_count} failed (attempt {attempt + 1}/{max_retries}): {err}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Page {page_count} failed after {max_retries} attempts: {err}")
                    raise

        response_body = response.json()
        response_headers = response.headers

        try:
            current_offset = int(response_headers.get("offset", 0))
            max_items = int(response_headers.get("max", 0))
            total = int(response_headers.get("total", 0))
            offset = current_offset + max_items

            logger.debug(
                f"Page {page_count} received: {len(response_body.get('items', []))} items "
                f"(offset={current_offset}, max={max_items}, total={total})"
            )
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to parse pagination headers: {e}. Headers: {dict(response_headers)}")
            break

        items = response_body.get("items", [])
        if not items:
            logger.debug(f"No more items at offset {current_offset}. Ending pagination.")
            break

        for item in items:
            yield item


def validate_input(definition: smi.ValidationDefinition):
    """
    Validate the input stanza configurations.
    Ensures that region parameter is valid.
    """
    opt_region = definition.parameters.get("region", "us")

    if opt_region not in ["us", "emea"]:
        raise ValueError("Region must be either 'us' or 'emea'.")


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    """
    Collect events from the Cisco BCS API and write to Splunk.
    Always collects ALL data (no checkpointing).
    """
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)

        try:
            session_key = inputs.metadata["session_key"]

            # Set log level from settings conf
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name="lcs_plug_in_settings",
            )
            logger.setLevel(log_level)
            log.modular_input_start(logger, normalized_input_name)

            # ── Retrieve credentials from account configuration ──
            account_name = input_item.get("account")
            opt_clientid = get_account_clientid(session_key, account_name)
            opt_secret = get_account_secret(session_key, account_name)

            # ── Retrieve input-level parameters ──
            opt_region = input_item.get("region", "us")
            opt_security_vulnerable_only = input_item.get("security_vulnerable_only", "1") == "1"
            output_index = input_item.get("index", "default")

            # ── Configuration ──
            server = "api-cx.cisco.com"
            calls_per_second = 10
            calls_per_day = 10000

            logger.info(
                f"Starting data collection - Server: {server}, Region: {opt_region}, "
                f"Security vulnerable only: {opt_security_vulnerable_only}, "
                f"Rate limits: {calls_per_second}/sec, {calls_per_day}/day"
            )
            logger.debug(f"Collection started at {datetime.datetime.now(timezone.utc).isoformat()} UTC")

            # ── Initialize rate limiter ──
            rate_limiter = RateLimiter(calls_per_second, calls_per_day, logger)

            # ── Counters ──
            collection_start = time.time()
            total_events_collected = 0
            total_bytes_collected = 0

            # ── Data sources ──
            data_sources = [
                {
                    "sourcetype": "cisco:bcs:asset",
                    "endpoint_path": "/inventory/assets",
                    "id_field": "deviceId",
                },
                {
                    "sourcetype": "cisco:bcs:collector",
                    "endpoint_path": "/collectors",
                    "id_field": "applianceId",
                },
                {
                    "sourcetype": "cisco:bcs:configbestpracticedetail",
                    "endpoint_path": "/configBestPractices/details",
                    "id_field": "deviceId",
                },
                {
                    "sourcetype": "cisco:bcs:configbestpracticerule",
                    "endpoint_path": "/configBestPractices/rules",
                    "id_field": "bestPracticeRuleId",
                },
                {
                    "sourcetype": "cisco:bcs:configbestpracticerulereference",
                    "endpoint_path": "/configBestPractices/rulesReferences",
                    "id_field": "bestPracticeRuleId",
                },
                {
                    "sourcetype": "cisco:bcs:configbestpracticesummary",
                    "endpoint_path": "/configBestPractices/summary",
                    "id_field": "bestPracticeRuleId",
                },
                {
                    "sourcetype": "cisco:bcs:device",
                    "endpoint_path": "/inventory/devices",
                    "id_field": "deviceId",
                },
                {
                    "sourcetype": "cisco:bcs:devicegroup",
                    "endpoint_path": "/deviceGroups/groups",
                    "id_field": "groupId",
                },
                {
                    "sourcetype": "cisco:bcs:devicegroupmember",
                    "endpoint_path": "/deviceGroups/groupMembers",
                    "id_field": "deviceId",
                },
                {
                    "sourcetype": "cisco:bcs:fieldnotice",
                    "endpoint_path": "/productAlerts/fieldNotices",
                    "id_field": "deviceId",
                    "supports_match_confidence_filter": True,
                },
                {
                    "sourcetype": "cisco:bcs:fieldnoticebulletin",
                    "endpoint_path": "/productAlerts/fieldNoticeBulletins",
                    "id_field": "fieldNoticeId",
                },
                {
                    "sourcetype": "cisco:bcs:hardwareendoflife",
                    "endpoint_path": "/productAlerts/hardwareEndOfLife",
                    "id_field": "deviceId",
                },
                {
                    "sourcetype": "cisco:bcs:hardwareendoflifebulletin",
                    "endpoint_path": "/productAlerts/hardwareEndOfLifeBulletins",
                    "id_field": "hardwareEndOfLifeId",
                },
                {
                    "sourcetype": "cisco:bcs:lastresetdetails",
                    "endpoint_path": "/deviceReset/lastResetDetails",
                    "id_field": "deviceId",
                },
                {
                    "sourcetype": "cisco:bcs:pindetails",
                    "endpoint_path": "/placeInNetwork/details",
                    "id_field": "deviceId",
                },
                {
                    "sourcetype": "cisco:bcs:resetcount",
                    "endpoint_path": "/deviceReset/resetCount",
                    "id_field": "trackingId",
                },
                {
                    "sourcetype": "cisco:bcs:resethistory",
                    "endpoint_path": "/deviceReset/resetHistory",
                    "id_field": "deviceId",
                },
                {
                    "sourcetype": "cisco:bcs:riskmitigationdetails",
                    "endpoint_path": "/riskMitigation/details",
                    "id_field": "deviceId",
                },
                {
                    "sourcetype": "cisco:bcs:riskmitigationsummary",
                    "endpoint_path": "/riskMitigation/summary",
                    "id_field": None,
                },
                {
                    "sourcetype": "cisco:bcs:securityadvisory",
                    "endpoint_path": "/productAlerts/securityAdvisories",
                    "id_field": "deviceId",
                    "supports_match_confidence_filter": True,
                },
                {
                    "sourcetype": "cisco:bcs:securityadvisorybulletin",
                    "endpoint_path": "/productAlerts/securityAdvisoryBulletins",
                    "id_field": "bugIds",
                },
                {
                    "sourcetype": "cisco:bcs:softwareadvisoryalert",
                    "endpoint_path": "/productAlerts/softwareAdvisoryAlerts",
                    "id_field": "deviceId",
                },
                {
                    "sourcetype": "cisco:bcs:softwareendoflife",
                    "endpoint_path": "/productAlerts/softwareEndOfLife",
                    "id_field": "deviceId",
                },
                {
                    "sourcetype": "cisco:bcs:softwareendoflifebulletin",
                    "endpoint_path": "/productAlerts/softwareEndOfLifeBulletins",
                    "id_field": "bulletinNumber",
                },
                {
                    "sourcetype": "cisco:bcs:softwaretrackmember",
                    "endpoint_path": "/softwareTrack/members",
                    "id_field": "softwareTrackId",
                },
                {
                    "sourcetype": "cisco:bcs:softwaretracksoftwaremaintenanceupgradecompliance",
                    "endpoint_path": "/softwareTrack/softwareMaintenanceUpgradeCompliance",
                    "id_field": "softwareTrackId",
                },
                {
                    "sourcetype": "cisco:bcs:softwaretracksoftwaremaintenanceupgraderecommendation",
                    "endpoint_path": "/softwareTrack/softwareMaintenanceUpgradeRecommendations",
                    "id_field": "softwareTrackId",
                },
                {
                    "sourcetype": "cisco:bcs:softwaretracksummary",
                    "endpoint_path": "/softwareTrack/summary",
                    "id_field": "softwareTrackId",
                },
                {
                    "sourcetype": "cisco:bcs:uirdetails",
                    "endpoint_path": "/unidentifiedInventory/details",
                    "id_field": None,
                },
                {
                    "sourcetype": "cisco:bcs:uirsummary",
                    "endpoint_path": "/unidentifiedInventory/summary",
                    "id_field": None,
                },
                {
                    "sourcetype": "cisco:bcs:contractserial",
                    "endpoint_path": "/contract/serials",
                    "id_field": "serialNumber",
                },
            ]

            # ── Authenticate ──
            jwt, jwt_expires_in = get_jwt(logger, server, opt_clientid, opt_secret, rate_limiter)
            jwt_timestamp = time.time()
            logger.info(f"Authentication successful, JWT expires in {jwt_expires_in} seconds")
            headers = {"Authorization": f"Bearer {jwt}"}

            JWT_REFRESH_BUFFER_SECONDS = 300

            # ── Iterate over data sources ──
            for data_source in data_sources:

                # Proactive JWT refresh before expiration
                if time.time() - jwt_timestamp > (jwt_expires_in - JWT_REFRESH_BUFFER_SECONDS):
                    logger.info("JWT approaching expiration, refreshing token...")
                    jwt, jwt_expires_in = get_jwt(logger, server, opt_clientid, opt_secret, rate_limiter)
                    jwt_timestamp = time.time()
                    headers = {"Authorization": f"Bearer {jwt}"}
                    logger.info(f"JWT refreshed successfully, new JWT expires in {jwt_expires_in} seconds")

                sourcetype = data_source["sourcetype"]
                endpoint_path = data_source["endpoint_path"]
                id_field_name = data_source.get("id_field")
                supports_match_confidence_filter = data_source.get("supports_match_confidence_filter", False)

                # Construct base URL with region
                full_url = f"https://{server}/{opt_region}/bcs/v2{endpoint_path}"

                # Build query parameters for security vulnerable filtering
                url_params = {}
                if opt_security_vulnerable_only and supports_match_confidence_filter:
                    url_params["matchConfidence"] = [
                        "Vulnerable",
                        "Potentially Vulnerable",
                    ]
                    logger.debug(f"  Applying security vulnerable filter: {url_params['matchConfidence']}")

                source_start = time.time()

                logger.info(f"Collecting {sourcetype}")
                logger.debug(f"  URL: {full_url}")
                logger.debug(f"  ID field: {id_field_name}")
                if url_params:
                    logger.debug(f"  Query parameters: {url_params}")

                try:
                    item_count = 0
                    source_bytes = 0
                    large_events = 0
                    failed_writes = 0

                    def refresh_jwt_and_headers():
                        nonlocal jwt, jwt_expires_in, jwt_timestamp, headers
                        jwt, jwt_expires_in = get_jwt(logger, server, opt_clientid, opt_secret, rate_limiter)
                        jwt_timestamp = time.time()
                        headers = {"Authorization": f"Bearer {jwt}"}
                        logger.info(f"JWT refreshed during pagination, " f"new JWT expires in {jwt_expires_in} seconds")
                        return headers

                    for item in get_all_items(
                        logger,
                        full_url,
                        headers,
                        rate_limiter,
                        url_params=url_params if url_params else None,
                        jwt_refresh_callback=refresh_jwt_and_headers,
                    ):
                        try:
                            # Serialize JSON compactly
                            json_output = json.dumps(item, ensure_ascii=False, separators=(",", ":"))
                            json_size = len(json_output)
                            source_bytes += json_size

                            # DEBUG: Log every event details
                            item_id = item.get(id_field_name, "N/A") if id_field_name else "N/A"
                            logger.debug(
                                f"Processing event: sourcetype={sourcetype}, "
                                f"{id_field_name}={item_id}, size={json_size} bytes"
                            )

                            # WARN: Large events
                            if json_size > 10000:
                                large_events += 1
                                logger.warning(
                                    f"Large event detected: {json_size} bytes for {sourcetype} "
                                    f"{id_field_name}={item_id}"
                                )

                            # DEBUG: Log event content (first 500 chars only)
                            logger.debug(f"  Event data: {json_output[:500]}...")

                        except (TypeError, ValueError) as e:
                            logger.error(f"JSON serialization failed for {sourcetype}: " f"{type(e).__name__}: {e}")
                            logger.debug(f"  Problematic item: {item}")
                            continue

                        # Create Splunk event
                        event_time = time.time()

                        logger.debug(
                            f"Creating Splunk event: index={output_index}, "
                            f"sourcetype={sourcetype}, time={event_time}"
                        )

                        event = smi.Event(
                            data=json_output,
                            host=server,
                            index=output_index,
                            sourcetype=sourcetype,
                            source=input_name,
                            time=event_time,
                        )

                        # Write event with error handling
                        try:
                            event_writer.write_event(event)
                            item_count += 1

                            logger.debug(f"Event written successfully: {sourcetype} " f"{id_field_name}={item_id}")

                            # INFO: Progress every 100 events
                            if item_count % 100 == 0:
                                elapsed = time.time() - source_start
                                rate = item_count / elapsed if elapsed > 0 else 0
                                logger.info(
                                    f"  Progress: {item_count} events, "
                                    f"{source_bytes / 1024:.1f} KB, "
                                    f"{rate:.1f} events/sec"
                                )

                        except Exception as e:
                            failed_writes += 1
                            logger.error(f"Failed to write event: {type(e).__name__}: {e}")
                            logger.debug(f"  Failed event data: {json_output[:500]}...")
                            continue

                    # Summary for this sourcetype
                    source_duration = time.time() - source_start
                    total_events_collected += item_count
                    total_bytes_collected += source_bytes

                    rate = item_count / source_duration if source_duration > 0 else 0

                    logger.info(
                        f"Completed {sourcetype}: {item_count} events, "
                        f"{source_bytes / 1024:.1f} KB in {source_duration:.2f}s "
                        f"({rate:.1f} events/sec)"
                    )

                    if large_events > 0:
                        logger.info(f"  └─ {large_events} large events (>10KB)")
                    if failed_writes > 0:
                        logger.warning(f"  └─ {failed_writes} failed writes")

                    logger.debug(
                        f"Sourcetype stats: collected={item_count}, "
                        f"failed={failed_writes}, large={large_events}, "
                        f"bytes={source_bytes}"
                    )

                    # Log events ingested per sourcetype using solnlib
                    log.events_ingested(
                        logger,
                        input_name,
                        sourcetype,
                        item_count,
                        output_index,
                        account=account_name,
                    )

                except Exception as e:
                    logger.error(f"Error collecting {sourcetype}: {type(e).__name__}: {e}")
                    logger.debug(f"Traceback:\n{traceback.format_exc()}")

                    # Critical: daily limit reached
                    if "Daily API call limit" in str(e):
                        logger.critical(
                            f"Daily API call limit reached. Stopping all collection. "
                            f"Collected {total_events_collected} events so far."
                        )
                        break

                    # Non-critical: continue with next sourcetype
                    logger.info(f"Skipping {sourcetype}, continuing with next sourcetype")
                    continue

            # ── Final summary ──
            collection_duration = time.time() - collection_start
            overall_rate = total_events_collected / collection_duration if collection_duration > 0 else 0

            logger.info(
                f"Collection complete: {total_events_collected} events, "
                f"{total_bytes_collected / 1024 / 1024:.2f} MB in "
                f"{collection_duration:.2f}s ({overall_rate:.1f} events/sec)"
            )
            logger.debug(
                f"Collection ended at {datetime.datetime.now(timezone.utc).isoformat()} UTC. "
                f"API calls made: {rate_limiter.daily_call_count}"
            )

            log.modular_input_end(logger, normalized_input_name)

        except Exception as e:
            log.log_exception(
                logger,
                e,
                "collection_error",
                msg_before=f"Exception raised while ingesting data for " f"{normalized_input_name}: ",
            )
