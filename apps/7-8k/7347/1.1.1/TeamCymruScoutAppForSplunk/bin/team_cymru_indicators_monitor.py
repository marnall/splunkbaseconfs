import import_declare_test  # isort: skip # noqa: F401
import sys
import time
import json
import six
from alert_actions_base import ModularAlertBase
from cymru_helpers.conf_helper import get_conf_file, get_credentials
from cymru_helpers.rest_helper import RestHelper
from cymru_helpers.event_ingestor import EventIngestor
from splunklib.modularinput.event_writer import EventWriter
from cymru_helpers.constants import DOMAIN_REGEX, IPV4_IPV6_REGEX
import re


class AlertActionIndicatorsMonitor(ModularAlertBase):
    """Alert Action."""

    def __init__(self, ta_name, alert_name):
        """Initialise Alert Action."""
        super(AlertActionIndicatorsMonitor, self).__init__(ta_name, alert_name)

    def validate_params(self):
        """Validate Params."""
        splunk_rest_host_info = get_conf_file(
            file="teamcymruscoutappforsplunk_settings",
            session_key=self.session_key,
            stanza="splunk_rest_host"
        )
        self.collection_type = splunk_rest_host_info.get("collection_type")
        if not self.get_param("field_name"):
            self.log_error("Field Name is a mandatory parameter, but its value is None.")
            return False
        else:
            if "," in self.get_param("field_name"):
                self.log_error("The Field Name field only supports a single value.")
                return False
        if not self.get_param("index"):
            if self.collection_type == "index":
                self.log_warn("Index is a mandatory parameter, but its value is None. Setting it's value to default.")
                self.configuration["index"] = "default"
            else:
                self.log_debug(
                    "Index field value is not required as Collection Type is set to Lookup.")
        if not self.get_param("global_account"):
            self.log_error("Team Cymru Scout Account is a mandatory parameter, but its value is None.")
            return False
        if not self.get_param("api_type"):
            self.log_error("API Type is a mandatory parameter, but its value is None.")
            return False
        return True

    def update_iocs(self, ioc):
        """Update IOCs."""
        if re.search(IPV4_IPV6_REGEX, ioc):
            self.set_ips.add(ioc)
        elif re.search(DOMAIN_REGEX, ioc):
            self.set_domains.add(ioc)
        else:
            self.not_matched_idicators.add(ioc)

    def update_ioc_value(self, set_ioc, ioc):
        """Update IOC Value."""
        if "\n" in ioc:
            ioc = ioc.split("\n")
            for item in ioc:
                set_ioc.add(item.strip())
        else:
            set_ioc.add(ioc.strip())

    def get_indicators_from_events(self):
        """Get set of indicators from the events."""
        self.set_ips = set()
        self.set_domains = set()
        self.not_matched_idicators = set()
        for event in self.get_events():
            ioc = event.get(self.field_name, "")
            set_ioc = set()
            if (
                isinstance(ioc, six.string_types)
                and ioc.strip()
                and ioc != ""
            ):
                self.update_ioc_value(set_ioc, ioc)
            elif isinstance(ioc, (list, tuple, set)):
                for item in ioc:
                    if (
                        isinstance(item, six.string_types)
                        and item.strip()
                        and item != ""
                    ):
                        set_ioc.add(item.strip())

            for ioc in set_ioc:
                self.update_iocs(ioc)
        self.log_debug(f'Matched IPs from events are: {self.set_ips}')
        self.log_debug(f'Matched Domains from events are: {self.set_domains}')
        self.log_debug(f'Unmatched indicators from events are: {self.not_matched_idicators}')

    def process_event(self, *args, **kwargs):
        """Process events."""
        status = 0
        start_time = time.time()
        try:
            if not self.validate_params():
                return 3
            self.field_name = self.get_param('field_name')
            self.global_account = self.get_param('global_account')
            self.index = self.get_param('index')
            self.api_type = self.get_param('api_type')
            self.log_info("Alert action team_cymru_indicators_monitor started.")
            self.log_debug((
                f'action=parameter_received field_name={self.field_name} '
                f'global_account={self.global_account} index={self.index} api_type={self.api_type}'))
            self.get_indicators_from_events()

            cymru_config = {
                "session_key": self.session_key,
                "api_type": self.api_type,
                "index": self.index
            }
            account_info = get_credentials(
                session_key=self.session_key,
                account_name=self.global_account
            )
            cymru_config.update(account_info)
            ip_event_count = 0
            if self.set_ips:
                cymru_config.update({"indicator_type": "ip"})
                cymru_config.update({"indicators": ",".join([str(x) for x in self.set_ips])})
                cymru_rest_helper = RestHelper(cymru_config, self._logger)
                indicator_datas = cymru_rest_helper.get_data()

                event_ingestor = EventIngestor(cymru_config, self, self._logger, is_alert=True)
                ip_event_count = event_ingestor.ingest(indicator_datas)
                self.log_info(f'Total events ingested for IPs indicator are: {ip_event_count}')

            domain_event_count = 0
            self.events = []
            if self.set_domains:
                if self.api_type == "foundation":
                    self.log_warn("Data collection for Domain Foundation is not supported. Skipping.")
                else:
                    cymru_config.update({"indicator_type": "domain"})
                    cymru_config.update({"indicators": ",".join([str(x) for x in self.set_domains])})
                    cymru_rest_helper = RestHelper(cymru_config, self._logger)
                    indicator_datas = cymru_rest_helper.get_data()

                    event_ingestor = EventIngestor(cymru_config, self, self._logger, is_alert=True)
                    domain_event_count = event_ingestor.ingest(indicator_datas)
                    self.log_info(f'Total events ingested for Domains indicator are: {domain_event_count}')

            total_time_taken = time.time() - start_time
            self.log_info("Total events ingested in Splunk are {}".format(
                ip_event_count + domain_event_count))
            self.log_info("Alert Action completed and total time taken: {}".format(total_time_taken))
            return 0
        except (AttributeError, TypeError) as ae:
            self.log_error(
                "Error: {}. Double check spelling and also verify that a compatible version of "
                "Splunk_SA_CIM is installed.".format(str(ae))
            )
            return 4
        except Exception as e:
            msg = "Unexpected error: {}."
            if str(e):
                self.log_error(msg.format(str(e)))
            else:
                import traceback
                self.log_error(msg.format(traceback.format_exc()))
            return 5
        return status


if __name__ == "__main__":
    exitcode = AlertActionIndicatorsMonitor("TeamCymruScoutAppForSplunk", "team_cymru_indicators_monitor").run(sys.argv)
    sys.exit(exitcode)
