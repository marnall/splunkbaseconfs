""" Copyright © 2019-2020, EPAM Systems, all rights reserved. """

""" This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/. """

import calendar
import collections
import datetime
import functools
import json
import logging
import platform
import re
import os
import sys

APP_NAME = "sap_solman_app"

sys.path.insert(
    0,
    "{}/etc/apps/{}/lib/".format(
        os.environ.get("SPLUNK_HOME", "/opt/splunk"), APP_NAME
    ),
)

import six
import six.moves.urllib.parse
from splunklib.client import connect
from splunklib.modularinput import Argument, Event, Scheme, Script

import epmspln_odata2.client
import epmspln_utils.checkpoint as checkpoint_utils
import epmspln_utils.log2 as log_utils
import epmspln_utils.password as password_utils

import common
addon_path = common.get_addon_path()
enterprise_libs_folder = os.path.join(addon_path, 'lib', 'enterprise_libs')

if os.path.isdir(enterprise_libs_folder):
    import enterprise_libs.limitations as limitations
    import enterprise_libs.kv_checkpoint_utils as checkpoint
else: 
    import community_libs.limitations as limitations
    import community_libs.file_checkpoint_utils as checkpoint

if platform.system() == "Windows":
    import msvcrt
else:
    import fcntl

log_utils.init_modular_input_logging()
logger = logging.getLogger("sap_solman_mi")

MI_NAME = os.path.basename(__file__).split(".")[0]
LOCK_FILENAME = checkpoint_utils.get_filename(
    "sap_solman_mi", "sap_solman_mi://global.lock"
)
APP_NAME = "sap_solman_app"

CHECKPOINT_TIMESTAMPS_COUNT = 4
CHECKPOINT_FORMAT = "_v2"

DEFAULT_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
KV_FIELDS = set(
    [
        six.u("SystemId"),
        six.u("SystemName"),
        six.u("MetricName"),
        six.u("Enabled"),
        six.u("EventName"),
        six.u("CalcTimeFrame"),
        six.u("Category"),
        six.u("Direction"),
        six.u("Greentored"),
        six.u("Greentoyellow"),
        six.u("MetricDatatype"),
        six.u("MoType"),
        six.u("ObjectType"),
        six.u("Period"),
        six.u("PeriodUnit"),
        six.u("Rating"),
        six.u("Redtoyellow"),
        six.u("RuleClass"),
        six.u("RuleType"),
        six.u("Threshold"),
        six.u("Unit"),
        six.u("Watermark"),
        six.u("Yellowtogreen"),
        six.u("Yellowtored"),
    ]
)

def convert_to_unixtime(stime, time_format=DEFAULT_TIME_FORMAT):
    try:
        return calendar.timegm(
            datetime.datetime.strptime(six.text_type(stime), time_format).timetuple()
        )
    except Exception:
        return None


class ConfigurationError(Exception):
    """Exception for invalid modular input configuration."""


