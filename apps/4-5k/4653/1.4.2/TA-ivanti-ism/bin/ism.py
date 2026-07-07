from __future__ import print_function
import sys
import os
import time
import datetime
import requests
import json
import logging
import copy

try:
    from urllib import unquote  # Python 2.X
except ImportError:
    from urllib.parse import unquote  # Python 3+


def ism_log(text, helper=None):
    if helper is not None:
        helper.log_info(text)
    else:
        print("LOCAL LOGGING: " + text)


def create_incident(
    auth_token,
    base_url,
    customer,
    summary,
    description,
    status,
    custom_fields="{}",
    helper=None,
    incident_type="standard",
):
    # Creates a new incident by building a payload and posting to the incidents endpoint

    # Hi Splunk Cloud vetting team - this is where I'm enforcing communication over HTTPS
    if not base_url.lower().startswith("https"):
        return None

    headers = {"Content-Type": "application/json", "Authorization": auth_token}

    # Get the recid of the nominated employee to use as the Customer for the new incident
    employee_recid = get_employee_recid(auth_token, base_url, customer, helper)

    path = ""
    payload = ""
    if incident_type == "security":
        path = "/api/odata/businessobject/ivnt_securityincidents"
        payload = {
            "ivnt_Subject": summary,
            "ivnt_Symptom": description,
            "ivnt_ProfileLink_RecID": employee_recid,
        }
    else:
        path = "/api/odata/businessobject/incidents"
        payload = {
            "Subject": summary,
            "Symptom": description,
            "Status": status,
            "ProfileLink_RecID": employee_recid,
        }

    # Add any custom key:value pairs, typically provided if a customer has customised which fields are mandatory for new tickets
    if (custom_fields is not None) and (custom_fields != ""):
        custom = json.loads(custom_fields)
        payload = merge_two_dicts(payload, custom)

    # Send the request to create the new incident
    try:
        response = requests.post(
            base_url + path, data=json.dumps(payload), headers=headers, verify=True
        )
        ism_log("Status code: " + str(response.status_code))
    except Exception as e:
        ism_log("Exception message: " + repr(str(e)), helper=helper)
        return None
    ism_log(
        "Incident Creation POST attempt status code: " + str(response.status_code),
        helper=helper,
    )

    r_json = None

    # Handle errors and log them for troubleshooting
    if response.status_code != 201:
        ism_log("Status code: " + str(response.status_code))
        try:
            r_json = response.json()
            ism_log("Description: " + r_json["description"])
            ism_log("Message: " + str(r_json["message"]))
        except:
            r_json = None

    return str(r_json)


def get_employee_recid(auth_token, base_url, name, helper=None):
    # Get the RecId of an employee based on LoginId

    path = "/api/odata/businessobject/employees"
    parameters = "$filter=LoginID eq '" + name + "'"
    result = get_busobjects(auth_token, base_url, path, parameters, 1)
    return result[0]["RecId"]


def authenticate(
    base_url, username, password, role, api_key="", helper=None
):
    # Return an auth token using either api key, or a value returned from authentication/login endpoint for a given username and pw

    # Hi Splunk Cloud vetting team - this is where I'm enforcing communication over HTTPS
    if not base_url.lower().startswith("https"):
        return None

    ism_log(helper=helper, text="entering ism.authenticate")
    if (api_key != None) and (api_key != ""):
        return "rest_api_key=" + api_key

    tenant = base_url.replace("https://", "")
    tenant = tenant.replace("http://", "")

    payload = {
        "tenant": tenant,
        "username": username,
        "password": password,
        "role": role,
    }

    redacted_payload = copy.copy(payload)
    redacted_payload["password"] = "redacted"
    ism_log(helper=helper, text=str(json.dumps(redacted_payload)))
    ism_log(helper=helper, text="Verify is {0}".format(str(verify)))
    ism_log(helper=helper, text="The type of verify is {0}".format(str(type(verify))))

    headers = {"Content-Type": "application/json"}

    response = requests.post(
        base_url + "/api/rest/authentication/login",
        data=json.dumps(payload),
        headers=headers,
        verify=True,
    )

    if response.status_code != 200:
        logging.warning("Failed to connect or authenticate")
        logging.info(response.content)
        exit()

    auth_token = (response.content).decode("UTF-8").replace('"', "")

    return auth_token


