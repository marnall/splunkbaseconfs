"""Modular input for Catalyst Center DeviceHealth."""
import import_declare_test  # noqa: F401

import json
import sys
import datetime

import consts
import utils
from splunklib import modularinput as smi
import cisco_dnac_api as api
import logger_manager


def get_epoch_current_previous_times():
    """
    Return the epoch time for the {timestamp} and a previous epoch time.

    :return: epoch time (now) including msec, epoch time (previous) including msec
    """
    # REVIEW: It is recommended that this time matches the Splunk's data input interval
    now = datetime.datetime.now()
    previous = now - datetime.timedelta(minutes=consts.CATALYSTC_DEVICE_HEALTH_START_TIME_MINUTES)
    now = now.replace(microsecond=0)
    previous = previous.replace(microsecond=0)
    return (int(now.timestamp() * 1000), int(previous.timestamp() * 1000))


def get_device_health(catalystc):
    """
    Retrieve the device health from a previous time to the time the function is called.

    :param catalystc: Cisco Catalyst Center SDK api
    :param input_interval: interval in seconds
    :return: device health response
    """
    (epoch_current_time, epoch_previous_time) = get_epoch_current_previous_times()
    limit = 20
    offset = 1
    devices_responses = []
    do_request_next = True
    while do_request_next:
        try:
            health_response = catalystc.devices.devices(
                start_time=epoch_previous_time,
                end_time=epoch_current_time,
                limit=limit,
                offset=offset,
            )
            if health_response and health_response.response:
                devices_responses.extend(health_response.response)
                if len(health_response.response) < limit:
                    do_request_next = False
                    break
            else:
                do_request_next = False
                break
        except Exception:
            do_request_next = False
            break
        offset = offset + limit
    return devices_responses


def get_devices(catalystc):
    """
    Retrieve the devices.

    :param catalystc: Cisco Catalyst Center SDK api
    :return: devices response
    """
    limit = 20
    offset = 1
    devices_responses = []
    do_request_next = True
    while do_request_next:
        try:
            device_response = catalystc.devices.get_device_list(limit=limit, offset=offset)
            if device_response and device_response.response:
                devices_responses.extend(device_response.response)
                if len(device_response.response) < limit:
                    do_request_next = False
                    break
            else:
                do_request_next = False
                break
        except Exception:
            do_request_next = False
            break
        offset = offset + limit
    return devices_responses


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
    response["DeviceID"] = device_item.get("id") or ""
    response["DeviceDescription"] = device_item.get("description") or ""
    response["DeviceType"] = device_item.get("type") or ""
    return response


