"""Modular input for Catalyst Center Issue."""
import import_declare_test  # noqa: F401

import json
import sys
import time

import consts
import utils
from splunklib import modularinput as smi
import cisco_dnac_api as api
import logger_manager


def get_important_device_values(device_item):
    """
    Simplify the device information for Splunk searches.

    :param device_item: device information
    :return: simplified device response
    """
    response = {}
    response["DeviceID"] = device_item.get("id") or ""
    response["DeviceName"] = device_item.get("hostname") or "N/A"
    response["DeviceIpAddress"] = (
        device_item.get("managementIpAddress") or device_item.get("ipAddress") or ""
    )
    response["DeviceFamily"] = device_item.get("family") or ""
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
    return response


def simplify_issue(issue_responses):
    """
    Simplify the site data for Splunk searches.

    :param issue_resp: Cisco Catalyst Center SDK api
    :return: new site response
    """
    simplified_issue = {}
    if len(issue_responses) > 0 and isinstance(issue_responses[0], dict):
        issue_resp = issue_responses[0]
        simplified_issue["IssueID"] = issue_resp.get("issueId")
        simplified_issue["IssueSpecificCategory"] = issue_resp.get("issueCategory")
        simplified_issue["IssueSpecificSource"] = issue_resp.get("issueSource")
        simplified_issue["IssueSpecificName"] = issue_resp.get("issueName")
        simplified_issue["IssueSpecificDescription"] = issue_resp.get(
            "issueDescription"
        )
        simplified_issue["IssueSpecificEntity"] = issue_resp.get("issueEntity")
        simplified_issue["IssueSpecificEntityValue"] = issue_resp.get(
            "issueEntityValue"
        )
        simplified_issue["IssueSpecificSeverity"] = issue_resp.get("issueSeverity")
        simplified_issue["IssueSpecificPriority"] = issue_resp.get("issuePriority")
        simplified_issue["IssueSpecificSummary"] = issue_resp.get("issueSummary")
        simplified_issue["IssueSpecificTimestamp"] = issue_resp.get("issueTimestamp")
        return simplified_issue
    else:
        return {}


def simplify_site(site_resp):
    """
    Simplify the site data for Splunk searches.

    :param site_resp: Cisco Catalyst Center SDK api
    :return: new site response
    """
    simplified_site = {}
    if site_resp:
        simplified_site["SiteName"] = site_resp.get("name")
        simplified_site["SiteNameHierarchy"] = site_resp.get("siteNameHierarchy")
        simplified_site["SiteType"] = "area"
        if site_resp.get("additionalInfo"):
            if len(site_resp["additionalInfo"]) > 0:
                for additional_info in site_resp["additionalInfo"]:
                    if isinstance(additional_info, dict) and additional_info.get(
                        "attributes"
                    ):
                        if isinstance(
                            additional_info["attributes"], dict
                        ) and additional_info["attributes"].get("type"):
                            simplified_site["SiteType"] = additional_info[
                                "attributes"
                            ].get("type")
        return simplified_site
    else:
        return {}


def clean_dict_of_empty_strings(**kwargs):
    """Return clean dict of empty strings."""
    dict_ = {**kwargs}
    dict_new = {}
    for key, value in dict_.items():
        if isinstance(value, str) and value != "":
            dict_new[key] = value
    return dict_new


