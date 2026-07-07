from datetime import datetime
import splunk.entity as entity
import sys
import os
import mso_session
import mso_urls
import xml.sax.saxutils as xss
import logger_manager

logger = logger_manager.get_logger("mso")

TIMEOUT = 180
myapp = os.path.abspath(__file__).split(os.sep)[-3]


class PrintResponseInSplunk(object):
    """This class consists of all methods that will parse the API response and print on Splunk side."""

    def __init__(self):
        """Initialize response."""
        self.response = []

    def dict_parse(self, data_to_be_parsed, keyset=None):
        """
        Covert the response in key=value format.

        :param data_to_be_parsed: The API data which will be parsed depending on datatype.
        :type keyset: dict
        :param keyset: Holds good, whenever we want to combine keys of nested response.
        :type keyset: string
        """
        if isinstance(data_to_be_parsed, dict):
            for key, val in list(data_to_be_parsed.items()):

                if isinstance(val, dict):
                    for key2, val2 in list(val.items()):
                        if keyset:
                            self.dict_parse(
                                val2, "{keyset}_{key}_{key2}".format(keyset=str(keyset), key=str(key), key2=str(key2))
                            )
                        else:
                            self.dict_parse(val2, "{key}_{key2}".format(key=str(key), key2=str(key2)))
                elif isinstance(val, list) and len(val) > 0:
                    if keyset:
                        self.list_parse(val, "{keyset}_{key}".format(keyset=str(keyset), key=str(key)))
                    else:
                        self.list_parse(val, str(key))
                elif isinstance(val, list) is False and isinstance(val, dict) is False:
                    if keyset:
                        self.response.append("{keyset}_{key}={val}".format(keyset=str(keyset), key=str(key), val=val))
                    else:
                        self.response.append("{key}={val}".format(key=str(key), val=str(val)))

        elif isinstance(data_to_be_parsed, list) and len(data_to_be_parsed) > 0:
            self.list_parse(data_to_be_parsed, keyset)

        elif isinstance(data_to_be_parsed, list) is False and isinstance(data_to_be_parsed, dict) is False:
            if keyset:
                self.response.append("{key}={val}".format(key=str(keyset), val=str(data_to_be_parsed)))

    def list_parse(self, data_to_be_parsed, keys, only_list_resp=False):
        """
        Iterate list elements and calls dict_parse method for further parsing.

        :param data_to_be_parsed: The API data which will be parsed depending on datatype.
        :type data_to_be_parsed: list
        :param keys: Holds good, whenever we want to combine keys of nested response.
        :type keys: string
        :param only_list_resp: Holds good, whenever json response is only array and not objects.
        :type only_list_resp: bool
        """
        if only_list_resp:
            for data in data_to_be_parsed:
                self.response.append("{key}={val}".format(key=str(keys), val=str(data)))
        else:
            for data in data_to_be_parsed:
                self.dict_parse(data, keys)

    def print_response(self, data, splunk_field, host, response_key=None, api_name=None, endpt_id=None):
        """
        Parse the response in key=value format and print on Splunk side.

        :param data: The data to be printed in Splunk.
        :type data: JSON
        :param response_key: Holds good whenever json response is only array and not objects,
                             since it is the only key in response.
        :type response_key: string
        :param splunk_field: The value for mso_api_endpoint field to be ingested in Splunk.
                             i.e. mso_api_endpoint=splunk_field, so user can know what response of which API is.
        :type splunk_field: string
        :param host: The value of mso_host field to be ingested in Splunk i.e. mso_host=host,
                     so user can know collected data belongs to which MSO host.
        :type host: string
        :param api_name: Holds good whenever API calls fetch specific endpoints details and not entire details.
                         Eg: api/v1/policies/usage/{policy_id}: to get policy usage details for various policy id.
                         Thus api_name=policy
        :type api_name: string
        :param endpt_id: The value of mso_api_name_id field to be ingested in Splunk i.e. mso_api_name_id=endpt_id,
                         so user can know collected data belongs to which id of MSO API.
                         Eg: api/v1/policies/usage/{policy_id}: To get policy usage details for various policy ids.
                         Thus mso_policy_id= policy_id
        :type endpt_id: string
        """
        events_ingested_count = 0
        for mso_data in data:

            self.response = []

            current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")

            if splunk_field == "msoAuditRecords":
                timestamp_field = mso_data.get("timestamp")
                if timestamp_field:  # bcz timestamp field is coming in UTC timezone
                    self.response.append("current_time=" + str(timestamp_field) + "Z")
                else:
                    self.response.append("current_time=" + str(current_time))
            else:
                self.response.append("current_time=" + str(current_time))

            self.response.append("mso_host=" + host)
            self.response.append("mso_api_endpoint=" + splunk_field)

            # Because the response of APIs for specific id, does not have id in it
            if api_name and endpt_id:
                if api_name == "fabric":
                    self.response.append("mso_site_id=" + str(endpt_id))
                else:
                    self.response.append("mso_" + api_name + "_id=" + str(endpt_id))

            if not isinstance(mso_data, list) and not isinstance(mso_data, dict):
                if isinstance(data, list) and len(data) > 0:
                    self.list_parse(data, response_key, True)
                    print("\t".join(self.response))
                    events_ingested_count += 1
                    print("\n")
                    break

                if isinstance(data, dict):
                    self.dict_parse(data)
                    print("\t".join(self.response))
                    events_ingested_count += 1
                    print("\n")
                    break

            else:
                for keys in mso_data:
                    if str(mso_data[keys]):
                        if isinstance(mso_data[keys], dict):
                            self.dict_parse(mso_data[keys], keys)
                        elif isinstance(mso_data[keys], list) and len(mso_data[keys]) > 0:
                            self.list_parse(mso_data[keys], keys)
                        else:
                            self.response.append(keys + "=" + str(mso_data[keys]))
                print("\t".join(self.response))
                events_ingested_count += 1
                print("\n")

        return events_ingested_count


