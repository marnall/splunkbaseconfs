#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import argparse
import time

import remedy_consts as c
import remedy_helper
import splunk.Intersplunk as sI
from account_manager import AccountManager
from logger_manager import get_logger
from multiprocessing.pool import ThreadPool
from solnlib import utils

_LOGGER = get_logger("rest_incident", True)

remedy_helper.set_logger(_LOGGER)


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        sI.parseError("{0}. {1}".format(message, self.format_usage()))


INCIDENT_CREATE_REQUIRED_FIELDS = {"account"}
INCIDENT_CREATE_OPTIONAL_FIELDS = {
    "Assigned Group Shift Name",
    "Assigned Group",
    "Assigned Support Company",
    "Assigned Support Organization",
    "Assignee",
    "Categorization Tier 1",
    "Categorization Tier 2",
    "Categorization Tier 3",
    "CI Name",
    "Closure Manufacturer",
    "Closure Product Category Tier1",
    "Closure Product Category Tier2",
    "Closure Product Category Tier3",
    "Closure Product Model/Version",
    "Closure Product Name",
    "Contact_Company",
    "Corporate ID",
    "Department",
    "Description",
    "Detailed_Decription",
    "Direct Contact First Name",
    "Direct Contact Last Name",
    "Direct Contact Middle Initial",
    "First_Name",
    "Flag_Create_Request",
    "HPD_CI_FormName",
    "HPD_CI_ReconID",
    "HPD_CI",
    "Impact",
    "Last_Name",
    "Login_ID",
    "Lookup Keyword",
    "Manufacturer",
    "Middle Initial",
    "Product Categorization Tier 1",
    "Product Categorization Tier 2",
    "Product Categorization Tier 3",
    "Product Model/Version",
    "Product Name",
    "Reported Source",
    "Resolution Category Tier 1",
    "Resolution Category Tier 2",
    "Resolution Category Tier 3",
    "Resolution",
    "Service_Type",
    "ServiceCI_ReconID",
    "ServiceCI",
    "Status_Reason",
    "Status",
    "TemplateID",
    "Urgency",
    "z1D_Action",
    "z1D_Activity_Type",
    "z1D_ActivityDate_tab",
    "z1D_CommunicationSource",
    "z1D_Details",
    "z1D_Secure_Log",
    "z1D_View_Access",
    "z1D_WorklogDetails",
    "z2AF_Act_Attachment_1",
    "custom_fields",
}

INCIDENT_UPDATE_REQUIRED_FIELDS = {"account", "Incident Number"}
INCIDENT_UPDATE_OPTIONAL_FIELDS = {
    "Categorization Tier 1",
    "Categorization Tier 2",
    "Categorization Tier 3",
    "Closure Manufacturer",
    "Closure Product Category Tier1",
    "Closure Product Category Tier2",
    "Closure Product Category Tier3",
    "Closure Product Model/Version",
    "Closure Product Name",
    "Company",
    "Description",
    "Detailed Decription",
    "HPD_CI_FormName",
    "HPD_CI_ReconID",
    "HPD_CI",
    "Impact",
    "Manufacturer",
    "Product Categorization Tier 1",
    "Product Categorization Tier 2",
    "Product Categorization Tier 3",
    "Product Model/Version",
    "Product Name",
    "Reported Source",
    "Resolution Category Tier 2",
    "Resolution Category Tier 3",
    "Resolution Category",
    "Resolution Method",
    "Resolution",
    "Service Type",
    "ServiceCI_ReconID",
    "ServiceCI",
    "Status_Reason",
    "Status",
    "Urgency",
    "z1D Action",
    "z1D_Activity_Type",
    "z1D_ActivityDate_tab",
    "z1D_CI_FormName",
    "z1D_CommunicationSource",
    "z1D_Details",
    "z1D_Secure_Log",
    "z1D_View_Access",
    "z1D_WorklogDetails",
    "z2AF_Act_Attachment_1",
    "custom_fields",
}


def add_url(results, account_info):
    """
    Function to add Incident URL to the custom command response
    :param results: List of incident details without Incident URL attached
    :param account_info: Account stanza name in the configuration file
    :return: List of incident details with Incident URL attached
    """
    smart_it_url = account_info.get("smart_it_url", None)
    if smart_it_url:
        smart_it_url = smart_it_url + c.SMART_IT_INSTANCE_ID_ENDPOINT
    for value in results:
        url_mode = (
            account_info.get("midtier_url", "").strip(" /")
            + "/arsys/forms/"
            + account_info.get("server_name", "").strip()
            + "/SHR:LandingConsole/Default Administrator View/?mode=search&F304255500=HPD:Help "
            "Desk&F1000000076=FormOpenNoAppList&F303647600=SearchTicketWithQual&F304255610"
            "='1000000161'=\"{}\""
        )
        url = url_mode.format(value["Incident Number"])
        value.update({"Incident Link": url})
        if smart_it_url:
            value.update({"Smart IT URL": smart_it_url.format(value["InstanceId"])})
    return results


