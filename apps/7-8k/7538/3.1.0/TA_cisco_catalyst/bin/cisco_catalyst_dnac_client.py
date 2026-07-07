"""Modular input for Catalyst Center Client."""
import import_declare_test  # noqa: F401
import json
import sys
import cisco_dnac_api as api
import consts
import logger_manager
from splunklib import modularinput as smi
import utils


def get_clients(catalystc, logger):
    """Get client details from Catalyst Center host.

    :param catalystc: Catalyst Center API object.
    :param logger: Logger object.
    """
    events_count = 0
    offset = 1
    response = []
    while True:
        try:
            logger.debug(
                "Making an API call to collect the client details for offset %d with limit %d.",
                offset,
                consts.CLIENT_LIMIT,
            )
            client_response = catalystc.clients.get_clients(
                offset=offset,
                limit=consts.CLIENT_LIMIT,
            )
            if client_response and client_response.response:
                response.extend(client_response.response)
            else:
                logger.debug("Received 0 Client.")
                break

            logger.debug("Received %d Client(s).", len(client_response.response))
            events_count += len(client_response.response)

            if len(client_response.response) < consts.CLIENT_LIMIT:
                break
            offset += consts.CLIENT_LIMIT
        except Exception:
            logger.exception("Error occurred while fetching the client details.")
            break
    logger.info(f"Successfully collected {events_count} clients.")
    return response


class CiscoCatalystCenterClient(smi.Script):
    """Get the Client details from Cisco Catalyst Center Server."""

    def __init__(self):
        """Initialise CISCO_Catalyst_CLIENT class."""
        super(CiscoCatalystCenterClient, self).__init__()

    def get_scheme(self):
        """Load the arguments in the Configuration page."""
        scheme = smi.Scheme("cisco_catalyst_dnac_client")
        scheme.description = "cisco_catalyst_dnac_client"
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
            f"catalyst_center_client_{input_name}", input_conf["logging_level"]
        )
        logger.info("Starting data collection of Client for input: %s.", input_name)

        account_conf = utils.get_account_config(
            session_key, consts.ACCOUNT_CONF_FILE, logger
        )
        account_conf_info = account_conf.get(opt_cisco_catalyst_center_account)
        opt_cisco_catalyst_center_host = account_conf_info.get("cisco_dna_center_host")
        account_username = account_conf_info.get("username")
        account_password = account_conf_info.get("password")
        use_ca_cert = account_conf_info.get("use_ca_cert")
        current_verify = True
        current_version = "2.2.3.3"

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
            catalystc = api.CatalystCenterAPI(
                username=account_username,
                password=account_password,
                base_url=opt_cisco_catalyst_center_host,
                version=current_version,
                verify=current_verify,
                debug=current_debug,
                helper=logger,
            )

            client_details = []
            client_details = get_clients(
                catalystc,
                logger,
            )
            for client in client_details:
                client["cisco_catalyst_host"] = opt_cisco_catalyst_center_host
                event = smi.Event(
                    data=json.dumps(client),
                    source="://".join(["cisco_catalyst_dnac_client", input_name]),
                    host=opt_cisco_catalyst_center_host,
                    index=None,
                )
                ew.write_event(event)
            logger.info(
                "instance={}, product=Cisco Catalyst Center,"
                " filter_value=cisco_catalyst_dnac_client://{},"
                " status=Connected,".format(input_name, input_name)
            )
        except Exception:
            logger.info(
                "instance={}, product=Cisco Catalyst Center, "
                "filter_value=cisco_catalyst_dnac_client://{}, "
                "status=Not Connected,".format(input_name, input_name)
            )
            logger.exception("Error occurred while performing the data collection.")
        logger.info(f"Data collection completed for input. {input_name}")


if __name__ == "__main__":
    exit_code = CiscoCatalystCenterClient().run(sys.argv)
    sys.exit(exit_code)