class GetAPIResponse(object):
    """This class consists of all functions, that will hit various APIs of required endpoints."""

    def __init__(self, session, mso_host):
        """
        Initialize object with given parameters.

        :param session: MSO session
        :type session: session object
        :param mso_host: Hostname/IP address of MSO
        :type mso_host: string
        """
        self.session = session
        self.print_response_object = PrintResponseInSplunk()

        host_split_by_port = mso_host[::-1].split(":", 1)
        # host variable consists of only mso_host and not port number
        self.host = host_split_by_port[1][::-1] if len(host_split_by_port) == 2 else host_split_by_port[0][::-1]

    @staticmethod
    def fetch_ids(data):
        """Iterate over data to get value of id field returned in API response."""
        ids = []
        for elements in data:
            if elements.get("id"):
                ids.append(elements.get("id"))
        return ids

    def _getResponseForSpecificID(self, mso_api_endpoint, ids, api_name):
        """
        Fetch the data for all APIs that require specific id to fetch data.

        Example: The API call will need specific policy id /api/v1/policies/usage/{id}.
        :param mso_api_endpoint: The MSO API endpoint from data is to be fetched.
        :type mso_api_endpoint: string
        :param ids: Fetch endpoint data only for given IDs.
                Eg: api/v1/policies/usage/{policy_id}: Here we want policy usage details for various policy ids.
                So we will hit this endpoint for values in ids list.
        :type ids: list
        :param api_name: Name of MSO API
        :type api_name: string
        """
        for splunk_field, endpt in list(mso_api_endpoint.items()):
            for endpt_id in ids:
                events_ingested_count = 0
                try:
                    endpoint = endpt.format(id=endpt_id)

                    if splunk_field == "siteHealth":
                        params = {"include": "health,faults,cluster-status"}

                    elif splunk_field == "fabricDetails":
                        params = {"include": "health,faults"}

                    else:
                        params = None

                    response = self.session.get(api_endpoint=endpoint, params=params)

                    logger.debug("Endpoint: {endpt}. Response returned successfully.".format(endpt=endpoint))

                    if response:
                        keys = list(response.keys())
                        for key in keys:
                            if len(keys) == 1 and isinstance(response[key], list):
                                events_ingested_count += self.print_response_object.print_response(
                                    data=response[key],
                                    splunk_field=splunk_field,
                                    host=self.host,
                                    response_key=key,
                                    api_name=api_name,
                                    endpt_id=endpt_id,
                                )
                                logger.debug(
                                    "Collected %d events for %s id for %s field.",
                                    events_ingested_count,
                                    endpt_id,
                                    splunk_field,
                                )
                            else:
                                events_ingested_count += self.print_response_object.print_response(
                                    data=response,
                                    splunk_field=splunk_field,
                                    host=self.host,
                                    api_name=api_name,
                                    endpt_id=endpt_id,
                                )
                                logger.debug(
                                    "Collected %d events for %s id for %s field.",
                                    events_ingested_count,
                                    endpt_id,
                                    splunk_field,
                                )
                                break
                    else:
                        logger.info("Received empty response for Endpoint: {}.".format(endpoint))

                except Exception as err:
                    logger.error(
                        "MSO Error: Error while collecting data for host: {host}, api: {api}, "
                        "endpoint: {endpt}. Error: {err}".format(
                            host=self.host, api=api_name, endpt=endpoint, err=str(err)
                        )
                    )
                    logger.error("Skipping this endpoint.")
                    continue

    def _getSiteIdForEndpoints(self, api_name, splunk_field_url):
        """
        Fetch set of site IDs.

        :param api_name: Name of MSO API
        :type api_name: string
        :param splunk_field_url: dict holding URLs of MSO API endpoint, from where data is to be fetched.
            dict key: Name of field to be appended alongwith response
            dict value: Endpoint URL
        :type splunk_field_url: dict
        """
        site_id = []
        endpoint = mso_urls.API_RETURNING_SITE_ID

        try:
            response = self.session.get(api_endpoint=endpoint)
            logger.debug("Endpoint: {endpt}. Response returned successfully.".format(endpt=endpoint))

            if response:
                for key in list(response.keys()):
                    data = response[key]
                    site_id = self.fetch_ids(data)
            else:
                logger.info("Received empty response for Endpoint: {}.".format(endpoint))

        except Exception as err:
            logger.error(
                "MSO Error: Could not fetch the Site Ids for host: {host}. Hence data cannot be collected "
                "for endpoint/s: {id_endpts}. Error: {err}".format(
                    host=self.host, err=str(err), id_endpts=list(splunk_field_url.values())
                )
            )
        if site_id:
            self._getResponseForSpecificID(splunk_field_url, site_id, api_name)
        else:
            logger.debug(
                "MSO Error: Failed fetching Site ids for host: {host}. Hence data cannot be collected for "
                "endpoint/s: {id_endpts}.".format(host=self.host, id_endpts=list(splunk_field_url.values()))
            )

    def _getAuditResponse(self):
        """Fetch MSO Audit Logs and create/update checkpoint file."""
        endpoint_details = mso_urls.AUDIT_RECORDS
        endpoint = endpoint_details["api"]
        offset = 0

        scriptPath = os.path.dirname(os.path.realpath(sys.argv[0]))
        fileName = self.host + "_auditRecords_LastTransactionTime.txt"
        filePath = os.path.join(scriptPath, fileName)

        params = {"sort": "timestamp", "limit": 250}
        current_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S%z")

        if os.path.isfile(filePath):
            logger.info("Reading the checkpoint file %s.", filePath)
            fd = open(filePath, "r")
            params["start"] = fd.read()
            params["end"] = current_time
            fd.close()
            logger.info("Read the checkpoint file %s successfully.", filePath)

        events_ingested_count = 0
        try:
            while True:
                params["offset"] = offset
                response = self.session.get(api_endpoint=endpoint, params=params)
                logger.debug("Endpoint: {endpt}. Response returned successfully.".format(endpt=endpoint))

                offset += 250
                data = response["auditRecords"]

                if not data:
                    break

                events_ingested_count += self.print_response_object.print_response(
                    data=data,
                    splunk_field=endpoint_details["splunk_field"],
                    host=self.host,
                    response_key="auditRecords",
                )

                if data:
                    latest_time = data[-1].get("timestamp", current_time)
                    logger.info("Updating the checkpoint file %s.", filePath)
                    fd = open(filePath, "w")
                    fd.write(latest_time)
                    fd.close()
                    logger.info("Updated the checkpoint file %s with value %s.", filePath, latest_time)

        except Exception as err:
            logger.error(
                "MSO Error: Error while collecting Audit Logs for host: {host} .Error: {err}".format(
                    host=self.host, err=str(err)
                )
            )

        logger.info("Collected %d events for auditrecords.", events_ingested_count)

    def _getNdUserResponse(self, endpoint_details, api_name):
        """Fetch User Response for ND Auth."""
        api_endpoints = endpoint_details["url"]

        events_ingested_count = 0
        for splunk_field, endpoint in list(api_endpoints.items()):
            try:
                response = self.session.get(api_endpoint=endpoint)
                logger.debug(
                    "Host: {host} Endpoint: {endpt}. Response returned successfully.".format(
                        host=self.host, endpt=endpoint
                    )
                )

                if response:
                    keys = response if splunk_field == "userDetails" else list(response.keys())
                    for key in keys:
                        if len(keys) == 1 and isinstance(response[key], list):
                            events_ingested_count += self.print_response_object.print_response(
                                data=response[key], splunk_field=splunk_field, host=self.host, response_key=key
                            )
                        else:
                            events_ingested_count += self.print_response_object.print_response(
                                data=response, splunk_field=splunk_field, host=self.host
                            )
                            break
                else:
                    logger.info("Received empty response for Endpoint: {}.".format(endpoint))

            except Exception as err:
                logger.error(
                    "MSO Error: Could not fetch the data for host: {host} and endpoint: {endpt}. "
                    "Error: {err}".format(host=self.host, endpt=api_name, err=str(err))
                )
                logger.error("Skipping this endpoint: {endpt}".format(endpt=endpoint))
                continue

        logger.info("Collected %d events for NDO User Response.", events_ingested_count)

    def _getResponse(self, endpoint_details, api_name):
        """
        Fetch the data for MSO APIs that do not require specific id to fetch data.

        Example: The API call api/v1/users, will give information of all MSO users, not of any specific user.
        :param endpoint_details: dict holding details of MSO API endpoint, from where data is to be fetched.
            - endpoint_details['url']: dict consisting of endpoint URL.
                Eg: endpoint_details['url']= {
                                                'userDetails':'api/v1/users',
                                                'userAllowedRoles':'api/v1/users/allowed-roles'
                                             }
            - endpoint_details['url_consisting_ids']: dict consisting of endpoint URLs which require ids for api_name.
                Eg: endpoint_details['url_consisting_ids'] = {
                                                                'userPermissions':'api/v1/users/{id}/permissions'
                                                             }
            - endpoint_details['splunk_field_consisting_id']: string i.e. key of endpoint_details['url'] dictionary
              which will give list of ids for given api_name.
                Eg: endpoint_details['splunk_field_consisting_id'] = 'userDetails'
        :type endpoint_details: dict
        :param api_name: Name of MSO API
            Example: Here value is user because the above api calls are for MSO users.
        :type api_name: string
        """
        api_endpoints = endpoint_details["url"]

        ids = []
        events_ingested_count = 0
        for splunk_field, endpoint in list(api_endpoints.items()):
            try:
                response = self.session.get(api_endpoint=endpoint)
                logger.debug("Endpoint: {endpt}. Response returned successfully.".format(endpt=endpoint))

                if response:
                    keys = list(response.keys())
                    for key in keys:
                        if len(keys) == 1 and isinstance(response[key], list):
                            events_ingested_count += self.print_response_object.print_response(
                                data=response[key], splunk_field=splunk_field, host=self.host, response_key=key
                            )
                            if splunk_field == endpoint_details["splunk_field_consisting_id"]:
                                ids = self.fetch_ids(response[key])
                        else:
                            events_ingested_count += self.print_response_object.print_response(
                                data=response, splunk_field=splunk_field, host=self.host
                            )
                            break
                else:
                    logger.info("Received empty response for Endpoint: {}.".format(endpoint))

            except Exception as err:
                if (
                    splunk_field == endpoint_details["splunk_field_consisting_id"]
                    and len(endpoint_details["url_consisting_ids"]) > 0
                ):
                    logger.error(
                        "MSO Error: Could not fetch the data for host: {host} and endpoint: {endpt}. Hence data cannot "
                        "be collected for endpoint/s: {id_endpts}. Error: {err}".format(
                            host=self.host,
                            endpt=api_name,
                            err=str(err),
                            id_endpts=list(endpoint_details["url_consisting_ids"].values()),
                        )
                    )
                else:
                    logger.error(
                        "MSO Error: Could not fetch the data for host: {host} and endpoint: {endpt}. "
                        "Error: {err}".format(host=self.host, endpt=api_name, err=str(err))
                    )
                logger.error("Skipping this endpoint: {endpt}".format(endpt=endpoint))
                continue

        logger.info("Collected %d events for %s api.", events_ingested_count, api_name)

        if len(endpoint_details["url_consisting_ids"]) > 0 and ids:
            self._getResponseForSpecificID(endpoint_details["url_consisting_ids"], ids, api_name)
        else:
            logger.debug(
                "MSO Error: Failed fetching {endpt} ids for host: {host}, hence data cannot be collected "
                "for endpoints: {id_endpts}.".format(
                    host=self.host, endpt=api_name, id_endpts=endpoint_details["url_consisting_ids"]
                )
            )


