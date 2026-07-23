# Splunk ships Python 3.9 linked against OpenSSL 1.0.2 which cannot negotiate
# modern TLS cipher suites. Re-exec once with LD_LIBRARY_PATH pointing to the
# system OpenSSL 1.1.1+ so the ssl module can handle TLS 1.2+.
# Also set REQUESTS_CA_BUNDLE so requests finds the system CA certificates.
import os  # noqa: E402
import sys  # noqa: E402

_SYSTEM_SSL_DIR = "/usr/lib64"
_SYSTEM_CA_BUNDLE = "/etc/pki/tls/certs/ca-bundle.crt"

if os.environ.get("_DARKSTRATA_SSL_BOOTSTRAPPED") != "1" and os.path.exists(
    os.path.join(_SYSTEM_SSL_DIR, "libssl.so.1.1")
):
    os.environ["_DARKSTRATA_SSL_BOOTSTRAPPED"] = "1"
    os.environ["LD_LIBRARY_PATH"] = _SYSTEM_SSL_DIR + ":" + os.environ.get("LD_LIBRARY_PATH", "")
    if os.path.exists(_SYSTEM_CA_BUNDLE):
        os.environ["REQUESTS_CA_BUNDLE"] = _SYSTEM_CA_BUNDLE
    os.execv(sys.executable, [sys.executable] + sys.argv)

import import_declare_test  # noqa: F401

import json
import logging
import sys
from datetime import datetime, timezone

from solnlib import conf_manager
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

from darkstrata_inputs import (
    DarkStrataAPIClient,
    SOURCETYPE_ALERT,
    SOURCETYPE_OBSERVED_DATA,
)

APP_NAME = "TA-darkstrata"


class DarkStrataAlerts(smi.Script):
    def get_scheme(self):
        scheme = smi.Scheme("darkstrata_alerts")
        scheme.description = "DarkStrata Alerts"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(smi.Argument("name", title="Name", required_on_create=True))
        scheme.add_argument(smi.Argument("account", required_on_create=True))
        scheme.add_argument(smi.Argument("detail", required_on_create=False))
        scheme.add_argument(smi.Argument("include_identities", required_on_create=False))
        scheme.add_argument(smi.Argument("confidence_threshold", required_on_create=False))
        scheme.add_argument(smi.Argument("hash_emails", required_on_create=False))
        return scheme

    def validate_input(self, definition):
        return

    def stream_events(self, inputs, ew):
        logger = logging.getLogger("ta_darkstrata_alerts")
        logger.setLevel(logging.INFO)

        for input_name, input_item in inputs.inputs.items():
            session_key = inputs.metadata.get("session_key", "")
            account_name = input_item.get("account")
            detail = input_item.get("detail", "full")
            include_identities = input_item.get("include_identities", "1") in ("1", "true", True)
            confidence_threshold = int(input_item.get("confidence_threshold", 0))
            hash_emails = input_item.get("hash_emails", "0") in ("1", "true", True)
            index = input_item.get("index", "default")

            logger.info("Starting alerts collection for account: %s", account_name)

            # Get account credentials
            try:
                cfm = conf_manager.ConfManager(
                    session_key,
                    APP_NAME,
                    realm=f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-ta_darkstrata_account",
                )
                account_config = cfm.get_conf("ta_darkstrata_account").get(account_name, {})
            except Exception as e:
                logger.error("Failed to get account config: %s", e)
                continue

            api_base_url = account_config.get("api_base_url")
            api_key = account_config.get("api_key")

            if not api_base_url or not api_key:
                logger.error("Missing API configuration for account: %s", account_name)
                continue

            # Get proxy settings
            proxy_settings = None
            try:
                settings_cfm = conf_manager.ConfManager(session_key, APP_NAME)
                proxy_settings = settings_cfm.get_conf("ta_darkstrata_settings").get("proxy", {})
            except Exception:
                pass

            # Initialise API client
            client = DarkStrataAPIClient(
                api_base_url=api_base_url,
                api_key=api_key,
                proxy_settings=proxy_settings,
                logger=logger,
            )

            # Get checkpoint for incremental sync
            checkpoint_key = f"darkstrata_alerts_{input_name}"
            since = None
            try:
                ckpt = checkpointer.KVStoreCheckpointer(
                    collection_name="ta_darkstrata_checkpoints",
                    session_key=session_key,
                    app=APP_NAME,
                )
                checkpoint = ckpt.get(checkpoint_key)
                if checkpoint:
                    since = checkpoint.get("last_sync")
            except Exception:
                pass

            logger.info("Starting sync from checkpoint: %s", since)

            # Fetch and write events
            event_count = 0
            latest_timestamp = since

            try:
                for bundle in client.fetch_alerts(
                    since=since,
                    detail=detail,
                    include_identities=include_identities,
                    confidence_threshold=confidence_threshold,
                    hash_emails=hash_emails,
                ):
                    # Find the report object to get timestamp
                    report_obj = None
                    for obj in bundle.get("objects", []):
                        if obj.get("type") == "report":
                            report_obj = obj
                            break

                    event_time = None
                    if report_obj:
                        event_time = _parse_timestamp(report_obj.get("published"))

                    # Write the entire bundle as a single event
                    event = smi.Event(
                        data=json.dumps(bundle),
                        time=event_time,
                        index=index,
                        sourcetype=SOURCETYPE_ALERT,
                    )
                    ew.write_event(event)
                    event_count += 1

                    # Also write individual observed-data objects for searching
                    for obj in bundle.get("objects", []):
                        if obj.get("type") == "observed-data":
                            obj_time = _parse_timestamp(obj.get("modified") or obj.get("created"))
                            event = smi.Event(
                                data=json.dumps(obj),
                                time=obj_time,
                                index=index,
                                sourcetype=SOURCETYPE_OBSERVED_DATA,
                            )
                            ew.write_event(event)

                            ts = obj.get("modified") or obj.get("created")
                            if ts and (not latest_timestamp or ts > latest_timestamp):
                                latest_timestamp = ts

            except Exception as e:
                logger.error("Error collecting alerts: %s", e)
                raise

            # Update checkpoint
            if latest_timestamp:
                try:
                    ckpt = checkpointer.KVStoreCheckpointer(
                        collection_name="ta_darkstrata_checkpoints",
                        session_key=session_key,
                        app=APP_NAME,
                    )
                    ckpt.update(
                        checkpoint_key,
                        {
                            "last_sync": latest_timestamp,
                            "last_run": datetime.now(timezone.utc).isoformat(),
                            "event_count": event_count,
                        },
                    )
                except Exception as e:
                    logger.error("Failed to save checkpoint: %s", e)

            logger.info("Collected %d alert bundles", event_count)


def _parse_timestamp(timestamp_str):
    if not timestamp_str:
        return None
    try:
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        return dt.timestamp()
    except ValueError:
        return None


if __name__ == "__main__":
    sys.exit(DarkStrataAlerts().run(sys.argv))