def get_health_device_values(health_device):
    """
    Simplify the health device data for Splunk searches.

    :param health_device: health device data
    :return: new health device response
    """
    response = {"HasHealthReport": "True"}
    if health_device.get("overallHealth") is not None:
        response["OverallHealth"] = health_device.get("overallHealth")
    else:
        response["OverallHealth"] = 0
    response["HealthScore"] = response["OverallHealth"]
    response["IssueCount"] = health_device.get("issueCount") or 0
    response["Site"] = health_device.get("location") or ""
    response["Location"] = health_device.get("location") or ""

    response["InterfaceLinkErrHealth"] = (
        health_device.get("interfaceLinkErrHealth") or 0
    )
    response["CPUUtilization"] = (
        health_device.get("cpuUlitilization")
        or health_device.get("cpuUtilization")
        or 0
    )
    response["CPUHealth"] = health_device.get("cpuHealth") or 0
    response["MemoryUtilizationHealth"] = (
        health_device.get("memoryUtilizationHealth") or 0
    )
    response["MemoryUtilization"] = health_device.get("memoryUtilization") or 0
    response["InterDeviceLinkAvailHealth"] = (
        health_device.get("interDeviceLinkAvailHealth") or 0
    )

    client_count = health_device.get("clientCount") or {}
    response["HasClientCount"] = str(len(client_count) > 0)
    response["ClientCountRadio0"] = client_count.get("radio0") or 0
    response["ClientCountRadio1"] = client_count.get("radio1") or 0
    response["ClientCountGhz24"] = client_count.get("Ghz24") or 0
    response["ClientCountGhz50"] = client_count.get("Ghz50") or 0

    interference_health = health_device.get("interferenceHealth") or {}
    response["HasInterferenceHealth"] = str(len(interference_health) > 0)
    response["InterferenceHealthRadio0"] = interference_health.get("radio0") or 0
    response["InterferenceHealthRadio1"] = interference_health.get("radio1") or 0
    response["InterferenceHealthGhz24"] = interference_health.get("Ghz24") or 0
    response["InterferenceHealthGhz50"] = interference_health.get("Ghz50") or 0

    noise_health = health_device.get("noiseHealth") or {}
    response["HasNoiseHealth"] = str(len(noise_health) > 0)
    response["NoiseHealthRadio1"] = noise_health.get("radio1") or 0
    response["NoiseHealthGhz50"] = noise_health.get("Ghz50") or 0
    # following attribute is not present in documentation
    response["NoiseHealthRadio0"] = noise_health.get("radio0") or 0
    # following attribute is not present in documentation
    response["NoiseHealthGhz24"] = noise_health.get("Ghz24") or 0

    air_quality_health = health_device.get("airQualityHealth") or {}
    response["HasAirQualityHealth"] = str(len(air_quality_health) > 0)
    response["AirQualityHealthRadio0"] = air_quality_health.get("radio0") or 0
    response["AirQualityHealthRadio1"] = air_quality_health.get("radio1") or 0
    response["AirQualityHealthGhz24"] = air_quality_health.get("Ghz24") or 0
    response["AirQualityHealthGhz50"] = air_quality_health.get("Ghz50") or 0

    utilization_health = health_device.get("utilizationHealth") or {}
    response["HasUtilization"] = str(len(utilization_health) > 0)
    response["UtilizationRadio0"] = utilization_health.get("radio0") or 0
    response["UtilizationRadio1"] = utilization_health.get("radio1") or 0
    response["UtilizationGhz24"] = utilization_health.get("Ghz24") or 0
    response["UtilizationGhz50"] = utilization_health.get("Ghz50") or 0

    # NOTE: Properties that are already present
    # NOTE: WARNING: data maybe have slightly different format
    # response['DeviceFamily'] = health_device.get('deviceFamily') or ''
    # response['DeviceSeries'] = health_device.get('deviceType') or health_device.get('model') or ''
    # response['MACAddress'] = health_device.get('macAddress') or ''
    # response['DeviceName'] = health_device.get('name') or "N/A"
    # response['ImageVersion'] = health_device.get('osVersion') or ''
    # response['IpAddress'] = health_device.get('ipAddress') or ''
    # response['Reachability'] = health_device.get('reachabilityHealth') or ''
    return response


def filter_health_data(health_devices, devices_items):
    """
    Filter data to get the overall device data.

    :param health_devices: health devices data
    :param devices_items: devices data
    :return: health summary response
    """
    health_summary_response = []
    device_dict = {}
    for device_item in devices_items:
        ip_address_key = device_item.get("managementIpAddress") or device_item.get(
            "ipAddress"
        )
        device_dict[ip_address_key] = dict(get_important_device_values(device_item))
    for health_device in health_devices:
        ip_address_key = health_device.get("ipAddress") or health_device.get(
            "managementIpAddress"
        )
        if device_dict.get(ip_address_key):
            device_dict[ip_address_key].update(get_health_device_values(health_device))
        else:
            device_dict[ip_address_key].update({"HasHealthReport": "False"})
    health_summary_response = list(device_dict.values())
    return health_summary_response


class CISCO_CATALYST_CENTER_DEVICEHEALTH(smi.Script):
    """Get the Devicehealth from Cisco Catalyst Center Server."""

    def __init__(self):
        """Initialise CISCO_CATALYST_CENTER_DEVICEHEALTH class."""
        super(CISCO_CATALYST_CENTER_DEVICEHEALTH, self).__init__()

    def get_scheme(self):
        """Load the arguments in the Configuration page."""
        scheme = smi.Scheme('cisco_catalyst_dnac_devicehealth')
        scheme.description = 'cisco_catalyst_dnac_devicehealth'
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
        source = "cisco_catalyst_dnac_devicehealth://{}".format(input_name)
        opt_cisco_catalyst_center_account = input.get("cisco_dna_center_account")
        logger = logger_manager.get_logger(
            f"catalyst_center_devicehealth_{input_name}", input["logging_level"]
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

            # get the overall device health
            health_devices = get_device_health(catalystc)
            # get the information of all devices
            devices_items = get_devices(catalystc)
            # merge and simplify gathered information
            overall_device_health = filter_health_data(health_devices, devices_items)

            r_json = []
            for item in overall_device_health:
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
            logger.info("instance={}, product=Cisco Catalyst Center,"
                        " filter_value={},"
                        " status=Connected,".format(input_name, source))
        except Exception:
            logger.info("instance={}, product=Cisco Catalyst Center,"
                        " filter_value={},"
                        " status=Not Connected,".format(input_name, source))
            logger.exception("Error occurred while performing the data collection.")


if __name__ == '__main__':
    exit_code = CISCO_CATALYST_CENTER_DEVICEHEALTH().run(sys.argv)
    sys.exit(exit_code)
