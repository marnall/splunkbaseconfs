"""Module for custom Splunk search command to track new and remediated vulnerabilities."""
import import_declare_test    # noqa: F401
import sys
import time
import traceback
from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option
from log_helper import setup_logging

logger = setup_logging("xmcyber_vuln_difference_command")

REDIRECT_TO_LOG_FILE_MSG = "See {} for more details.".format(
    "xmcyber_vuln_difference_command.log"
)


@Configuration()
class XMCyberVulnDifferenceCommand(EventingCommand):
    """XMCyberVulnDifferenceCommand Class to track new and remediated vulnerabilities."""

    active_field = Option(name="active_field", require=True)
    prev_active_field = Option(name="prev_active_field", require=True)
    remediated_field = Option(name="remediated_field", require=True)
    prev_remediated_field = Option(name="prev_remediated_field", require=True)

    def _write_error(self, msg):
        """Log error message to Splunk UI from where this custom command was triggered."""
        self.write_error("{} {}".format(msg, REDIRECT_TO_LOG_FILE_MSG))
        exit(0)

    def transform(self, events):
        """Transform method to process vulnerability data."""
        try:
            logger.info("message=command_start_execution | Started Custom Command Script Execution.")

            start_time = time.time()

            for event in events:
                # Get current and previous vulnerabilities from the event
                active_vulns_raw = event.get(self.active_field, [])
                prev_active_vulns_raw = event.get(self.prev_active_field, [])
                remediated_vulns_raw = event.get(self.remediated_field, [])
                prev_remediated_vulns_raw = event.get(self.prev_remediated_field, [])

                # Convert to sets - handle both multivalue fields and strings
                active_vulns = self._convert_to_set(active_vulns_raw)
                prev_active_vulns = self._convert_to_set(prev_active_vulns_raw)
                remediated_vulns = self._convert_to_set(remediated_vulns_raw)
                prev_remediated_vulns = self._convert_to_set(prev_remediated_vulns_raw)

                # Calculate new and remediated vulnerabilities
                new_vulns = active_vulns - prev_active_vulns
                newly_remediated = remediated_vulns - prev_remediated_vulns

                event['new_vulnerabilities'] = len(new_vulns)
                event['remediated_vulnerabilities'] = len(newly_remediated)

                yield event

        except Exception as ex:
            logger.error(
                "message=unknown_error | Unknown error occurred: {}".format(
                    traceback.format_exc()
                )
            )
            self._write_error("Unknown Error: {}".format(ex))
        finally:
            if self._finished:
                logger.info(
                    'message=command_end_execution | End of the "{}" command execution.'
                    " Total time taken: elapsed_seconds={:.3f}".format(
                        self.name, time.time() - start_time
                    )
                )

    def _convert_to_set(self, value):
        """Convert various input types to a set."""
        if not value:
            return set()

        if isinstance(value, list):
            return {item for item in value if item}  # Filter out empty strings
        else:
            return set()


dispatch(XMCyberVulnDifferenceCommand, sys.argv, sys.stdin, sys.stdout, __name__)