def parse_arguments(required_fields, optional_fields):
    parser = ArgumentParser()

    for arg in required_fields:
        parser.add_argument(
            "--" + arg, dest=arg, type=str, action="store", required=True, help=arg
        )
    for arg in optional_fields - required_fields:
        parser.add_argument(
            "--" + arg, dest=arg, type=str, action="store", required=False, help=arg
        )

    opts = parser.parse_args()
    all_args = required_fields.union(optional_fields)
    event = {arg: getattr(opts, arg) for arg in all_args if hasattr(opts, arg)}
    return [event]


def remove_empty_fields(data):
    events = []

    for item in data:
        temp_events = {
            k: v for k, v in item["values"].items() if v is not None and v != ""
        }
        temp_events["_time"] = time.time()
        events.append(temp_events)
    return events


def extract_custom_fields(custom_field_str):
    # Extract custom_fields
    fields = {}
    raw_custom_fields = custom_field_str.strip()
    if not raw_custom_fields:
        return fields

    for item in raw_custom_fields.split("||"):
        field_kv_list = item.split("=", 1)
        # Verifying that custom fields are in key value format and key is not null
        if len(field_kv_list) == 2 and field_kv_list[0].strip():
            fields[field_kv_list[0].strip()] = field_kv_list[1].strip()
        else:
            raise ValueError(
                'custom_fields "{}" is not in key value format. Expected format: key1=value||key2=value2 ...'.format(
                    item
                )
            )
    return fields


def prepare_incident_data(
    events, account_manager, required_fields, optional_fields, default_fields
):
    incident_data = []
    for event in events:
        if "account" not in event:
            raise ValueError(
                'Unable to find "account" field in the event. Please provide "account" field.'
            )
        if event["account"].strip() == "":
            raise ValueError('Please provide valid value for the "account" field.')

        account_manager.get_account_details(event["account"])

        incident = {}
        for field in required_fields:
            if field not in event:
                raise ValueError(
                    'Unable to find "{0}" field in the event. Please provide "{0}" field.'.format(
                        field
                    )
                )
            value = event[field]
            if value.strip() == "":
                raise ValueError(
                    'Please provide valid value for the "{}" field.'.format(field)
                )

            incident[field] = value

        for field in optional_fields - required_fields:
            if (
                field in event
                and event[field] is not None
                and event[field] != ""
                and event[field] != "null"
            ):
                if field != "custom_fields":
                    incident[field] = event[field]
                else:
                    incident.update(extract_custom_fields(event[field]))

        for key, val in default_fields.items():
            if event.get(key) is None:
                incident[key] = val

        incident_data.append(incident)

    return incident_data


def parse_error(msg):
    try:
        response = msg.split("response")[1].strip("=").strip()
        return response
    except Exception:
        return msg


def create_incident(account_name, retrier, proxy_config, verify_ssl, data, count):
    """
    Invoke helper function to create an incident
    Args:
        account_name: name of the account configured
        retrier: object of Retry
        proxy_config: details of the proxy configured
        verify_ssl: SSL check configuration
        data: payload to create incident
    Returns:
        Incident Number of the incident created on success else error message
    """
    account_name = data.pop("account")
    data["z1D_Action"] = "CREATE"
    try:
        retrier.account_name = account_name
        response = retrier.retry(
            remedy_helper.create_incident,
            form_name=remedy_helper.INCIDENT_CREATE_FORM,
            params={"fields": "values(Incident Number)"},
            payload={"values": data},
            verify_ssl=verify_ssl,
            proxy_config=proxy_config,
            event_number=count,
        )
        _LOGGER.info(
            "[event_number={}], Successfully Created Incident. the Incident Number is {}".format(
                count, response["Incident Number"]
            )
        )
    except Exception as err:
        err_msg = parse_error(str(err))
        _LOGGER.exception(
            f"[event_number={count}], Failed to create incident. reason={err_msg}"
        )
        return {"Error Message": err_msg}

    return "'Incident Number'=\"{}\"".format(response["Incident Number"])


