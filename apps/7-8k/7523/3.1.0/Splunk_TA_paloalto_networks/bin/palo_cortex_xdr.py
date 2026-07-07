#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import import_declare_test

import sys
import json
import time
import hashlib

import os
import logging
import traceback
import datetime
from typing import Dict, Optional, List, Any, Tuple
from splunklib import modularinput as smi
from solnlib import conf_manager, log
from palo_checkpointer import Checkpoint
from pyxdr.pyxdr import PyXDRClient
from splunklib.modularinput import event
from palo_utils import (
    logger_instance,
    APP_NAME,
    get_proxy_settings,
    get_account_credentials,
)

bin_dir = os.path.basename(__file__)
DEFAULT_FIRST_FETCH = 7


class CortexXDRScript(smi.Script):
    def __init__(self) -> None:
        super().__init__()

    def get_scheme(self) -> smi.Scheme:
        scheme = smi.Scheme("cortex_xdr")
        scheme.description = "Cortex XDR"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                "name", title="Name", description="Name", required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                "xdr_get_details",
                title="Detailed event",
                description="Detailed event",
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "xdr_audit_logs",
                title="Audit Logs",
                description="Audit Logs",
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "xdr_get_endpoints",
                title="Collect Endpoints",
                description="Collect Endpoints",
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "xdr_get_alerts",
                title="Collect Alerts",
                description="Collect Alerts",
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "xdr_account",
                required_on_create=True,
            )
        )

        return scheme

    def validate_input(self, definition) -> None:
        pass

    def ts_to_string(self, timestamp: int) -> str:
        """
        Used for debugging, converts a timestamp in ms to an ISO string

        :param timestamp: Timestamp.
        :returns: Time formatted according to ISO.
        """
        return datetime.datetime.fromtimestamp(
            int(timestamp / 1000), datetime.timezone.utc
        ).isoformat()

    def get_mod_time(
        self, checkpoint: Checkpoint, logger: logging.Logger, start_time: str
    ) -> int:
        """
        Gets last modification time from KVstore lookup
        or calculates it if KVstore lookup doesn't exist

        :param checkpoint: KVstore checkpointer object.
        :param logger: Logger object instance.
        :param start_time: Start time for the first fetch.
        :returns: Timestamp.
        """
        latest_modification_time = checkpoint.get("latest_incident_modified")

        if latest_modification_time:
            mod_time = latest_modification_time + 1
        else:
            parsed_dt = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            mod_time = int(parsed_dt.timestamp() * 1000)
            logger.debug(f"First fetch timestamp Incidents in Cortex XDR: {mod_time}")
        return mod_time

    def get_alert_time(
        self, checkpoint: Checkpoint, logger: logging.Logger, start_time: str
    ) -> int:
        """
        Gets last alert creation time from KVstore lookup
        or calculates it if KVstore lookup doesn't exist.

        :param checkpoint: KVstore checkpointer object.
        :param logger: Logger object instance.
        :param start_time: Start time for the first fetch.
        :returns: Timestamp in ms since epoch.
        """
        latest_alert_time = checkpoint.get("latest_alert_creation_time")

        if latest_alert_time:
            alert_time = latest_alert_time + 1
        else:
            parsed_dt = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            alert_time = int(parsed_dt.timestamp() * 1000)
            logger.debug(f"First fetch timestamp Alerts in Cortex XDR: {alert_time}")
        return alert_time

    def get_audit_time(
        self,
        checkpoint: Checkpoint,
        audit_type: str,
        logger: logging.Logger,
        start_time: str,
    ) -> int:
        """
        Gets last audit time from KVstore lookup
        or calculates it if KVstore lookup doesn't exist

        :param checkpoint: KVstore checkpointer object.
        :param audit_type: Audit Type.
        :param logger: Logger object instance.
        :param start_time: Start time for the first fetch.
        :returns: Timestamp.
        """

        if audit_type == "agent_audit":
            latest_audit_time = checkpoint.get("latest_agent_audit_log")
        else:
            latest_audit_time = checkpoint.get("latest_mgmt_audit_log")

        if latest_audit_time:
            audit_time = latest_audit_time + 1000
        else:
            parsed_dt = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            audit_time = int(parsed_dt.timestamp() * 1000)
            logger.debug(
                f"First fetch timestamp for Audit Logs in Cortex XDR: {audit_time}"
            )
        return audit_time

    def fetch_xdr_incidents(
        self, client: PyXDRClient, mod_time: int, inc_limit: int, logger: logging.Logger
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Calls XDR API to fetch incidents

        :param client: KVstore checkpointer object.
        :param mod_time: Last modification time.
        :param inc_limit: Incident limit.
        :param logger: Logger object instance.
        :returns: Incidents fetched from XDR API.
        """
        logger.debug(f"modification_time filter set to: {self.ts_to_string(mod_time)}")
        try:
            incidents = client.get_incidents(
                limit=inc_limit,
                sort_field="modification_time",
                sort_order="asc",
                filters=[
                    {
                        "field": "modification_time",
                        "operator": "gte",
                        "value": mod_time,
                    }
                ],
            )
            logger.info("Message: XDR API Returned Incidents Successfully")
            return incidents
        except Exception as e:
            log.log_exception(
                logger,
                e,
                "Cortex XDR Error",
                msg_before=f"Error while fetching XDR incidents: {e}",
            )

    def fetch_incident_details(
        self, client: PyXDRClient, incident: Dict[str, Any], logger: logging.Logger
    ) -> Optional[Tuple[str, Any]]:
        """
        Calls XDR API to get extra details for incidents.

        :param client: Cortex XDR API client.
        :param incident: Incident returned from cortex XDR API.
        :param logger: Logger object instance.
        :returns: Tuple containing incident and its alerts.
        """
        try:
            incident_details = client.get_incident_extra_data(
                incident_id=int(incident["incident_id"])
            )
            alerts = []
            incident = incident_details.get("incident")
            incident
            incident_url = incident.get("xdr_url", [])
            for alert in incident_details["alerts"]["data"]:
                alert["incident_url"] = incident_url
                alerts.append(alert)
            return incident, alerts
        except KeyError as ex:
            log.log_exception(
                logger,
                ex,
                "Cortex XDR Error",
                msg_before=f"Skipping incident as incident_id is not found: {str(ex)}",
            )

    def fetch_audit_logs(
        self,
        client: PyXDRClient,
        timestamp: int,
        audit_type: str,
        logger: logging.Logger,
    ) -> Optional[Dict[str, Any]]:
        """
        Calls XDR API to get extra details for incidents.

        :param client: Cortex XDR API client.
        :param timestamp: Last timestamp.
        :param audit_type: Audit type.
        :param logger: Logger object instance.
        :returns: Audit Logs base on type.
        """
        logger.debug(f"timestamp filter set to: {self.ts_to_string(timestamp)}")
        try:
            audit_logs = client.get_audit_logs(
                type_of_log=audit_type, timestamp=timestamp
            )
            logger.info("Message: XDR API Returned Successfully Audit Logs")
            return audit_logs
        except Exception as e:
            log.log_exception(
                logger,
                e,
                "Cortex XDR Error",
                msg_before=f"Error while fetching audit logs: {e}",
            )

    def fetch_xdr_endpoints(
        self, client: PyXDRClient, logger: logging.Logger
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Calls XDR API to fetch all endpoints with pagination.

        :param client: PyXDRClient instance.
        :param logger: Logger object instance.
        :returns: List of endpoints fetched from XDR API.
        """
        try:
            all_endpoints = []
            search_from = 0
            max_iterations = 1000  # Safety limit to prevent infinite loops
            batch_size = 100
            rate_limit_delay = 0.1  # 100ms delay between API calls

            for iteration in range(max_iterations):
                search_to = search_from + batch_size - 1
                result = client.get_endpoints(
                    search_from=search_from, search_to=search_to
                )

                if not result:
                    if iteration == 0:
                        logger.info("No endpoints found in XDR")
                    break

                endpoints = result.get("endpoints", [])
                total_count = result.get("total_count", 0)

                if not endpoints:
                    break

                all_endpoints.extend(endpoints)
                logger.debug(
                    f"Fetched {len(endpoints)} endpoints. "
                    f"Progress: {len(all_endpoints)}/{total_count}"
                )

                if len(all_endpoints) >= total_count:
                    break

                search_from += batch_size
                time.sleep(rate_limit_delay)
            else:
                logger.warning(
                    f"Reached maximum iteration limit ({max_iterations}) "
                    f"while fetching endpoints. Collected {len(all_endpoints)} endpoints."
                )

            if all_endpoints:
                logger.info(
                    f"Message: XDR API Returned {len(all_endpoints)} Endpoints Successfully"
                )
            return all_endpoints if all_endpoints else None

        except Exception as e:
            log.log_exception(
                logger,
                e,
                "Cortex XDR Error",
                msg_before=f"Error while fetching XDR endpoints: {e}",
            )
            return None

    def fetch_xdr_alerts(
        self, client: PyXDRClient, alert_time: int, logger: logging.Logger
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Calls XDR API to fetch alerts created at or after alert_time, with pagination.

        :param client: PyXDRClient instance.
        :param alert_time: Watermark in ms since epoch; only alerts with creation_time >= this are fetched.
        :param logger: Logger object instance.
        :returns: List of alerts fetched from XDR API.
        """
        logger.debug(f"creation_time filter set to: {self.ts_to_string(alert_time)}")
        filters = [{"field": "creation_time", "operator": "gte", "value": alert_time}]
        sort = {"field": "creation_time", "keyword": "asc"}
        try:
            all_alerts = []
            search_from = 0
            max_iterations = 1000  # Safety limit to prevent infinite loops
            batch_size = 100
            rate_limit_delay = 0.1  # 100ms delay between API calls

            for iteration in range(max_iterations):
                search_to = search_from + batch_size - 1
                result = client.get_alerts(
                    search_from=search_from,
                    search_to=search_to,
                    filters=filters,
                    sort=sort,
                )

                if not result:
                    if iteration == 0:
                        logger.info("No alerts found in XDR")
                    break

                alerts = result.get("alerts", [])
                total_count = result.get("total_count", 0)

                if not alerts:
                    break

                all_alerts.extend(alerts)
                logger.debug(
                    f"Fetched {len(alerts)} alerts. "
                    f"Progress: {len(all_alerts)}/{total_count}"
                )

                if len(all_alerts) >= total_count:
                    break

                search_from += batch_size
                time.sleep(rate_limit_delay)
            else:
                logger.warning(
                    f"Reached maximum iteration limit ({max_iterations}) "
                    f"while fetching alerts. Collected {len(all_alerts)} alerts."
                )

            if all_alerts:
                logger.info(
                    f"Message: XDR API Returned {len(all_alerts)} Alerts Successfully"
                )
            return all_alerts if all_alerts else None

        except Exception as e:
            log.log_exception(
                logger,
                e,
                "Cortex XDR Error",
                msg_before=f"Error while fetching XDR alerts: {e}",
            )
            return None

    def handle_incidents(
        self,
        client: PyXDRClient,
        incidents: List[Dict[str, Any]],
        get_details: bool,
        base_url: str,
        logger: logging.Logger,
        checkpoint: Checkpoint,
        event_writer: smi.EventWriter,
        input_item: Dict[str, Any],
        input_name: str,
    ) -> None:
        """
        Method writes data to Splunk and gets event details if required

        :param client: Cortex XDR API client.
        :param incidents: Incidents returned from cortex XDR API.
        :param get_details: Parameter from user input defined in modular input.
        :param base_url: Url for API requests.
        :param logger: Logger object instance.
        :param checkpoint: KVstore checkpointer object.
        :param event_writer: Object of class EventWriter to write Splunk modular input events.
        :param input_item: Configuration of modular input defined by user.
        :param input_name: Input name defined by user in modular input configuration.
        """
        sourcetype = "pan:xdr:incident"
        try:
            latest_modification_time = int(incidents[-1].get("modification_time"))
            latest_incident_id = int(incidents[-1].get("incident_id"))
            checkpoint.update("latest_incident_modified", latest_modification_time)
            for incident in incidents:
                if get_details:
                    incident_event, alerts = self.fetch_incident_details(
                        client, incident, logger
                    )
                else:
                    incident_event = incident

                event_writer.write_event(
                    event.Event(
                        data=json.dumps(incident_event),
                        host=base_url,
                        index=input_item["index"],
                        source=input_name.split("/")[-1],
                        sourcetype=sourcetype,
                    )
                )
                if get_details and alerts:
                    for alert in alerts:
                        event_writer.write_event(
                            event.Event(
                                data=json.dumps(alert),
                                host=base_url,
                                index=input_item["index"],
                                source=input_name.split("/")[-1],
                                sourcetype=f"{sourcetype}:alert",
                            )
                        )
            logger.info(f"Retrieved {len(incidents)} incident results")
            logger.debug(
                "Got the following incident IDs: "
                + " ".join([str(y) for y in incidents])
            )
            logger.debug(
                f"latest_modification_time: {self.ts_to_string(latest_modification_time)}, latest_incident_id: {latest_incident_id}"
            )
            log.events_ingested(
                logger,
                input_name,
                "pan:xdr:incident",
                len(incidents),
                input_item["index"],
            )
        except Exception as e:
            log.log_exception(
                logger,
                e,
                "Cortex XDR Error",
                msg_before=f"Can't ingest Cortex XDR incidents. Error: {e}",
            )

    def handle_audit_logs(
        self,
        audit_logs: List[Dict[str, Any]],
        audit_type: str,
        logger: logging.Logger,
        base_url: str,
        checkpoint: Checkpoint,
        event_writer: smi.EventWriter,
        input_item: Dict[str, Any],
        input_name: str,
    ) -> None:
        """
        Method writes data to Splunk and gets event details if required

        :param audit_logs: Incidents returned from cortex XDR API.
        :param audit_type: Audit Type.
        :param logger: Logger object instance.
        :param base_url: Url for API requests.
        :param checkpoint: KVstore checkpointer object.
        :param event_writer: Object of class EventWriter to write Splunk modular input events.
        :param input_item: Configuration of modular input defined by user.
        :param input_name: Input name defined by user in modular input configuration.
        """
        try:
            if audit_type == "agent_audit":
                audit_source_type = "pan:xdr:audit"
                latest_audit_time = int(audit_logs[-1].get("TIMESTAMP"))
                checkpoint.update("latest_agent_audit_log", latest_audit_time)
            else:
                audit_source_type = "pan:xdr:mgmt:audit"
                latest_audit_time = int(audit_logs[-1].get("AUDIT_INSERT_TIME"))
                checkpoint.update("latest_mgmt_audit_log", latest_audit_time)

            for audit_log in audit_logs:
                event_writer.write_event(
                    event.Event(
                        data=json.dumps(audit_log),
                        host=base_url,
                        index=input_item["index"],
                        source=input_name.split("/")[-1],
                        sourcetype=audit_source_type,
                    )
                )
            logger.info(f"Retrieved {len(audit_logs)} {audit_type} results")

            logger.debug(f"latest_audit_log: {self.ts_to_string(latest_audit_time)}")
            log.events_ingested(
                logger,
                input_name,
                audit_source_type,
                len(audit_logs),
                input_item["index"],
            )
        except Exception as e:
            log.log_exception(
                logger,
                e,
                "Cortex XDR Error",
                msg_before=f"Can't ingest Cortex XDR Management Audit Logs. Error: {e}",
            )

    def handle_endpoints(
        self,
        endpoints: List[Dict[str, Any]],
        base_url: str,
        logger: logging.Logger,
        checkpoint: Checkpoint,
        event_writer: smi.EventWriter,
        input_item: Dict[str, Any],
        input_name: str,
    ) -> None:
        """
        Method writes endpoint data to Splunk.

        :param endpoints: Endpoints returned from Cortex XDR API.
        :param base_url: URL for API requests.
        :param logger: Logger object instance.
        :param checkpoint: KVstore checkpointer object.
        :param event_writer: Object of class EventWriter to write Splunk modular input events.
        :param input_item: Configuration of modular input defined by user.
        :param input_name: Input name defined by user in modular input configuration.
        """
        if not endpoints:
            logger.info("No endpoints to ingest")
            return

        try:
            source = input_name.split("/")[-1]
            index = input_item["index"]
            sourcetype = "pan:xdr:endpoint"
            ingested_count = 0
            unchanged_count = 0
            skipped_no_id = 0

            prior_hashes = checkpoint.get("endpoint_hashes") or {}
            new_hashes = dict(prior_hashes)

            for endpoint in endpoints:
                endpoint_id = endpoint.get("endpoint_id")
                if not endpoint_id:
                    skipped_no_id += 1
                    continue

                serialized = json.dumps(endpoint, sort_keys=True, default=str)
                current_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

                if prior_hashes.get(endpoint_id) == current_hash:
                    unchanged_count += 1
                    continue

                try:
                    event_writer.write_event(
                        event.Event(
                            data=serialized,
                            host=base_url,
                            index=index,
                            source=source,
                            sourcetype=sourcetype,
                        )
                    )
                    ingested_count += 1
                    new_hashes[endpoint_id] = current_hash
                except Exception as write_error:
                    logger.warning(
                        f"Failed to write endpoint {endpoint_id}: {write_error}"
                    )

            if new_hashes != prior_hashes:
                checkpoint.update("endpoint_hashes", new_hashes)

            logger.info(
                f"Endpoint poll: {ingested_count} written, "
                f"{unchanged_count} unchanged (skipped), "
                f"{skipped_no_id} missing endpoint_id, "
                f"{len(endpoints)} fetched"
            )
            log.events_ingested(
                logger,
                input_name,
                sourcetype,
                ingested_count,
                index,
            )

        except Exception as e:
            log.log_exception(
                logger,
                e,
                "Cortex XDR Error",
                msg_before=f"Can't ingest Cortex XDR endpoints. Error: {e}",
            )

    def handle_alerts(
        self,
        alerts: List[Dict[str, Any]],
        base_url: str,
        logger: logging.Logger,
        checkpoint: Checkpoint,
        event_writer: smi.EventWriter,
        input_item: Dict[str, Any],
        input_name: str,
    ) -> None:
        """
        Method writes alert data to Splunk.

        :param alerts: Alerts returned from Cortex XDR API.
        :param base_url: URL for API requests.
        :param logger: Logger object instance.
        :param checkpoint: KVstore checkpointer object.
        :param event_writer: Object of class EventWriter to write Splunk modular input events.
        :param input_item: Configuration of modular input defined by user.
        :param input_name: Input name defined by user in modular input configuration.
        """
        if not alerts:
            logger.info("No alerts to ingest")
            return

        try:
            source = input_name.split("/")[-1]
            index = input_item["index"]
            sourcetype = "pan:xdr:alert"
            ingested_count = 0
            written_insert_ts = []

            for alert in alerts:
                try:
                    event_writer.write_event(
                        event.Event(
                            data=json.dumps(alert),
                            host=base_url,
                            index=index,
                            source=source,
                            sourcetype=sourcetype,
                        )
                    )
                    ingested_count += 1
                    insert_ts = alert.get("local_insert_ts")
                    if insert_ts is not None:
                        written_insert_ts.append(int(insert_ts))
                except Exception as write_error:
                    alert_id = alert.get("alert_id", "unknown")
                    logger.warning(f"Failed to write alert {alert_id}: {write_error}")

            if written_insert_ts:
                latest_creation = max(written_insert_ts)
                checkpoint.update("latest_alert_creation_time", latest_creation)
                logger.debug(
                    f"latest_alert_creation_time: {self.ts_to_string(latest_creation)} "
                    f"(advanced over {ingested_count}/{len(alerts)} successfully written alerts)"
                )
            elif ingested_count < len(alerts):
                logger.warning(
                    f"Skipping alert checkpoint update: only {ingested_count}/{len(alerts)} alerts written, "
                    f"none had local_insert_ts"
                )
            else:
                logger.warning(
                    "Skipping alert checkpoint update: no local_insert_ts on any returned alert"
                )

            logger.info(f"Retrieved {ingested_count} alert results")
            log.events_ingested(
                logger,
                input_name,
                sourcetype,
                ingested_count,
                index,
            )

        except Exception as e:
            log.log_exception(
                logger,
                e,
                "Cortex XDR Error",
                msg_before=f"Can't ingest Cortex XDR alerts. Error: {e}",
            )

    def stream_events(
        self, inputs: smi.InputDefinition, event_writer: smi.EventWriter
    ) -> None:
        for input_name, input_item in inputs.inputs.items():
            logger = logger_instance(input_name)
            try:
                session_key = self._input_definition.metadata["session_key"]
                log_level = conf_manager.get_log_level(
                    logger=logger,
                    session_key=session_key,
                    app_name=APP_NAME,
                    conf_name="splunk_ta_paloalto_networks_settings",
                )
                logger.setLevel(log_level)
                proxies = get_proxy_settings(logger, session_key)
                get_details = True if input_item.get("xdr_get_details") else False
                get_endpoints = True if input_item.get("xdr_get_endpoints") else False
                get_alerts = True if input_item.get("xdr_get_alerts") else False
                audit_logging = input_item.get("xdr_audit_logs")
                audit_types = audit_logging.split("|") if audit_logging else []
                tenant_name = input_item.get("xdr_account")
                inc_limit = int(input_item.get("xdr_incident_limit", 50))
                account_creds = get_account_credentials(
                    session_key, tenant_name, "xdr_account", logger
                )
                region = account_creds.get("region")
                api_key_id = account_creds.get("api_key_id")
                api_key = account_creds.get("api_key")
                checkpoint = Checkpoint(
                    logger=logger,
                    input_name=input_name,
                    session_key=self._input_definition.metadata["session_key"],
                )

                base_url = (
                    f"https://api-{tenant_name}.xdr.{region}.paloaltonetworks.com"
                )

                client = PyXDRClient(
                    api_key_id=api_key_id,
                    api_key=api_key,
                    base_url=base_url,
                    logger=logger,
                    proxy=proxies,
                )

                mod_time = self.get_mod_time(
                    checkpoint, logger, input_item.get("start_time")
                )

                incidents = self.fetch_xdr_incidents(
                    client, mod_time, inc_limit, logger
                )
                logger.debug(f"Incidents: {incidents}")
                if incidents:
                    self.handle_incidents(
                        client,
                        incidents,
                        get_details,
                        base_url,
                        logger,
                        checkpoint,
                        event_writer,
                        input_item,
                        input_name,
                    )
                else:
                    logger.info("No Incidents")

                if len(audit_types) > 0:
                    for audit_type in audit_types:
                        audit_time = self.get_audit_time(
                            checkpoint, audit_type, logger, input_item.get("start_time")
                        )

                        audit_logs = self.fetch_audit_logs(
                            client, audit_time, audit_type, logger
                        )
                        logger.debug(f"{audit_type} logs: {audit_logs}")
                        if audit_logs:
                            self.handle_audit_logs(
                                audit_logs,
                                audit_type,
                                logger,
                                base_url,
                                checkpoint,
                                event_writer,
                                input_item,
                                input_name,
                            )
                        else:
                            logger.info(f"No {audit_type} logs.")

                if get_endpoints:
                    logger.info("Starting Cortex XDR endpoints collection")
                    endpoints = self.fetch_xdr_endpoints(client, logger)
                    if endpoints:
                        self.handle_endpoints(
                            endpoints,
                            base_url,
                            logger,
                            checkpoint,
                            event_writer,
                            input_item,
                            input_name,
                        )
                    else:
                        logger.info("No endpoints found")

                if get_alerts:
                    logger.info("Starting Cortex XDR alerts collection")
                    alert_time = self.get_alert_time(
                        checkpoint, logger, input_item.get("start_time")
                    )
                    alerts = self.fetch_xdr_alerts(client, alert_time, logger)
                    if alerts:
                        self.handle_alerts(
                            alerts,
                            base_url,
                            logger,
                            checkpoint,
                            event_writer,
                            input_item,
                            input_name,
                        )
                    else:
                        logger.info("No alerts found")

            except Exception as e:
                log.log_exception(
                    logger,
                    e,
                    "Cortex XDR Error",
                    msg_before=f"Exception raised while ingesting data for Cortex XDR modular input: {e}. "
                    f"Traceback: {traceback.format_exc()}",
                )


if __name__ == "__main__":
    exit_code = CortexXDRScript().run(sys.argv)
    sys.exit(exit_code)