def get_issues(catalystc, logger, **kwargs):
    """
    Retrieve the issue details and devices&site data as necessary.

    :param catalystc: Cisco Catalyst Center SDK api
    :param **kwargs: key arguments
    :return: simplified issues and device&site response
    """
    responses = []
    issues_response = catalystc.issues.issues(**clean_dict_of_empty_strings(**kwargs))
    issue_info = {}
    site_info = {}
    device_info = {}
    wait_seconds_for_issue_details_requests = 15
    if issues_response and issues_response.response:
        last_index = len(issues_response.response) - 1
        for index, issue_item in enumerate(issues_response.response):
            response = {}
            issue_id = issue_item.get("issueId") or ""
            site_id = issue_item.get("siteId") or ""
            device_id = issue_item.get("deviceId") or ""
            # site_id represents a siteId hierarchy, the last value is the correct siteId
            # Python allows to call last string array without issues here
            site_id = site_id.split("/")[-1]
            if issue_id:
                logger.debug(
                    "Getting the issue details from the issue id {0}".format(issue_id)
                )
                if issue_info.get(issue_id):
                    response.update(issue_info[issue_id])
                    logger.debug(
                        "Saved the issue details from the issue id {0} to final response. Cache".format(
                            issue_id
                        )
                    )
                else:
                    tmp_issue = {}
                    try:
                        tmp_issue = catalystc.issues.get_issue_enrichment_details(
                            headers=dict(entity_type="issue_id", entity_value=issue_id)
                        )
                        if index != last_index:
                            time.sleep(wait_seconds_for_issue_details_requests)
                    except Exception:
                        tmp_issue = {}
                        logger.exception('Error getting issues. ')

                    if (
                        tmp_issue
                        and isinstance(tmp_issue.get("issueDetails"), dict)
                        and isinstance(tmp_issue["issueDetails"].get("issue"), list)
                    ):
                        issue_info[issue_id] = simplify_issue(
                            tmp_issue["issueDetails"]["issue"]
                        )
                        logger.debug(
                            "Saved the issue details from the issue id {0}".format(
                                issue_id
                            )
                        )
                    else:
                        issue_info[issue_id] = {}

                    issue_info[issue_id].update(
                        {
                            "IssueName": issue_item.get("name") or "",
                            "IssueDeviceRole": issue_item.get("deviceRole") or "",
                            "IssueAiDriven": issue_item.get("aiDriven") or "",
                            "IssueClientMac": issue_item.get("clientMac") or "",
                            "IssueCount": issue_item.get("issue_occurence_count") or "",
                            "IssueStatus": issue_item.get("status") or "",
                            "IssuePriority": issue_item.get("priority") or "",
                            "IssueCategory": issue_item.get("category") or "",
                        }
                    )
                    response.update(issue_info[issue_id])
                    logger.debug(
                        "Saved the issue details from the issue id {0} to final response.".format(
                            issue_id
                        )
                    )
            if site_id:
                logger.debug(
                    "Getting the site data from the site id {0}".format(site_id)
                )
                if site_info.get(site_id):
                    response.update(site_info[site_id])
                    logger.debug(
                        "Saved the site data from the site id {0} to final response. Cache".format(
                            site_id
                        )
                    )
                else:
                    tmp_site = {}
                    try:
                        tmp_site = catalystc.sites.get_site(site_id=site_id)
                    except Exception:
                        tmp_site = {}
                        logger.exception('Error getting site. ')

                    if tmp_site and tmp_site.response:
                        site_info[site_id] = simplify_site(tmp_site["response"])
                        response.update(site_info[site_id])
                        logger.debug(
                            "Saved the site data from the site id {0} to final response.".format(
                                site_id
                            )
                        )
            if device_id:
                logger.debug(
                    "Getting the device data from the device id {0}".format(device_id)
                )
                if device_info.get(device_id):
                    response.update(device_info[device_id])
                    logger.debug(
                        "Saved the device data from the device id {0} to final response. Cache".format(
                            device_id
                        )
                    )
                else:
                    tmp_device = {}
                    try:
                        tmp_device = catalystc.devices.get_device_by_id(id=device_id)
                    except Exception:
                        tmp_device = {}
                        logger.exception('Error getting device. ')

                    if tmp_device and tmp_device.response:
                        device_info[device_id] = get_important_device_values(
                            tmp_device["response"]
                        )
                        response.update(device_info[device_id])
                        logger.debug(
                            "Saved the device data from the device id {0} to final response.".format(
                                device_id
                            )
                        )
            responses.append(response)
            logger.debug("Saved the issue data with all details to responses.")
    return responses


class CISCO_CATALYST_CENTER_ISSUE(smi.Script):
    """Get the Issue Details from Cisco Catalyst Center Server."""

    def __init__(self):
        """Initialise CISCO_CATALYST_CENTER_ISSUE class."""
        super(CISCO_CATALYST_CENTER_ISSUE, self).__init__()

    def get_scheme(self):
        """Load the arguments in the Configuration page."""
        scheme = smi.Scheme('cisco_catalyst_dnac_issue')
        scheme.description = 'cisco_catalyst_dnac_issue'
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
        source = "cisco_catalyst_dnac_issue://{}".format(input_name)
        opt_cisco_catalyst_center_account = input.get("cisco_dna_center_account")
        logger = logger_manager.get_logger(
            f"catalyst_center_issue_{input_name}", input["logging_level"]
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
            # get the issue details and devices&site data as necessary
            overall_issues = []
            overall_issues_active = []
            overall_issues_ignored = []
            overall_issues_resolved = []

            try:
                overall_issues_active = get_issues(catalystc, logger, issue_status="ACTIVE")
            except Exception:
                logger.exception('Get exception when getting issues of type ACTIVE. ')
                overall_issues_active = []
            try:
                overall_issues_ignored = get_issues(catalystc, logger, issue_status="IGNORED")
            except Exception:
                logger.exception('Get exception when getting issues of type IGNORED. ')
                overall_issues_ignored = []
            try:
                overall_issues_resolved = get_issues(catalystc, logger, issue_status="RESOLVED")
            except Exception:
                logger.exception('Get exception when getting issues of type RESOLVED. ')
                overall_issues_resolved = []

            overall_issues = (
                overall_issues_active + overall_issues_ignored + overall_issues_resolved
            )
            for item in overall_issues:
                key = "{0}_{1}".format(opt_cisco_catalyst_center_host, item.get("IssueID"))
                item["cisco_catalyst_host"] = opt_cisco_catalyst_center_host
                state = utils.get_checkpoint(session_key, key, logger)
                if state is None:
                    utils.update_checkpoint(session_key, key, item, logger)
                    r_json.append(item)
                elif utils.is_different(logger, state, item):
                    utils.update_checkpoint(session_key, key, item, logger)
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
    exit_code = CISCO_CATALYST_CENTER_ISSUE().run(sys.argv)
    sys.exit(exit_code)
