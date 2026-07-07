"""Modular input for Catalyst Center Security Advisory."""
import import_declare_test  # noqa: F401

import json
import sys

import consts
import utils
from splunklib import modularinput as smi
import cisco_dnac_api as api
import logger_manager


def get_important_device_values(device_item):
    """
    Simplify the device data for Splunk searches.

    :param device_item: device data
    :return: new device response
    """
    response = {}
    response["DeviceName"] = device_item.get("hostname") or "N/A"
    response["DeviceIpAddress"] = (
        device_item.get("managementIpAddress") or device_item.get("ipAddress") or ""
    )
    response["DeviceFamily"] = device_item.get("family") or ""
    response["DeviceReachability"] = device_item.get("reachabilityStatus") or ""
    response["DeviceReachabilityFailureReason"] = (
        device_item.get("reachabilityFailureReason") or ""
    )
    # Section to set the value of Manageability and ManageErrors
    response["DeviceManageErrors"] = ""
    if device_item.get("managementState") == "Managed":
        response["DeviceManageability"] = "Managed"
        if (
            device_item.get("collectionStatus")
            and device_item["collectionStatus"] != "Managed"
        ):
            response["DeviceManageability"] = "Managed (With Errors)"
            response["DeviceManageErrors"] = device_item["collectionStatus"]
    elif device_item.get("managementState") in ["Unmanaged", "Never Managed"]:
        response["DeviceManageability"] = "Unmanaged"
    else:
        response["DeviceManageability"] = "Managed (With Errors)"
    response["DeviceMACAddress"] = (
        device_item.get("macAddress") or device_item.get("apEthernetMacAddress") or ""
    )
    response["DeviceRole"] = device_item.get("role") or "UNKNOWN"
    response["DeviceImageVersion"] = device_item.get("softwareVersion") or ""
    response["DeviceUptime"] = device_item.get("upTime") or ""
    if device_item.get("uptimeSeconds") is not None:
        response["DeviceUptimeSeconds"] = device_item.get("uptimeSeconds")
    else:
        response["DeviceUptimeSeconds"] = 0
    response["DeviceLastUpdated"] = device_item.get("lastUpdated") or ""
    if device_item.get("lastUpdateTime") is not None:
        response["DeviceLastUpdateTime"] = device_item.get("lastUpdateTime")
    else:
        response["DeviceLastUpdateTime"] = 0
    response["DeviceSerialNumber"] = device_item.get("serialNumber") or ""
    response["DeviceSeries"] = device_item.get("series") or ""
    response["DevicePlatform"] = device_item.get("platformId") or ""
    response["DeviceSupportType"] = device_item.get("deviceSupportLevel") or ""
    response["DeviceAssociatedWLCIP"] = device_item.get("associatedWlcIp") or ""
    return response


def get_advisories_summary(catalystc):
    """
    Retrieve the advisories summary.

    :param catalystc: Cisco Catalyst Center SDK api
    :return: simplified advisories summary response
    """
    advisories_summary = catalystc.security_advisories.get_advisories_summary()
    responses = []
    if advisories_summary and advisories_summary.response:
        for category in advisories_summary.response:
            for subcategory in advisories_summary.response[category]:
                responses.append(
                    {
                        "Summary": "True",
                        "Category": category,
                        "SubCategory": subcategory,
                        "Amount": int(
                            advisories_summary.response[category][subcategory]
                        ),
                    }
                )
    return responses


