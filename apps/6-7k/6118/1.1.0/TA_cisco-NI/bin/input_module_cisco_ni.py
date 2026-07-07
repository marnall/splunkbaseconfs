# encoding = utf-8

import json
import requests
import cisco_ni_constants
# import threadpool
import time
from datetime import datetime, timedelta
from logger_manager import setup_logging

"""
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
"""
"""
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
"""
ORIGINAL_HOSTS = []
TRIED_HOSTS = []


class NexusInsightsParameters(object):
    """Class responsible for all communication with the Nexus Dashboard Insights."""

    def __init__(
        self, count, ew, global_account, helper, ni_host, no_of_threads, timeout, verify_ssl, logger
    ):
        """
        Initialize object with given parameters.

        :param count: Page number for which we want to fetch data
        :type count: int
        :param ew: object of EventWriter class
        :param helper: object of BaseModInput class
        :param ni_host: Hostname/IP address of Nexus Dashboard Insights instance.
        :type ni_host: string
        :param timeout: The timeout interval for http/https request.
        :type timeout: int
        :param verify_ssl: Used only for SSL connections with the MSO.\
        Indicates whether SSL certificates must be verified.  Possible\
        values are True and False with the default being False.
        :type verify_ssl: boolean
        """
        self.count = count
        self.global_account = global_account
        self.helper = helper
        self.ni_host = ni_host
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.ew = ew
        self.token = None
        self.data_count = 0
        self.data_count_API = 0
        self.no_of_threads = no_of_threads
        self.logger = logger

    def get(self, endpoint_url, params=None):
        """
        Hit particular endpoint and fetch data.

        :param endpoint_url: Endpoint URL for which we want to fetch data.
        :type endpoint_url: string
        :param params: The parameter to be set for http/https request.
        :type params: dict
        """
        global ORIGINAL_HOSTS, TRIED_HOSTS

        remaining_hosts = list(set(ORIGINAL_HOSTS) - set(TRIED_HOSTS))
        url = "https://{hostname}/{url}".format(hostname=self.ni_host, url=endpoint_url)

        response = self.helper.send_http_request(
            url=url,
            method="GET",
            headers=self.form_headers(),
            parameters=params,
            verify=self.verify_ssl,
            timeout=self.timeout,
            use_proxy=True,
        )

        if response.status_code == 200 or response.status_code == 201:
            return response.json()
        elif response.status_code == 401:
            self.logger.debug("Nexus Dashboard Insights Error: Performing Nexus Dashboard Insights relogin.")
            try:
                self.login()
                return self.get(endpoint_url, params)
            except Exception as err:
                self.logger.error(
                    "Nexus Dashboard Insights Error: Could not re-login to Nexus Dashboard Insights. "
                    "Error: {err}.".format(err=err)
                )
                raise

        # retry only when exception occurs from server side and 429 error on client side
        elif response.status_code == 429 or 500 <= response.status_code < 600:
            self.logger.warning(
                "Nexus Dashboard Insights Warning: Received error for URL: {url} params: {params}. "
                "Response Code: {code}. Response: {response}".format(
                    url=url, params=params, code=response.status_code, response=response.text
                )
            )
            retries = 3
            while retries > 0:
                if response.status_code == 429:
                    time.sleep(15)

                self.logger.debug(
                    "Retrying: URL:{url} params: {params}".format(url=url, params=params)
                )
                response = self.helper.send_http_request(
                    url=url,
                    method="GET",
                    headers=self.form_headers(),
                    parameters=params,
                    verify=self.verify_ssl,
                    timeout=self.timeout,
                )
                if response.status_code == 200 or response.status_code == 201:
                    return response.json()
                elif response.status_code == 401:
                    self.logger.debug(
                        "Nexus Dashboard Insights Error: Performing Nexus Dashboard Insights relogin.")
                    try:
                        self.login()
                    except Exception as err:
                        self.logger.error(
                            "Nexus Dashboard Insights Error: Could not re-login to Nexus Dashboard Insights. "
                            "Error: {err}.".format(err=err)
                        )
                        raise
                self.logger.debug(
                    "Retrying was not successful for URL:{url}"
                    " params: {params}".format(url=url, params=params)
                )
                retries -= 1
            if retries == 0:
                if len(remaining_hosts) == 0:
                    self.logger.error(
                        "%% Nexus Dashboard Insights Error: URL:{url} params: {params} Response Code: {code}."
                        " Response: {response}".format(
                            url=url,
                            code=response.status_code,
                            response=response.text,
                            params=params,
                        )
                    )
                    if len(ORIGINAL_HOSTS) > 1:
                        self.logger.error(
                            "Nexus Dashboard Insights Error: None of the cluster host is "
                            "reachable: {}.".format(", ".join(ORIGINAL_HOSTS))
                        )
                    response.raise_for_status()
                else:
                    self.logger.error(
                        "% Nexus Dashboard Insights Error: URL:{url} params: {params} Response Code: {code}."
                        " Response: {response}".format(
                            url=url,
                            code=response.status_code,
                            response=response.text,
                            params=params,
                        )
                    )
                    self.ni_host = remaining_hosts[0]
                    self.logger.warning(
                        "Nexus Dashboard Insights Warning: Performing login in Host: {} to fetch further "
                        "data.".format(self.ni_host)
                    )
                    self.login()
                    return self.get(endpoint_url, params)
        else:
            if len(remaining_hosts) == 0:
                self.logger.error(
                    "Nexus Dashboard Insights Error: URL:{url} params: {params} Response Code: {code}."
                    " Response: {response}".format(
                        url=url, code=response.status_code, response=response.text, params=params
                    )
                )
                if len(ORIGINAL_HOSTS) > 1:
                    self.logger.error(
                        "Nexus Dashboard Insights Error: None of the cluster host is reachable: {}.".format(
                            ", ".join(ORIGINAL_HOSTS)
                        )
                    )
                response.raise_for_status()
            else:
                self.logger.error(
                    "Nexus Dashboard Insights Error: URL:{url} params: {params} Response Code: {code}."
                    " Response: {response}".format(
                        url=url, code=response.status_code, response=response.text, params=params
                    )
                )
                self.ni_host = remaining_hosts[0]
                self.logger.warning(
                    "Nexus Dashboard Insights Warning: Performing login in Host: {} "
                    "to fetch further data.".format(
                        self.ni_host
                    )
                )
                self.login()
                return self.get(endpoint_url, params)

    def login(self):
        """Perform login Nexus Dashboard Insights instance and set token."""
        global ORIGINAL_HOSTS, TRIED_HOSTS
        TRIED_HOSTS.append(self.ni_host)

        self.logger.info(
            "Nexus Dashboard Insights Info: Hit login endpoint for Host: {host}".format(host=self.ni_host)
        )

        msg = "Nexus Dashboard Insights Error: An Error Occured while logging in Host: {}".format(
            self.ni_host
        )
        login_domain = (
            "DefaultAuth"
            if self.global_account["account_type"] == "local_user_authentication"
            else self.global_account["login_domain"]
        )

        credentials = {
            "userName": self.global_account["username"],
            "userPasswd": self.global_account["password"],
            "domain": login_domain,
        }
        credentials = json.dumps(credentials)
        url = "https://{hostname}/{url}".format(hostname=self.ni_host, url=cisco_ni_constants.LOGIN)
        try:
            response = self.helper.send_http_request(
                url=url,
                method="POST",
                payload=credentials,
                verify=self.verify_ssl,
                timeout=self.timeout,
            )
            if response.status_code == 200 or response.status_code == 201:
                self.logger.debug(
                    "Login Successful for Nexus Insight: {host}".format(host=self.ni_host)
                )
                self.token = response.json()["token"]
                return self.token

            # retry only when exception occurs from server side and 429 error on client side
            elif response.status_code == 429 or 500 <= response.status_code < 600:
                self.logger.warning(
                    "Nexus Dashboard Insights Warning: Received error for Host: {host}."
                    " Response Code: {code}. Response: {response}".format(
                        host=self.ni_host, code=response.status_code, response=response.text
                    )
                )
                retries = 3
                while retries > 0:
                    if response.status_code == 429:
                        time.sleep(15)

                    self.logger.debug("Retrying login")
                    response = self.helper.send_http_request(
                        url=url,
                        method="POST",
                        payload=credentials,
                        verify=self.verify_ssl,
                        timeout=self.timeout,
                    )
                    if response.status_code == 200 or response.status_code == 201:
                        self.logger.debug("Login retry was successful.")
                        self.token = response.json()["token"]
                        return self.token
                    retries -= 1
                if retries == 0:
                    self.logger.error(
                        "{msg}. Response Code: {code}. Response: {response}".format(
                            msg=msg, code=response.status_code, response=response.text
                        )
                    )
                    response.raise_for_status()
            else:
                self.logger.error(
                    "{msg}. Response Code: {code}. Response: {response}".format(
                        msg=msg, code=response.status_code, response=response.text
                    )
                )
                response.raise_for_status()
        except requests.exceptions.SSLError:
            self.logger.error(
                "Nexus Dashboard Insights Error: Please provide valid SSL certificate or "
                "disbale SSL Certificate validation for host: {host}.".format(host=self.ni_host)
            )
            return False
        except Exception as e:
            self.logger.error("{msg}. Error: {err}".format(msg=msg, err=str(e)))
            return False

    def form_headers(self):
        """Form token for URL endpoint."""
        headers = {
            "Authorization": "Bearer {}".format(self.token),
            "Content-Type": "application/json",
        }
        return headers

    def get_fabric_details(self):
        """Fetch the fabric endpoint data and form the list of fabrics in given NI."""
        endpoint_url = cisco_ni_constants.get_url("insightsGroup")
        insights_group_fabrics_dict = {}
        try:
            insights_group_response = self.get(endpoint_url)
            if insights_group_response:
                insights_group = insights_group_response.get("value", {})
                if len(insights_group) > 0:
                    insights_group = insights_group.get("data", {})
                    if len(insights_group) > 0:
                        for data in insights_group:
                            insights_group = data.get("name", None)
                            if insights_group:
                                insights_group_fabrics_dict[insights_group] = []
                                assuranceEntities = data.get("assuranceEntities")
                                for entitiy in assuranceEntities:
                                    insights_group_fabrics_dict[insights_group].append(
                                        entitiy["name"]
                                    )
        except Exception as e:
            self.logger.error(
                "Nexus Dashboard Insights Error: An Error Occured while fetching Insights Group data. "
                "Endpoint URL: {url} and Host: {host}. Error: {err}".format(
                    url=endpoint_url, host=self.ni_host, err=str(e)
                )
            )
            return None
        return insights_group_fabrics_dict

    def get_endpoint_details(self, fabric_list, group, startTs_from_hrs_configured, current_time):
        """
        Fetch the anomalies/advisories data for particular fabric and print events in Splunk.

        :param fabric_list: List of all fabrics in NI.
        :type fabric_list: list
        """
        alert_type = self.helper.get_arg("alert_type")
        endpoint_url = cisco_ni_constants.get_url(alert_type)
        current_time = current_time.isoformat() + "Z"
        index = self.helper.get_arg("index")
        source_type = "cisco:ni:" + alert_type
        params = {"count": self.count, "orderBy": "endTs,asc"}

        severity_list = self.helper.get_arg("severity")
        if alert_type == "advisories":
            category_list = self.helper.get_arg("advisories_category")
        else:
            category_list = self.helper.get_arg("anomalies_category")

        if "*" in severity_list and "*" in category_list:
            filter_str = ""
        elif "*" in severity_list:
            filter_str = " OR ".join(category_list)
        elif "*" in category_list:
            filter_str = " OR ".join(severity_list)
        else:
            filter_str = ""
            for category in category_list:
                for severity in severity_list:
                    filter_str += "(" + severity + " AND " + category + ") OR "
            filter_str = filter_str[:-4]

        if filter_str != "":
            params["filter"] = filter_str

        # threads = threadpool.ThreadPool(self.no_of_threads)
        hrs_configured = int(self.helper.get_arg("time_range"))

        for fabric_name in fabric_list:
            total_Items_Count = None
            key = self.helper.get_arg("name") + "_" + group + "_" + fabric_name + "_" + alert_type
            chkpt_start_time = self.helper.get_check_point(key)
            # Logic to convert hours to relative time
            if chkpt_start_time:
                startTs = datetime.strptime(chkpt_start_time, "%Y-%m-%dT%H:%M:%S.%fZ") + timedelta(
                    seconds=0.001
                )
                startTs = startTs.isoformat() + "Z"
                self.logger.info(
                    "Nexus Dashboard Insights Info: Found an existing checkpoint with value: {startTs} for "
                    " {alert_type} endpoint Insights Group: {group} for fabric:"
                    "  {fabric} and Host: {host}.".format(
                        startTs=startTs,
                        alert_type=alert_type,
                        fabric=fabric_name,
                        group=group,
                        host=self.ni_host,
                    )
                )
            elif hrs_configured == 0:
                startTs = "1970-01-01T00:00:00Z"
                self.logger.info(
                    "Nexus Dashboard Insights Info: No existing checkpoint found, starting data collection"
                    " to collect all events with value: {startTs} for "
                    " {alert_type} endpoint Insights Group: {group} for fabric:"
                    "  {fabric} and Host: {host}".format(
                        startTs=startTs,
                        alert_type=alert_type,
                        fabric=fabric_name,
                        group=group,
                        host=self.ni_host,
                    )
                )
            else:
                startTs = startTs_from_hrs_configured.isoformat() + "Z"
                self.logger.info(
                    "Nexus Dashboard Insights Info: No existing checkpoint found,"
                    " starting data collection with value: {startTs} for "
                    " {alert_type} endpoint Insights Group: {group} for fabric:"
                    "  {fabric} and Host: {host}".format(
                        startTs=startTs,
                        alert_type=alert_type,
                        fabric=fabric_name,
                        group=group,
                        host=self.ni_host,
                    )
                )
            self.logger.info(
                "Nexus Dashboard Insights Info: Value of startTs: {startTs} endTs: {endTs} for {alert_type}"
                " endpoint for Insights Group: {group} for fabric: {fabric} "
                "and Host: {host}.".format(
                    startTs=startTs,
                    endTs=current_time,
                    alert_type=alert_type,
                    group=group,
                    fabric=fabric_name,
                    host=self.ni_host,
                )
            )

            offset = 0
            params["fabricName"] = fabric_name
            params["startTs"] = startTs
            params["endTs"] = current_time

            try:
                while True:
                    params["offset"] = offset
                    response = self.get(endpoint_url, params=params)
                    if response:
                        entries_events = response.get("entries", [])
                        if len(entries_events) > 0:
                            total_Items_Count = response.get("totalResultsCount", None)
                            for events in entries_events:
                                events["ni_host"] = self.ni_host
                                events["insights_group"] = group
                                # endpoint_id = (
                                #     events["anomalyId"]
                                #     if alert_type == "anomalies"
                                #     else events["advisoryId"]
                                # )
                                # threads.add_task(
                                #     self.get_id_details,
                                #     endpoint_id,
                                #     fabric_name,
                                #     events["startTs"],
                                #     events["endTs"],
                                # )
                                event = self.helper.new_event(
                                    json.dumps(events),
                                    index=index,
                                    sourcetype=source_type,
                                    source=alert_type,
                                )
                                self.ew.write_event(event)
                                endTs = events["endTs"]
                            self.helper.save_check_point(key, endTs)
                            self.logger.info(
                                "Nexus Dashboard Insights Info: Value saved in checkpoint: {startTs} for "
                                " {alert_type} endpoint Insights Group: {group} for fabric:"
                                "  {fabric} and Host: {host}.".format(
                                    startTs=endTs,
                                    alert_type=alert_type,
                                    fabric=fabric_name,
                                    group=group,
                                    host=self.ni_host,
                                )
                            )
                            self.data_count += len(entries_events)
                        else:
                            self.logger.info(
                                "Nexus Dashboard Insights Info: Value saved in checkpoint: {startTs} for "
                                " {alert_type} endpoint Insights Group: {group} for fabric:"
                                "  {fabric} and Host: {host}.".format(
                                    startTs=self.helper.get_check_point(key),
                                    alert_type=alert_type,
                                    fabric=fabric_name,
                                    group=group,
                                    host=self.ni_host,
                                )
                            )
                            break
                    offset += self.count
                if total_Items_Count:
                    self.data_count_API += total_Items_Count
            except Exception as e:
                if total_Items_Count:
                    self.data_count_API += total_Items_Count
                self.logger.error(
                    "Nexus Dashboard Insights Error: An Error Occured while fetching data "
                    "for {alert_type} data."
                    " URL: {url} and Host: {host}. Error: {err}".format(
                        alert_type=alert_type, url=endpoint_url, host=self.ni_host, err=str(e)
                    )
                )

        # threads.wait_completion()

    # def get_id_details(self, endpoint_id, fabric_name, startTs, endTs):
    #     """
    #     Fetch recommendations data for particular anomalies/advisories ID and print in Splunk.

    #     :param endpoint_id: ID of anomalies/advisories.
    #     :type endpoint_id: string
    #     :param fabric_name: Fabric Name for particular anomalies/advisories ID.
    #     :type fabric_name: string
    #     :param startTs: Value of startTs field for response of particular anomalies/advisories ID.
    #     :type startTs: string
    #     :param endTs: Value of endTs field for response of particular anomalies/advisories ID.
    #     :type endTs: string
    #     """
    #     alert_type = self.helper.get_arg("alert_type")

    #     endpoint_url = cisco_ni_constants.get_url(
    #         endpoint="recommendations", recomd_type=alert_type
    #     )
    #     index = self.helper.get_arg("index")
    #     source_type = "cisco:ni:" + alert_type
    #     source = "recommend:" + alert_type
    #     params = {}
    #     params["fabricName"] = fabric_name
    #     try:
    #         parameter = "anomalyId" if alert_type == "anomalies" else "advisoryId"
    #         params[parameter] = endpoint_id
    #         response = self.get(endpoint_url, params=params)
    #         if response:
    #             entries_events = response.get("entries", [])
    #             if len(entries_events) > 0:
    #                 events = {}
    #                 events["entries"] = entries_events
    #                 events["ni_host"] = self.ni_host
    #                 events["fabric"] = fabric_name
    #                 events["startTs"] = startTs
    #                 events["endTs"] = endTs
    #                 events[parameter] = endpoint_id
    #                 event = self.helper.new_event(
    #                     json.dumps(events), index=index, sourcetype=source_type, source=source
    #                 )
    #                 self.ew.write_event(event)
    #     except Exception as e:
    #         self.logger.error(
    #             "Nexus Dashboard Insights Error: An Error Occured while fetching Recommendation data for "
    #             " endpoint: {url} params: {params} host: {host}. Error: {err}".format(
    #                 url=endpoint_url, params=params, host=self.ni_host, err=str(e)
    #             )
    #         )


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations."""
    interval = definition.parameters.get("interval", None)
    time_range = definition.parameters.get("time_range", None)
    if int(time_range) < 0:
        helper.log_error("Validation Error: Time Range should be greater than or equal to zero.")
        raise ValueError("Time Range should be greater than or equal to zero.")
    if int(interval) < 60:
        helper.log_error("Minimum value of interval should be 60.")
        raise ValueError("Validation Error: Minimum value of interval should be 60.")


def collect_events(helper, ew):
    """Implement your data collection logic here."""
    global ORIGINAL_HOSTS
    logger = setup_logging("ta_cisco_ni_cisco_ni_{}".format(helper.get_input_stanza_names()))

    script_start_time = time.time()
    logger.info("Script Invoked for Input: {}".format(helper.get_arg("name")))

    global_account = helper.get_arg("global_account")
    ni_hosts = global_account["ni_hostname"].split(",")

    for index in range(len(ni_hosts)):
        ni_hosts[index] = ni_hosts[index].strip()

    ORIGINAL_HOSTS = ni_hosts
    login_flag = True

    try:
        no_of_threads = cisco_ni_constants.NUMBER_OF_THREADS
        if no_of_threads not in range(1, 17):
            logger.error(
                "Nexus Dashboard Insights Error: Number of threads should be greater than zero"
                " and less than or equal to 16. "
                "Please change the value first and then enable the script "
            )
            return
    except Exception as e:
        logger.error(
            "Nexus Dashboard Insights Error: Error occured while fetching number of threads from "
            " cisco_ni_constants.py Exception: {}. Defaulting to 16".format(str(e))
        )
        no_of_threads = 16

    try:
        count = cisco_ni_constants.COUNT
        if not isinstance(count, int) or count <= 0:
            logger.error(
                "Nexus Dashboard Insights Error: Count should be an integer greater than zero. "
                "Please change the value first and then enable the script. "
            )
            return
    except Exception as e:
        logger.error(
            "Nexus Dashboard Insights Error: Error occured while fetching value of count from "
            "cisco_ni_constants.py. Exception: {}. Defaulting to 100".format(str(e))
        )
        count = 100

    try:
        timeout = cisco_ni_constants.TIMEOUT
        if timeout <= 0:
            logger.error(
                "Nexus Dashboard Insights Error: Timeout should be greater than zero. "
                "Please change the value first and then enable the script. "
            )
            return
    except Exception as e:
        logger.error(
            "Nexus Dashboard Insights Error: Error occured while fetching timeout from cisco_ni_constants.py"
            "Exception: {}. Defaulting to 180".format(str(e))
        )
        timeout = 180

    hrs_configured = int(helper.get_arg("time_range"))
    current_time = datetime.utcnow()
    startTs_from_hrs_configured = current_time - timedelta(hours=hrs_configured)
    for ni_host in ni_hosts:
        nexus_insights_object = NexusInsightsParameters(
            count,
            ew,
            global_account,
            helper,
            ni_host,
            no_of_threads,
            timeout,
            cisco_ni_constants.VERIFY_SSL,
            logger,
        )
        token = nexus_insights_object.login()
        if token:
            # Fetch Fabrics for NI
            insights_group_fabrics_dict = nexus_insights_object.get_fabric_details()
            login_flag = False
            try:
                if insights_group_fabrics_dict:
                    for group in insights_group_fabrics_dict:
                        fabric_list = insights_group_fabrics_dict[group]
                        logger.info(
                            "Nexus Dashboard Insights Info: Insights Group:"
                            " {group} Number of Fabric/s: {num_fabric} "
                            "List of Fabric/s: {fabrics} for Host: {host}.".format(
                                group=group,
                                num_fabric=len(fabric_list),
                                fabrics=fabric_list,
                                host=ni_host,
                            )
                        )
                        nexus_insights_object.get_endpoint_details(
                            fabric_list, group, startTs_from_hrs_configured, current_time
                        )
                else:
                    logger.warning(
                        "Nexus Dashboard Insights Warning: No Insights Group found for Host: {host}.".format(
                            host=ni_host
                        )
                    )
            except Exception as e:
                logger.error(
                    "Nexus Dashboard Insights Error: An Error Occured while fetching {endpt} details for "
                    "Host: {host}. Error: {err}".format(
                        endpt=helper.get_arg("alert_type"), host=ni_host, err=str(e)
                    )
                )
            break

    if len(ni_hosts) > 1 and login_flag and ni_hosts[-1] == ni_host:
        logger.error(
            "Nexus Dashboard Insights Error: Not able to login"
            " in any of the cluster instance: {host}".format(host=ni_hosts)
        )

    logger.info(
        "Total no. of events in API Response: {}".format(nexus_insights_object.data_count_API)
    )
    logger.info("Total no. of collected events is: {}".format(nexus_insights_object.data_count))
    logger.info(
        "Execution of the script is finished for input: {}. Time taken: {} minutes.".format(
            helper.get_arg("name"), (time.time() - script_start_time) / 60
        )
    )
