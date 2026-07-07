import itertools
import json
import logging as logger
import math
import os
import sys
import time
import urllib
from datetime import datetime, date

import code42_util
import py42.settings
import py42.util
from Utilities import KennyLoggins, Utilities
from code42_batch_processor import Code42BatchDataProcessor, SplunkSecurityEventFetcherHandlers
from code42_mod_input import Code42ForSplunkModularInput
from py42.sdk import SDK
from py42.sdk.util.queued_logger import QueuedLogger
import version

_SECONDS_IN_A_DAY = 86400
_DEFAULT_DAYS_TO_LOOK_BACK = 60
_MIN_DAYS_TO_CHECK_FOR_NEW_RESTORES = 1

__author__ = 'ksmith'

_MI_APP_NAME = 'Code42 App For Splunk Modular Input'
_APP_NAME = 'IA-Code42ForSplunk'


class Code42ForSplunk(object):

    def __init__(self, modular_input_log, rest_log, modular_input, utils, proxy_loader):
        self.modular_input_log = modular_input_log
        self.rest_log = rest_log
        self.modular_input = modular_input
        self.utils = utils
        self.proxy_loader = proxy_loader

    def initialize_sdk(self):
        self.modular_input_log.info("action=start object=runinitialize_and_build_sdk_client")
        self.modular_input_log.info("action=start object=modular_input")
        try:
            self.modular_input_log.debug("action=setup utilities instantiated")
            report_user = self.modular_input.get_config("report_user")
            report_pwd = self.utils.get_credential(self.modular_input.get_config("credential_realm"), urllib.quote(report_user))

            if report_pwd is None or report_pwd == "none":
                self.modular_input_log.error(
                    "action=failure stanza={} message=\"No credential found for user: {}\"".format(self.modular_input.get_config("name"), report_user))
                exit()
            else:
                self.modular_input_log.debug(
                    "action=debug_user Report user: {}, pwd_length: {}".format(report_user, len(report_pwd)))

            code42_server_hostname = self.modular_input.get_config("hostname")
            _raise_if_hostname_value_invalid(code42_server_hostname)
            self.modular_input.host(code42_server_hostname)

            use_http = code42_util.parse_boolean(self.modular_input.get_config("use_http"))
            self._raise_if_use_http_value_invalid(use_http)

            code42_host_address = _add_url_scheme(code42_server_hostname, use_http)

            self.modular_input.source(self.modular_input.get_config("name"))
            verify_ssl = self.modular_input.get_config("ssl_verify")
            vss = True
            if verify_ssl is None:
                vss = True
            elif verify_ssl == "0" or verify_ssl.lower() == "false":
                vss = False

            proxies = self.proxy_loader.load()
            py42.settings.proxies = proxies
            py42.settings.verify_ssl_certs = vss
            py42.settings.global_exception_message_receiver = self.handle_error
            py42.settings.set_user_agent_suffix(version.__version__)
            self.modular_input_log.info("Using URL {} to connect to Code42".format(code42_host_address))
            sdk = SDK.create_using_local_account(
                code42_host_address, urllib.unquote(report_user), report_pwd, is_async=True)
            return sdk
        except Exception as e:
            self.modular_input_log.error("Could not initialize SDK client. Cause: " + repr(e))
            raise e

    def _raise_if_use_http_value_invalid(self, use_http):
        if self.utils.is_cloud() and use_http:
            raise Exception("Splunk Cloud requires using https.")

    def handle_error(self, exception_trace):
        self.modular_input.log.error("An exception occurred while running the code42 modular input. Details:" + exception_trace)

    def handle_generic_response(self, response, data_key, sourcetype):
        items_list = py42.util.get_obj_from_response(response, data_key)
        if not isinstance(items_list, list):
            items_list = [items_list]
        self.modular_input.print_multiple_events_of_sourcetype("code42:" + sourcetype, items_list)

    def handle_checkpoint_data_response(self, response, report_name, data_key, id_property, checkpoint):
        try:
            use_kvstore = False
            if self.modular_input.get_config("use_mi_kvstore") == "true":
                use_kvstore = True
                self.modular_input_log.info("action=kvstore_usage message=using_kvstore_for_internal_ids")
            self.modular_input_log.debug("checkpoint for endpoint={} is {}".format(report_name, checkpoint))
            events = py42.util.get_obj_from_response(response, data_key)
            # Some endpoints support sequential numbering. If they do, use compress/decompress routines
            use_compress = False
            if id_property not in checkpoint:
                checkpoint[id_property] = []
            internal_checkpoint_ids = checkpoint[id_property]
            if report_name == "alertlog":
                use_compress = True
            if events is None:
                events = []
            self.modular_input_log.info("action=retrieve_events endpoint={} result_length={}".format(report_name, len(events)))
            self.modular_input_log.info("action=found_checkpoints_ids checkpoint={} items={}".format(checkpoint, internal_checkpoint_ids))

            if use_kvstore:
                search_query = {"checkpoint_name": report_name}
                found_data_ids = [x[id_property] for x in events]
                if len(found_data_ids) > 0:
                    search_query["$or"] = [{"internal_id": x} for x in found_data_ids]
                internal_checkpoint_ids = [x["internal_id"] for x in self.utils.get_kvstore_data("mi_code42",
                                                                                            json.dumps(
                                                                                                search_query))]
                self.modular_input_log.info("action=got_kvstore_items items={}".format(len(internal_checkpoint_ids)))

            if use_compress:
                self.modular_input_log.info("action=found_checkpoint_ids report_name={} id_used={} result_length={} output={}".format(
                                                                                        report_name,
                                                                                        id_property,
                                                                                        len(internal_checkpoint_ids), internal_checkpoint_ids ))
                internal_checkpoint_ids = self.modular_input.decompress_ranges(internal_checkpoint_ids)

            events_not_found = [x for x in events if
                                    int("{}".format(x[id_property])) not in internal_checkpoint_ids]
            self.modular_input_log.info("len_events_not_found={}".format(len(events_not_found)))

            self.modular_input.print_multiple_events_of_sourcetype("code42:" + report_name, events_not_found, time_field="timestamp")
            not_found_ids = [int(x[id_property]) for x in events_not_found]

            if use_kvstore:
                def store_ids(iid):
                    self.modular_input_log.debug(
                        "storing id in kvstore={} mi_key={} number_of_items={}".format("mi_code42", report_name,
                                                                                       len(iid)))
                    self.utils.kvstore_batch_save("mi_code42",
                                             [{"checkpoint_name": report_name, "internal_id": x} for x in iid])
                    return iid

                not_found_ids = store_ids([x[id_property] for x in events_not_found])

            combined_ranges = [x for x in itertools.chain(not_found_ids, internal_checkpoint_ids)]

            if use_kvstore:
                checkpoint[id_property] = "stored_in_kvstore"
            else:
                if use_compress:
                    self.modular_input_log.info("combined_ranges={}".format(combined_ranges))
                    compressed = self.modular_input.compress_ranges(combined_ranges)
                else:
                    compressed = ["{}".format(x) for x in combined_ranges]
                checkpoint["last_time"] = int(math.ceil(time.mktime(datetime.now().timetuple())))
                checkpoint[id_property] = compressed
            self.modular_input._set_checkpoint(report_name, object=checkpoint)
            tc_events = [{"endpoint": report_name, "total_events": len(events_not_found)}]
            self.modular_input.print_multiple_events_of_sourcetype("code42:api", tc_events, time_field="now")
        except Exception as e:
            self.modular_input_log.error("Error occurred while handling response for " + report_name + ". Cause: " + repr(e))

    def run(self):
        sdk = self.initialize_sdk()
        report_ids = self.modular_input.get_config("data_keys")
        # "computer,org,user,security,alertlog,restore,diagnostic"
        reports = report_ids.split(",")
        if "," not in report_ids:
            reports = [report_ids]
        do_computer = "computer" in reports
        do_user = "user" in reports
        do_security = "security" in reports
        do_alertlog = "alertlog" in reports
        do_restore = "restore" in reports
        do_diagnostic = "diagnostic" in reports
        try:
            # split the report IDs into individual reports and run the reports
            self.modular_input_log.info("action=starting_modular_input reports={}".format(report_ids))
            self.modular_input_log.info("action=get_kvstore_status {}".format(self.utils.get_kvstore_status()))

            counter = 0
            while not self.utils.is_kvstore_ready():
                if counter > 11:
                    break
                counter = counter + 1
                self.modular_input_log.info("action=wait_for_kvstore counter={} status={}".format(counter, self.utils.get_kvstore_status()))
                time.sleep(5)

            # get non-checkpoint data. security events are "checkpoint", but this is handled by storing cursors in the
            # kvstore.
            if do_computer:
                self.modular_input_log.info("action=retrieve_computers status=starting")

                def handle_computers(computer_list):
                    self.modular_input.print_multiple_events_of_sourcetype("code42:computer", computer_list)
                    self.modular_input_log.info("action=retrieve_computers status=complete")

                sdk.devices.for_each_device(include_backup_usage=True, return_each_page=True, then=handle_computers)

            if do_diagnostic:
                self.modular_input_log.info("action=retrieve_diagnostics status=starting")

                def log_retrieve_diagnostics_as_complete(*args):
                    self.modular_input_log.info("action=retrieve_diagnostics status=complete")

                def handle_diagnostics(response):
                    self.handle_generic_response(response, "data", "diagnostic")
                    log_retrieve_diagnostics_as_complete()

                sdk.administration.get_diagnostics(then=handle_diagnostics, catch=log_retrieve_diagnostics_as_complete)

            # this does all the parallel requests across storage nodes in order to get a huge amount of data
            # as efficiently as possible. Note that both users and security events are handled by this.
            if do_user or do_security:
                self.modular_input_log.info("action=retrieve_users_and_security_events status=starting")
                custom_handler = self._create_splunk_security_event_fetcher_handlers()
                min_timestamp = self._calculate_min_timestamp_for_security_events()
                processor = self._create_batch_data_processor(sdk, min_timestamp, custom_handler, do_user, do_security)
                processor.start()
                stats = processor.get_stats()
                tc_events = [{"endpoint": "user", "total_events": stats["user_count"]},
                             {"endpoint": "security", "total_events": stats["event_count"]}]
                self.modular_input.print_multiple_events_of_sourcetype("code42:api", tc_events, time_field="now")
                self.modular_input_log.info("action=retrieve_users_and_security_events status=complete")

            # Get checkpoint data (alert logs and restore history):
            if do_alertlog:
                self.modular_input_log.info("action=retrieve_alert_logs status=starting")
                alert_checkpoint = self.modular_input._get_checkpoint("alertlog")
                if alert_checkpoint is None:
                    alert_checkpoint = {}
                if "last_time" not in alert_checkpoint:
                    alert_checkpoint["last_time"] = 0

                def log_retrieve_alertlogs_as_complete(*args):
                    self.modular_input_log.info("action=retrieve_alert_logs status=complete")

                def handle_alert_logs(response):
                    self.handle_checkpoint_data_response(response, "alertlog", "log", "id", alert_checkpoint)
                    log_retrieve_alertlogs_as_complete()

                sdk.administration.get_alert_log(
                    page_size=999999, then=handle_alert_logs, catch=log_retrieve_alertlogs_as_complete)

            if do_restore:
                self.modular_input_log.info("action=retrieve_restores status=starting")
                restore_checkpoint = self.modular_input._get_checkpoint("restore")
                if restore_checkpoint is None:
                    restore_checkpoint = {}
                if "last_time" not in restore_checkpoint:
                    restore_checkpoint["last_time"] = 0

                def handle_restores(response):
                    self.handle_checkpoint_data_response(response, "restore", "restoreEvents", "restoreId",
                                                         restore_checkpoint)
                    self.modular_input_log.info("action=retrieve_restores status=complete")

                def get_restore_history(org_response, num_days):
                    org_id = py42.util.get_obj_from_response(org_response, "data")["orgId"]
                    sdk.archive.get_restore_history(num_days, org_id=org_id, page_size=999999, then=handle_restores)

                days = self._get_days_to_look_back()
                if restore_checkpoint["last_time"]:
                    last_time = date.fromtimestamp(restore_checkpoint["last_time"])
                    diff = date.today() - last_time
                    days = abs(diff.days)

                if days >= _MIN_DAYS_TO_CHECK_FOR_NEW_RESTORES:
                    sdk.orgs.get_current_user_org(then=lambda (response): get_restore_history(response, days))
                else:
                    self.modular_input_log.info("skipping retrieval of new restores because it has not been at least {} day(s)"
                                                .format(_MIN_DAYS_TO_CHECK_FOR_NEW_RESTORES))
                    self.modular_input_log.info("action=retrieve_restores status=complete")

            sdk.wait()

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            myJson = "message=\"{}\" exception_type=\"{}\" exception_arguments=\"{}\" filename=\"{}\"" \
                     " execution_line_number=\"{}\" input=\"{}\"".format(
                      str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, self.modular_input.get_config("name"))
            self.modular_input_log.error("{}".format(myJson))
        finally:
            self.modular_input_log.info("action=ending_modular_input")
            self.modular_input_log.info("action=stop object=modular_input")
            self.modular_input.stop()
            self.modular_input_log.debug("stopped mod input")

            self.rest_log.wait()
            self.modular_input_log.wait()

    def _calculate_min_timestamp_for_security_events(self):
        return code42_util.get_current_timestamp_in_seconds() - (_SECONDS_IN_A_DAY * self._get_days_to_look_back())

    def _get_days_to_look_back(self):
        days_to_look_back = _DEFAULT_DAYS_TO_LOOK_BACK
        historical_lookback_config_value = self.modular_input.get_config("historical_lookback")
        # If we upgraded, and the flag is not set, just ignore and set default.
        if historical_lookback_config_value is not None:
            days_to_look_back = int(historical_lookback_config_value)
        return days_to_look_back

    def _create_splunk_security_event_fetcher_handlers(self):
        return SplunkSecurityEventFetcherHandlers(self.modular_input_log, self.utils,
                                                  self.modular_input.print_multiple_events_of_sourcetype, KennyLoggins)

    def _create_batch_data_processor(self, sdk, min_timestamp, custom_handler, do_user, do_security):
        return Code42BatchDataProcessor(sdk, min_timestamp, custom_handler,
                                        self.modular_input.print_multiple_events_of_sourcetype, do_user, do_security)