def _msoRedundancy(argv, host, username, password, domain_name, auth_type, verify_ssl):
    """
    Fetch the data for MSO APIs that do not require specific id.

    :param host: MSO hostname
    :type host: string
    :param username: MSO Username
    :type username: string
    :param password: MSO Password
    :type password: string
    :param verify_ssl: To perform SSL connections with the MSO.
    :type verify_ssl: string
    """
    try:
        for each in host:
            # Login from 2nd MSO
            if domain_name:
                logger.info("Collecting data using Remote Based Authentication for the host: {0} ".format(host))
            else:
                logger.info("Collecting data using Password Based Authentication for the host: {0} ".format(host))
            try:
                each = each.strip()
                msoUrl = "https://{host}".format(host=str(each))
                session = mso_session.Session(
                    msoUrl, username, password, domain_name, TIMEOUT, auth_type, verify_ssl, logger=logger
                )
                response = session.login()
                if response.ok:
                    _getDataArgs(argv, session, each, auth_type)
                    break
            except Exception as err:
                logger.error("MSO Error: Unable to connect {host} Error: {err}".format(host=each, err=str(err)))
                if str(each) == str(host[-1]):
                    logger.error(
                        "Could not find other MSOs to login: {host}, Username: {uname}".format(
                            host=host, uname=username
                        )
                    )
                continue
    except Exception:
        logger.error("Could not find other MSOs to login: {host}, Username: {uname}".format(host=host, uname=username))