def handle_create_incident(events, session_key):
    """
    Parse the events and create incidents asynchronously using multi-threading
    Args:
        events: events data of the search results
        session_key: Session key for splunk
    """
    if len(events) == 0:
        return

    account_manager = AccountManager(session_key)
    proxy_config = remedy_helper.get_proxy_config(session_key)

    required_fields, default_fields = remedy_helper.get_remedy_fields(
        session_key, "create_incident_rest"
    )

    incident_data = prepare_incident_data(
        events,
        account_manager,
        required_fields.union(INCIDENT_CREATE_REQUIRED_FIELDS),
        INCIDENT_CREATE_OPTIONAL_FIELDS,
        default_fields,
    )

    account_name = incident_data[0]["account"]
    account_info = account_manager.get_account_details(account_name)

    verify_ssl = remedy_helper.get_sslconfig(
        session_key,
        utils.is_true(account_info.get("disable_ssl_certificate_validation", False)),
        _LOGGER,
    )

    retrier = remedy_helper.Retry(
        session_key, account_name, proxy_config, account_manager, verify_ssl
    )

    pool = ThreadPool(20)
    incident_query = []
    error_results = []
    create_incident_resp = []
    count = 0
    for item in incident_data:
        count += 1
        create_incident_resp.append(
            pool.apply_async(
                create_incident,
                args=(account_name, retrier, proxy_config, verify_ssl, item, count),
            )
        )
    pool.close()
    pool.join()

    for item in create_incident_resp:
        item = item.get()
        if isinstance(item, str):
            incident_query.append(item)
        else:
            error_results.append(item)

    refetch_events(
        incident_query,
        error_results,
        retrier,
        account_name,
        verify_ssl,
        proxy_config,
        account_info,
    )


