import import_declare_test
import sys
import time
import traceback
from infoblox_helpers.logger_manager import setup_logging
from infoblox_helpers.conf_helper import get_credentials
from infoblox_helpers.rest_helper import RestHelper
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option


logger = setup_logging("ta_infoblox_ipam_lookup_custom_command")


@Configuration()
class InfoBloxIPAMLookup(GeneratingCommand):
    """Infoblox IPAM Lookup custom command."""

    filter = Option(name="filter", require=True)
    account_name = Option(name="account_name", require=True)

    def validate(self):
        """Validate method."""
        if self.filter.strip() == 'address==""':
            logger.error("message=command_error | Infoblox Error : Given Filter parameter is empty.")
            raise Exception("Given Filter parameter is empty.")

    def generate(self):
        """Generate method."""
        try:
            logger.info("message=command_start_execution | Infoblox Info : Started Custom Command Script Execution.")
            start_time = time.time()
            session_key = self._metadata.searchinfo.session_key
            logger.info(
                f'message=command_start_execution | Infoblox Info : Provided params are'
                f' filter: {self.filter} account_name: {self.account_name}.'
            )
            self.validate()
            account_info = get_credentials(self.account_name, session_key)

            infoblox_config = {
                "session_key": session_key
            }
            infoblox_config.update(account_info)

            rest_helper_obj = RestHelper(infoblox_config, logger)
            params = {
                "_filter": self.filter
            }

            data = rest_helper_obj.get_ipam_lookup(params)

            logger.info("message=command_info | Infoblox Info : Json Data Retrived.")

            for event in data.get("results", []):
                if event.get("parent"):
                    data = rest_helper_obj.get_ipam_sub_details(event.get("parent"))
                    data = data.get("result", {})
                    logger.info("message=command_info | Infoblox Info : Json Data Retrived for Subnet.")
                    if data:
                        event["subnet_address"] = data.get("address", "") + "/" + str(data.get("cidr", ""))
                        event["subnet_name"] = data.get("name", "-")
                if event.get("space"):
                    data = rest_helper_obj.get_ipam_sub_details(event.get("space"))
                    data = data.get("result", {})
                    logger.info("message=command_info | Infoblox Info : Json Data Retrived for IP Space.")
                    if data:
                        event["space_name"] = data.get("name", "-")

                ipam_details = {
                    "address": event.get("address", "-"),
                    "host": event.get("host", "-"),
                    "comment": event.get("comment", "-"),
                    "space_name": event.get("space_name", "-"),
                    "subnet_name": event.get("subnet_name", "-"),
                    "subnet_address": event.get("subnet_address", "-"),
                    "tags": event.get("tags", {}),
                    "dhcp_info_client_hostname": "-",
                    "dhcp_info_client_hwaddr": "-",
                    "dhcp_info_fingerprint": "-"
                }
                dhcp_info = event.get("dhcp_info", {})
                if dhcp_info:
                    ipam_details["dhcp_info_client_hostname"] = dhcp_info.get("client_hostname", "-")
                    ipam_details["dhcp_info_client_hwaddr"] = dhcp_info.get("client_hwaddr", "-")
                    ipam_details["dhcp_info_fingerprint"] = dhcp_info.get("fingerprint", "-")
                yield {
                    "_raw": ipam_details
                }
        except Exception:
            logger.error(
                "message=unknown_error | Unknown error occured: {}".format(
                    traceback.format_exc()
                )
            )
            self.write_error(
                "Insufficient permissions to run custom commands or unexpected error."
                " Please see ta_infoblox_ipam_lookup_custom_command.log file for more information."
            )
            exit(0)
        finally:
            logger.info(
                'message=command_end_execution | End of the "{}" command execution.'
                " Total time taken: elapsed_seconds={:.3f}".format(
                    self.name, time.time() - start_time
                )
            )


dispatch(InfoBloxIPAMLookup, sys.argv, sys.stdin, sys.stdout, __name__)
