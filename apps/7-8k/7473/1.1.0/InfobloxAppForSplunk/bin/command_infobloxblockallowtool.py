import import_declare_test
import sys
import time
import traceback
import json
from infoblox_helpers.logger_manager import setup_logging
from infoblox_helpers.conf_helper import get_credentials
from infoblox_helpers.rest_helper import RestHelper
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option


logger = setup_logging("ta_infoblox_block_allow_tool_custom_command")


@Configuration()
class InfoBloxBlockAllowTool(GeneratingCommand):
    """Infoblox Named List custom command."""

    account_name = Option(name="account_name", require=True)
    action = Option(name="action", require=True)
    named_list = Option(name="named_list", require=True)
    value = Option(name="value", require=True)
    description = Option(name="description", require=False)

    def validate(self):
        """Validate method."""
        if self.action not in ("allow", "block"):
            logger.info("message=command_error | Infoblox Error : Given Action parameter is not valid.")
            raise Exception("Given Action parameter is not valid.")
        if self.value.strip() == "":
            logger.error("message=command_error | Infoblox Error : Given Value parameter is empty.")
            raise Exception("Given Value parameter is empty.")
        if self.named_list.strip() == "":
            logger.error("message=command_error | Infoblox Error : Given Named List parameter is empty.")
            raise Exception("Given Named List parameter is empty.")
        if len(self.description) > 256:
            logger.error(
                "message=command_error | Infoblox Error : The length of Description parameter should"
                " not exceed 256 characters."
            )
            raise Exception("The length of Description parameter should not exceed 256 characters.")

    def generate(self):
        """Generate method."""
        try:
            logger.info("message=command_start_execution | Infoblox Info : Started Custom Command Script Execution.")
            start_time = time.time()
            session_key = self._metadata.searchinfo.session_key
            logger.info(
                f'message=command_start_execution | Infoblox Info : Provided params are'
                f' named_list: {self.named_list} action: {self.action} value: {self.value}'
                f' description: {self.description} account_name: {self.account_name}.'
            )
            self.validate()
            account_info = get_credentials(self.account_name, session_key)

            infoblox_config = {
                "session_key": session_key
            }
            infoblox_config.update(account_info)

            rest_helper_obj = RestHelper(infoblox_config, logger)

            if self.action == "allow":
                tool_key = "inserted_items_described"
            else:
                tool_key = "deleted_items_described"

            payload = {
                tool_key: [
                    {
                        "description": self.description,
                        "item": self.value
                    }
                ]
            }
            data = rest_helper_obj.patch_block_allow_tool(self.named_list, json.dumps(payload, ensure_ascii=False))

            logger.info("message=command_info | Infoblox Info : Json Data Retrived.")

            yield {
                "_raw": json.dumps(data, ensure_ascii=False),
                "_time": time.time()
            }
        except Exception:
            logger.error(
                "message=unknown_error | Unknown error occured: {}".format(
                    traceback.format_exc()
                )
            )
            self.write_error(
                "Insufficient permissions to run custom commands or unexpected error."
                " Please see ta_infoblox_block_allow_tool_custom_command.log file for more information."
            )
            exit(0)
        finally:
            logger.info(
                'message=command_end_execution | End of the "{}" command execution.'
                " Total time taken: elapsed_seconds={:.3f}".format(
                    self.name, time.time() - start_time
                )
            )


dispatch(InfoBloxBlockAllowTool, sys.argv, sys.stdin, sys.stdout, __name__)
