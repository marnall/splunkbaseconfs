"""Modular input for Catalyst Center NetworkHealth."""
import import_declare_test  # noqa: F401

import json
import sys
import time

import consts
import utils
from splunklib import modularinput as smi
import cisco_dnac_api as api
import logger_manager


def get_epoch_current_time():
    """
    Return the epoch time for the {timestamp}.

    :return: epoch time including msec
    """
    epoch = time.time() * 1000
    return "{0}".format(int(epoch))


def get_overall_network_health(catalystc):
    """
    Retrieve the network health.

    :param catalystc: Cisco Catalyst Center SDK api
    :return: network health response
    """
    network_health_fn = None
    # Select function
    if hasattr(catalystc, "topology") and hasattr(
        catalystc.topology, "get_overall_network_health"
    ):
        network_health_fn = catalystc.topology.get_overall_network_health
    elif hasattr(catalystc, "networks") and hasattr(
        catalystc.networks, "get_overall_network_health"
    ):
        network_health_fn = catalystc.networks.get_overall_network_health
    # If not function was found return None
    if network_health_fn is None:
        return None

    network_health_response = network_health_fn()
    return network_health_response


def filter_health_data(network_health_response, epoch_time):
    """
    Filter data to get the overall network data.

    :param network_health_response: network health response
    :return: health summary response
    """
    health_distribution = []
    # Capture possible None
    if network_health_response is None:
        return health_distribution

    if network_health_response.healthDistirubution:
        health_distribution = list(network_health_response.healthDistirubution)

    if network_health_response.response:
        if len(network_health_response.response) > 0:
            if network_health_response.response[0]:
                key_list = [
                    "healthScore",
                    "totalCount",
                    "goodCount",
                    "noHealthCount",
                    "fairCount",
                    "badCount",
                ]
                overall_health = {"category": "All"}
                tmp = dict(network_health_response.response[0])
                for i in key_list:
                    if tmp[i]:
                        overall_health[i] = tmp[i]
                health_distribution.append(overall_health)
    for i in health_distribution:
        i["time"] = epoch_time
    return health_distribution


class CISCO_CATALYST_CENTER_NETWORKHEALTH(smi.Script):
    """Get the Networkhealth from Cisco Catalyst Server."""

    def __init__(self):
        """Initialise CISCO_CATALYST_CENTER_NETWORKHEALTH class."""
        super(CISCO_CATALYST_CENTER_NETWORKHEALTH, self).__init__()

    def get_scheme(self):
        """Load the arguments in the Configuration page."""
        scheme = smi.Scheme('cisco_catalyst_dnac_networkhealth')
        scheme.description = 'cisco_catalyst_dnac_networkhealth'
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
        source = "cisco_catalyst_dnac_networkhealth://{}".format(input_name)
        opt_cisco_catalyst_center_account = input.get("cisco_dna_center_account")
        logger = logger_manager.get_logger(
            f"catalyst_center_networkhealth_{input_name}", input["logging_level"]
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
            epoch_time = get_epoch_current_time()
            # get the overall network health
            overall_network_health = get_overall_network_health(catalystc)
            # simplify gathered information
            network_health_summary = filter_health_data(overall_network_health, epoch_time)

            for item in network_health_summary:
                item["cisco_catalyst_host"] = opt_cisco_catalyst_center_host
                r_json.append(item)

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
            logger.info("instance={}, product=Cisco Catalyst Center, "
                        "filter_value={}, "
                        "status=Connected,".format(input_name, source))
        except Exception:
            logger.info("instance={}, product=Cisco Catalyst Center, "
                        "filter_value={}, "
                        "status=Not Connected,".format(input_name, source))
            logger.exception("Error occurred while performing the data collection.")


if __name__ == '__main__':
    exit_code = CISCO_CATALYST_CENTER_NETWORKHEALTH().run(sys.argv)
    sys.exit(exit_code)
