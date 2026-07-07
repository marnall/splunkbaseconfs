import re
import sys
import time

import splunk.rest as rest
from splunk import RESTException
from splunklib.searchcommands import Configuration, GeneratingCommand, Option, dispatch

ALLOWED_CRON_TYPES = [
    "cron_schedule",
    "run_every_hour",
    "run_every_day",
    "run_every_week",
    "run_every_month",
]
ALERT_NAME_PREFIX = "Critical IPs Alert || "
BASE_SEARCH = "`cisco_sdwan_index` {search_str} | stats count | search count > {threshold}"
ALERT_DESCRIPTION = "The Splunk alert for '$name$' was triggered for IPs/CIDR '{ip_cidr}'"
IP_REGEX = r"^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}$"
IP_SEARCH_STR = '| where in(src_ip,"{ip_list}") OR in(dest_ip,"{ip_list}")'
CIDR_SEARCH_STR = '| where cidrmatch("{cidr}", src_ip) OR cidrmatch("{cidr}", dest_ip)'


def is_int(value: any):
    """Checks whether values is a integer value or not.

    :param: a value to check
    :returns: `True` if value is integer else `False`
    """
    try:
        int(str(value))
        return True
    except ValueError:
        return False


@Configuration(type="events")
class MonitorCriticalIPs(GeneratingCommand):
    """Custom Command to create Monitor Critical IPs alert."""

    # Custom command parameters
    alert_name = Option(require=True)
    alert_description = Option(require=True)
    threshold = Option(require=True)
    cron_type = Option(require=True)
    earliest = Option(require=False)
    latest = Option(require=False)
    at_min = Option(require=False)
    at_hour = Option(require=False)
    at_day = Option(require=False)
    at_date = Option(require=False)
    cron_schedule = Option(require=False)
    email = Option(require=True)
    ip_cidr = Option(require=True)

    conf_payload = {
        "name": "",
        "description": "",
        "search": "",
        "cron_schedule": "0 * * * *",
        "dispatch.earliest_time": "-1h",
        "dispatch.latest_time": "now",
        "is_scheduled": 1,
        "alert_comparator": "greater than",
        "alert_threshold": 0,
        "alert_type": "number of events",
        "actions": "email",
        "action.email": True,
        "action.email.subject": "Splunk Alert: $name$",
        "action.email.message.alert": "",
        "action.email.to": "abc@example.com",
        "action.email.allow_empty_attachment": 0,
        "action.email.include.results_link": 1,
        "action.email.include.trigger_time": 1,
        "action.email.include.view_link": 1,
        "alert.expires": "30d",
    }

    def parse_ip_cidr(self):
        """Parses IP address list or CIDR address."""
        error_msg = None
        search_str = None

        if "," in self.ip_cidr:
            ip_list = [ip.strip() for ip in self.ip_cidr.split(",")]
            for ip in ip_list:
                if not re.search(IP_REGEX, ip):
                    error_msg = f"Invalid IP address '{ip}' in the list."
                    break
            else:
                search_str = IP_SEARCH_STR.format(ip_list='","'.join(ip_list))
        elif "/" in self.ip_cidr:
            try:
                mask, cidr_len = [x.strip() for x in self.ip_cidr.split("/")]
                if not re.search(IP_REGEX, mask) or not (int(cidr_len) >= 1 and int(cidr_len) <= 32):
                    raise ValueError
                search_str = CIDR_SEARCH_STR.format(cidr="/".join([mask, cidr_len]))
            except ValueError:
                error_msg = f"Invalid CIDR address '{self.ip_cidr}'."
        elif re.search(IP_REGEX, self.ip_cidr):
            search_str = IP_SEARCH_STR.format(ip_list=self.ip_cidr)
        else:
            error_msg = "Not a valid IP address, IP list or CIDR address."

        self.conf_payload["search"] = BASE_SEARCH.format(search_str=search_str, threshold=self.threshold)
        return error_msg

    def validate_configurations(self):
        """Validates configurations.

        :returns: error messages if there is validation error else `None`
        """
        error_msg = None
        self.alert_name = self.alert_name.strip()
        self.alert_description = self.alert_description.strip()
        self.email = self.email.strip()
        self.threshold = self.threshold.strip()
        self.ip_cidr = self.ip_cidr.strip(" ,")

        # cron_type validation
        if self.cron_type not in ALLOWED_CRON_TYPES:
            error_msg = f"Invalid 'cron_type' provided. Allowed values are {ALLOWED_CRON_TYPES}"
        elif self.cron_type == "cron_schedule" and not self.cron_schedule:
            error_msg = "Required field 'cron_schedule' not provided."
        elif self.cron_type == "run_every_hour" and not self.at_min:
            error_msg = "Required field 'at_min' not provided."
        elif self.cron_type == "run_every_day" and not self.at_hour:
            error_msg = "Required field 'at_hour' not provided."
        elif self.cron_type == "run_every_week" and (not self.at_hour or not self.at_day):
            error_msg = "One or more of the required fields (at_hour and at_day) not provided."
        elif self.cron_type == "run_every_month" and (not self.at_hour or not self.at_date):
            error_msg = "One or more of the required fields (at_hour and at_date) not provided."

        # Required fields
        elif not self.alert_name:
            error_msg = "'Alert Name' must not be empty."
        elif not self.email:
            error_msg = "'Send Email to' must not be empty."
        elif not self.threshold:
            error_msg = "''Event Threshold' must not be empty."
        elif not self.ip_cidr:
            error_msg = "'IPs/CIDR to Monitor' must not be empty."

        # Positive integer validation
        elif not is_int(self.threshold):
            error_msg = "Only positive integer value is allowed in 'Event Threshold'."
        elif int(self.threshold) < 0:
            error_msg = "Value of 'Event Threshold' should be greater than or equal to zero."

        return error_msg

    def set_configurations(self):
        """Sets configuration to create saved search via Splunk rest."""
        self.conf_payload["name"] = ALERT_NAME_PREFIX + self.alert_name
        self.conf_payload["description"] = self.alert_description
        self.conf_payload["action.email.to"] = self.email
        self.conf_payload["action.email.message.alert"] = ALERT_DESCRIPTION.format(ip_cidr=self.ip_cidr)

        if self.cron_type == "cron_schedule":
            self.conf_payload["dispatch.earliest_time"] = self.earliest
            self.conf_payload["dispatch.latest_time"] = self.latest
            self.conf_payload["cron_schedule"] = self.cron_schedule
        elif self.cron_type == "run_every_hour":
            self.conf_payload["dispatch.earliest_time"] = "-1h"
            self.conf_payload["cron_schedule"] = "{} * * * *".format(self.at_min)
        elif self.cron_type == "run_every_day":
            self.conf_payload["dispatch.earliest_time"] = "-1d"
            self.conf_payload["cron_schedule"] = "0 {} * * *".format(self.at_hour)
        elif self.cron_type == "run_every_week":
            self.conf_payload["dispatch.earliest_time"] = "-1w"
            self.conf_payload["cron_schedule"] = "0 {} * * {}".format(self.at_hour, self.at_day)
        elif self.cron_type == "run_every_month":
            self.conf_payload["dispatch.earliest_time"] = "-1mon"
            self.conf_payload["cron_schedule"] = "0 {} {} * *".format(self.at_hour, self.at_date)

    def create_saved_search(self):
        """Creates saved search with rest endpoint.

        :returns: dictionary of status message and status code from response received
        """
        try:
            endpoint = "/servicesNS/nobody/{}/saved/searches/".format(self.service.namespace.app)
            response, _ = rest.simpleRequest(
                endpoint,
                method="POST",
                sessionKey=self.service.token,
                postargs=self.conf_payload,
                raiseAllErrors=True,
            )
            self.write_warning(response.reason)
            return {
                "status_code": response.status,
                "message": response.reason,
            }
        except RESTException as ex:
            self.write_error(ex.get_extended_message_text())
            return {
                "status_code": ex.statusCode,
                "message": ex.get_extended_message_text(),
            }
        except Exception as ex:
            self.write_error(str(ex))
            return {"message": str(ex), "status_code": None}

    def write_error(self, message: str):
        """Overrides parent's write_error method.

        By default, write_error formats message with 'format' method
        of string class and there is no way to disable formatting of
        message. This raises a issue when string contains opening and
        closing curly braces which are part of the message.

        :message: error message to write on command's output
        """

        class CustomStr(str):
            def format(self) -> str:
                return self

        super().write_error(CustomStr(message))

    def generate(self):
        """Generating custom command."""
        # Validate alert configurations
        validation_error_msg = self.validate_configurations()
        ip_error_msg = self.parse_ip_cidr()
        if validation_error_msg or ip_error_msg:
            self.write_error(validation_error_msg or ip_error_msg)
            yield {"_raw": validation_error_msg or ip_error_msg, "_time": time.time()}
            return

        self.set_configurations()

        # Create saved search from the configurations after validation
        response = self.create_saved_search()

        yield {"_raw": response.get("message"), "_time": time.time()}


dispatch(MonitorCriticalIPs, sys.argv, sys.stdin, sys.stdout, __name__)