class SAPSolmanModularInput(Script):
    """Modular input to fetch SAP Solman AI_SYSMON_OVERVIEW_SRV data."""

    def get_scheme(self):
        """Generate schema for MI."""
        scheme = Scheme("SAP Solman input")
        scheme.description = (
            "Modular input to get SAP Solman AI_SYSMON_OVERVIEW_SRV data"
        )

        services_base = Argument("services_base")
        services_base.title = "Solman service base URL"
        services_base.data_type = Argument.data_type_string
        services_base.description = "E.g. https://foo.bar:123/sap/opu/odata/sap"
        services_base.required_on_create = True
        scheme.add_argument(services_base)

        userid = Argument("userid")
        userid.title = "Username"
        userid.data_type = Argument.data_type_string
        userid.description = "SAP username for authentication"
        userid.required_on_create = True
        scheme.add_argument(userid)

        password = Argument("password")
        password.title = "Password"
        password.data_type = Argument.data_type_string
        password.description = "SAP password for the given user"
        password.required_on_create = True
        scheme.add_argument(password)

        return scheme

    def validate_input(self, validation_definition):
        """Check user-provided params for the modular input."""
        params = validation_definition.parameters

        try:
            if params["password"] != password_utils.MASK:
                sap_connector = epmspln_odata2.client.OdataClient(
                    services_base=params["services_base"],
                    userid=params["userid"],
                    password=params["password"],
                )

                sap_connector.get_feed_collection_items(
                    "AI_SYSMON_OVERVIEW_SRV", "SystemListSet"
                )
        except Exception as e:
            raise ConfigurationError(
                "Error connecting to SAP ODATA endpoint at {} - {} {}".format(
                    params["services_base"], type(e).__name__, e
                )
            )

    def stream_events(self, inputs, event_writer):
        """Discover new metrics and stream events from SAP Solman.

        Metrics configuration is stored in odata_metrics KV store collection.
        This function reconciles KV store state with the actual Solman state.
        Method adds newly discovered SAP environments and metrics and updates
        existing ones. It does not delete the data from the KV store.

        Once reconciliation is complete, the method produces the actual events
        to be ingested as Splunk metrics data points.
        """

        session_key = self._input_definition.metadata["session_key"]

        management_endpoint = six.moves.urllib.parse.urlparse(
            self._input_definition.metadata["server_uri"]
        )

        service = connect(
            scheme=management_endpoint.scheme,
            host=management_endpoint.hostname,
            port=management_endpoint.port,
            token=session_key,
        )
        kv_service = connect(
            scheme=management_endpoint.scheme,
            host=management_endpoint.hostname,
            port=management_endpoint.port,
            token=session_key,
            owner="nobody",
            app=APP_NAME,
        )

        password_manager = password_utils.PasswordManager(service)

        odata_metrics_collection = kv_service.kvstore["odata_metrics"]
        kv_store_data_cache = odata_metrics_collection.data.query()

        if limitations.exceeds_limits(odata_metrics_collection):
            sys.exit(0)

        kv_store_data_by_system_metric = {}
        for item in kv_store_data_cache:
            key = (item["SystemId"], item["MetricName"])
            kv_store_data_by_system_metric[key] = item

        for input_name, input_item in six.iteritems(inputs.inputs):
            password = input_item["password"]
            solman_host = six.moves.urllib.parse.urlparse(
                input_item["services_base"]
            ).hostname
            user_pw_key = "{}@{}".format(input_item["userid"], solman_host)

            if password == password_utils.MASK:
                password = password_manager.get_password(user_pw_key)
            else:
                password_manager.encrypt_password(user_pw_key, password)
                password_manager.mask_password(input_item, input_name, "password")

            checkpoint_data = collections.defaultdict(lambda: [0])
            try:
                checkpoint_dict = checkpoint.read_checkpoint_data(kv_service, input_name)
                checkpoint_data.update(checkpoint_dict)
            except PermissionError as perms_exc:
                logger.exception("Permission denied - checkpoint file: {}".format(repr(perms_exc)))
            except FileNotFoundError  as nf_exc:
                logger.exception("Can't find checkpoint file : {}".format(repr(nf_exc)))
            except Exception as exc:
                logger.exception("Can't read checkpoint data: {}".format(repr(exc)))

            sap_connector = epmspln_odata2.client.OdataClient(
                services_base=input_item["services_base"],
                userid=input_item["userid"],
                password=password,
            )

            systems = sap_connector.get_feed_collection_items(
                "AI_SYSMON_OVERVIEW_SRV", "SystemListSet"
            )
            for _, system in systems:
                system_id = system["Contextid"]
                if not system_id:
                    # not fully configured systems, skip those
                    logger.debug("System {} is not fully configured in SAP SolMan and is skipped".format(system["Name"]))
                    continue
                try:
                    sap_events = list(
                        sap_connector.get_feed_collection_items(
                            "AI_SYSMON_OVERVIEW_SRV", "EventListSet", search=system_id
                        )
                    )
                except Exception as exc:
                    event_writer.log("ERROR", repr(exc))
                    logger.exception(repr(exc))
                    continue
                for _, sap_event in sap_events:
                    self.index_event(
                        event_writer,
                        sap_event,
                        system,
                        solman_host,
                        checkpoint_data,
                        odata_metrics_collection,
                        kv_store_data_by_system_metric,
                    )

            checkpoint.save_checkpoint_data(kv_service, checkpoint_data, input_name)
            
    @staticmethod
    def index_event(
        event_writer,
        sap_event,
        system,
        solman_host,
        checkpoint_data,
        odata_metrics_collection,
        kv_store_data_by_system_metric,
    ):
        if not sap_event["EventName"]:
            return
        sap_event["SystemId"] = system["Contextid"]
        sap_event["SystemName"] = system["Name"]
        sap_event["MetricName"] = re.sub(r"[^\w]", "_", sap_event["EventName"]).strip(
            "_"
        )
        sap_event["Enabled"] = "FALSE"
        unix_timestamp = convert_to_unixtime(
            sap_event["ValueTimestampMeasurement"]
        ) or convert_to_unixtime(sap_event["ValueTimestamp"])
        if not unix_timestamp:
            return
        checkpoint_key = "{} # {}".format(system["Name"], sap_event["EventName"])
        has_new_data = unix_timestamp > checkpoint_data[checkpoint_key][-1]
        logger.debug(
            'checkpoint_key="%s" new_data="%s" old_ts="%s" new_ts="%s"',
            checkpoint_key,
            has_new_data,
            checkpoint_data[checkpoint_key],
            unix_timestamp,
        )
        if has_new_data:
            checkpoint_data[checkpoint_key].append(unix_timestamp)
            checkpoint_data[checkpoint_key] = checkpoint_data[checkpoint_key][
                -CHECKPOINT_TIMESTAMPS_COUNT:
            ]
        else:
            return
        data = json.dumps(
            {
                "_time": unix_timestamp,
                "_value": sap_event["ValueLast"],
                "metric_name": sap_event["MetricName"],
                "system_name": system["Name"],
            }
        )
        event = Event(data=data, host=solman_host)
        # TODO(mtroianovskyi): add handling of Solman updating some of params
        key = (sap_event["SystemId"], sap_event["MetricName"])
        if key not in kv_store_data_by_system_metric:
            for field in list(sap_event.keys()):
                if field not in KV_FIELDS:
                    del sap_event[field]
            odata_metrics_collection.data.insert(json.dumps(sap_event))
        elif kv_store_data_by_system_metric[key]["Enabled"] == "TRUE":
            event_writer.write_event(event)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--scheme":
        sys.exit(SAPSolmanModularInput().run(sys.argv))
    else:
        with open(LOCK_FILENAME, "w") as lock_file:
            try:
                if platform.system() == "Windows":
                    # https://docs.python.org/2/library/msvcrt.html
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 10)
                else:
                    fcntl.lockf(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError:
                # modinput instance is already running
                logger.info("Another instance of this modular input is already running. Exiting.")
                sys.exit(0)

            sys.exit(SAPSolmanModularInput().run(sys.argv))
