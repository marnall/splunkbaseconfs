import import_declare_test
import sys
import time
import traceback
from datetime import datetime
from infoblox_helpers.kvstore import CollectionManager
from infoblox_helpers.logger_manager import setup_logging
from infoblox_helpers.conf_helper import get_credentials
from infoblox_helpers.rest_helper import RestHelper
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option


logger = setup_logging("ta_infoblox_tide_lookup_custom_command")


@Configuration()
class InfoBloxTideLookup(GeneratingCommand):
    """Infoblox Tide Lookup custom command."""

    insight_type = Option(name="type", require=True)
    value = Option(name="value", require=True)
    account_name = Option(name="account_name", require=True)

    def validate(self):
        """Validate method."""
        if self.insight_type not in ("host", "ip", "url", "email", "hash"):
            logger.info("message=command_error | Infoblox Error : Given Type parameter is not valid.")
            raise Exception("Given Type parameter is not valid.")
        if self.value.strip() == "":
            logger.error("message=command_error | Infoblox Error : Given Value parameter is empty.")
            raise Exception("Given Value parameter is empty.")

    def generate(self):
        """Generate method."""
        try:
            logger.info("message=command_start_execution | Infoblox Info : Started Custom Command Script Execution.")
            start_time = time.time()
            session_key = self._metadata.searchinfo.session_key
            logger.info(
                f'message=command_start_execution | Infoblox Info : Provided params are'
                f' type: {self.insight_type} and value: {self.value} account_name: {self.account_name}.'
            )
            self.validate()
            tide_lookup = CollectionManager(
                "infoblox_tide",
                service=self.service,
                session_key=session_key,
            )
            kv_values = tide_lookup.get(query={"$or": [{self.insight_type: self.value}]})
            if kv_values:
                logger.info(
                    f'message=command_kv_values_found | Value {self.value} is found'
                    f' in the KV store with total events: {len(kv_values)}.'
                )
                for event in kv_values:
                    yield {
                        "_raw": event,
                        "_time": event.get("detected", time.time())
                    }
            else:
                logger.info(f'message=command_kv_values_not_found | Value {self.value} is not found in the KV store.')
                account_info = get_credentials(self.account_name, session_key)
                infoblox_config = {
                    "session_key": session_key
                }
                infoblox_config.update(account_info)

                rest_helper_obj = RestHelper(infoblox_config, logger)
                params = {
                    "type": self.insight_type,
                    self.insight_type: self.value
                }

                data = rest_helper_obj.get_tide_lookup(params)

                logger.info("message=command_info | Infoblox Info : Json Data Retrived.")

                events = data.get("threat", [])
                time_stamp = datetime.now().isoformat()
                for event in events:
                    notes = event.get("extended", {}).get("notes", "-")
                    event["notes"] = notes
                    event["timestamp"] = time_stamp
                kv_upsert_start_time = time.time()
                tide_lookup.upsert(events)
                logger.info(
                    f'message=command_kv_write | Total events ingested in KV store'
                    f' for value {self.value} : {len(events)} and total time taken:'
                    f' elapsed_seconds={time.time() - kv_upsert_start_time}.'
                )

                for event in events:
                    yield {
                        "_raw": event,
                        "_time": event.get("detected", time.time())
                    }
        except Exception:
            logger.error(
                "message=unknown_error | Unknown error occured: {}".format(
                    traceback.format_exc()
                )
            )
            self.write_error(
                "Insufficient permissions to run custom commands or unexpected error."
                " Please see ta_infoblox_tide_lookup_custom_command.log file for more information."
            )
            exit(0)
        finally:
            logger.info(
                'message=command_end_execution | End of the "{}" command execution.'
                " Total time taken: elapsed_seconds={:.3f}".format(
                    self.name, time.time() - start_time
                )
            )


dispatch(InfoBloxTideLookup, sys.argv, sys.stdin, sys.stdout, __name__)