class ProxyLoader(object):

    def __init__(self, proxy_name, utils, modular_input_log, rest_log):
        self.proxy_name = proxy_name
        self.utils = utils
        self.modular_input_log = modular_input_log
        self.rest_log = rest_log

    def load(self):
        proxy = None
        if self.proxy_name is not None and self.proxy_name != "not_configured" and self.proxy_name is not "none":
            proxy_config = self.utils.get_proxy_configuration(self.proxy_name)
            self.rest_log.debug("component=proxy found proxy configuration")
            self.modular_input_log.info("component=proxy found proxy configuration {0}".format(proxy_config))
            pconfig = proxy_config

            if "host" not in pconfig or "port" not in pconfig:
                self.rest_log.error(
                    "component=proxy action=get_proxy_config status=failed step='host_or_port'")
                raise AttributeError("Failed to find Hostname or Port in Configuration Object")
            protocol = "http"
            if "protocol" in pconfig:
                protocol = pconfig["protocol"]
            authentication = ""
            hostname = pconfig["host"]
            proxyport = pconfig["port"]
            self.rest_log.debug("component=proxy set hostname={0} and port={1} in proxy configuration".format(hostname,
                                                                                                              proxyport))
            if "authentication" in pconfig:
                self.rest_log.debug("component=proxy found authentication settings")
                authconfig = pconfig["authentication"]
                if "username" not in authconfig or "password" not in authconfig:
                    self.rest_log.error("component=proxy action=get_proxy_authentication_config status=failed")
                authentication = "{0}:{1}@".format(authconfig["username"], authconfig["password"])
            proxy = {"http": "{0}://{1}{2}:{3}/".format(protocol, authentication, hostname, proxyport),
                     "https": "{0}://{1}{2}:{3}/".format(protocol, authentication, hostname, proxyport)}
        return proxy


