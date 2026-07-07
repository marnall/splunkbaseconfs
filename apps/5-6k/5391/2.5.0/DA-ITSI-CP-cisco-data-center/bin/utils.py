# ${copyright}
"""
Utility for setting up default connections for Cisco Data Center data sources in Splunk ITSI
"""
import json
import logging
import logging.handlers
from typing import Optional

from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk import rest, SplunkdConnectionException

ITSI_EVENT_MANAGEMENT_INTERFACE_API = "/servicesNS/{}/{}/event_management_interface/data_integration"
LOG_FORMAT = '%(asctime)s process:%(process)d thread:%(threadName)s %(levelname)s [%(name)s] ' \
             '[%(module)s:%(lineno)d] [%(funcName)s] %(message)s'


def setup_logger(logger_name: str, log_level=logging.INFO, log_format=LOG_FORMAT):
    """
    Set up logging for the Cisco Data Center setup defaults script.

    Returns:
        logging.Logger: Configured logger instance
    """
    log_filename = make_splunkhome_path([
        'var', 'log', 'splunk', 'cisco_data_center_default_loader.log'
    ])

    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)

    # Create rotating file handler
    handler = logging.handlers.RotatingFileHandler(
        log_filename,
        maxBytes=1024000,
        backupCount=5
    )

    # Set log format
    formatter = logging.Formatter(log_format)
    handler.setFormatter(formatter)
    handler.setLevel(log_level)

    logger.addHandler(handler)
    return logger