def refetch_events(
    incident_query,
    error_results,
    retrier,
    account_name,
    verify_ssl,
    proxy_config,
    account_info,
):
    """
    Fetch incidents data from the Remedy and display in Splunk UI
    Args:
        incident_query: Incident Numbers to fetch the data
        error_results: Errors occured while creating/updating the incident
        retrier: object of Retry
        account_name: Name of the Remedy account configured
        verify_ssl: SSL check configuration
        proxy_config: Details of the proxy configured
        account_info: Details of the Remedy account configured
    """
    if len(incident_query) == 0:
        sI.outputResults(error_results)
        return
    else:
        results = []
        pool = ThreadPool(20)
        incident_data = []
        # example query: '\'Incident Number\'="<INC_NUMBER" OR \'Incident Number\'="<INC_NUMBER>" OR \'Incident Number\'="<INC_NUMBER>"'
        # incident query is divided into small batches to avoid URL too large error
        batch_size = 4900 // (
            len(incident_query[0]) + 4
        )  # total String length allowed in query string was observed as 5000 chars in postman
        retrier.account_name = account_name
        for i in range((len(incident_query) // batch_size) + 1):
            incident_batch = incident_query[i * batch_size : (i + 1) * batch_size]
            if len(incident_batch):
                params = {"q": " OR ".join(incident_batch)}
                incident_data.append(
                    pool.apply_async(
                        retrier.retry,
                        args=(
                            remedy_helper.fetch_form_data,
                            remedy_helper.INCIDENT_FORM,
                            params,
                            verify_ssl,
                            proxy_config,
                        ),
                    )
                )
        pool.close()
        pool.join()
        for data in incident_data:
            results.extend(data.get().get("entries", []))

        results = remove_empty_fields(results)
        results = add_url(results, account_info)
        results.extend(error_results)
        sI.outputResults(results)


def update_incident(
    account_name,
    retrier,
    request_id,
    incident_number,
    proxy_config,
    verify_ssl,
    data,
    count,
):
    """
    Invoke helper function to update an incident
    Args:
        account_name: name of the account configured
        retrier: object of Retry
        request_id: Request ID of the remedy incident
        incident_number: Incident Number
        proxy_config: details of the proxy configured
        verify_ssl: SSL check configuration
        data: payload to update incident
    Returns:
        Incident Number of the incident updated on success else error message
    """
    try:
        retrier.account_name = account_name
        retrier.retry(
            remedy_helper.update_incident,
            request_id=request_id,
            incident_number=incident_number,
            payload={"values": data},
            verify_ssl=verify_ssl,
            proxy_config=proxy_config,
            event_number=count,
        )
    except Exception as err:
        err_msg = parse_error(str(err))
        _LOGGER.error(
            '[event_number={}], Failed to update Incident Number "{}". Reason={}'.format(
                count, incident_number, err_msg
            )
        )
        return {"Error Message": err_msg}

    return "'Incident Number'=\"{}\"".format(incident_number)


def handle_update_incident(events, session_key):
    """
    Parse the events and update incidents asynchronously using multi-threading
    Args:
        events: events data of the search results
        session_key: Session key for splunk
    """
    if len(events) == 0:
        return

    account_manager = AccountManager(session_key)
    proxy_config = remedy_helper.get_proxy_config(session_key)

    required_fields, default_fields = remedy_helper.get_remedy_fields(
        session_key, "update_incident_rest"
    )

    incident_data = prepare_incident_data(
        events,
        account_manager,
        required_fields.union(INCIDENT_UPDATE_REQUIRED_FIELDS),
        INCIDENT_UPDATE_OPTIONAL_FIELDS,
        default_fields,
    )

    account_name = incident_data[0]["account"]
    account_info = account_manager.get_account_details(account_name)

    verify_ssl = remedy_helper.get_sslconfig(
        session_key,
        utils.is_true(account_info.get("disable_ssl_certificate_validation", False)),
        _LOGGER,
    )

    retrier = remedy_helper.Retry(
        session_key, account_name, proxy_config, account_manager, verify_ssl
    )

    incident_query = [
        "'Incident Number'=\"{}\"".format(data["Incident Number"])
        for data in incident_data
    ]

    # First need to get the "Request ID" of each incident
    retrier.account_name = account_name

    pool = ThreadPool(20)
    request_ids = []
    # example query: '\'Incident Number\'="<INC_NUMBER" OR \'Incident Number\'="<INC_NUMBER>" OR \'Incident Number\'="<INC_NUMBER>"'
    # incident query is divided into small batches to avoid URL too large error
    batch_size = 4900 // (
        len(incident_query[0]) + 4
    )  # total String length allowed in query string was observed as 5000 chars in postman
    for i in range((len(incident_query) // batch_size) + 1):
        incident_batch = incident_query[i * batch_size : (i + 1) * batch_size]
        if len(incident_batch):
            params = {
                "q": " OR ".join(incident_batch),
                "fields": "values(Incident Number, Request ID)",
            }
            request_ids.append(
                pool.apply_async(
                    retrier.retry,
                    args=(
                        remedy_helper.fetch_form_data,
                        remedy_helper.INCIDENT_FORM,
                        params,
                        verify_ssl,
                        proxy_config,
                    ),
                )
            )
    pool.close()
    pool.join()
    incident_id_lookup = {}
    for data in request_ids:
        incident_request_ids = data.get()
        incident_id_lookup.update(
            {
                item["values"]["Incident Number"]: item["values"]["Request ID"]
                for item in incident_request_ids.get("entries", [])
            }
        )

    pool = ThreadPool(20)
    incident_query = []
    error_results = []
    update_incident_resp = []
    relate_ci_resp = []
    count = 0
    hpd_ci = None
    for data in incident_data:
        count += 1
        account_name = data.pop("account")
        incident_number = data.pop("Incident Number")
        if data.get("HPD_CI"):
            hpd_ci = data.pop("HPD_CI")

        if incident_number not in incident_id_lookup:
            # will continue updating the incidents for the remaining events
            temp_msg = 'Unable to find Incident Number "{}" in the remedy.'.format(
                incident_number
            )
            _LOGGER.error(temp_msg)
            error_results.append({"Error Message": temp_msg})
            continue

        request_id = incident_id_lookup[incident_number]

        update_incident_resp.append(
            pool.apply_async(
                update_incident,
                args=(
                    account_name,
                    retrier,
                    request_id,
                    incident_number,
                    proxy_config,
                    verify_ssl,
                    data,
                    count,
                ),
            )
        )

        if hpd_ci:
            relate_ci_resp.append(
                pool.apply_async(
                    relate_ci_to_incident,
                    args=(
                        account_name,
                        retrier,
                        incident_number,
                        proxy_config,
                        verify_ssl,
                        hpd_ci,
                    ),
                )
            )

    pool.close()
    pool.join()

    for item in update_incident_resp:
        item = item.get()
        if isinstance(item, str):
            incident_query.append(item)
        else:
            error_results.append(item)

    for item in relate_ci_resp:
        item = item.get()
        if not isinstance(item, bool):
            error_results.append(item)

    refetch_events(
        incident_query,
        error_results,
        retrier,
        account_name,
        verify_ssl,
        proxy_config,
        account_info,
    )


def relate_ci_to_incident(
    account_name, retrier, incident_number, proxy_config, verify_ssl, hpd_ci
):
    """
    Invoke helper function to relate a CI to an incident
    Args:
        account_name: name of the account configured
        retrier: object of Retry
        incident_number: Incident Number
        proxy_config: details of the proxy configured
        verify_ssl: SSL check configuration
        hpd_ci: CI Name to be related to the incident
    Returns:
        True on success else error message
    """
    try:
        data = {
            "Incident Number": incident_number,
            "HPD_CI": hpd_ci,
            "z1D_Action": "RELATE_CI",
        }
        retrier.account_name = account_name
        retrier.retry(
            remedy_helper.relate_ci_to_incident,
            payload={"values": data},
            verify_ssl=verify_ssl,
            proxy_config=proxy_config,
        )
    except Exception as err:
        err_msg = parse_error(str(err))
        _LOGGER.error(
            'Failed to relate CI for Incident Number "{}". Reason={}'.format(
                incident_number, err_msg
            )
        )
        return {"Error Message": err_msg}

    return True