def _getCredentials(sessionKey):
    """
    Get credentials from storage/paswords, configured by user.

    :param sessionKey: scripted inputs arguments
    :type sessionKey: string
    """
    mso_credentials = {}

    try:
        # list all credentials
        entities = entity.getEntities(
            ["admin", "passwords"], search="eai:acl.app=" + myapp, sessionKey=sessionKey, count=-1
        )
        for i, c in list(entities.items()):

            host = str(xss.unescape(i.split(":")[0])).strip()

            user_detail = c["username"].split(",")

            if user_detail[0] == "mso" or user_detail[0] == "nd_auth":
                auth_type = user_detail[0]
                user_detail = user_detail[1:]
                port = user_detail[0]
                username = xss.unescape(user_detail[1])
                verify_ssl = user_detail[2].strip().upper()

                if verify_ssl in ("0", "FALSE", "F", "N", "NO", "NONE", ""):
                    verify_ssl = "False"
                else:
                    verify_ssl = "True"

                password = c["clear_password"]
                credential = []
                if port:
                    host_list = host.split(",")
                    port1 = ":" + port + ","
                    host = port1.join(host_list)
                    host = host + ":" + port

                credential = [username, password, verify_ssl, auth_type]
                mso_credentials[host] = list(credential)

        # logger.error("MSO Error: Credentials Not Found through REST API")

        return mso_credentials

    except Exception as e:
        logger.error("MSO Error: Could not get %s credentials from splunk. Error: %s" % (myapp, str(e)))
        return mso_credentials


