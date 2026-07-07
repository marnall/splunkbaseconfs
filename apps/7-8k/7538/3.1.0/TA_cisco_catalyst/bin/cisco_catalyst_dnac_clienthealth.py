"""Modular input for Catalyst Center ClientHealth."""
import import_declare_test  # noqa: F401

import json
import sys

import consts
import utils
from splunklib import modularinput as smi
import cisco_dnac_api as api
import logger_manager


def get_client_health(catalystc):
    """
    Retrieve the client health at the time the function is called.

    :param catalystc: Cisco Catalyst Center SDK api
    :return: client health response
    """
    health_response = catalystc.clients.get_overall_client_health()
    return health_response


def filter_health_data(network_health_response):
    """
    Filter the data to get the overall client data.

    :param network_health_response: network health data
    :return: health distribution summary response
    """
    health_distribution = []

    for response_item in network_health_response.response:
        # Set siteId
        for score_item in response_item["scoreDetail"]:
            health_item = {}
            # Set default data
            health_item["siteId"] = response_item["siteId"]

            health_item["clientType"] = ""
            if score_item.scoreCategory:
                health_item["clientType"] = score_item.scoreCategory.value

            health_item["clientCount"] = score_item.clientCount
            health_item["clientUniqueCount"] = score_item.clientUniqueCount
            health_item["scoreValue"] = score_item.scoreValue
            health_item["starttime"] = score_item.starttime
            health_item["endtime"] = score_item.endtime
            health_item["scoreType"] = "ALL"

            # TODO: check value
            # If it is ALL skip, nothing more to do
            if score_item.scoreCategory and score_item.scoreCategory.value == "ALL":
                health_distribution.append(health_item)
                continue

            if score_item.scoreList:
                # Set artificial scoreType for general client
                health_distribution.append(health_item)
                for score_type in score_item.scoreList:
                    health_item_new = dict(health_item)

                    health_item_new["scoreType"] = ""
                    if score_type.scoreCategory:
                        health_item_new["scoreType"] = score_type.scoreCategory.value

                    health_item_new["clientCount"] = score_type.clientCount
                    health_item_new["clientUniqueCount"] = score_type.clientUniqueCount
                    health_item_new["scoreValue"] = score_type.scoreValue
                    health_item_new["starttime"] = score_type.starttime
                    health_item_new["endtime"] = score_type.endtime
                    health_distribution.append(health_item_new)

    return health_distribution


class CISCO_CATALYST_CENTER_CLIENTHEALTH(smi.Script):
    """Get the Clienthealth from Cisco Catalyst Center Server."""

    def __init__(self):
        """Initialise CISCO_CATALYST_CENTER_CLIENTHEALTH class."""
        super(CISCO_CATALYST_CENTER_CLIENTHEALTH, self).__init__()

    def get_scheme(self):
        """Load the arguments in the Configuration page."""
        scheme = smi.Scheme('cisco_catalyst_dnac_clienthealth')
        scheme.description = 'cisco_catalyst_dnac_clienthealth'
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                'name',
                title='Name',
                description='Name',
                required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                'cisco_dna_center_account',
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
        input_name, input = [
            [key.split("/")[-1], val] for key, val in inputs.inputs.items()
        ][0]
        input["input_name"] = input_name
        source = "cisco_catalyst_dnac_clienthealth://{}".format(input_name)
        opt_cisco_catalyst_center_account = input.get("cisco_dna_center_account")
        logger = logger_manager.get_logger(
            f"catalyst_center_clienthealth_{input_name}", input["logging_level"]
        )

        account_conf = utils.get_account_config(session_key, consts.ACCOUNT_CONF_FILE, logger)
        account_conf_info = account_conf.get(opt_cisco_catalyst_center_account)
        opt_cisco_catalyst_center_host = account_conf_info.get("cisco_dna_center_host")
        account_username = account_conf_info.get("username")
        account_password = account_conf_info.get("password")

        account_name = account_conf_info.get("name")  # noqa: F841
        current_version = "2.2.3.3"
        use_ca_cert = account_conf_info.get("use_ca_cert")
        current_verify = True
        if use_ca_cert is None:
            current_verify = utils.get_sslconfig(session_key, logger)
        elif utils.is_true(use_ca_cert):
            current_verify = consts.CATALYSTC_CERT_FILE_LOC.format(
                cert_name=account_conf_info.get("copy_account_name").strip()
            )
            logger.debug(
                "SSL Verification is set to True and will use the cert from this path. {}.".format(current_verify)
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
            r_json = []
            # get the overall client health
            overall_client_health = get_client_health(catalystc)
            # simplify gathered information
            response = filter_health_data(overall_client_health)

            for item in response:
                key = "{0}_{1}_{2}_{3}".format(
                    opt_cisco_catalyst_center_host,
                    item.get("siteId") or "N/A",
                    item.get("clientType") or "N/A",
                    item.get("scoreType") or "N/A",
                )
                state = utils.get_checkpoint(session_key, key, logger)
                item["cisco_catalyst_host"] = opt_cisco_catalyst_center_host
                if state is None:
                    utils.update_checkpoint(session_key, key, item, logger)
                    r_json.append(item)
                elif utils.is_different(logger, state, item):
                    utils.update_checkpoint(session_key, key, item, logger)
                    r_json.append(item)
                # helper.delete_check_point(key)

            event = smi.Event(
                data=json.dumps(r_json),
                time=None,
                host=None,
                index=None,
                source=source,
                sourcetype=None,
                done=True,
                unbroken=True,
            )
            ew.write_event(event)
            logger.info("instance={}, product=Cisco Catalyst Center,"
                        " filter_value={},"
                        " status=Connected,".format(input_name, source))
        except Exception:
            logger.info("instance={}, product=Cisco Catalyst Center,"
                        " filter_value={},"
                        " status=Not Connected,".format(input_name, source))
            logger.exception("Error occurred while performing the data collection.")


if __name__ == '__main__':
    exit_code = CISCO_CATALYST_CENTER_CLIENTHEALTH().run(sys.argv)
    sys.exit(exit_code)
