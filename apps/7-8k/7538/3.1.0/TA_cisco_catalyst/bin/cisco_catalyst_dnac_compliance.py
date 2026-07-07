"""Modular input for Catalyst Center Compliance."""
import import_declare_test  # noqa: F401

import json
import sys

from splunklib import modularinput as smi

import consts
import utils
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
    response["IpAddress"] = (
        device_item.get("managementIpAddress") or device_item.get("ipAddress") or ""
    )
    response["DeviceFamily"] = device_item.get("family") or ""
    response["Reachability"] = device_item.get("reachabilityStatus") or ""
    response["ReachabilityFailureReason"] = (
        device_item.get("reachabilityFailureReason") or ""
    )
    # Section to set the value of Manageability and ManageErrors
    response["ManageErrors"] = ""
    if device_item.get("managementState") == "Managed":
        response["Manageability"] = "Managed"
        if (
            device_item.get("collectionStatus")
            and device_item["collectionStatus"] != "Managed"
        ):
            response["Manageability"] = "Managed (With Errors)"
            response["ManageErrors"] = device_item["collectionStatus"]
    elif device_item.get("managementState") in ["Unmanaged", "Never Managed"]:
        response["Manageability"] = "Unmanaged"
    else:
        response["Manageability"] = "Managed (With Errors)"
    response["MACAddress"] = (
        device_item.get("macAddress") or device_item.get("apEthernetMacAddress") or ""
    )
    response["DeviceRole"] = device_item.get("role") or "UNKNOWN"
    response["ImageVersion"] = device_item.get("softwareVersion") or ""
    response["Uptime"] = device_item.get("upTime") or ""
    if device_item.get("uptimeSeconds") is not None:
        response["UptimeSeconds"] = device_item.get("uptimeSeconds")
    else:
        response["UptimeSeconds"] = 0
    response["LastUpdated"] = device_item.get("lastUpdated") or ""
    if device_item.get("lastUpdateTime") is not None:
        response["LastUpdateTime"] = device_item.get("lastUpdateTime")
    else:
        response["LastUpdateTime"] = 0
    response["SerialNumber"] = device_item.get("serialNumber") or ""
    response["DeviceSeries"] = device_item.get("series") or ""
    response["Platform"] = device_item.get("platformId") or ""
    response["SupportType"] = device_item.get("deviceSupportLevel") or ""
    response["AssociatedWLCIP"] = device_item.get("associatedWlcIp") or ""
    return response


def get_simplified_compliance_detail(compliance_item):
    """
    Simplify the compliance data for Splunk searches.

    :param compliance_item: compliance data
    :return: new compliance response
    """
    response = {}
    response["ComplianceDeviceID"] = (
        compliance_item.get("deviceUuid") or compliance_item.get("deviceId") or ""
    )
    response["ComplianceComplianceType"] = compliance_item.get("complianceType") or ""
    response["ComplianceStatus"] = compliance_item.get("status") or ""
    response["ComplianceState"] = compliance_item.get("state") or ""
    response["ComplianceLastSyncTime"] = compliance_item.get("lastSyncTime") or 0
    response["ComplianceLastUpdateTime"] = compliance_item.get("lastUpdateTime") or 0
    return response


def get_simplified_compliance_status(compliance_item):
    """
    Simplify the compliance data for Splunk searches.

    :param compliance_item: compliance data
    :return: new compliance response
    """
    response = {}
    response["ComplianceDeviceID"] = (
        compliance_item.get("deviceUuid") or compliance_item.get("deviceId") or ""
    )
    response["ComplianceStatus"] = compliance_item.get("complianceStatus") or ""
    response["ComplianceLastUpdateTime"] = compliance_item.get("lastUpdateTime") or 0
    return response


def simplified_complaince_status_page(
    catalystc, compliance_page_response, devices_retrieved, logger
):
    """
    Retrieve the compliance status and devices data as necessary.

    :param catalystc: Cisco Catalyst Center SDK api
    :return: compliance status response
    """
    simplified_complaince_response = []
    for compliance in compliance_page_response:
        simplified_complaince = dict(get_simplified_compliance_status(compliance))
        device_key = simplified_complaince["ComplianceDeviceID"]
        # Manage device info ...
        device_info = {}
        # ... if already present, reuse
        if devices_retrieved.get(device_key):
            device_info = dict(devices_retrieved[device_key])
        else:  # ... if not retrieve and save it
            logger.debug(
                "Getting the device data from the compliance device id {0}".format(
                    device_key
                )
            )
            device_info = catalystc.devices.get_device_by_id(id=device_key)
            devices_retrieved[device_key] = device_info
        if isinstance(device_info, dict) and device_info.get("response"):
            simplified_complaince.update(
                get_important_device_values(device_info["response"])
            )
            logger.debug(
                "Saved the device data from the compliance device id {0}".format(
                    device_key
                )
            )
        simplified_complaince_response.append(simplified_complaince)
    return simplified_complaince_response


