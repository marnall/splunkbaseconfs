"""Modular input for Catalyst Center Audit logs."""

import import_declare_test  # noqa: F401

import json
import sys
import time

import cisco_dnac_api as api
import consts
import logger_manager
from splunklib import modularinput as smi
import utils


def get_epoch_current_time():
    """
    Return the epoch time for the {timestamp}.

    :return: epoch time including msec
    """
    epoch = time.time() * 1000

    return "{0}".format(int(epoch))


def get_start_time(interval):
    """
    Return the epoch time for the {timestamp}.

    :return: epoch time including msec
    """
    interval = int(interval)
    epoch = (time.time() - interval) * 1000

    return "{0}".format(int(epoch))


def get_audit_logs_details(
    catalystc, logger, input_start_date
):
    """Get Audit logs details from Catalyst Center host.

    :param catalystc: Catalyst Center API object.
    :param logger: Logger object.
    :param input_start_date: Start date provided in the input page.
    """
    start_time = input_start_date
    end_time = get_epoch_current_time()

    offset = 0
    limit = consts.AUDIT_LOGS_LIMIT
    events_count = 0
    logger.info(
        f"Data collection would be performed from start_time: {start_time}, end_time: {end_time} from offset: {offset}."
    )
    additional_query_params = {"sortBy": "timestamp", "order": "asc"}

    while True:
        try:
            logger.debug(
                "Making an API call to collect the audit logs for offset %d with limit %d.",
                offset,
                limit,
            )
            response = catalystc.audit_logs.get_audit_logs(
                offset=offset,
                limit=limit,
                start_time=start_time,
                end_time=end_time,
                **additional_query_params,
            )
            logger.debug("Successfully received %d Audit logs.", len(response))
            yield from response

            events_count += len(response)
            if len(response) < limit:
                break

            offset += limit
        except Exception:
            logger.exception("Error occurred while fetching the audit logs.")
            break

    logger.info(f"Successfully collected {events_count} Audit logs.")


class CiscoCatalystCenterAuditLogs(smi.Script):
    """Get the Security Advisory details from Cisco Catalyst Center Server."""

    def __init__(self):
        """Initialise CISCO_CATALYST_CENTER_CLIENTHEALTH class."""
        super(CiscoCatalystCenterAuditLogs, self).__init__()

    def get_scheme(self):
        """Load the arguments in the Configuration page."""
        scheme = smi.Scheme("cisco_catalyst_dnac_audit_logs")
        scheme.description = "cisco_catalyst_dnac_audit_logs"
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
                "cisco_dna_center_account",
                required_on_create=True,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        """Validate the input parameters provided by the user."""
        pass

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        """Collect the events from the Cisco Catalyst Center Server."""
        session_key = self._input_definition.metadata["session_key"]
        input_name, input_conf = [
            [key.split("/")[-1], val] for key, val in inputs.inputs.items()
        ][0]
        input_conf["input_name"] = input_name
        opt_cisco_catalyst_center_account = input_conf.get("cisco_dna_center_account")
        logger = logger_manager.get_logger(
            f"catalyst_center_audit_logs_{input_name}", input_conf["logging_level"]
        )

        logger.info("Starting data collection of Audit logs for input: %s.", input_name)

        account_conf = utils.get_account_config(
            session_key, consts.ACCOUNT_CONF_FILE, logger
        )
        account_conf_info = account_conf.get(opt_cisco_catalyst_center_account)
        opt_cisco_catalyst_center_host = account_conf_info.get("cisco_dna_center_host")
        account_username = account_conf_info.get("username")
        account_password = account_conf_info.get("password")
        input_start_date = get_start_time(input_conf.get("interval"))

        use_ca_cert = account_conf_info.get("use_ca_cert")
        current_verify = True
        if use_ca_cert is None:
            current_verify = utils.get_sslconfig(session_key, logger)
        elif utils.is_true(use_ca_cert):
            current_verify = consts.CATALYSTC_CERT_FILE_LOC.format(
                cert_name=account_conf_info.get("copy_account_name").strip()
            )
            logger.debug(
                "SSL Verification is set to True and will use the cert from this path. {}.".format(
                    current_verify
                )
            )
        else:
            current_verify = utils.get_verify_ssl(session_key, logger)
        current_debug = False

        try:
            logger.info("Making Authentication call to Catalyst Center host.")
            catalystc = api.CatalystCenterAPI(
                username=account_username,
                password=account_password,
                base_url=opt_cisco_catalyst_center_host,
                verify=current_verify,
                debug=current_debug,
                helper=logger,
            )

            audit_logs_details = []
            audit_logs_details = get_audit_logs_details(
                catalystc,
                logger,
                input_start_date,
            )
            for audit_log in audit_logs_details:
                # Replacing the source key with src as source is a reserved keyword in Splunk.
                if "source" in audit_log:
                    audit_log["src"] = audit_log.pop("source")
                event = smi.Event(
                    data=json.dumps(audit_log),
                    source="://".join(["cisco_catalyst_dnac_audit_logs", input_name]),
                    host=opt_cisco_catalyst_center_host,
                    index=None,
                )
                ew.write_event(event)
            logger.info(
                "instance={}, product=Cisco Catalyst Center,"
                " filter_value=cisco_catalyst_dnac_audit_logs://{},"
                " status=Connected,".format(input_name, input_name)
            )
        except Exception:
            logger.info(
                "instance={}, product=Cisco Catalyst Center, "
                "filter_value=cisco_catalyst_dnac_audit_logs://{}, "
                "status=Not Connected,".format(input_name, input_name)
            )
            logger.exception("Error occurred while performing the data collection.")

        logger.info(f"Data collection completed for input. {input_name}")


if __name__ == "__main__":
    exit_code = CiscoCatalystCenterAuditLogs().run(sys.argv)
    sys.exit(exit_code)