def get_devices_per_advisory(catalystc):
    """
    Retrieve the advisories data and devices data as necessary.

    :param catalystc: Cisco Catalyst Center SDK api
    :return: simplified advisories and devices response
    """
    advisories_list = catalystc.security_advisories.get_advisories_list()
    responses = []
    devices_retrieved = {}
    if advisories_list and advisories_list.response:
        for advisories_item in advisories_list.response:
            response = {}
            response["AdvisoryID"] = advisories_item.get("advisoryId") or ""
            response["AdvisoryDeviceCount"] = advisories_item.get("deviceCount") or 0
            # response['AdvisoryCves'] = advisories_item.get('cves') or []
            response["AdvisoryCvesStr"] = ", ".join(advisories_item.get("cves")) or ""
            response["AdvisoryPublicationUrl"] = (
                advisories_item.get("publicationUrl") or ""
            )
            response["AdvisorySir"] = advisories_item.get("sir") or ""
            response["AdvisoryDetectionType"] = (
                advisories_item.get("detectionType") or ""
            )
            response["AdvisoryDefaultDetectionType"] = (
                advisories_item.get("defaultDetectionType") or ""
            )
            if response["AdvisoryID"]:
                advisory_device = catalystc.security_advisories.get_devices_per_advisory(
                    response["AdvisoryID"]
                )
                if advisory_device and advisory_device.response:
                    for device_id in advisory_device.response:
                        # Manage device info ...
                        device_info = {}
                        # ... if already present, reuse
                        if devices_retrieved.get(device_id):
                            device_info = dict(devices_retrieved[device_id])
                        else:  # ... if not retrieve and save it
                            device_info = catalystc.devices.get_device_by_id(id=device_id)
                            devices_retrieved[device_id] = device_info
                        if isinstance(device_info, dict) and device_info.get(
                            "response"
                        ):
                            response_device = dict(response)
                            response_device.update(
                                get_important_device_values(device_info["response"])
                            )
                            response_device.update({"Summary": "False"})
                            responses.append(response_device)
            else:
                responses.append(response)
    return responses


class CISCO_CATALYST_CENTER_SECURITYADVISORY(smi.Script):
    """Get the Security Advisory details from Cisco Catalyst Center Server."""

    def __init__(self):
        """Initialise CISCO_CATALYST_CENTER_SECURITYADVISORY class."""
        super(CISCO_CATALYST_CENTER_SECURITYADVISORY, self).__init__()

    def get_scheme(self):
        """Load the arguments in the Configuration page."""
        scheme = smi.Scheme('cisco_catalyst_dnac_securityadvisory')
        scheme.description = 'cisco_catalyst_dnac_securityadvisory'
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
        source = "cisco_catalyst_dnac_securityadvisory://{}".format(input_name)
        opt_cisco_catalyst_center_account = input.get("cisco_dna_center_account")
        logger = logger_manager.get_logger(
            f"catalyst_center_securityadvisory_{input_name}", input["logging_level"]
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

        # use default input_interval
        input_interval = 900  # noqa: F841
        try:
            input_interval = int(input.get("interval"))
        except ValueError:
            input_interval = 900  # noqa: F841

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

            # get the security advisories details and devices data as necessary
            r_json = []
            security_advisories = []
            advisories_summary = []
            try:
                security_advisories = get_devices_per_advisory(catalystc)
            except Exception:
                logger.exception("Error occurred while getting the devices per advisory.")

            for item in security_advisories:
                key = "{0}_{1}_{2}".format(
                    opt_cisco_catalyst_center_host,
                    item.get("AdvisoryID") or "N/A",
                    item.get("DeviceIpAddress") or "N/A",
                )
                state = utils.get_checkpoint(session_key, key, logger)
                item["cisco_catalyst_host"] = opt_cisco_catalyst_center_host
                if state is None:
                    utils.update_checkpoint(session_key, key, item, logger)
                    r_json.append(item)
                elif utils.is_different(logger, state, item):
                    utils.update_checkpoint(session_key, key, item, logger)
                    r_json.append(item)

            try:
                advisories_summary = get_advisories_summary(catalystc)
            except Exception:
                logger.exception("Error occurred while getting advisories summary.")

            for item in advisories_summary:
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
    exit_code = CISCO_CATALYST_CENTER_SECURITYADVISORY().run(sys.argv)
    sys.exit(exit_code)