def get_incidents_simple(auth_token, base_url, parameters, helper=None):
    # Poll the incidents endpoint for incidents matching the supplied value of 'parameters'
    # Note that this function isn't currently used as get_incidents is an enhanced version that enriches incident objects with SLAs
    path = "/api/odata/businessobject/incidents"
    return get_busobjects(
        auth_token, base_url, path, parameters, 100, helper=helper
    )


def get_incidents(auth_token, base_url, parameters, helper=None):
    # Poll the incidents endpoint for incidents matching the supplied value of 'parameters'
    # Queries the Frs_data_escalation_watchs endpoint to get SLAs for the incidents
    path = "/api/odata/businessobject/incidents"
    incs = get_busobjects(
        auth_token, base_url, path, parameters, 100, helper=helper
    )

    breaches = get_busobjects(
        auth_token,
        base_url,
        "/api/odata/businessobject/Frs_data_escalation_watchs",
        "$filter=ClockState eq 'Run' and ParentLink_Category eq 'Incident'&$select=L3Passed, BreachPassed, BreachDateTime, RecId",
        100,
    )

    if breaches is None:
        return incs

    breach_times = {}
    for b in breaches:
        if b["BreachPassed"] == False:
            breach_times[b["RecId"]] = b["BreachDateTime"]
    for i in incs:
        if i["ResolutionEscLink_RecID"] in breach_times:
            i["BreachDateTime"] = breach_times[i["ResolutionEscLink_RecID"]]

    return incs


def get_servicereqs(auth_token, base_url, parameters, helper=None):
    # Poll the servicereqs endpoint for incidents matching the supplied value of 'parameters'
    path = "/api/odata/businessobject/servicereqs"
    return get_busobjects(
        auth_token, base_url, path, parameters, 100, helper=helper
    )


def get_problems(auth_token, base_url, parameters, helper=None):
    # Poll the problems endpoint for incidents matching the supplied value of 'parameters'
    path = "/api/odata/businessobject/problems"
    return get_busobjects(
        auth_token, base_url, path, parameters, 100, helper=helper
    )


def get_changes(auth_token, base_url, parameters, helper=None):
    # Poll the changes endpoint for incidents matching the supplied value of 'parameters'
    path = "/api/odata/businessobject/changes"
    return get_busobjects(
        auth_token, base_url, path, parameters, 100, helper=helper
    )


def get_busobjects(
    auth_token, base_url, path, parameters, page_size, helper=None
):
    # Helper function to query a given endpoint and handle paging to build a complete result set

    # Hi Splunk Cloud vetting team - this is where I'm enforcing communication over HTTPS
    if not base_url.lower().startswith("https"):
        return None

    headers = {"Content-Type": "application/json", "Authorization": auth_token}
    url = base_url + path + "?$top=" + str(page_size) + "&$skip=0&" + parameters

    try:
        response = requests.get(url, headers=headers, verify=True)
        ism_log("Status code: " + str(response.status_code))
    except Exception as e:
        ism_log("Exception message: " + repr(str(e)))
        return None

    # Handle errors and log them for troubleshooting
    if response.status_code != 200:
        ism_log("Status code: " + str(response.status_code))
        try:
            r_json = response.json()
            ism_log("Description: " + r_json["description"])
            ism_log("Message: " + str(r_json["message"]))
        except:
            r_json = None
            return {}

    r_json = response.json()
    values = response.json()["value"]
    logging.info("count returned by initial query: " + str(int(r_json["@odata.count"])))

    if r_json["@odata.count"] > page_size:
        count = int(r_json["@odata.count"])
        for i in range(page_size, count, page_size):
            logging.info("iterating with skip set to " + str(count))
            request_str = (
                base_url
                + path
                + "?$top="
                + str(page_size)
                + "&$skip="
                + str(i)
                + "&"
                + parameters
            )
            response = requests.get(request_str, headers=headers, verify=True)
            j2 = response.json()
            values.extend(j2["value"])

    return values


def merge_two_dicts(x, y):
    # Helper function to add values from one json object to another
    z = x.copy()  # start with x's keys and values
    z.update(y)  # modifies z with y's keys and values & returns None
    return z