def _raise_if_hostname_value_invalid(hostname):
    if hostname is None:
        raise Exception("Hostname is None, and is not configured.")
    if hostname.startswith("http://") or hostname.startswith("https://"):
        message = "Hostname cannot start with 'http://' or 'https://'. Expected format: <hostname>:<port>. " + \
                  "Actual value: {}. ".format(hostname) + \
                  "Set 'use_http = true' in inputs.conf to force HTTP instead of HTTPS."
        raise Exception(message)


def _add_url_scheme(hostname_and_port, use_http=False):
    if use_http:
        scheme = "http"
    else:
        scheme = "https"
    return "{0}://{1}".format(scheme, hostname_and_port)


if __name__ == '__main__':

    _mi_log = KennyLoggins().get_logger(_APP_NAME, "modularinput", logger.INFO)
    _rest_log = KennyLoggins().get_logger(_APP_NAME, "restclient", logger.INFO)
    rest_qlog = QueuedLogger(logger=_rest_log)
    mi_qlog = QueuedLogger(logger=_mi_log)

    mi_qlog.debug("logging setup complete")

    modular_input = Code42ForSplunkModularInput(mi_qlog, app_name=_APP_NAME, scheme={
        "title": "Code42 App For Splunk",
        "description": "Code42 Modular Input",
        "args": [
            {"name": "hostname",
             "description": "The Code42 server to connect with. Include port.",
             "title": "Hostname",
             "required": True
             },
            {"name": "data_keys",
             "description": "The data keys to pull from the API.",
             "title": "Data Keys",
             "required": True},
            {"name": "report_user",
             "description": "Username for running reports",
             "title": "Username"
             },
            {"name": "proxy_name",
             "description": "The stanza name for a configured proxy.",
             "title": "Proxy Name"
             },
            {"name": "credential_realm",
             "description": "Stanza Name to use for credentials",
             "title": "Credential Realm"},
            {"name": "use_mi_kvstore",
             "description": "Should the checkpoint use KVStore? ADVANCED NEED ONLY",
             "title": "Use KVStore for Checkpoints"},
            {"name": "historical_lookback",
             "description": "Defaults to 60. Number is in days, and is controls how far back to pull the information.",
             "title": "Consume data from these days in the past"},
            {"name": "ssl_verify", "description": "Support Only", "title": "SSL Verify"},
            {"name": "use_http", "description": "Use HTTP (not HTTPS) when connecting to Code42. Not supported in Splunk Cloud. Default: False", "title": "Use HTTP"}
        ]
    })

    mi_qlog.info("action=instantiated object=modular_input")

    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            modular_input.scheme()
        elif sys.argv[1] == "--validate-arguments":
            modular_input.validate_arguments()
        elif sys.argv[1] == "--test":
            print 'No tests for the scheme present'
        else:
            print 'You giveth weird arguments'
    else:
        modular_input.start()
        utils = Utilities(app_name=_APP_NAME, session_key=modular_input.get_config("session_key"))
        proxy_loader = ProxyLoader(modular_input.get_config("proxy_name"), utils, mi_qlog, rest_qlog)
        Code42ForSplunk(mi_qlog, rest_qlog, modular_input, utils, proxy_loader).run()

    sys.exit(0)