def simplified_complaince_detail_page(
    catalystc, compliance_page_response, devices_retrieved, logger
):
    """
    Retrieve the compliance details and devices data as necessary.

    :param catalystc: Cisco Catalyst Center SDK api
    :return: compliance details response
    """
    simplified_complaince_response = []
    for compliance in compliance_page_response:
        simplified_complaince = dict(get_simplified_compliance_detail(compliance))
        device_key = simplified_complaince["ComplianceDeviceID"]
        # Manage device info ...
        device_info = {}
        # ... if already present, reuse
        if devices_retrieved.get(device_key):
            device_info = dict(devices_retrieved[device_key])
        else:  # ... if not retrieve and save it
            logger.debug(
                "Getting the device data from the compliance device id {0}".format(
                    device_key
                )
            )
            device_info = catalystc.devices.get_device_by_id(id=device_key)
            devices_retrieved[device_key] = device_info
        if isinstance(device_info, dict) and device_info.get("response"):
            simplified_complaince.update(
                get_important_device_values(device_info["response"])
            )
            logger.debug(
                "Saved the device data from the compliance device id {0}".format(
                    device_key
                )
            )
        simplified_complaince_response.append(simplified_complaince)
    return simplified_complaince_response


def get_compliance_and_device_details(catalystc, logger):
    """
    Retrieve the compliance details and devices as necessary.

    :param catalystc: Cisco Catalyst Center SDK api
    :return: compliance details response
    """
    compliances_details_response = []
    compliances_response = []
    devices_retrieved = {}
    limit = 20
    offset = 1
    do_request_next = True
    while do_request_next:
        try:
            compliances_page_response = catalystc.compliance.get_compliance_status(
                limit=str(limit), offset=str(offset)
            )
            if compliances_page_response and compliances_page_response.response:
                compliances_response.extend(
                    simplified_complaince_status_page(
                        catalystc,
                        compliances_page_response.response,
                        devices_retrieved,
                        logger,
                    )
                )
                if len(compliances_page_response.response) < limit:
                    do_request_next = False
                    break
            else:
                do_request_next = False
                break
        except Exception:
            do_request_next = False
            break
        offset = offset + limit

    # Set again for new requests
    do_request_next = True
    limit = 20
    offset = 1
    while do_request_next:
        try:
            compliances_page_details_response = catalystc.compliance.get_compliance_detail(
                limit=str(limit), offset=str(offset)
            )
            if compliances_page_details_response and compliances_page_details_response.response:
                compliances_details_response.extend(
                    simplified_complaince_detail_page(
                        catalystc,
                        compliances_page_details_response.response,
                        devices_retrieved,
                        logger,
                    )
                )
                if len(compliances_page_details_response.response) < limit:
                    do_request_next = False
                    break
            else:
                do_request_next = False
                break
        except Exception:
            do_request_next = False
            break
        offset = offset + limit
    return [compliances_details_response, compliances_response]


class CISCO_CATALYST_CENTER_COMPLIANCE(smi.Script):
    """Get the Compliance details from Cisco Catalyst Center Server."""

    def __init__(self):
        """Initialise CISCO_CATALYST_CENTER_COMPLIANCE class."""
        super(CISCO_CATALYST_CENTER_COMPLIANCE, self).__init__()

    def get_scheme(self):
        """Load the arguments in the Configuration page."""
        scheme = smi.Scheme('cisco_catalyst_dnac_compliance')
        scheme.description = 'cisco_catalyst_dnac_compliance'
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
        source = "cisco_catalyst_dnac_compliance://{}".format(input_name)
        opt_cisco_catalyst_center_account = input.get("cisco_dna_center_account")
        logger = logger_manager.get_logger(
            f"catalyst_center_compliance_{input_name}", input["logging_level"]
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

            # get the compliance devices count
            compliance_device_count = {
                "ComplianceDetail": "False",
                "ComplianceCount": "True",
                "cisco_catalyst_center_host": opt_cisco_catalyst_center_host
            }
            try:
                all_status = catalystc.compliance.get_compliance_status_count()
                if all_status and all_status.response:
                    compliance_device_count["ComplianceDeviceCount"] = all_status.response
                compliant_status = catalystc.compliance.get_compliance_status_count(compliance_status="COMPLIANT")
                if compliant_status and compliant_status.response:
                    compliance_device_count["CompliantDeviceCount"] = compliant_status.response
            except Exception:
                logger.exception('Error getting COMPLIANT count. ')

            r_json.append(compliance_device_count)

            # get the compliance details and devices data as necessary
            [overall_compliance_details, overall_compliance] = get_compliance_and_device_details(catalystc, logger)

            for item in overall_compliance_details:
                item["cisco_catalyst_host"] = opt_cisco_catalyst_center_host
                item["ComplianceDetail"] = "True"
                item["ComplianceCount"] = "False"
                r_json.append(item)

            for item in overall_compliance:
                item["cisco_catalyst_host"] = opt_cisco_catalyst_center_host
                item["ComplianceDetail"] = "False"
                item["ComplianceCount"] = "False"
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
            logger.info("instance={}, product=Cisco Catalyst Center,"
                        " filter_value={},"
                        " status=Connected,".format(input_name, source))
        except Exception:
            logger.info("instance={}, product=Cisco Catalyst Center,"
                        " filter_value={},"
                        " status=Not Connected,".format(input_name, source))
            logger.exception("Error occurred while performing the data collection.")


if __name__ == '__main__':
    exit_code = CISCO_CATALYST_CENTER_COMPLIANCE().run(sys.argv)
    sys.exit(exit_code)