class CiscoDataCenterConnectionsUtil:
    """
    This class contains default connections for Cisco Data Center data sources.
    Each connection is defined as a dictionary with specific fields and configurations.
    """

    NEXUS_DASHBOARD = {
        "data_source": "nexus_dashboard",
        "ingestion_method": {
            "type": "INDEXED_DATA",
            "value": "`cisco_dc_nd_index` sourcetype IN (\"cisco:dc:nd:anomalies\", "
                     "\"cisco:dc:nd:advisories\") \n| mvexpand node_names\n| rename node_names "
                     "as node_name\n| eval itsi_entity_id = fabricName.\":\".node_name",
            "time_range": {
                "earliest": "-15m",
                "latest": "now"
            }
        },
        "mapped_fields": {
            "src": {
                "name": "src",
                "display_name": "Source",
                "type": "notable_event_field",
                "input_type": "composition",
                "rule_type": "",
                "regex_source": "",
                "values": [
                    "{node_name}"
                ]
            },
            "signature": {
                "name": "signature",
                "display_name": "Signature",
                "type": "notable_event_field",
                "input_type": "composition",
                "rule_type": "",
                "regex_source": "",
                "values": [
                    "{signature}"
                ]
            },
            "vendor_severity": {
                "name": "vendor_severity",
                "display_name": "Vendor Severity",
                "type": "notable_event_field",
                "input_type": "composition",
                "rule_type": "",
                "regex_source": "",
                "values": [
                    "{vendor_severity}"
                ]
            },
            "severity_id": {
                "name": "severity_id",
                "display_name": "Severity ID",
                "type": "notable_event_field",
                "input_type": "mapping_rule",
                "rule_type": "case",
                "regex_source": "",
                "values": [
                    {
                        "condition": "IF",
                        "clauses": [
                            {
                                "field": "vendor_severity",
                                "operator": "==",
                                "value": "critical",
                                "case_sensitive": False
                            }
                        ],
                        "outcomes": [
                            "6"
                        ]
                    },
                    {
                        "condition": "ELSE_IF",
                        "clauses": [
                            {
                                "field": "vendor_severity",
                                "operator": "==",
                                "value": "major",
                                "case_sensitive": False
                            }
                        ],
                        "outcomes": [
                            "5"
                        ]
                    },
                    {
                        "condition": "ELSE_IF",
                        "clauses": [
                            {
                                "field": "vendor_severity",
                                "operator": "==",
                                "value": "minor",
                                "case_sensitive": False
                            }
                        ],
                        "outcomes": [
                            "4"
                        ]
                    },
                    {
                        "condition": "ELSE_IF",
                        "clauses": [
                            {
                                "field": "vendor_severity",
                                "operator": "==",
                                "value": "warning",
                                "case_sensitive": False
                            }
                        ],
                        "outcomes": [
                            "3"
                        ]
                    },
                    {
                        "condition": "ELSE_IF",
                        "clauses": [
                            {
                                "field": "vendor_severity",
                                "operator": "==",
                                "value": "normal",
                                "case_sensitive": False
                            }
                        ],
                        "outcomes": [
                            "2"
                        ]
                    },
                    {
                        "condition": "ELSE_IF",
                        "clauses": [
                            {
                                "field": "vendor_severity",
                                "operator": "==",
                                "value": "info",
                                "case_sensitive": False
                            }
                        ],
                        "outcomes": [
                            "1"
                        ]
                    },
                    {
                        "condition": "ELSE",
                        "outcomes": [
                            "3"
                        ]
                    }
                ],
                "default_value": "1"
            },
            "title": {
                "name": "title",
                "display_name": "Title",
                "type": "notable_event_field",
                "input_type": "mapping_rule",
                "rule_type": "case",
                "regex_source": "",
                "values": [
                    {
                        "condition": "IF",
                        "clauses": [
                            {
                                "field": "alertType",
                                "operator": "==",
                                "value": "advisory",
                                "case_sensitive": False
                            }
                        ],
                        "outcomes": [
                            "{title}"
                        ]
                    },
                    {
                        "condition": "ELSE",
                        "outcomes": [
                            "{fabricName}",
                            "-",
                            "{signature}",
                            "-",
                            "{src}"
                        ]
                    }
                ]
            },
            "owner": {
                "name": "owner",
                "display_name": "Owner",
                "type": "notable_event_field",
                "input_type": "composition",
                "rule_type": "",
                "regex_source": "",
                "values": [
                    "unassigned"
                ],
                "default_value": "unassigned"
            },
            "status": {
                "name": "status",
                "display_name": "Status",
                "type": "notable_event_field",
                "input_type": "composition",
                "rule_type": "",
                "regex_source": "",
                "values": [
                    "1"
                ]
            },
            "subcomponent": {
                "name": "subcomponent",
                "display_name": "Subcomponent",
                "type": "notable_event_field",
                "input_type": "composition",
                "rule_type": "",
                "regex_source": "",
                "values": [
                    "{entityName}"
                ]
            },
            "alert_identifier_fields": {
                "name": "alert_identifier_fields",
                "display_name": "Alert Identifier Fields",
                "type": "notable_event_field",
                "input_type": "composition",
                "rule_type": "",
                "regex_source": "",
                "values": [
                    "{id}"
                ],
                "default_value": "default_identifier"
            },
            "description": {
                "name": "description",
                "display_name": "Description",
                "type": "notable_event_field",
                "input_type": "composition",
                "rule_type": "",
                "regex_source": "",
                "values": [
                    "{description}"
                ]
            },
            "app": {
                "name": "app",
                "display_name": "App",
                "type": "notable_event_field",
                "input_type": "composition",
                "rule_type": "",
                "regex_source": "",
                "values": [
                    "{app}"
                ],
                "default_value": "Cisco DC Networking"
            },
            "itsiDrilldownSearchName": {
                "name": "itsiDrilldownSearchName",
                "display_name": "ITSI Drilldown Search Name",
                "type": "notable_event_field",
                "input_type": "composition",
                "rule_type": "",
                "regex_source": "",
                "values": [
                    "{itsiDrilldownSearchName}"
                ]
            },
            "itsiDrilldownSearch": {
                "name": "itsiDrilldownSearch",
                "display_name": "ITSI Drilldown Search",
                "type": "notable_event_field",
                "input_type": "composition",
                "rule_type": "",
                "regex_source": "",
                "values": [
                    "{itsiDrilldownSearch}"
                ]
            },
            "itsiDrilldownEarliestOffset": {
                "name": "itsiDrilldownEarliestOffset",
                "display_name": "ITSI Drilldown earliest offset",
                "type": "notable_event_field",
                "input_type": "mapping_rule",
                "rule_type": "coalesce",
                "regex_source": "",
                "values": [
                    "{itsiDrilldownEarliestOffset}",
                    [
                        "-900"
                    ]
                ],
                "default_value": "-900"
            },
            "itsiDrilldownLatestOffset": {
                "name": "itsiDrilldownLatestOffset",
                "display_name": "ITSI Drilldown latest offset",
                "type": "notable_event_field",
                "input_type": "mapping_rule",
                "rule_type": "coalesce",
                "regex_source": "",
                "values": [
                    "{itsiDrilldownLatestOffset}",
                    [
                        "900"
                    ]
                ],
                "default_value": "900"
            },
            "itsiDrilldownWebName": {
                "name": "itsiDrilldownWebName",
                "display_name": "ITSI Drilldown Website Name",
                "type": "notable_event_field",
                "input_type": "mapping_rule",
                "rule_type": "case",
                "regex_source": "",
                "values": [
                    {
                        "condition": "IF",
                        "clauses": [
                            {
                                "field": "alertType",
                                "operator": "==",
                                "case_sensitive": False,
                                "value": "advisory"
                            }
                        ],
                        "outcomes": [
                            "Advisories"
                        ]
                    },
                    {
                        "condition": "ELSE",
                        "outcomes": [
                            "Anomalies"
                        ]
                    }
                ]
            },
            "itsiDrilldownWebURL": {
                "name": "itsiDrilldownWebURL",
                "display_name": "ITSI Drilldown Website URL",
                "type": "notable_event_field",
                "input_type": "mapping_rule",
                "rule_type": "case",
                "regex_source": "",
                "values": [
                    {
                        "condition": "IF",
                        "clauses": [
                            {
                                "field": "alertType",
                                "operator": "==",
                                "value": "advisory",
                                "case_sensitive": False
                            }
                        ],
                        "outcomes": [
                            "https://",
                            "{nd_host}",
                            "/advisories"
                        ]
                    },
                    {
                        "condition": "ELSE",
                        "outcomes": [
                            "https://",
                            "{nd_host}",
                            "/anomalies"
                        ]
                    }
                ]
            },
            "itsi_instruction": {
                "name": "itsi_instruction",
                "display_name": "ITSI Instruction",
                "type": "notable_event_field",
                "input_type": "composition",
                "rule_type": "",
                "regex_source": "",
                "values": [
                    "{itsi_instruction}"
                ]
            }
        },
        "association": {
            "entity_lookup_field": "itsi_entity_id",
            "service_ids": ""
        },
        "cron_schedule": {
            "value": "*/5 * * * *",
            "type": "Basic"
        },
        "status": "inactive",
        "title": "nexus_dashboard_default",
        "throttling": {
            "throttling_enabled": False,
            "dedup_notable_event": False,
            "throttling_earliest_time": "-59m",
            "throttling_latest_time": "now"
        },
        "is_out_of_the_box": 1,
        "_key": "nexus_dashboard_default",
    }

    def __init__(self, session_key, logger=None):
        self.session_key = session_key
        self.logger = logger if logger else logging.getLogger(__name__)
        self.connections = {
            "nexus_dashboard": self.NEXUS_DASHBOARD
        }

    def _setup_connection(self, connection_type: Optional[str] = None) -> bool:
        """
        Set up a default connection for the specified Cisco Data Center data source.
        :param connection_type:
        :return: True if the connection was successfully created or already exists, False otherwise.
        """
        if connection_type is None:
            return False

        base_url = ITSI_EVENT_MANAGEMENT_INTERFACE_API.format("nobody", "SA-ITOA")
        config = self.connections.get(connection_type)

        if not config:
            self.logger.error("No configuration found for connection type: %s", connection_type)
            return False

        try:
            # check if the connection already exists
            connection_url = "{}/{}".format(base_url, config["_key"])
            response, content = rest.simpleRequest(
                connection_url,
                method='GET',
                sessionKey=self.session_key,
                rawResult=True,
            )

            if response.status == 200:
                # connection already exists, no need to create
                self.logger.info("Default connection already exists for connection_type=%s",
                                 connection_type)
                return True

            if response.status == 404:
                # create the connection if it does not exist
                self.logger.info(
                    "Default connection does not exist, creating connection_type=%s",
                    connection_type)
                response, content = rest.simpleRequest(
                    base_url,
                    method='POST',
                    jsonargs=json.dumps(config),
                    sessionKey=self.session_key,
                )
                if response.status == 200:
                    self.logger.info("Connection created successfully connection_type=%s",
                                     connection_type)
                    return True

                self.logger.error(
                    "Failed to create connection response_status=%s response_content=%s "
                    "connection_type=%s connection_config=%s",
                    response.status, content, connection_type, config)
            else:
                self.logger.error(
                    "Unexpected response status response_status=%s response_content=%s connection_type=%s",
                    response.status, content, connection_type)
        except SplunkdConnectionException as err:
            self.logger.exception(
                "Failed to setup default connection connection_type=%s error=%s",
                connection_type,
                err
            )

        return False

    def setup_connections(self):
        """
        Set up default alerts connections for Cisco Data Center data sources.
        :return:
        """
        nexus_connection = self._setup_connection("nexus_dashboard")

        return nexus_connection