def _getDataArgs(argv, session, host, auth_type):
    """
    Call methods of GetAPIResponse based on value of MSO API call arguments.

    :param argv: scripted inputs arguments
    :type argv: list
    :param session: MSO session
    :type session: session object
    :param host: MSO hostname
    :type host: string
    """
    if argv[0] == "-mso":
        get_API_response_object = GetAPIResponse(session=session, mso_host=host)
        mso_apis = argv[1:]
        endpoint_details = {}

        for api in mso_apis:
            if api == "audit":
                get_API_response_object._getAuditResponse()
            elif api == "fabric":
                get_API_response_object._getSiteIdForEndpoints(api, mso_urls.FABRIC_API)
            elif api == "policy":
                endpoint_details["url"] = mso_urls.POLICY_APIS
                endpoint_details["url_consisting_ids"] = mso_urls.SPECIFIC_POLICY_APIS
                endpoint_details["splunk_field_consisting_id"] = "policyDetails"
                get_API_response_object._getResponse(endpoint_details, api)
            elif api == "schema":
                endpoint_details["url"] = mso_urls.SCHEMA_APIS
                endpoint_details["url_consisting_ids"] = mso_urls.SPECIFIC_SCHEMA_APIS
                endpoint_details["splunk_field_consisting_id"] = "schemaDetails"
                get_API_response_object._getResponse(endpoint_details, api)
            elif api == "site":
                get_API_response_object._getSiteIdForEndpoints(api, mso_urls.SPECIFIC_SITE_APIS)
            elif api == "tenant":
                endpoint_details["url"] = mso_urls.TENANT_APIS
                endpoint_details["url_consisting_ids"] = mso_urls.SPECIFIC_TENANT_APIS
                endpoint_details["splunk_field_consisting_id"] = "tenantDetails"
                get_API_response_object._getResponse(endpoint_details, api)
            elif api == "user":
                endpoint_details["url"] = mso_urls.USER_APIS
                if auth_type == "nd_auth":
                    get_API_response_object._getNdUserResponse(endpoint_details, api)
                else:
                    endpoint_details["url_consisting_ids"] = mso_urls.SPECIFIC_USER_APIS
                    endpoint_details["splunk_field_consisting_id"] = "userDetails"
                    get_API_response_object._getResponse(endpoint_details, api)
            else:
                logger.error(
                    "MSO Error: Please choose one of the following APIs: audit, fabricConnectivity, "
                    "schemas, sites, tenant, policy and user."
                )
    else:
        logger.error("MSO Error: Please keep append -mso <mso_api> at end of scripted input stanza.")
        sys.exit()
    session.close()


