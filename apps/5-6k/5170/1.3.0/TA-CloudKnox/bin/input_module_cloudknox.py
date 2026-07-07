
# encoding = utf-8

import json
import cloudknox_consts

from log_manager import setup_logging
from cloudknox_collect import CloudKnoxCollect
import cloudknox_upgrade_utility as utility
from ta_cloudknox_declare import ta_name
from solnlib import conf_manager

_LOGGER = setup_logging("cloudknox_mod_input")

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations."""
    # This example accesses the modular input variable
    # global_account = definition.parameters.get('global_account', None)
    pass


def splunk_create_event(record, sourcetype, helper, ew):
    """Create a event into a splunk.

    Args:
        record (dict): data dictionary
        sourcetype (str): Sourcetype
        helper (object): helper object
        ew (object): Event writer object
    """
    try:
        event = helper.new_event(
            source=helper.get_input_type(),
            index=helper.get_output_index(),
            sourcetype=sourcetype,
            data=json.dumps(record),
        )
        ew.write_event(event)
    except Exception as e:
        _LOGGER.error("PAR: Unexpected error while indexing data: {}".format(str(e)))


def collect_events(helper, ew):
    """Collect Cloudknox PAR data."""
    # Get inputs from helper
    AUTH_SYS_TYPE = helper.get_arg("auth_system_type")
    CONFIGURED_AUTH_SYS = helper.get_arg("auth_systems")
    app_name = helper.get_app_name()
    session_key = helper.context_meta["session_key"]
    cfm = conf_manager.ConfManager(
        session_key, ta_name, realm='__REST_CREDENTIAL__#TA-CloudKnox#configs/conf-ta_cloudknox_settings')
    has_upgraded = utility.check_has_upgraded_value(cfm, cloudknox_consts.inputs_upgradation_stanza)
    if has_upgraded == "0":
        _LOGGER.warning("Will continue data collection after the inputs are upgraded.")
        exit()

    _LOGGER.info("PAR: Started data collection for {} ".format(AUTH_SYS_TYPE))

    # # Initialize CloudKnoxCollect Object
    collect_obj = CloudKnoxCollect(session_key, app_name)

    # # # Get all authsystems using CloudKnoxCollect Object
    _LOGGER.info("Input: Fetching CloudKnox auth systems.")
    response = collect_obj.cloudknox_get_all_auth_systems()
    if not response:
        _LOGGER.info("Input: No CloudKnox auth systems found.")
        exit()

    # Get all auth systems
    ck_auth_systems = response.json().get("data")
    if "All" not in CONFIGURED_AUTH_SYS:
        auth_systems = [
            auth_sys
            for auth_sys in ck_auth_systems
            if (auth_sys.get("name") + " (" + auth_sys["id"] + ")")
            in CONFIGURED_AUTH_SYS and auth_sys["type"].upper() == AUTH_SYS_TYPE
            and auth_sys["status"].upper() != "OFFLINE"
        ]
        offline_auth_systems = [
            auth_sys.get("name") + " (" + auth_sys["id"] + ")"
            for auth_sys in ck_auth_systems
            if (auth_sys.get("name") + " (" + auth_sys["id"] + ")")
            in CONFIGURED_AUTH_SYS and auth_sys["type"].upper() == AUTH_SYS_TYPE
            and auth_sys["status"].upper() == "OFFLINE"
        ]
    else:
        auth_systems = [
            auth_sys
            for auth_sys in ck_auth_systems
            if auth_sys["type"].upper() == AUTH_SYS_TYPE and auth_sys["status"].upper() != "OFFLINE"
        ]
        offline_auth_systems = [
            auth_sys.get("name") + " (" + auth_sys["id"] + ")"
            for auth_sys in ck_auth_systems
            if auth_sys["type"].upper() == AUTH_SYS_TYPE and auth_sys["status"].upper() == "OFFLINE"
        ]
    if len(offline_auth_systems) != 0:
        _LOGGER.warning("Following auth systems are offline,"
                        " data for them will not be collected in this invokation - {}"
                        .format(','.join(offline_auth_systems)))
    chunked_auth_systems = [
        auth_systems[i:i + cloudknox_consts.AUTH_SYS_CHUNK_SIZE]
        for i in range(0, len(auth_systems), cloudknox_consts.AUTH_SYS_CHUNK_SIZE)
    ]

    # Collect data for each category
    for category in cloudknox_consts.CATEGORIES.get(AUTH_SYS_TYPE, {}):
        event_count = 0
        sourcetype = category.get("sourcetype")
        dataSummarySourcetype = sourcetype + ":summary"
        name = category.get("name")
        for each_chunked_auth_systems in chunked_auth_systems:
            each_chunked_auth_systems_map = {each["id"]: each["name"] for each in each_chunked_auth_systems}
            # Collect data for each subcategory within category
            for sub_category in category.get("subCategory", []):
                try:
                    responses = collect_obj.cloudknox_collect_par_data(
                        name, sub_category, each_chunked_auth_systems, AUTH_SYS_TYPE, cloudknox_consts.PAR_DATA_ENDPOINT
                    )
                    if responses:
                        for response in responses:
                            data = response.json().get("data")

                            # Create splunk events
                            for record in data:
                                record.update({"category": name, "subCategory": sub_category})
                                splunk_create_event(record, sourcetype, helper, ew)
                            event_count += len(data)
                except Exception as e:
                    _LOGGER.error("PAR: {}".format(str(e)))
                    break
            # Collect data for each summary data type within category
            for summaryDataType in category.get("summaryDataType", []):
                try:
                    responses = collect_obj.cloudknox_collect_par_data(
                        name, summaryDataType, each_chunked_auth_systems, AUTH_SYS_TYPE,
                        cloudknox_consts.PAR_DATA_SUMMARY_ENDPOINT, dataSummary=True
                    )
                    if responses:
                        for response in responses:
                            data = response.json().get("data")
                            for record in data:
                                event_asid = record.get("asId").strip()
                                record.get("summaryData").update({
                                    "asName": each_chunked_auth_systems_map.get(event_asid),
                                    "asId": event_asid,
                                    "category": name,
                                    "type": summaryDataType})
                                # Create splunk event
                                splunk_create_event(
                                    record.get("summaryData"), dataSummarySourcetype, helper, ew)
                            event_count += len(data)
                except Exception as e:
                    _LOGGER.error("PAR: {}".format(str(e)))
                    break
        # Collect data for Report summary data type within category
        if ("summaryType" in category):
            for auth_system in auth_systems:
                reportSummary = category.get("summaryType")
                try:
                    responses = collect_obj.cloudknox_collect_par_data(
                        name, reportSummary, auth_system, AUTH_SYS_TYPE,
                        cloudknox_consts.PAR_DATA_ENDPOINT, reportSummary=True
                    )
                    if responses:
                        for response in responses:
                            data = response.json()
                            data.update(
                                {"asName": auth_system.get("name"),
                                    "asId": auth_system.get("id"),
                                    "summaryType": reportSummary,
                                    "category": name})
                            # Create splunk event
                            splunk_create_event(
                                data, sourcetype, helper, ew)
                            event_count += 1
                except Exception as e:
                    _LOGGER.error("PAR: {}".format(str(e)))
                    break
        _LOGGER.info(
            "PAR: Number of events indexed for {} - {} are {}".format(
                AUTH_SYS_TYPE, category.get("name"), str(event_count)
            )
        )
    _LOGGER.info("PAR: Completed data collection for {} ".format(AUTH_SYS_TYPE))