def main(argv):
    """Driver function and entry point of execution."""
    global logger
    sessionKey = sys.stdin.readline().strip()
    input_class_name = argv[0]
    logger = logger_manager.get_logger(input_class_name.strip("-"))

    if len(sessionKey) == 0:
        logger.error(
            "MSO Error: Did not receive a session key from splunkd. "
            + "Please enable passAuth in inputs.conf for this "
            + "script\n"
        )
        sys.exit()

    mso_credentials = _getCredentials(sessionKey)

    if not mso_credentials:
        logger.error(
            "Did not find any credentials configured for MSO. Please configure it first and then enable the scripts"
        )
        return

    for host_str in mso_credentials:
        domain_name = None
        username = mso_credentials[host_str][0]
        password = mso_credentials[host_str][1]
        verify_ssl = mso_credentials[host_str][2]
        auth_type = mso_credentials[host_str][3]

        if "\\\\" in username:
            uname_domain = username.split("\\\\")
            domain_name = uname_domain[0]
            username = uname_domain[1]

        host_list = host_str.split(",")
        host = host_list[0].strip()
        host_split_by_port = host[::-1].split(":", 1)

        # common_host variable consists of only mso_host and not port number
        common_host = host_split_by_port[1][::-1] if len(host_split_by_port) == 2 else host_split_by_port[0][::-1]
        msoUrl = "https://{host}".format(host=str(host))

        if domain_name:
            logger.info("Collecting data using Remote Based Authentication for the host: {0} ".format(common_host))
        else:
            logger.info("Collecting data using Password Based Authentication for the host: {0} ".format(common_host))

        try:
            # Connect to the MSO REST interface and authenticate using the specified credentials
            session = mso_session.Session(
                msoUrl, username, password, domain_name, TIMEOUT, auth_type, verify_ssl, logger=logger
            )
            response = session.login()

            if response.ok:
                _getDataArgs(argv, session, host, auth_type)
            else:
                logger.error(
                    "MSO Error: Could not login to MSO: {host}, Username: {uname}".format(
                        host=common_host, uname=username
                    )
                )
                if len(host_list) > 1:
                    _msoRedundancy(argv, host_list[1:], username, password, domain_name, auth_type, verify_ssl)

        except Exception as err:
            logger.error("MSO Error: Not able to connect to {host} Error: {err}".format(host=common_host, err=str(err)))
            if len(host_list) > 1:
                _msoRedundancy(argv, host_list[1:], username, password, domain_name, auth_type, verify_ssl)


if __name__ == "__main__":
    main(sys.argv[1:])
    logger.info("Data collection completed.")
