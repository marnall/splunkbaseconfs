#!/usr/bin/python

################################################################################################################
# Get some libraries we will need
################################################################################################################

from __future__ import print_function
import json
import time
import datetime
import xmltodict
import requests
import warnings


class ClientError(RuntimeError):
    pass


class ServerError(RuntimeError):
    pass


################################################################################################################
# Declares the SMC API Utility object
################################################################################################################


class stealthwatch_api(object):
    __sdk_version = "1.3.0"
    ############################################################################################################
    # Global variables used throughout the object
    ############################################################################################################
    __smc_ip = None
    __smc_username = None
    __smc_password = None
    __api_session = None
    __orientation_list = None
    __order_by_list = None
    __connection_direction_list = None
    __version = None
    __domain_id = None
    __requests_disable_warnings = None
    DEBUG = None

    ############################################################################################################
    # Initializes the object
    ############################################################################################################
    def __init__(self):
        self.__smc_ip = None
        self.__smc_username = None
        self.__smc_password = None
        if self.__api_session is not None:
            self.__api_session.close()
        self.__api_session = None
        self.__orientation_list = ["EITHER", "CLIENT", "SERVER"]
        self.__order_by_list = ["TOTAL_BYTES", "TOTAL_PACKETS", "TOTAL_FLOWS", "TOTAL_CONNECTIONS"]
        self.__connection_direction_list = ["INBOUND_PLUS_OUTBOUND", "INBOUND", "OUTBOUND", "WITHIN"]
        self.__version = None
        self.__domain_id = None
        self.__requests_disable_warnings = None
        self.__timeout = None
        self.__long_timeout = None
        self.__xsrf = None
        self.DEBUG = False

    ############################################################################################################
    # Set the domain ID to be used
    ############################################################################################################
    def set_domain_id(self, domain_id):
        self.__domain_id = domain_id

    ############################################################################################################
    # Set the domain ID to be used
    ############################################################################################################
    def get_domain_id(self):
        return self.__domain_id

    ############################################################################################################
    # Set the domain ID to be used
    ############################################################################################################
    def set_tenant_id(self, tenant_id):
        self.set_domain_id(tenant_id)

    ############################################################################################################
    # Logs in to a new API session
    ############################################################################################################
    def login(self, smc_ip, smc_username, smc_password, requests_disable_warnings=True, skip_checks=False,
              timeout=None):
        self.disconnect()

        self.__smc_ip = smc_ip
        self.__smc_username = smc_username
        self.__smc_password = smc_password
        self.__requests_disable_warnings = requests_disable_warnings
        self.__timeout = timeout
        self.__long_timeout = timeout * 20 if timeout else None
        if self.__requests_disable_warnings:
            requests.packages.urllib3.disable_warnings()
        self.__api_session = requests.Session()

        login_url = 'https://{}/token/v2/authenticate'.format(self.__smc_ip)
        login_credentials = {'username': self.__smc_username, 'password': self.__smc_password}
        if self.DEBUG:
            print('Stealthwatch login URL: {}'.format(login_url))

        response = None
        try:
            response = self.__api_session.post(login_url, data=login_credentials, verify=False, timeout=self.__timeout)
        except Exception as e:  # Likely a network, service, or protocol error.
            self.disconnect()
            if skip_checks:
                return False
            raise e

        if not response.ok:
            self.disconnect()
            if skip_checks:
                return False
            exception_class = ClientError if response.status_code < 500 else ServerError
            raise exception_class('Could not authenticate: {}'.format(response.reason))

        xsrf_token = response.cookies.get('XSRF-TOKEN')
        if xsrf_token:
            self.__xsrf = xsrf_token

        if not skip_checks:
            # Retrieve the SMC version - post authentication
            self.__version = self.get_version_info()
            tenants = self.get_tenants()

            if tenants and tenants[0]["id"]:
                self.__domain_id = tenants[0]["id"]
            else:
                raise RuntimeError("Could not get SMC tenants / domains")
        return True

    def disconnect(self):
        if self.__api_session:
            try:
                self.__api_session.close()
            except Exception:
                pass
            self.__api_session = None

    def version_before(self, major, minor):
        if self.__version:
            if self.__version[0] < major:
                return True
            if self.__version[0] == major and self.__version[1] < minor:
                return True
            return False
        return None

    def version_after(self, major, minor):
        if self.__version:
            if self.__version[0] > major:
                return True
            if self.__version[0] == major and self.__version[1] > minor:
                return True
            return False
        return None

    ############################################################################################################
    # Logs out of the current API session
    ############################################################################################################
    def logout(self):
        uri = 'https://' + self.__smc_ip + '/token'
        if self.DEBUG:
            print('Stealthwatch logout URL: ' + uri)
        response = self.__api_session.delete(uri, timeout=self.__timeout, verify=False)
        self.disconnect()

    def get_version_info(self):
        """"Get SMC version.

        This fn is used to distinguish between different APIs for different
        versions.

        It only works post authentication, and has replaced 'get_version()' which
        is deprecated. Therefore this is assuming SMC version 6.8.3 and below are
        not supported.

        There are a couple of APIs that can be used.

        1. This API is unsupported but has a lot of useful info that could be used later:

        https://10.208.133.100/smc/rest/appliance/api/info

        Output example:
            {
                model: "StealthWatch Management Console VE",
                serialNumber: "SMCVE-VMware-421e98a27a668657-14574f06d307c774",
                version: "7.1.1",
                build: "2019.07.31.1629-0",
                fqdn: {
                    hostname: "rich-smc",
                    domainname: "lcs.ciscolabs.com"
                },
                setupToolComplete: true,
                networkSettingsComplete: false
            }

        2. This API was recomended by SWE:

        https://10.208.133.100/smc/rest/system/info

        Output example:
        {
            "version" : "7.2.1",
            "build" : "2020.04.21.1550-0",
            "hostName" : "smc-721-10-0-35-135-1"
        }

        This supported API is the one we will use for now.

        Returns a tuple containing the SMC version in the form (major, minor) or
        a tuple set to None if the API was unnsuccessful.
        """
        uri = 'https://' + self.__smc_ip + '/smc/rest/system/info'
        response = self.__execute_query(uri, None)
        version = None

        if self.DEBUG:
            print('Stealthwatch API call response: \n' + json.dumps(response, indent=4, sort_keys=True))

        if response:
            (major, minor, _) = response["version"].split('.', 2)
            version = (int(major), int(minor))

        return version

    ############################################################################################################
    # DEPRECATED Gets the version of the SMC
    ############################################################################################################
    def get_version(self, no_raise=False):
        """Deprecated as SMC version 6.8.3 and below is no longer supported."""
        warnings.warn("deprecated", DeprecationWarning)

        version = None

        response = None
        login_page_url = 'https://{}/smc/login.html'.format(self.__smc_ip)
        try:
            response = self.__api_session.get(login_page_url, timeout=self.__timeout, verify=False)
        except Exception as e:
            if no_raise:
                return version
            raise e
        if response.status_code != 200:
            if no_raise:
                return version
            raise Exception()

        version_string = ''
        login_page = response.text
        login_message_div = '<div id="loginMessage">'
        if login_message_div in login_page:
            after_login_message_div = login_page.split(login_message_div)[1]
            after_login_message_div = after_login_message_div.replace('<br />', '<br/>').replace('<br>', '<br/>')
            after_first_line_of_login_message = after_login_message_div.split('<br/>')[1]
            version_string = after_first_line_of_login_message.split('</div>')[0]
            version_string = version_string.strip()
        if not version_string:
            if no_raise:
                return version
            raise Exception()

        (major, minor, _) = version_string.split('.', 2)
        try:
            version = (int(major), int(minor))
        except Exception as e:
            if no_raise:
                return version
            raise e

        return version

    ############################################################################################################
    # Gets the domain ids
    ############################################################################################################
    def get_domain_ids(self):
        all_domains = self.get_tenants()
        ids = []
        for domain in all_domains:
            ids.append(domain["id"])
        return ids

    ############################################################################################################
    # Executes an API call with the given URI and request data
    ############################################################################################################
    def __execute_query(self, uri, request_data=None, rest_method='get', return_response_code=False):
        request_kwargs = {'url': uri, 'timeout': self.__long_timeout, 'verify': False}

        if request_data:
            if rest_method == 'get':
                print('GET with request data')
            request_kwargs['data'] = request_data

            request_kwargs['headers'] = {'Content-type': 'application/json', 'Accept': 'application/json'}
            if self.__xsrf:
                request_kwargs['headers']['X-XSRF-TOKEN'] = self.__xsrf

        request_method = self.__api_session.get

        if rest_method == 'put':
            request_method = self.__api_session.put
        elif rest_method == 'post':
            request_method = self.__api_session.post
        elif rest_method == 'delete':
            request_method = self.__api_session.delete
            # Probably don't need these headers
            request_kwargs['headers'] = {'Content-type': 'application/json', 'Accept': 'application/json'}
            if self.__xsrf:
                request_kwargs['headers']['X-XSRF-TOKEN'] = self.__xsrf

        response = None
        if self.DEBUG:
            print('Stealthwatch API call: {}({})'.format(rest_method, request_kwargs))
        try:
            response = request_method(**request_kwargs)
        except Exception as e:
            if not uri.endswith('getHomePage'):
                self.disconnect()
                raise RuntimeError('Unable to execute query ({}): {}({})'.format(uri, e.__class__.__name__, e))

        if return_response_code:  # All the caller wants is the status code, so don't raise exceptions if we got this far.
            if self.DEBUG:
                print('RESPONSE CODE: {}'.format(response.status_code))
            try:
                json.loads(response.content)
            except ValueError as e:
                if response.content:  # If there is non-json content, return the whole response.
                    if self.DEBUG:
                        print('RESPONSE CONTENT: {}'.format(response.content))
                    return response
            return response.status_code

        if not response.ok:
            exception_class = ClientError if response.status_code < 500 else ServerError
            raise exception_class(
                'Unable to execute query ({}): {} {}'.format(uri, response.status_code, response.reason))

        if not response:
            raise RuntimeError('Unable to execute query ({}): server returned empty response'.format(uri))

        # Trying to get the delete method working
        if rest_method == 'delete':
            return str(response.content)

        json_response = None
        try:
            json_response = json.loads(response.content)
        except ValueError as e:
            print('Unable to parse server response: {}'.format(e))
            raise e
        #
        # if json_response and isinstance(json_response, int):
        #     return json_response

        if json_response and 'data' in json_response:
            json_response = json_response['data']
        return json_response

    ############################################################################################################
    #  Executes a SOAP API call with the given URI and request data
    ############################################################################################################
    def __execute_soap_query(self, uri, request_body, raise_on_error=None, return_error=None):
        http_response = None
        try:
            request_data = None
            if request_body:
                request_data = '<?xml version="1.0" encoding="UTF-8"?><soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"><soapenv:Body>{}</soapenv:Body></soapenv:Envelope>'.format(
                    request_body)
            if self.DEBUG:
                print('Stealthwatch API call URI: {}'.format(uri))
                if request_data:
                    print('Stealthwatch API call data: {}'.format(request_data))

            auth = (self.__smc_username, self.__smc_password)
            timeout = 6000
            verify = False
            try:
                if request_data is None:
                    http_repsonse = requests.get(uri, auth=auth, timeout=timeout, verify=verify)
                else:
                    http_response = requests.post(uri, auth=auth, timeout=timeout, verify=verify, data=request_data)
            except requests.exceptions.RequestException as e:
                self.__api_session.close()
                if raise_on_error in [None, True]:
                    raise RuntimeError('ERROR: Unable to execute query: {}'.format(e))
                if return_error:
                    return str(e)
                return None

            if 200 > http_response.status_code >= 300:
                self.__api_session.close()
                if raise_on_error in [None, True]:
                    raise RuntimeError('ERROR: Unable to execute query: {} - {}'.format(http_response.status_code,
                                                                                        http_response.reason))
                if return_error:
                    return http_response.reason
                return None

            json_response = None
            try:
                soap_response = xmltodict.parse(http_response.content, xml_attribs=True)
                json_response = json.loads(json.dumps(soap_response, indent=4).replace('"@', '"'))
            except ValueError as e:
                self.__api_session.close()
                if raise_on_error in [None, True]:
                    raise RuntimeError('ERROR: Could not parse server response: {}'.format(e))
                if return_error:
                    return str(e)
                return None

            if 'soapenc:Fault' in json_response['soapenc:Envelope']['soapenc:Body']:
                self.__api_session.close()
                error = json_response['soapenc:Envelope']['soapenc:Body']['soapenc:Fault']['faultstring']
                if raise_on_error:
                    raise RuntimeError(error)
                if return_error:
                    return error
                return None

            return json_response

        except Exception as error:
            self.__api_session.close()
            if raise_on_error in [None, True]:
                raise error
            if return_error:
                return str(error)
        return None

    ############################################################################################################
    # Fetches a file from the SMC
    ############################################################################################################
    def __get_file_as_string(self, uri):
        response = None
        if self.DEBUG:
            print('Stealthwatch File call URI: ' + uri)
        try:
            response = self.__api_session.get(uri, timeout=self.__long_timeout, verify=False)
            if response.status_code != 200:
                return None
            else:
                return response.content
        except:
            self.__api_session.close()
            raise Exception("ERROR: Unable to execute query: " + str(response.status_code) + " - " +
                            requests.status_codes._codes[response.status_code][0] + ")")

    ############################################################################################################
    ############################################################################################################
    ############################################################################################################
    # SOAP API
    ############################################################################################################
    ############################################################################################################
    ############################################################################################################

    def __generate_soap_date_selection(self, start_datetime=None, end_datetime=None, number_days_back=None,
                                       force_day_selection=None, force_active_time_selection=None):
        date_selection_filter = ''
        if force_day_selection is not None and force_day_selection == True and start_datetime is not None:
            start_timestamp = start_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
            date_selection_filter = '<date-selection><day-selection start="' + start_timestamp + '"/></date-selection>'
        elif force_active_time_selection is not None and force_active_time_selection == True and start_datetime is not None and end_datetime is not None:
            start_timestamp = start_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
            end_timestamp = end_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
            date_selection_filter = '<date-selection><active-time-selection><time-range-selection start="' + start_timestamp + '" end="' + end_timestamp + '"/></active-time-selection></date-selection>'
        elif number_days_back is None:
            if start_datetime is not None or end_datetime is not None:
                date_selection_filter = '<date-selection><time-range-selection'
                if start_datetime is not None:
                    start_timestamp = start_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
                    date_selection_filter += ' start="' + str(start_timestamp) + '"'
                if end_datetime is not None:
                    end_timestamp = end_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
                    date_selection_filter += ' end="' + str(end_timestamp) + '"'
                date_selection_filter += '/></date-selection>'
        elif number_days_back is not None and (number_days_back > 1 or end_datetime is not None):
            if force_day_selection is not None and force_day_selection == True:
                date_selection_filter = '<date-selection><day-selection days-before="' + str(
                    number_days_back) + '"/></date-selection>'
            else:
                date_selection_filter = '<date-selection><day-range-selection'
                if end_datetime is not None:
                    end_timestamp = end_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
                    date_selection_filter += ' last-day="' + str(end_timestamp) + '"'
                date_selection_filter += ' day-count="' + str(number_days_back) + '"'
                date_selection_filter += '/></date-selection>'
        return date_selection_filter

    def __generate_soap_device_selection(self, filter_by, device_id=None, exporter_ip=None, interface_id=None,
                                         is_single_interface=None):
        device_selection_filter = ''
        if filter_by == "FLOW_COLLECTOR" and device_id is not None:
            device_selection_filter += '<device-selection>'
            device_selection_filter += '<device-list-selection>'
            if isinstance(device_id, list):
                for id in device_id:
                    device_selection_filter += '<device device-id="' + str(id) + '"/>'
            else:
                device_selection_filter += '<device device-id="' + str(device_id) + '"/>'
            device_selection_filter += '</device-list-selection>'
            device_selection_filter += '</device-selection>'
        elif filter_by == "EXPORTER" and device_id is not None and exporter_ip is not None:
            device_selection_filter += '<device-selection>'
            device_selection_filter += '<interface-list-selection>'
            if isinstance(exporter_ip, list):
                for ip in exporter_ip:
                    device_selection_filter += '<interface device-id="' + str(device_id) + '" exporter-ip="' + str(
                        ip) + '"/>'
            else:
                device_selection_filter += '<interface device-id="' + str(device_id) + '" exporter-ip="' + str(
                    exporter_ip) + '"/>'
            device_selection_filter += '</interface-list-selection>'
            device_selection_filter += '</device-selection>'
        elif filter_by == "INTERFACE" and device_id is not None and exporter_ip is not None and interface_id is not None:
            device_selection_filter += '<device-selection>'
            if is_single_interface is None or is_single_interface is False:
                device_selection_filter += '<interface-list-selection>'
                if isinstance(interface_id, list):
                    for id in interface_id:
                        device_selection_filter += '<interface device-id="' + str(device_id) + '" exporter-ip="' + str(
                            exporter_ip) + '" interface-id="' + str(id) + '"/>'
                else:
                    device_selection_filter += '<interface device-id="' + str(device_id) + '" exporter-ip="' + str(
                        exporter_ip) + '" interface-id="' + str(interface_id) + '"/>'
                device_selection_filter += '</interface-list-selection>'
            else:
                device_selection_filter += '<interface-selection device-id="' + str(
                    device_id) + '" exporter-ip="' + str(
                    exporter_ip) + '" interface-id="' + str(interface_id) + '"/>'
            device_selection_filter += '</device-selection>'
        return device_selection_filter

    def __generate_soap_host_selection(self, subject_ip=None, subject_host_group_id=None, peer_ip=None,
                                       peer_host_group_id=None, subject_orientation=None, force_pair_selection=None):
        host_selection_filter = ''
        if force_pair_selection is None:
            force_pair_selection = False
        if subject_ip is None and subject_host_group_id is None and (
                peer_ip is not None or peer_host_group_id is not None):
            subject_ip = peer_ip
            subject_host_group_id = peer_host_group_id
            peer_ip = None
            peer_host_group_id = None
        if subject_ip is not None or subject_host_group_id is not None:
            host_selection_filter += '<host-selection>'
            if peer_ip is not None or peer_host_group_id is not None or force_pair_selection:
                if subject_orientation is None:
                    subject_orientation = "BETWEEN_SELECTION_1_SELECTION_2"
                elif subject_orientation.lower() == "client":
                    subject_orientation = "SELECTION_1_A_SELECTION_2_Z"
                elif subject_orientation.lower() == "server":
                    subject_orientation = "SELECTION_1_Z_SELECTION_2_A"
                else:
                    subject_orientation = "BETWEEN_SELECTION_1_SELECTION_2"
                host_selection_filter += '<host-pair-selection direction="' + str(subject_orientation) + '">'
                if subject_ip is not None or subject_host_group_id is not None:
                    host_selection_filter += '<selection-1>'
            if subject_ip is not None:
                if isinstance(subject_ip, list):
                    host_selection_filter += '<ip-address-list-selection>'
                    for ip in subject_ip:
                        host_selection_filter += '<ip-address value="' + str(ip) + '"/>'
                    host_selection_filter += '</ip-address-list-selection>'
                else:
                    if '/' in subject_ip:
                        host_selection_filter += '<ip-address-range-selection value="' + str(subject_ip) + '"/>'
                    else:
                        host_selection_filter += '<ip-address-selection value="' + str(subject_ip) + '"/>'
            if subject_host_group_id is not None:
                host_selection_filter += '<host-group-selection host-group-id="' + str(subject_host_group_id) + '"/>'
            if peer_ip is not None or peer_host_group_id is not None or force_pair_selection:
                if subject_ip is not None or subject_host_group_id is not None:
                    host_selection_filter += '</selection-1>'
                if peer_ip is not None or peer_host_group_id is not None:
                    host_selection_filter += '<selection-2>'
                if peer_ip is not None:
                    if isinstance(peer_ip, list):
                        host_selection_filter += '<ip-address-list-selection>'
                        for ip in peer_ip:
                            host_selection_filter += '<ip-address value="' + str(ip) + '"/>'
                        host_selection_filter += '</ip-address-list-selection>'
                    else:
                        if '/' in peer_ip:
                            host_selection_filter += '<ip-address-range-selection value="' + str(peer_ip) + '"/>'
                        else:
                            host_selection_filter += '<ip-address-selection value="' + str(peer_ip) + '"/>'
                if peer_host_group_id is not None:
                    host_selection_filter += '<host-group-selection host-group-id="' + str(peer_host_group_id) + '"/>'
                if peer_ip is not None or peer_host_group_id is not None:
                    host_selection_filter += '</selection-2>'
                host_selection_filter += '</host-pair-selection>'
            host_selection_filter += '</host-selection>'
        return host_selection_filter

    def __generate_soap_flow_report_basic_filter(self, filter_type, filter_includes, filter_excludes):
        filter_body = ''
        if filter_includes is not None and len(filter_includes) > 0:
            filter_body += '<' + str(filter_type) + ' exclude="false">'
            for item in filter_includes:
                filter_body += str(item) + ','
            filter_body = filter_body[:-1]
            filter_body += '</' + str(filter_type) + '>'
        elif filter_excludes is not None and len(filter_excludes) > 0:
            filter_body += '<' + str(filter_type) + ' exclude="true">'
            for item in filter_excludes:
                filter_body += str(item) + ','
            filter_body = filter_body[:-1]
            filter_body += '</' + str(filter_type) + '>'
        return filter_body

    def __generate_soap_flow_report_traffic_filter(self, client_bytes_greater_than, client_bytes_less_than,
                                                   client_packets_greater_than, client_packets_less_than,
                                                   server_bytes_greater_than, server_bytes_less_than,
                                                   server_packets_greater_than, server_packets_less_than,
                                                   total_bytes_greater_than, total_bytes_less_than,
                                                   total_packets_greater_than, total_packets_less_than):
        filter_body = ''
        if client_bytes_greater_than is not None or client_bytes_less_than is not None or client_packets_greater_than is not None or client_packets_less_than is not None or server_bytes_greater_than is not None or server_bytes_less_than is not None or server_packets_greater_than is not None or server_packets_less_than is not None or total_bytes_greater_than is not None or total_bytes_less_than is not None or total_packets_greater_than is not None or total_packets_less_than is not None:
            filter_body += '<traffic>'
            if client_bytes_greater_than is not None or client_bytes_less_than is not None or client_packets_greater_than is not None or client_packets_less_than is not None:
                filter_body += '<client>'
                if client_bytes_greater_than is not None or client_bytes_less_than is not None:
                    filter_body += '<bytes-range'
                    if client_bytes_greater_than is not None:
                        filter_body += ' low-value="' + str(client_bytes_greater_than) + '"'
                    if client_bytes_less_than is not None:
                        filter_body += ' high-value="' + str(client_bytes_less_than) + '"'
                    filter_body += '/>'
                if client_packets_greater_than is not None or client_packets_less_than is not None:
                    filter_body += '<packets-range'
                    if client_packets_greater_than is not None:
                        filter_body += ' low-value="' + str(client_packets_greater_than) + '"'
                    if client_packets_less_than is not None:
                        filter_body += ' high-value="' + str(client_packets_less_than) + '"'
                    filter_body += '/>'
                filter_body += '</client>'
            if server_bytes_greater_than is not None or server_bytes_less_than is not None or server_packets_greater_than is not None or server_packets_less_than is not None:
                filter_body += '<server>'
                if server_bytes_greater_than is not None or server_bytes_less_than is not None:
                    filter_body += '<bytes-range'
                    if server_bytes_greater_than is not None:
                        filter_body += ' low-value="' + str(server_bytes_greater_than) + '"'
                    if server_bytes_less_than is not None:
                        filter_body += ' high-value="' + str(server_bytes_less_than) + '"'
                    filter_body += '/>'
                if server_packets_greater_than is not None or server_packets_less_than is not None:
                    filter_body += '<packets-range'
                    if server_packets_greater_than is not None:
                        filter_body += ' low-value="' + str(server_packets_greater_than) + '"'
                    if server_packets_less_than is not None:
                        filter_body += ' high-value="' + str(server_packets_less_than) + '"'
                    filter_body += '/>'
                filter_body += '</server>'
            if total_bytes_greater_than is not None or total_bytes_less_than is not None or total_packets_greater_than is not None or total_packets_less_than is not None:
                filter_body += '<total>'
                if total_bytes_greater_than is not None or total_bytes_less_than is not None:
                    filter_body += '<bytes-range'
                    if total_bytes_greater_than is not None:
                        filter_body += ' low-value="' + str(total_bytes_greater_than) + '"'
                    if total_bytes_less_than is not None:
                        filter_body += ' high-value="' + str(total_bytes_less_than) + '"'
                    filter_body += '/>'
                if total_packets_greater_than is not None or total_packets_less_than is not None:
                    filter_body += '<packets-range'
                    if total_packets_greater_than is not None:
                        filter_body += ' low-value="' + str(total_packets_greater_than) + '"'
                    if total_packets_less_than is not None:
                        filter_body += ' high-value="' + str(total_packets_less_than) + '"'
                    filter_body += '/>'
                filter_body += '</total>'
            filter_body += '</traffic>'
        return filter_body

    def __generate_soap_flow_report_network_performance_filter(self, total_connections_greater_than,
                                                               total_connections_less_than,
                                                               total_retransmissions_greater_than,
                                                               total_retransmissions_less_than,
                                                               minimum_rtt_greater_than, minimum_rtt_less_than,
                                                               average_rtt_greater_than, average_rtt_less_than,
                                                               maximum_rtt_greater_than, maximum_rtt_less_than,
                                                               minimum_srt_greater_than, minimum_srt_less_than,
                                                               average_srt_greater_than, average_srt_less_than,
                                                               maximum_srt_greater_than, maximum_srt_less_than):
        filter_body = ''
        if total_connections_greater_than is not None or total_connections_less_than is not None or total_retransmissions_greater_than is not None or total_retransmissions_less_than is not None or minimum_rtt_greater_than is not None or minimum_rtt_less_than is not None or average_rtt_greater_than is not None or average_rtt_less_than is not None or maximum_rtt_greater_than is not None or maximum_rtt_less_than is not None or minimum_srt_greater_than is not None or minimum_srt_less_than is not None or average_srt_greater_than is not None or average_srt_less_than is not None or maximum_srt_greater_than is not None or maximum_srt_less_than is not None:
            filter_body += '<network-performance>'
            if total_connections_greater_than is not None or total_connections_less_than is not None:
                filter_body += '<total-connections'
                if total_connections_greater_than is not None:
                    filter_body += ' low-value="' + str(total_connections_greater_than) + '"'
                if total_connections_less_than is not None:
                    filter_body += ' high-value="' + str(total_connections_less_than) + '"'
                filter_body += '/>'
            if total_retransmissions_greater_than is not None or total_retransmissions_less_than is not None:
                filter_body += '<total-retransmissions'
                if total_retransmissions_greater_than is not None:
                    filter_body += ' low-value="' + str(total_retransmissions_greater_than) + '"'
                if total_retransmissions_less_than is not None:
                    filter_body += ' high-value="' + str(total_retransmissions_less_than) + '"'
                filter_body += '/>'
            if minimum_rtt_greater_than is not None or minimum_rtt_less_than is not None or average_rtt_greater_than is not None or average_rtt_less_than is not None or maximum_rtt_greater_than is not None or maximum_rtt_less_than:
                filter_body += '<round-trip-time>'
                if minimum_rtt_greater_than is not None or minimum_rtt_less_than is not None:
                    filter_body += '<min'
                    if minimum_rtt_greater_than is not None:
                        filter_body += ' low-value="' + str(minimum_rtt_greater_than) + '"'
                    if minimum_rtt_less_than is not None:
                        filter_body += ' high-value="' + str(minimum_rtt_less_than) + '"'
                    filter_body += '/>'
                if average_rtt_greater_than is not None or average_rtt_less_than is not None:
                    filter_body += '<avg'
                    if average_rtt_greater_than is not None:
                        filter_body += ' low-value="' + str(average_rtt_greater_than) + '"'
                    if average_rtt_less_than is not None:
                        filter_body += ' high-value="' + str(average_rtt_less_than) + '"'
                    filter_body += '/>'
                if maximum_rtt_greater_than is not None or maximum_rtt_less_than:
                    filter_body += '<max'
                    if maximum_rtt_greater_than is not None:
                        filter_body += ' low-value="' + str(maximum_rtt_greater_than) + '"'
                    if maximum_rtt_less_than:
                        filter_body += ' high-value="' + str(maximum_rtt_less_than) + '"'
                    filter_body += '/>'
                filter_body += '</round-trip-time>'
            if minimum_srt_greater_than is not None or minimum_srt_less_than is not None or average_srt_greater_than is not None or average_srt_less_than is not None or maximum_srt_greater_than is not None or maximum_srt_less_than is not None:
                filter_body += '<server-response-time>'
                if minimum_srt_greater_than is not None or minimum_srt_less_than is not None:
                    filter_body += '<min'
                    if minimum_srt_greater_than is not None:
                        filter_body += ' low-value="' + str(minimum_srt_greater_than) + '"'
                    if minimum_srt_less_than is not None:
                        filter_body += ' high-value="' + str(minimum_srt_less_than) + '"'
                    filter_body += '/>'
                if average_srt_greater_than is not None or average_srt_less_than is not None:
                    filter_body += '<avg'
                    if average_srt_greater_than is not None:
                        filter_body += ' low-value="' + str(average_srt_greater_than) + '"'
                    if average_srt_less_than is not None:
                        filter_body += ' high-value="' + str(average_srt_less_than) + '"'
                    filter_body += '/>'
                if maximum_srt_greater_than is not None or maximum_srt_less_than is not None:
                    filter_body += '<max'
                    if maximum_srt_greater_than is not None:
                        filter_body += ' low-value="' + str(maximum_srt_greater_than) + '"'
                    if maximum_srt_less_than is not None:
                        filter_body += ' high-value="' + str(maximum_srt_less_than) + '"'
                    filter_body += '/>'
                filter_body += '</server-response-time>'
            filter_body += '</network-performance>'
        return filter_body

    def __generate_soap_flow_report_payload_filter(self, payload_includes, payload_exclude, payload_match_any):
        filter_body = ''
        if (payload_includes is not None and len(payload_includes) > 0) or (
                payload_exclude is not None and len(payload_exclude) > 0):
            filter_body += '<query>'
            if payload_includes is not None and len(payload_includes) > 0:
                payload_match_tag = 'payload-match-all'
                if payload_match_any is True:
                    payload_match_tag = 'payload-match-any'
                if isinstance(payload_includes, list):
                    for item in payload_includes:
                        filter_body += '<' + str(payload_match_tag) + '>' + str(item) + '</' + str(
                            payload_match_tag) + '>'
                else:
                    filter_body += '<' + str(payload_match_tag) + '>' + str(payload_includes) + '</' + str(
                        payload_match_tag) + '>'
            if payload_exclude is not None and len(payload_exclude) > 0:
                if isinstance(payload_exclude, list):
                    for item in payload_exclude:
                        filter_body += '<payload-not-match-all>' + str(item) + '</payload-not-match-all>'
                else:
                    filter_body += '<payload-not-match-all>' + str(payload_exclude) + '</payload-not-match-all>'
            filter_body += '</query>'
        return filter_body

    def __generate_soap_host_information_service_filter(self, server_service_id_list, client_service_id_list,
                                                        server_port_protocol_list, client_port_protocol_list,
                                                        service_id_match_all, port_protocol_match_all):
        filter_body = ''
        if (service_id_match_all is not None and service_id_match_all is True) or (
                port_protocol_match_all is not None and port_protocol_match_all is True):
            match_all = "AND"
        else:
            match_all = "OR"
        if (server_service_id_list is not None and len(server_service_id_list) > 0) or (
                server_port_protocol_list is not None and len(server_port_protocol_list) > 0):
            filter_body += '<server-service-list operator="' + str(match_all) + '">'
            if server_service_id_list is not None and len(server_service_id_list) > 0:
                filter_body += '<profiled-service-list>'
                for service_id in server_service_id_list:
                    filter_body += '<profiled-service profile-index="' + str(service_id) + '"/>'
                filter_body += '</profiled-service-list>'
            if server_port_protocol_list is not None and len(server_port_protocol_list) > 0:
                filter_body += '<custom-service-list>'
                for port_protocol in server_port_protocol_list:
                    if '/' in port_protocol:
                        port = port_protocol.split('/')[0]
                        protocol = port_protocol.split('/')[1]
                        filter_body += '<custom-service protocol="' + str(protocol) + '" port-number="' + str(
                            port) + '"/>'
                filter_body += '</custom-service-list>'
            filter_body += '</server-service-list>'
        if (client_service_id_list is not None and len(client_service_id_list) > 0) or (
                client_port_protocol_list is not None and len(client_port_protocol_list) > 0):
            filter_body += '<client-service-list operator="' + str(match_all) + '">'
            if client_service_id_list is not None and len(client_service_id_list) > 0:
                filter_body += '<profiled-service-list>'
                for service_id in client_service_id_list:
                    filter_body += '<profiled-service profile-index="' + str(service_id) + '"/>'
                filter_body += '</profiled-service-list>'
            if client_port_protocol_list is not None and len(client_port_protocol_list) > 0:
                filter_body += '<custom-service-list>'
                for port_protocol in client_port_protocol_list:
                    if '/' in port_protocol:
                        port = port_protocol.split('/')[0]
                        protocol = port_protocol.split('/')[1]
                        filter_body += '<custom-service protocol="' + str(protocol) + '" port-number="' + str(
                            port) + '"/>'
                filter_body += '</custom-service-list>'
            filter_body += '</client-service-list>'
        return filter_body

    def __generate_soap_host_information_basic_filter(self, filter_type, filter_list, operator):
        filter_body = ''
        if operator is not None and operator is True:
            operator = "AND"
        else:
            operator = "OR"
        if filter_list is not None and len(filter_list) > 0:
            filter_body += '<' + str(filter_type) + ' operator="' + str(operator) + '">'
            for item in filter_list:
                filter_body += str(item) + ','
            filter_body = filter_body[:-1]
            filter_body += '</' + str(filter_type) + '>'
        return filter_body

    ############################################################################################################
    # Get Flows REST API call
    # https://developer.cisco.com/docs/stealthwatch/enterprise/#!reporting-api-version-2
    ############################################################################################################
    def get_flows_rest(self,  start_datetime, end_datetime, search_name=None, record_limit={"recordLimit": 3000},
                       subject_orientation=None, subject_ips=None, subject_hg=None, subject_tcp_udp_ports=None,
                       subject_username=None, subject_byte_count=None, subject_packet_count=None,
                       subject_mac_address=None, subject_process_name=None, subject_process_hash=None,
                       subject_trust_sec_id=None, subject_trust_sec_name=None, peer_ips=None, peer_hg=None,
                       peer_tcp_udp_ports=None,
                       peer_username=None, peer_byte_count=None, peer_packet_count=None,
                       peer_mac_address=None, peer_process_name=None, peer_process_hash=None,
                       peer_trust_sec_id=None, peer_trust_sec_name=None, flow_tcp_udp_ports=None,
                       flow_applications=None,
                       flow_direction=None, flow_byte_count=None, flow_packet_count=None, flow_payload=None,
                       flow_tcp_connections=None,
                       flow_tcp_retransmissions=None, flow_tls_version=None, flow_cipher_suite=None, flow_avg_rtp=None,
                       flow_avg_serv_resp_time=None, flow_data_src=None, flow_protocol=None,
                       flow_include_interface_data=None,
                       flow_action=None):
        """
        :param search_name: {"searchName": "Flows API Search on 3/1/2017 at 12:36 PM"}
        :param start_datetime: {"startDateTime": "2017-03-10T08:00:00Z"}
        :param end_datetime: {"endDateTime": "2017-03-10T08:05:00Z"}
        :param record_limit: {"recordLimit": 500}
        :param subject_orientation: {"orientation": "CLIENT"}
        :param subject_ips: {"ipAddresses": {"includes": ["192.168.0", "10.20"],"excludes": ["10.20.20", "192.168.0.1-100"]}}
        :param subject_hg: {"hostGroups": {"includes": [1234, 2345],"excludes": [12345, 23456]}}
        :param subject_tcp_udp_ports: {"tcpUdpPorts": {"includes": ["80-9000/tcp", "67-68/udp"],"excludes": ["8000-9000/tcp", "68/udp"]}}
        :param subject_username: {"username": {"includes": ["admin", "veep"],"excludes": ["jdub", "ghill"]}}
        :param subject_byte_count: {"byteCount": [{"operator": ">=","value": [204800]}]}
        :param subject_packet_count: {"packetCount": [{"operator": "BETWEEN","value": [100, 400]}]}
        :param subject_mac_address: {"macAddress": {"includes": ["00-1B-63-84-45-36", "00-1B-63-84-45-63"],"excludes": ["00-14-22-01-23-45", "00-14-22-01-23-54"]}}
        :param subject_process_name: {"processName": {"includes": ["cmd.exe", "telnet.exe"],"excludes": ["ping.exe", "proc.bin"]}}
        :param subject_process_hash: {"processHash": {"includes": ["cf23df2207d99a74fbe169e3eba035e633b65d94"],"excludes": ["cf23df2207d99a74fbe169e3eba035e633b65d97"]}}
        :param subject_trust_sec_id: {"trustSecId": {"includes": [32, 44],"excludes": [75]}}
        :param subject_trust_sec_name: {"trustSecName": {"includes": ["CTS-One"],"excludes": ["CTS-Two", "CTS-Three"]}}
        :param peer_ips: {"ipAddresses": {"includes": ["2001:0db8:85a3:0000:0000:8a2e:0370:7334", "2001:DB8:0:56::/64"],"excludes": ["2001:DB80:0:56::ABCD:239.18.52.86", "2001:DB8:0:56:ABCD:EF12:3456:1–10"]}}
        :param peer_hg: {"hostGroups": {"includes": [1234, 2345],"excludes": [12345, 23456]}}
        :param peer_tcp_udp_ports: {"tcpUdpPorts": {"includes": ["80-9000/tcp", "67-68/udp"],"excludes": ["8000-9000/tcp", "68/udp"]}}
        :param peer_username: {"username": {"includes": ["admin", "veep"],"excludes": ["jdub", "ghill"]}}
        :param peer_byte_count: {"byteCount": [{"operator": ">=","value": [204800]}]}
        :param peer_packet_count: {"packetCount": [{"operator": "BETWEEN","value": [100, 400]}]}
        :param peer_mac_address: {"macAddress": {"includes": ["00-1B-63-84-45-36", "00-1B-63-84-45-63"],"excludes": ["00-14-22-01-23-45", "00-14-22-01-23-54"]}}
        :param peer_process_name: {"processName": {"includes": ["cmd.exe", "telnet.exe"],"excludes": ["ping.exe", "proc.bin"]}}
        :param peer_process_hash: {"processHash": {"includes": ["cf23df2207d99a74fbe169e3eba035e633b65d94"],"excludes": ["cf23df2207d99a74fbe169e3eba035e633b65d97"]}}
        :param peer_trust_sec_id: {"trustSecId": {"includes": [32, 44],"excludes": [75]}}
        :param peer_trust_sec_name: {"trustSecName": {"includes": ["CTS-One"],"excludes": ["CTS-Two", "CTS-Three"]}}
        :param flow_tcp_udp_ports: {"tcpUdpPorts": {"includes": ["80-9000/tcp", "67-68/udp"],"excludes": ["8000-9000/tcp", "68/udp"]}}
        :param flow_applications: {"applications": {"includes": [3002, 3001, 116, 136],"excludes": [127, 125, 147, 45]}}
        :param flow_direction: {"flowDirection": "BIDIRECTIONAL"}
        :param flow_byte_count: {"byteCount": [{"operator": ">=","value": [204800]}]}
        :param flow_packet_count: {"packetCount": [{"operator": "<=","value": [10]}]}
        :param flow_payload: {"payload": {"includes": ["http", "blah"],"excludes": []}}
        :param flow_tcp_connections: {"tcpConnections": [{"operator": ">=","value": [2000]}]}
        :param flow_tcp_retransmissions: {"tcpRetransmissions": [{"operator": ">=","value": [2000]}]}
        :param flow_tls_version: {"tlsVersion": ["TLS 1.2", "UNKNOWN"]}
        :param flow_cipher_suite: {"cipherSuite": {"messageAuthCode": ["SHA256"], "keyExchange": ["ECDHE"],"authAlgorithm": ["RSA"],"encAlgorithm": ["AES_128_CBC"],"keyLength": ["128"]}}
        :param flow_avg_rtp: {"averageRoundTripTime": [{"operator": "<=","value": [50]}]}
        :param flow_avg_serv_resp_time: {"averageServerResponseTime": [{"operator": ">=","value": [2000]}]}
        :param flow_data_src: {"flowDataSource": [{"flowCollectorId": 151,"exporters": [{"ipAddress": "10.100.100.7","interfaceIds": [7,27]},{"ipAddress": "10.203.1.1"}]}]}
        :param flow_protocol: {"protocol": [114, 10]}
        :param flow_include_interface_data: {"includeInterfaceData": false}
        :param flow_action: {"flowAction": "permitted"}
        :return:
        """

        url = f"https://{self.__smc_ip}/sw-reporting/v2/tenants/{self.__domain_id}/flows/queries"

        # Grab any argument passed into funciton
        arguments = locals()
        del arguments['self']

        # Select only args passed in
        not_none_args = {k: v for k, v in arguments.items() if v is not None}

        # Filter args relating to subject/peer/flow
        subject_args = {k: v for k, v in not_none_args.items() if k.startswith('subject')}
        peer_args = {k: v for k, v in not_none_args.items() if k.startswith('peer')}
        flow_args = {k: v for k, v in not_none_args.items() if k.startswith('flow')}

        # Building the request body for the search
        request_body = {}

        request_body.update(start_datetime)
        request_body.update(end_datetime)
        request_body.update(record_limit)

        # Adding optional args to request_body if they were passed in
        if subject_args:
            request_body.update({'subject': {}})
            for k, v in subject_args.items():
                request_body['subject'].update(v)

        if peer_args:
            request_body.update({'peer': {}})
            for k, v in peer_args.items():
                request_body['peer'].update(v)

        if flow_args:
            request_body.update({'flow': {}})
            for k, v in flow_args.items():
                request_body['flow'].update(v)

        # print(self.__api_session.cookies)
        post_response = self.__execute_query(url,request_data=json.dumps(request_body), rest_method='post')

        search = post_response['query']

        url = f"https://{self.__smc_ip}/sw-reporting/v2/tenants/{self.__domain_id}/flows/queries/{search['id']}"

        # Waiting for search to complete then returning flow results
        while search['percentComplete'] != 100.0:
            response = self.__execute_query(url)

            search = response['query']
            if search['percentComplete'] != 100.0:
                time.sleep(1)
                print('Waiting for search to complete')

        response = self.__execute_query(f"{url}/results")

        results = response['flows']

        return results

    ############################################################################################################
    # Get Flows SOAP API call
    ############################################################################################################
    def get_flows(self, start_datetime=None, end_datetime=None, subject_ip=None, subject_host_group_id=None,
                  peer_ip=None,
                  peer_host_group_id=None, username_list=None, subject_orientation=None, remove_duplicate_flows=None,
                  filter_by=None,
                  includes_services_id_list=None, excludes_services_id_list=None, includes_ports_list=None,
                  excludes_ports_list=None, includes_protocols_number_list=None,
                  excludes_protocols_number_list=None,
                  includes_applications_id_list=None, excludes_applications_id_list=None, includes_asn_list=None,
                  excludes_asn_list=None, includes_dscp_list=None, excludes_dscp_list=None,
                  includes_vlan_id_list=None, excludes_vlan_id_list=None, includes_mpls_vlan_id_list=None,
                  excludes_mpls_vlan_id_list=None, includes_client_ports_list=None, excludes_client_ports_list=None,
                  client_bytes_greater_than=None, client_bytes_less_than=None, client_packets_greater_than=None,
                  client_packets_less_than=None, server_bytes_greater_than=None, server_bytes_less_than=None,
                  server_packets_greater_than=None, server_packets_less_than=None, total_bytes_greater_than=None,
                  total_bytes_less_than=None, total_packets_greater_than=None, total_packets_less_than=None,
                  total_connections_greater_than=None, total_connections_less_than=None,
                  total_retransmissions_greater_than=None, total_retransmissions_less_than=None,
                  minimum_rtt_greater_than=None, minimum_rtt_less_than=None, average_rtt_greater_than=None,
                  average_rtt_less_than=None, maximum_rtt_greater_than=None, maximum_rtt_less_than=None,
                  minimum_srt_greater_than=None, minimum_srt_less_than=None, average_srt_greater_than=None,
                  average_srt_less_than=None, maximum_srt_greater_than=None, maximum_srt_less_than=None,
                  payload_includes=None, payload_exclude=None, payload_match_any=None, flow_collector_list=None,
                  flow_collector_id=None, exporter_ip_list=None, exporter_ip=None, interface_id_list=None,
                  order_by=None, descending_order=None, max_rows=None):
        response = None
        if max_rows is None:
            max_rows = 2000
        if remove_duplicate_flows is None:
            remove_duplicate_flows = False
        if order_by is None:
            order_by = "TOTAL_BYTES"
        if descending_order is None:
            descending_order = True
        uri = 'https://' + self.__smc_ip + '/smc/swsService/flows'
        request_body = '<getFlows><flow-filter max-rows="' + str(max_rows)
        request_body += '" domain-id="' + str(self.__domain_id)
        request_body += '" remove-duplicates="' + str(remove_duplicate_flows).lower()
        request_body += '" order-by="' + str(order_by)
        request_body += '" order-by-desc="' + str(descending_order).lower() + '">'
        request_body += self.__generate_soap_date_selection(start_datetime, end_datetime)
        if filter_by == 'FLOW_COLLECTOR':
            request_body += self.__generate_soap_device_selection(filter_by, device_id=flow_collector_list)
        elif filter_by == 'EXPORTER':
            request_body += self.__generate_soap_device_selection(filter_by, device_id=flow_collector_id,
                                                                  exporter_ip=exporter_ip_list)
        elif filter_by == 'INTERFACE':
            request_body += self.__generate_soap_device_selection(filter_by, device_id=flow_collector_id,
                                                                  exporter_ip=exporter_ip,
                                                                  interface_id=interface_id_list)
        request_body += self.__generate_soap_host_selection(subject_ip, subject_host_group_id, peer_ip,
                                                            peer_host_group_id, subject_orientation,
                                                            force_pair_selection=True)
        request_body += self.__generate_soap_flow_report_basic_filter('services', includes_services_id_list,
                                                                      excludes_services_id_list)
        request_body += self.__generate_soap_flow_report_basic_filter('ports', includes_ports_list,
                                                                      excludes_ports_list)
        request_body += self.__generate_soap_flow_report_basic_filter('protocols', includes_protocols_number_list,
                                                                      excludes_protocols_number_list)
        request_body += self.__generate_soap_flow_report_basic_filter('applications', includes_applications_id_list,
                                                                      excludes_applications_id_list)
        request_body += self.__generate_soap_flow_report_traffic_filter(client_bytes_greater_than,
                                                                        client_bytes_less_than,
                                                                        client_packets_greater_than,
                                                                        client_packets_less_than,
                                                                        server_bytes_greater_than,
                                                                        server_bytes_less_than,
                                                                        server_packets_greater_than,
                                                                        server_packets_less_than,
                                                                        total_bytes_greater_than,
                                                                        total_bytes_less_than,
                                                                        total_packets_greater_than,
                                                                        total_packets_less_than)
        request_body += self.__generate_soap_flow_report_network_performance_filter(total_connections_greater_than,
                                                                                    total_connections_less_than,
                                                                                    total_retransmissions_greater_than,
                                                                                    total_retransmissions_less_than,
                                                                                    minimum_rtt_greater_than,
                                                                                    minimum_rtt_less_than,
                                                                                    average_rtt_greater_than,
                                                                                    average_rtt_less_than,
                                                                                    maximum_rtt_greater_than,
                                                                                    maximum_rtt_less_than,
                                                                                    minimum_srt_greater_than,
                                                                                    minimum_srt_less_than,
                                                                                    average_srt_greater_than,
                                                                                    average_srt_less_than,
                                                                                    maximum_srt_greater_than,
                                                                                    maximum_srt_less_than)
        request_body += self.__generate_soap_flow_report_basic_filter('as-numbers', includes_asn_list,
                                                                      excludes_asn_list)
        request_body += self.__generate_soap_flow_report_basic_filter('dscps', includes_dscp_list,
                                                                      excludes_dscp_list)
        request_body += self.__generate_soap_flow_report_basic_filter('vlan-ids', includes_vlan_id_list,
                                                                      excludes_vlan_id_list)
        request_body += self.__generate_soap_flow_report_basic_filter('mpls-labels', includes_mpls_vlan_id_list,
                                                                      excludes_mpls_vlan_id_list)
        request_body += self.__generate_soap_flow_report_basic_filter('client-ports', includes_client_ports_list,
                                                                      excludes_client_ports_list)
        request_body += self.__generate_soap_flow_report_payload_filter(payload_includes, payload_exclude,
                                                                        payload_match_any)
        if username_list is not None and len(username_list) > 0:
            # Convert space sep. string into a list
            request_body += "<usernames>"

            for username in username_list.split():
                request_body += '<user name="' + username + '"/>'

            request_body += "</usernames>"

        request_body += "</flow-filter></getFlows>"
        response = self.__execute_soap_query(uri, request_body)
        if self.DEBUG:
            print('Stealthwatch API call response: \n' + json.dumps(response, indent=4, sort_keys=True))
        if response is None:
            print("ERROR: Unable to get flows.")
            return None
        elif response['soapenc:Envelope']['soapenc:Body']['getFlowsResponse']['flow-list'] is None or \
                response['soapenc:Envelope']['soapenc:Body']['getFlowsResponse']['flow-list'][
                    'flow'] is None:
            return {}
        else:
            if not isinstance(response['soapenc:Envelope']['soapenc:Body']['getFlowsResponse']['flow-list']['flow'],
                              list):
                response['soapenc:Envelope']['soapenc:Body']['getFlowsResponse']['flow-list']['flow'] = [
                    response['soapenc:Envelope']['soapenc:Body']['getFlowsResponse']['flow-list']['flow']]
            return response['soapenc:Envelope']['soapenc:Body']['getFlowsResponse']['flow-list']['flow']

    ############################################################################################################
    # Get Host Snapshot
    ############################################################################################################
    def get_host_snapshot(self, host_ip, start_datetime=None, number_days_back=None, flow_collector_list=None):
        response = None
        uri = 'https://' + self.__smc_ip + '/smc/swsService/hosts'
        request_body = '<getHostSnapshot><host-filter domain-id="' + str(self.__domain_id) + '">'
        request_body += self.__generate_soap_date_selection(start_datetime=start_datetime,
                                                            number_days_back=number_days_back,
                                                            force_day_selection=True)
        request_body += self.__generate_soap_device_selection('FLOW_COLLECTOR', device_id=flow_collector_list)
        request_body += self.__generate_soap_host_selection(host_ip, None, None, None)
        request_body += '</host-filter></getHostSnapshot>'
        response = self.__execute_soap_query(uri, request_body)
        if self.DEBUG:
            print('Stealthwatch API call response: \n' + json.dumps(response, indent=4, sort_keys=True))
        if response is None:
            print("ERROR: Unable to get host snapshot.")
            return None
        elif response['soapenc:Envelope']['soapenc:Body']['getHostSnapshotResponse'] is None or \
                response['soapenc:Envelope']['soapenc:Body']['getHostSnapshotResponse'][
                    'host-snapshot'] is None:
            return {}
        else:
            return response['soapenc:Envelope']['soapenc:Body']['getHostSnapshotResponse']['host-snapshot']

    ############################################################################################################
    # Retrive the host informatoion.
    ############################################################################################################
    def get_host_information(self, number_days_back=None, subject_ip=None, subject_host_group_id=None,
                             server_service_id_list=None, client_service_id_list=None,
                             server_port_protocol_list=None, client_port_protocol_list=None,
                             service_id_match_all=None, port_protocol_match_all=None,
                             operating_system_code_list=None, operating_system_code_match_all=None,
                             alarm_type_id_list=None, alarm_type_id_match_all=None, alert_type_id_list=None,
                             alert_type_id_match_all=None,
                             ci_event_type_id_list=None, ci_event_type_id_match_all=None, flow_collector_list=None):
        response = None
        uri = 'https://' + self.__smc_ip + '/smc/swsService/hosts'
        request_body = '<getHostInformation><host-information-filter domain-id="' + str(self.__domain_id) + '">'
        if number_days_back is None:
            number_days_back = 1
        request_body += self.__generate_soap_date_selection(number_days_back=number_days_back)
        request_body += self.__generate_soap_device_selection('FLOW_COLLECTOR', device_id=flow_collector_list)
        if subject_ip is not None and isinstance(subject_ip, str):
            subject_ip = [subject_ip]
        request_body += self.__generate_soap_host_selection(subject_ip, subject_host_group_id, None, None)
        request_body += self.__generate_soap_host_information_service_filter(server_service_id_list,
                                                                             client_service_id_list,
                                                                             server_port_protocol_list,
                                                                             client_port_protocol_list,
                                                                             service_id_match_all,
                                                                             port_protocol_match_all)
        request_body += self.__generate_soap_host_information_basic_filter('operating-system',
                                                                           operating_system_code_list,
                                                                           operating_system_code_match_all)
        request_body += self.__generate_soap_host_information_basic_filter('alarms',
                                                                           alarm_type_id_list,
                                                                           alarm_type_id_match_all)
        request_body += self.__generate_soap_host_information_basic_filter('alerts',
                                                                           alert_type_id_list,
                                                                           alert_type_id_match_all)
        request_body += self.__generate_soap_host_information_basic_filter('ci-events',
                                                                           ci_event_type_id_list,
                                                                           ci_event_type_id_match_all)
        request_body += '</host-information-filter></getHostInformation>'
        response = self.__execute_soap_query(uri, request_body)
        if self.DEBUG:
            print('Stealthwatch API call response: \n' + json.dumps(response, indent=4, sort_keys=True))
        if response is None:
            print("ERROR: Unable to get host information.")
            return None
        elif response['soapenc:Envelope']['soapenc:Body']['getHostInformationResponse'][
            'host-information-list'] is None or \
                response['soapenc:Envelope']['soapenc:Body']['getHostInformationResponse'][
                    'host-information-list']['host-information'] is None:
            return {}
        else:
            return \
                response['soapenc:Envelope']['soapenc:Body']['getHostInformationResponse']['host-information-list'][
                    'host-information']

    ############################################################################################################
    # Get host groups.
    ############################################################################################################
    def get_host_groups(self):
        response = None
        uri = 'https://' + self.__smc_ip + '/smc/swsService/configuration'
        request_body = '<getHostGroups><domain id="' + str(self.__domain_id) + '"/></getHostGroups>'
        response = self.__execute_soap_query(uri, request_body)
        if self.DEBUG:
            print('Stealthwatch API call response: \n' + json.dumps(response, indent=4, sort_keys=True))
        if response is None:
            print("ERROR: Unable to get host groups.")
            return None
        elif 'soapenc:Fault' in response['soapenc:Envelope']['soapenc:Body']:
            return response['soapenc:Envelope']['soapenc:Body']
        else:
            return response['soapenc:Envelope']['soapenc:Body']['getHostGroupsResponse']['domain']['host-group-tree']

    ############################################################################################################
    # Get non-domain-specific metadatas.
    ############################################################################################################
    def get_metadatas(self):
        response = None
        uri = 'https://' + self.__smc_ip + '/smc/jrmService/eventMetadataService'
        request_body = '<getNonDomainSpecificMetadatas></getNonDomainSpecificMetadatas>'
        response = self.__execute_soap_query(uri, request_body)
        if self.DEBUG:
            print('Stealthwatch API call response: \n' + json.dumps(response, indent=4, sort_keys=True))
        if response is None:
            print("ERROR: Unable to get non-domain-specific metadatas.")
            return None
        else:
            return response

    ############################################################################################################
    # Filter for SOAP security events types and ports selection
    ############################################################################################################
    def __generate_soap_security_events_qualitative_selection(self, selection_tag, selection_list):
        result = ""
        if selection_list is not None:
            if not isinstance(selection_list, list):
                selection_list = [selection_list]
            selection_list_string = ""
            for selection in selection_list:
                selection_list_string += str(selection) + ","
            selection_list_string = selection_list_string[:-1]
            if len(selection_list_string) > 0:
                result = '<' + selection_tag + '>' + selection_list_string + '</' + selection_tag + '>'
        return result

    ############################################################################################################
    # Filter for SOAP security events hit-count and ci-points selection
    ############################################################################################################
    def __generate_soap_security_events_quantitative_selection(self, selection_tag, selection_low_value,
                                                               selection_high_value):
        result = ""
        if selection_low_value is not None or selection_high_value is not None:
            result += '<' + selection_tag
            if selection_low_value is not None:
                result += ' low-value="' + str(selection_low_value) + '"'
            if selection_high_value is not None:
                result += ' high-value="' + str(selection_high_value) + '"'
            result += '/>'
        return result

    ############################################################################################################
    # Get Security Events API call
    ############################################################################################################
    def get_security_events_soap(self, start_datetime=None, end_datetime=None, subject_ip=None,
                                 subject_host_group_id=None, peer_ip=None, peer_host_group_id=None,
                                 subject_orientation=None,
                                 security_event_type_id_list=None, ports_list=None, hit_count_low_value=None,
                                 hit_count_high_value=None, ci_points_low_value=None, ci_points_high_value=None,
                                 filter_by=None, flow_collector_list=None, flow_collector_id=None,
                                 exporter_ip_list=None, exporter_ip=None, interface_id_list=None, max_rows=None):
        response = None
        if max_rows is None:
            max_rows = 2000
        uri = 'https://' + self.__smc_ip + '/smc/swsService/security'
        request_body = '<getSecurityEvents><security-event-filter max-rows="' + str(max_rows)
        request_body += '" domain-id="' + str(self.__domain_id) + '">'
        request_body += self.__generate_soap_date_selection(start_datetime, end_datetime,
                                                            force_active_time_selection=True)
        if filter_by == 'FLOW_COLLECTOR':
            request_body += self.__generate_soap_device_selection(filter_by, device_id=flow_collector_list)
        elif filter_by == 'EXPORTER':
            request_body += self.__generate_soap_device_selection(filter_by, device_id=flow_collector_id,
                                                                  exporter_ip=exporter_ip_list)
        elif filter_by == 'INTERFACE':
            request_body += self.__generate_soap_device_selection(filter_by, device_id=flow_collector_id,
                                                                  exporter_ip=exporter_ip,
                                                                  interface_id=interface_id_list)
        request_body += self.__generate_soap_host_selection(subject_ip, subject_host_group_id, peer_ip,
                                                            peer_host_group_id,
                                                            subject_orientation=subject_orientation,
                                                            force_pair_selection=True)
        request_body += self.__generate_soap_security_events_qualitative_selection("types",
                                                                                   security_event_type_id_list)
        request_body += self.__generate_soap_security_events_qualitative_selection("ports",
                                                                                   ports_list)
        request_body += self.__generate_soap_security_events_quantitative_selection("hit-count",
                                                                                    hit_count_low_value,
                                                                                    hit_count_high_value)
        request_body += self.__generate_soap_security_events_quantitative_selection("ci-points",
                                                                                    ci_points_low_value,
                                                                                    ci_points_high_value)
        request_body += '</security-event-filter></getSecurityEvents>'
        response = self.__execute_soap_query(uri, request_body)
        if self.DEBUG:
            print('Stealthwatch API call response: \n' + json.dumps(response, indent=4, sort_keys=True))
        if response is None:
            print("ERROR: Unable to get security events.")
            return None
        elif response['soapenc:Envelope']['soapenc:Body']['getSecurityEventsResponse']['security-event-list'] is None or \
                response['soapenc:Envelope']['soapenc:Body']['getSecurityEventsResponse'][
                    'security-event-list'][
                    'security-event'] is None:
            return {}
        else:
            if not isinstance(
                    response['soapenc:Envelope']['soapenc:Body']['getSecurityEventsResponse']['security-event-list'][
                        'security-event'],
                    list):
                response['soapenc:Envelope']['soapenc:Body']['getSecurityEventsResponse']['security-event-list'][
                    'security-event'] = [
                    response['soapenc:Envelope']['soapenc:Body']['getSecurityEventsResponse']['security-event-list'][
                        'security-event']]
            return response['soapenc:Envelope']['soapenc:Body']['getSecurityEventsResponse']['security-event-list'][
                'security-event']

    ############################################################################################################
    ############################################################################################################
    ############################################################################################################
    # LEGACY REST API
    ############################################################################################################
    ############################################################################################################
    ############################################################################################################

    ############################################################################################################
    # Retrieve the flow collectors.
    ############################################################################################################
    def get_flow_collectors(self, surpress_std_out=None):
        response = None
        if surpress_std_out is None:
            surpress_std_out = False
        uri = 'https://' + self.__smc_ip + '/smc/rest/system/domains/' + str(self.__domain_id) + '/flowCollectors'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch API call response: \n' + json.dumps(response, indent=4, sort_keys=True))
        if response is None:
            if not surpress_std_out:
                print("ERROR: Unable to get flow collectors.")
            return None
        else:
            return response

    ############################################################################################################
    # Get Alarm Summary per target Host
    ############################################################################################################
    def get_alarm_counts(self, source_or_target, is_active=None, is_acknowledged=None, alarm_types_list=None):
        response = None
        query_string = ""
        if is_active is not None:
            query_string += "&isActive=" + str(is_active).lower()
        if is_acknowledged is not None:
            query_string += "&isAcknowledged=" + str(is_acknowledged).lower()
        if alarm_types_list is not None:
            query_string += "&alarmTypes=" + str(alarm_types_list).replace("[", "").replace("]", "").replace(" ", "")
        if query_string.startswith("&"):
            query_string = "?" + query_string[1:]
        uri = 'https://' + self.__smc_ip + '/smc/rest/domains/' + str(
            self.__domain_id) + '/alarmSummary/alarms/per/' + source_or_target + query_string
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch API get_source_alarm_counts call response: \n' + json.dumps(response, indent=4,
                                                                                            sort_keys=True))
        if response is None:
            print("ERROR: Unable to get_source_alarm_counts.")
            return None
        else:
            return response

    ############################################################################################################
    # Generates a list with short-form representations of hosts that match the domain, and optionally the    # IP range OR keyword search
    ############################################################################################################
    def get_hosts_details_list(self):
        response = None
        uri = 'https://' + self.__smc_ip + '/smc/rest/domains/' + str(self.__domain_id) + '/hosts'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch API get_hosts_details_list call response: \n' + json.dumps(response, indent=4,
                                                                                           sort_keys=True))
        if response is None:
            print("ERROR: Unable to get_hosts_details_list.")
            return None
        else:
            return response

    ############################################################################################################
    # Generates a report on a single host with a short-form representations of the host for the domain and IP
    ############################################################################################################
    def get_host_details_by_ip(self, ip_address):
        response = None
        uri = 'https://' + self.__smc_ip + '/smc/rest/domains/' + str(self.__domain_id) + '/hosts/' + ip_address
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch API get_host_details_by_ip call response: \n' + json.dumps(response, indent=4,
                                                                                           sort_keys=True))
        if response is None:
            print("ERROR: Unable to get_host_details_by_ip.")
            return None
        else:
            return response

    ############################################################################################################
    # Generates an application traffic report for that host for the domain and IP
    ############################################################################################################
    def get_application_traffic_by_ip(self, ip_address):
        response = None
        uri = 'https://' + self.__smc_ip + '/smc/rest/domains/' + str(
            self.__domain_id) + '/hosts/' + ip_address + '/applicationTraffic'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print(
                'Stealthwatch API get_application_traffic_by_ip call response: \n' + json.dumps(response, indent=4,
                                                                                                sort_keys=True))
        if response is None:
            print("ERROR: Unable to get_application_traffic_by_ip.")
            return None
        else:
            return response

    ############################################################################################################
    # Generates a report on a single host with a long-form representation of that host for the domain and IP
    ############################################################################################################
    def get_host_report_by_ip(self, ip_address, utc_offset=None):
        response = None
        query_string = ""
        if utc_offset is None:
            utc_offset = 0
        uri = 'https://' + self.__smc_ip + '/smc/rest/domains/' + str(
            self.__domain_id) + '/hosts/' + ip_address + '/report?utcOffset=' + str(utc_offset)
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch API get_host_report_by_ip call response: \n' + json.dumps(response, indent=4,
                                                                                          sort_keys=True))
        if response is None:
            print("ERROR: Unable to get_host_report_by_ip.")
            return None
        else:
            return response

    ############################################################################################################
    # Generates a report on a single user with a long-form representation of that host for the domain and IP
    ############################################################################################################
    def get_user_details(self, username, utc_offset=None):
        response = None
        query_string = ""
        if utc_offset is None:
            utc_offset = 0
        uri = 'https://' + self.__smc_ip + '/smc/rest/domains/' + str(
            self.__domain_id) + '/users/userDetails?username=' + username + '&utcOffset=' + str(utc_offset)
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch API get_user_report call response: \n' + json.dumps(response, indent=4,
                                                                                    sort_keys=True))
        if response is None:
            print("ERROR: Unable to get_user_report.")
            return None
        else:
            return response

    ############################################################################################################
    # Generates a list of the number of alarms by category for an IP over the course of time
    ############################################################################################################
    def get_category_alarm_trends_by_ip(self, ip_address, utc_offset=None):
        response = None
        query_string = ""
        if utc_offset is None:
            utc_offset = 0
        current_time = str(datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "-0000")
        uri = 'https://' + self.__smc_ip + '/smc/rest/domains/' + str(
            self.__domain_id) + '/users/categories?currentTime=' + current_time + '&lastActiveSessionIp=' + ip_address + '&utcOffset=' + str(
            utc_offset)
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch API get_category_alarm_trends_by_ip call response: \n' + json.dumps(response, indent=4,
                                                                                                    sort_keys=True))
        if response is None:
            print("ERROR: Unable to get_category_alarm_trends_by_ip.")
            return None
        else:
            return response

    ############################################################################################################
    # Generates a list of the device sessions by a username
    ############################################################################################################
    def get_device_sessions_by_username(self, username, utc_offset=None):
        response = None
        if utc_offset is None:
            utc_offset = 0
        current_time = str(datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "-0000")
        try:
            uri = 'https://' + self.__smc_ip + '/smc/rest/domains/' \
                  + str(self.__domain_id) + '/users/devicesSessions?currentTime=' \
                  + current_time + '&username=' + username + '&utcOffset=' \
                  + str(utc_offset)
            response = self.__execute_query(uri, None)
            if response:
                if self.DEBUG:
                    print('Stealthwatch API get_device_sessions_by_username call response: \n' \
                          + json.dumps(response, indent=4, sort_keys=True))
            else:
                print('Could not get device sessions by username')
        except Exception as e:
            print('Error: Could not get Device Sessions by Username: {}'.format(e))
        if response is None:
            print("ERROR: Unable to get_device_sessions_by_username.")
            return None
        else:
            return response

    ############################################################################################################
    # Generates a report on a single host with a summary representation of that host for the domain and IP
    ############################################################################################################
    def get_host_summary_by_ip(self, ip_address):
        response = None
        uri = 'https://' + self.__smc_ip + '/smc/rest/domains/' + str(
            self.__domain_id) + '/hosts/' + ip_address + '/summary'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch API get_host_summary_by_ip call response: \n' + json.dumps(response, indent=4,
                                                                                           sort_keys=True))
        if response is None:
            print("ERROR: Unable to get_host_summary_by_ip.")
            return None
        else:
            return response

    def converst_search_type(self, search_type):
        if search_type.lower() == "flows":
            search_type = "flowAnalysis"
            return search_type
        elif search_type.lower() == "top applications":
            search_type = "topFlowApplications"
            return search_type
        elif search_type.lower() == "top ports":
            search_type = "topFlowPorts"
            return search_type
        elif search_type.lower() == "top protocols":
            search_type = "topFlowProtocols"
            return search_type
        elif search_type.lower() == "top hosts":
            search_type = "topFlowHosts"
            return search_type
        elif search_type.lower() == "top peers":
            search_type = "topFlowPeers"
            return search_type
        elif search_type.lower() == "top conversations":
            search_type = "topFlowConversations"
            return search_type
        elif search_type.lower() == "top services":
            search_type = "topFlowServices"
            return search_type
        else:
            return "unknown"

    ############################################################################################################
    #
    ############################################################################################################
    def __create_simple_search_request_data(self, search_type, subject_ip):
        current_time = time.ctime()
        search_name = "API flow report (" + self.__smc_username + "): " + search_type + " [" + current_time + "]"
        main_report_filter_key = ""
        if search_type.lower() == "flows":
            search_type = "flowAnalysis"
            main_report_filter_key = "flowAnalysisFilter"
        elif search_type.lower() == "top applications":
            search_type = "topFlowApplications"
            main_report_filter_key = "topReportFilter"
        elif search_type.lower() == "top ports":
            search_type = "topFlowPorts"
            main_report_filter_key = "topReportFilter"
        elif search_type.lower() == "top protocols":
            search_type = "topFlowProtocols"
            main_report_filter_key = "topReportFilter"
        elif search_type.lower() == "top hosts":
            search_type = "topFlowHosts"
            main_report_filter_key = "topReportFilter"
        elif search_type.lower() == "top peers":
            search_type = "topFlowPeers"
            main_report_filter_key = "topReportFilter"
        elif search_type.lower() == "top conversations":
            search_type = "topFlowConversations"
            main_report_filter_key = "topReportFilter"
        elif search_type.lower() == "top services":
            search_type = "topFlowServices"
            main_report_filter_key = "topReportFilter"
        request_data = {}
        request_data["searchDisplayName"] = search_name
        request_data["searchType"] = search_type
        request_data["savedByUser"] = False
        request_data["user"] = self.__smc_username
        request_data_filter = {}
        main_report_filter = {
            "name": search_name,
            "description": "",
            "domainId": self.__domain_id,
            "absolute": None,
            "relativeSecondsFromCurrent": 300,
            "hasRulesPacked": True,
            "advanced": {
                "direction": "INBOUND_PLUS_OUTBOUND",
                "maxRows": 50,
                "excludeBpsPps": True,
                "excludeOthers": True,
                "orderBy": "TOTAL_BYTES",
                "defaultColumns": True,
                "excludeCounts": False,
                "performanceOption": "Standard"
            },
            "connection": {
                "applications": {
                    "includes": [],
                    "excludes": []
                },
                "byteRates": [],
                "bytes": [],
                "deviceIds": {
                    "includes": [],
                    "excludes": []
                },
                "devices": {
                    "includes": [],
                    "excludes": []
                },
                "packetRates": [],
                "packets": [],
                "tcpConnections": [],
                "urls": {
                    "includes": [],
                    "excludes": []
                },
                "portProtocols": {
                    "includes": [],
                    "excludes": []
                },
                "interfaces": {
                    "includes": []
                },
                "protocols": [],
                "flowsDirection": "BOTH",
                "cipherSuite": {
                    "messageAuthCode": [],
                    "keyExchange": [],
                    "authAlgorithm": [],
                    "encAlgorithm": [],
                    "keyLength": []
                },
                "tlsVersion": [],
                "totalTcpConnections": [],
                "totalTcpRetransmissions": [],
                "roundTripTime": [],
                "serverResponseTime": [],
                "isDownload": False,
                "includeInterfaceData": False,
                "maxRecords": 2000
            },
            "object": {
                "byteRates": [],
                "bytes": [],
                "deviceIds": {
                    "includes": [],
                    "excludes": []
                },
                "devices": {
                    "includes": [],
                    "excludes": []
                },
                "hostGroups": {
                    "includes": [],
                    "excludes": []
                },
                "ipAddresses": {
                    "includes": [subject_ip],
                    "excludes": []
                },
                "orientation": "either",
                "packetRates": [],
                "packets": [],
                "portProtocols": {
                    "includes": [],
                    "excludes": []
                },
                "processHashes": {
                    "includes": [],
                    "excludes": []
                },
                "processNames": {
                    "includes": [],
                    "excludes": []
                },
                "ratios": [],
                "trustSecIds": {
                    "includes": [],
                    "excludes": []
                },
                "trustSecNames": {
                    "includes": [],
                    "excludes": []
                },
                "users": {
                    "includes": [],
                    "excludes": []
                }
            },
            "peer": {
                "byteRates": [],
                "bytes": [],
                "deviceIds": {
                    "includes": [],
                    "excludes": []
                },
                "devices": {
                    "includes": [],
                    "excludes": []
                },
                "hostGroups": {
                    "includes": [],
                    "excludes": []
                },
                "ipAddresses": {
                    "includes": [],
                    "excludes": []
                },
                "packetRates": [],
                "packets": [],
                "portProtocols": {
                    "includes": [],
                    "excludes": []
                },
                "processHashes": {
                    "includes": [],
                    "excludes": []
                },
                "processNames": {
                    "includes": [],
                    "excludes": []
                },
                "ratios": [],
                "trustSecIds": {
                    "includes": [],
                    "excludes": []
                },
                "trustSecNames": {
                    "includes": [],
                    "excludes": []
                },
                "users": {
                    "includes": [],
                    "excludes": []
                }
            }
        }
        request_data_filter[main_report_filter_key] = main_report_filter
        request_data["searchContext"] = request_data_filter
        return request_data

    ############################################################################################################
    #
    ############################################################################################################
    def create_simple_search(self, search_type, subject_ip):
        response = None
        request_data = self.__create_simple_search_request_data(search_type, subject_ip)
        uri = 'https://' + self.__smc_ip + '/smc/rest/domains/' + str(self.__domain_id) + '/searches'
        response = self.__execute_query(uri, json.dumps(request_data), rest_method="post")
        if self.DEBUG:
            print(
                'Stealthwatch API create_simple_search call response: \n' + json.dumps(response, indent=4,
                                                                                       sort_keys=True))
        if response is None:
            print("ERROR: Unable to create_simple_search.")
            return None
        else:
            return response

    ############################################################################################################
    #
    ############################################################################################################
    def create_simple_job(self, search_id):
        response = None
        uri = 'https://' + self.__smc_ip + '/smc/rest/domains/' + str(self.__domain_id) + '/searches/' + str(
            search_id) + '/jobs'
        response = self.__execute_query(uri, json.dumps({}), rest_method="post")
        if self.DEBUG:
            print('Stealthwatch API create_simple_job call response: \n' + json.dumps(response, indent=4,
                                                                                      sort_keys=True))
        if response is None:
            print("ERROR: Unable to create_simple_job.")
            return None
        else:
            return response

    ############################################################################################################
    # Retrieve job status by serach id and search job id.
    ############################################################################################################
    def get_job_status(self, search_id, job_id):
        response = None
        uri = 'https://' + self.__smc_ip + '/smc/rest/domains/' + str(self.__domain_id) + '/searches/' + str(
            search_id) + '/jobstatus/' + job_id
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch API get_job_status_by_id call response: \n' + json.dumps(response, indent=4,
                                                                                         sort_keys=True))
        if response is None:
            print("ERROR: Unable to get_job_status_by_id.")
            return None
        else:
            return response

    ############################################################################################################
    # Generates a list of time series data with inbound, outbound and within application traffic.
    ############################################################################################################
    def get_application_traffic_by_host_group_id(self, host_group_id, start_datetime=None, end_datetime=None):
        response = None
        query_string = ""
        after_7_0 = self.version_after(7, 0)
        for key, value in [('start', start_datetime), ('end', end_datetime)]:
            if value is not None:
                timestamp = value.strftime('%Y-%m-%dT%H:%M:%S.%f')
                timestamp, subseconds = timestamp.split('.')
                subseconds = subseconds[0:3]  # Java's parser can only handle this much precision.
                timestamp = '.'.join([timestamp, subseconds])
                parameter = '{}Time'.format(key) if after_7_0 else key
                query_string += '&{}={}'.format(parameter, timestamp)
        if query_string.startswith("&"):
            query_string = "?" + query_string[1:]
        uri = 'https://' + self.__smc_ip + '/smc/rest/domains/' + str(self.__domain_id) + '/hostgroups/' + str(
            host_group_id) + '/applicationTraffic' + query_string
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch API get_application_traffic call response: \n' + json.dumps(response, indent=4,
                                                                                            sort_keys=True))
        if response is None:
            print("ERROR: Unable to get_application_traffic.")
            return None
        else:
            return response

    ############################################################################################################
    # Generates a list of time series data with inbound, outbound and within application traffic.
    ############################################################################################################
    def get_application_traffic_by_interface(self, flow_collector_id, exporter_ip, interface_id, start_datetime=None,
                                             end_datetime=None, application_limit=None):
        response = None
        if flow_collector_id is None or exporter_ip is None or interface_id is None:
            return None
        if application_limit is None:
            application_limit = 10
        query_string = "?responseType=TimeSeries"
        if application_limit is not None:
            query_string += "&limit=" + str(application_limit)
        if start_datetime is not None:
            start_timestamp = start_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f')
            while len(start_timestamp.split('.')[1]) > 3:
                start_timestamp = start_timestamp[:-1]
            query_string += "&filter[startTime]=" + start_timestamp
        if end_datetime is not None:
            end_timestamp = end_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f')
            while len(end_timestamp.split('.')[1]) > 3:
                end_timestamp = end_timestamp[:-1]
            query_string += "&filter[endTime]=" + end_timestamp
        uri = 'https://' + self.__smc_ip + '/smc/rest/sw-reporting/v1/tenants/' + str(
            self.__domain_id) + '/devices/' + str(
            flow_collector_id) + '/exporters/' + str(exporter_ip) + '/interfaces/' + str(
            interface_id) + '/application-traffic' + query_string
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch API get_application_traffic call response: \n' + json.dumps(response, indent=4,
                                                                                            sort_keys=True))
        if response is None:
            print("ERROR: Unable to get_application_traffic.")
            return None
        else:
            return response

    ############################################################################################################
    # Retrieve system built-in application definitions.
    ############################################################################################################
    def get_application_definitions(self):
        response = None
        uri = 'https://' + self.__smc_ip + '/smc/rest/system/applications/definitions'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch get_application_definitions: \n' + json.dumps(response, indent=4, sort_keys=True))
        if response is None:
            print("ERROR: Unable to get_application_definitions.")
            return None
        else:
            return response

    ############################################################################################################
    # Retrieve application mappings.
    ############################################################################################################
    def get_application_ids(self):
        response = None
        uri = 'https://' + self.__smc_ip + '/smc/rest/system/applications/mappings'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch get_application_ids: \n' + json.dumps(response, indent=4, sort_keys=True))
        if response is None:
            print("ERROR: Unable to get_application_ids.")
            return None
        else:
            return response

    ############################################################################################################
    # Retrieve System Domains.
    ############################################################################################################
    def get_domains(self):
        if self.version_after(6, 9):
            return self.get_tenants()

        response = None
        try:
            url = 'https://{}/smc/rest/system/domains'.format(self.__smc_ip)
            response = self.__execute_query(url, None)
        except Exception as e:
            print('Could not get SMC domains: {}'.format(e))
            return None
        if not response:
            print('Could not get SMC domains')
            return None
        if self.DEBUG:
            print('SMC domains:\n{}'.format(json.dumps(response, indent=4, sort_keys=True)))
        return response

    ############################################################################################################
    # Retrieve domain application list.
    ############################################################################################################
    def get_custom_applications(self):
        response = None
        uri = 'https://' + self.__smc_ip + '/smc/rest/system/domains/' + str(self.__domain_id) + '/applications'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch get_custom_applications: \n' + json.dumps(response, indent=4, sort_keys=True))
        if response is None:
            print("ERROR: Unable to get_custom_applications.")
            return None
        else:
            return response

    ############################################################################################################
    # Retrieve the custom security event configurations for the specified domain.
    ############################################################################################################
    def get_custom_security_events(self):
        response = None
        if self.__version[0] <= 6 and self.__version[1] <= 10:
            uri = 'https://' + self.__smc_ip + '/smc/rest/system/domains/' + str(self.__domain_id) + '/customEvents'
        else:
            uri = 'https://' + self.__smc_ip + '/smc-configuration/rest/v1/tenants/' + str(
                self.__domain_id) + '/policy/customEvents'

        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch get_custom_security_events: \n' + json.dumps(response, indent=4, sort_keys=True))
        if response is None:
            print("ERROR: Unable to get_custom_security_events.")
            return None
        else:
            return response

    ############################################################################################################
    # Retrieve all flow sensors for the specified domain.
    ############################################################################################################
    def get_flow_sensors(self, surpress_std_out=None):
        response = None
        if surpress_std_out is None:
            surpress_std_out = False
        uri = 'https://' + self.__smc_ip + '/smc/rest/system/domains/' + str(self.__domain_id) + '/flowSensors'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch get_flow_sensors: \n' + json.dumps(response, indent=4, sort_keys=True))
        if response is None or "exception" in response:
            if not surpress_std_out:
                print("ERROR: Unable to get_flow_sensors.")
            return None
        else:
            return response

    ############################################################################################################
    # Retrieve hosts groups that contain given ip address.
    ############################################################################################################
    def get_host_groups_by_ip(self, ip_address):
        response = None
        uri = 'https://' + self.__smc_ip + '/smc/rest/system/domains/' + str(
            self.__domain_id) + '/hGroups/getHostGroupsByIpAddress?ipAddress=' + ip_address
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch get_host_groups_by_ip: \n' + json.dumps(response, indent=4, sort_keys=True))
        if response is None:
            print("ERROR: Unable to get_host_groups_by_ip.")
            return None
        else:
            return response

    ############################################################################################################
    # Retrieve the number of alarms and their types by IP
    ############################################################################################################
    def get_daily_alarm_types(self, ip_address=None, number_of_days_back=None):
        response = None
        if number_of_days_back is None or int(number_of_days_back) <= 0:
            number_of_days_back = 1
        uri = 'https://' + self.__smc_ip + '/smc/rest/domains/' + str(
            self.__domain_id) + '/dashboard/alarms/bytype?days=' + str(number_of_days_back)

        # Splunk accepts '*' as an IP wildcard, Stealthwatch API accepts a
        # blank string. Therefore wildcard *, or if no IP is added - don't add IP
        # Address search and get the default which is all IPs.
        if ip_address is not None and not ip_address == "*":
            uri += '&ipAddress=' + ip_address
        response = self.__execute_query(uri, None)

        if self.DEBUG:
            print('Stealthwatch get_daily_alarm_types: \n' + json.dumps(response, indent=4, sort_keys=True))
        if response is None:
            print("ERROR: Unable to get_daily_alarm_types.")
            return None
        else:
            return response

    ############################################################################################################
    # Retrieve the Host Group severity trend.
    ############################################################################################################
    def get_host_group_severity_trend(self, host_group_id, category, utc_offset=None):
        response = None
        if utc_offset is None:
            utc_offset = 0
        uri = 'https://' + self.__smc_ip + '/smc/rest/system/domains/' + str(
            self.__domain_id) + '/hostGroups/' + str(host_group_id) + '?category=' + category + '&utcOffset=' + str(
            utc_offset)
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch get_host_group_severity_trend: \n' + json.dumps(response, indent=4, sort_keys=True))
        if response is None:
            print("ERROR: Unable to get_host_group_severity_trend.")
            return None
        else:
            return response

    ############################################################################################################
    # Get the disk space allocation map.
    ############################################################################################################
    def get_disk_allocation(self):
        response = None
        uri = 'https://' + self.__smc_ip + '/smc/rest/system/info/diskAllocation'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch get_disk_allocation: \n' + json.dumps(response, indent=4, sort_keys=True))
        if response is None:
            print("ERROR: Unable to get_disk_allocation.")
            return None
        else:
            return response

    ############################################################################################################
    # Get the licensing info.
    ############################################################################################################
    def get_licensing_info(self):
        response = None
        uri = 'https://' + self.__smc_ip + '/smc/rest/system/licensing/info'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch get_licensing_info: \n' + json.dumps(response, indent=4, sort_keys=True))
        if response is None:
            print("ERROR: Unable to get_licensing_info.")
            return None
        else:
            return response

    ############################################################################################################
    # Retrieve all udp directors.
    ############################################################################################################
    def get_udp_directors(self, surpress_std_out=None):
        response = None
        if surpress_std_out is None:
            surpress_std_out = False
        uri = 'https://' + self.__smc_ip + '/smc/rest/system/udpDirectors'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch get_udp_directors: \n' + json.dumps(response, indent=4, sort_keys=True))
        if response is None:
            if not surpress_std_out:
                print("ERROR: Unable to get_udp_directors.")
            return None
        else:
            return response

    ############################################################################################################
    # Get the protocols
    ############################################################################################################
    def get_protocol_list(self, surpress_std_out=None):
        if self.__version[0] <= 6 and self.__version[1] < 10:
            if surpress_std_out is not None and surpress_std_out is True:
                return None
            self.__api_session.close()
            raise Exception("Error: This function is not supported by this version of Stealthwatch.")
        response = None
        if surpress_std_out is None:
            surpress_std_out = False
        uri = 'https://' + self.__smc_ip + '/smc/rest/list-of-values/protocols'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch get_protocol_list: \n' + json.dumps(response, indent=4, sort_keys=True))
        if response is None or "protocols" not in response:
            if not surpress_std_out:
                print("ERROR: Unable to get_protocol_list.")
            return None
        else:
            return response["protocols"]

    ############################################################################################################
    # Validate IP address. This is an empty post that does not change the state of the server. Returns and empty 200 if the address is valid.
    ############################################################################################################
    def validate_ip_address(self, ip_address):
        response = None
        uri = 'https://' + self.__smc_ip + '/smc/rest/validation/ipAddress?ipAddress=' + ip_address
        response = self.__execute_query(uri, None, return_response_code=True)

        if self.DEBUG:
            print('Stealthwatch validate_ip_address: response code =\n' + str(response))
        if response is None:
            print("ERROR: Unable to validate_ip_address.")
            return None
        else:
            if response == 200:
                return True
            else:
                return False

    ############################################################################################################
    # Validate IP address range. This is an empty post that does not change the state of the server. Returns an empty 200 response if the range is valid.
    ############################################################################################################
    def validate_ip_range(self, ip_address_range):
        response = None
        uri = 'https://' + self.__smc_ip + '/smc/rest/validation/ipAddressRange?ipAddressRange=' + ip_address_range
        response = self.__execute_query(uri, None, return_response_code=True)
        if self.DEBUG:
            print('Stealthwatch validate_ip_range: response code =\n' + str(response))
        if response is None:
            print("ERROR: Unable to validate_ip_range.")
            return None
        else:
            if response == 200:
                return True
            else:
                return False

    ############################################################################################################
    # Validate IP addresses. Returns and empty 200 if the addresses are valid. Otherwise returns invalid ip addresses.
    ############################################################################################################
    def validate_ip_address_list(self, ip_address_list):
        response = None
        query_string = ""
        for ip in ip_address_list:
            query_string += "&ipAddressList=" + str(ip)
        if query_string.startswith("&"):
            query_string = "?" + query_string[1:]
        uri = 'https://' + self.__smc_ip + '/smc/rest/validation/ipAddresses' + query_string
        response = self.__execute_query(uri, None, return_response_code=True)
        if self.DEBUG:
            print('Stealthwatch validate_ip_address_list: response code =\n' + str(response))
        if response is None:
            print("ERROR: Unable to validate_ip_address_list.")
            return None
        else:
            if response == 200:
                return True
            else:
                return False

    ############################################################################################################
    # Retrieve information about the appliance
    ############################################################################################################
    def get_appliance_homepage_info(self, appliance_ip=None, surpress_std_out=None):
        response = None
        if appliance_ip is None:
            appliance_ip = self.__smc_ip
        if appliance_ip == self.__smc_ip:
            uri = 'https://' + appliance_ip + '/smc/admin-json/common/getHomePage'
            response = self.__execute_query(uri, None)
        else:
            response = None
            appliance_api = stealthwatch_api()
            login_response = appliance_api.login(appliance_ip, self.__smc_username, self.__smc_password,
                                                 requests_disable_warnings=self.__requests_disable_warnings,
                                                 skip_checks=True, device_type="swa")
            if login_response is None:
                login_response = appliance_api.login(appliance_ip, self.__smc_username, self.__smc_password,
                                                     requests_disable_warnings=self.__requests_disable_warnings,
                                                     skip_checks=True, device_type="fs")
                if login_response is None:
                    login_response = appliance_api.login(appliance_ip, self.__smc_username, self.__smc_password,
                                                         requests_disable_warnings=self.__requests_disable_warnings,
                                                         skip_checks=True, device_type="fr")
            if login_response is not None:
                uri = 'https://' + appliance_ip + '/smc/admin-json/common/getHomePage'
                response = appliance_api.__execute_query(uri, None)
                if response is None:
                    response = None
                    uri = 'https://' + appliance_ip + '/swa/admin-json/common/getHomePage'
                    response = appliance_api.__execute_query(uri, None)
                    if response is None:
                        response = None
                        uri = 'https://' + appliance_ip + '/fs/admin-json/common/getHomePage'
                        response = appliance_api.__execute_query(uri, None)
                        if response is None:
                            response = None
                            uri = 'https://' + appliance_ip + '/fr/admin-json/common/getHomePage'
                            response = appliance_api.__execute_query(uri, None)
                appliance_api.logout()
        if self.DEBUG:
            print('Stealthwatch API get_appliance_homepage_info: \n' + json.dumps(response, indent=4,
                                                                                  sort_keys=True))
        if response is None:
            if surpress_std_out is None or surpress_std_out is False:
                print("ERROR: Unable to get_appliance_homepage_info.")
            return None
        else:
            return response

    ############################################################################################################
    # Retrieve status of the SWA Engine
    ############################################################################################################
    def get_fc_engine_status(self, appliance_ip=None, surpress_std_out=None):
        response = None
        if appliance_ip is None:
            appliance_ip = self.__smc_ip
        if appliance_ip == self.__smc_ip:
            uri = 'https://' + appliance_ip + '/swa/admin-json/swa/getEngineStatus'
            response = self.__execute_query(uri, None)
        else:
            response = None
            appliance_api = stealthwatch_api()
            login_response = appliance_api.login(appliance_ip, self.__smc_username, self.__smc_password,
                                                 requests_disable_warnings=self.__requests_disable_warnings,
                                                 skip_checks=True, device_type="swa")
            if login_response is not None:
                uri = 'https://' + appliance_ip + '/swa/admin-json/swa/getEngineStatus'
                response = appliance_api.__execute_query(uri, None)
                appliance_api.logout()
        if self.DEBUG:
            print('Stealthwatch API get_fc_engine_status: \n' + json.dumps(response, indent=4,
                                                                           sort_keys=True))
        if response is None:
            if surpress_std_out is None or surpress_std_out is False:
                print("ERROR: Unable to get_fc_engine_status.")
            return None
        else:
            return response

    ############################################################################################################
    # Retrieve options of the SWA
    ############################################################################################################
    def get_fc_options(self, appliance_ip=None, surpress_std_out=None):
        response = None
        if appliance_ip is None:
            appliance_ip = self.__smc_ip
        if appliance_ip == self.__smc_ip:
            uri = 'https://' + appliance_ip + '/swa/admin-json/swa/getSWAOptions'
            response = self.__execute_query(uri, None)
        else:
            response = None
            appliance_api = stealthwatch_api()
            login_response = appliance_api.login(appliance_ip, self.__smc_username, self.__smc_password,
                                                 requests_disable_warnings=self.__requests_disable_warnings,
                                                 skip_checks=True, device_type="swa")
            if login_response is not None:
                uri = 'https://' + appliance_ip + '/swa/admin-json/swa/getSWAOptions'
                response = appliance_api.__execute_query(uri, None)
                appliance_api.logout()
        if self.DEBUG:
            print('Stealthwatch API get_fc_options: \n' + json.dumps(response, indent=4,
                                                                     sort_keys=True))
        if response is None:
            if surpress_std_out is None or surpress_std_out is False:
                print("ERROR: Unable to get_fc_options.")
            return None
        else:
            return response

    ############################################################################################################
    # Retrieve custom events from an FC
    ############################################################################################################
    def get_fc_custom_events(self, appliance_ip=None, surpress_std_out=None):
        response = None
        if appliance_ip is None:
            appliance_ip = self.__smc_ip
        if appliance_ip == self.__smc_ip:
            uri = 'https://' + appliance_ip + '/swa/files/sw/today/config/custom_events.xml'
            response = self.__get_file_as_string(uri)
        else:
            response = None
            appliance_api = stealthwatch_api()
            login_response = appliance_api.login(appliance_ip, self.__smc_username, self.__smc_password,
                                                 requests_disable_warnings=self.__requests_disable_warnings,
                                                 skip_checks=True, device_type="swa")
            if login_response is not None:
                uri = 'https://' + appliance_ip + '/swa/files/sw/today/config/custom_events.xml'
                response = appliance_api.__get_file_as_string(uri, None)
                appliance_api.logout()
        if self.DEBUG:
            print('Stealthwatch API get_fc_custom_events: \n' + json.dumps(response, indent=4,
                                                                           sort_keys=True))
        if response is None:
            if surpress_std_out is None or surpress_std_out is False:
                print("ERROR: Unable to get_fc_custom_events.")
            return None
        else:
            soap_response = xmltodict.parse(response, xml_attribs=True)
            json_response = json.loads(json.dumps(soap_response, indent=4).replace('"@', '"'))
            if "rules" in json_response:
                return json_response["rules"]
            elif "rules-list" in json_response:
                return json_response["rules-list"]
            else:
                return None

    ############################################################################################################
    # Retrieve the full exporter data from the FC for today
    ############################################################################################################
    def get_fc_exporter_data(self, appliance_ip=None, surpress_std_out=None):
        response = None
        if appliance_ip is None:
            appliance_ip = self.__smc_ip
        if appliance_ip == self.__smc_ip:
            uri = 'https://' + appliance_ip + '/swa/files/sw/today/config/exporters.xml'
            response = self.__get_file_as_string(uri)
        else:
            response = None
            appliance_api = stealthwatch_api()
            login_response = appliance_api.login(appliance_ip, self.__smc_username, self.__smc_password,
                                                 requests_disable_warnings=self.__requests_disable_warnings,
                                                 skip_checks=True, device_type="swa")
            if login_response is not None:
                uri = 'https://' + appliance_ip + '/swa/files/sw/today/config/exporters.xml'
                response = appliance_api.__get_file_as_string(uri, None)
                appliance_api.logout()
        if self.DEBUG:
            print('Stealthwatch API get_fc_exporter_data: \n' + json.dumps(response, indent=4,
                                                                           sort_keys=True))
        if response is None:
            if surpress_std_out is None or surpress_std_out is False:
                print("ERROR: Unable to get_fc_exporter_data.")
            return None
        else:
            soap_response = xmltodict.parse(response, xml_attribs=True)
            json_response = json.loads(json.dumps(soap_response, indent=4).replace('"@', '"'))
            if "exporter-list" in json_response:
                return json_response["exporter-list"]
            else:
                return None

    ############################################################################################################
    # Retrieve information about the appliance
    ############################################################################################################
    def get_failover_smc(self):
        response = None
        uri = 'https://' + self.__smc_ip + '/smc/files/smc/config/smc_failover.xml'
        response = self.__get_file_as_string(uri)
        if self.DEBUG:
            print(
                'Stealthwatch API get_failover_smc: \n' + json.dumps(response, indent=4, sort_keys=True))
        if response is None:
            return None
        else:
            return str(response).split("ip-address=\"")[1].split("\"")[0]

    ############################################################################################################
    # Retrieve the security events metadata
    ############################################################################################################
    def get_security_events_metadata(self):
        response = None
        uri = 'https://' + self.__smc_ip + '/smc/files/smc/config/security_event_metadata.xml'
        response = self.__get_file_as_string(uri)
        if self.DEBUG:
            print('Stealthwatch API call response: \n' + response)
        if response is None:
            print("ERROR: Unable to get security events metadata.")
            return None
        else:
            soap_response = xmltodict.parse(response, xml_attribs=True)
            json_response = json.loads(json.dumps(soap_response, indent=4).replace('"@', '"'))
            if "security-event-metadata-list" in json_response and "security-event-metadata" in json_response[
                "security-event-metadata-list"]:
                return json_response["security-event-metadata-list"]["security-event-metadata"]
            else:
                return None

    ############################################################################################################
    # Retrieve the host policy data
    ############################################################################################################
    def get_host_policy_data(self):
        response = None
        uri = 'https://' + self.__smc_ip + '/smc/files/smc/config/domain_' + str(self.__domain_id) + '/host_policy.xml'
        response = self.__get_file_as_string(uri)
        if self.DEBUG:
            print('Stealthwatch API call response: \n' + response)
        if response is None:
            print("ERROR: Unable to get host policy data.")
            return None
        else:
            soap_response = xmltodict.parse(response, xml_attribs=True)
            json_response = json.loads(json.dumps(soap_response, indent=4).replace('"@', '"'))
            if "policy-list" in json_response:
                return json_response["policy-list"]
            else:
                return None

    ############################################################################################################
    # Retrieve the system application definitions
    ############################################################################################################
    def get_system_application_definitions(self):
        response = None
        uri = 'https://' + self.__smc_ip + '/smc/files/smc/config/system_application_definitions.xml'
        response = self.__get_file_as_string(uri)
        if self.DEBUG:
            print('Stealthwatch API call response: \n' + response)
        if response is None:
            print("ERROR: Unable to get system application definitions.")
            return None
        else:
            soap_response = xmltodict.parse(response, xml_attribs=True)
            json_response = json.loads(json.dumps(soap_response, indent=4).replace('"@', '"'))
            if "application-list" in json_response:
                return json_response["application-list"]
            else:
                return None

    ############################################################################################################
    # Retrieve the system application mappings
    ############################################################################################################
    def get_system_application_mappings(self):
        response = None
        uri = 'https://' + self.__smc_ip + '/smc/files/smc/config/system_application_mappings.xml'
        response = self.__get_file_as_string(uri)
        if self.DEBUG:
            print('Stealthwatch API call response: \n' + response)
        if response is None:
            print("ERROR: Unable to get system application mappings.")
            return None
        else:
            soap_response = xmltodict.parse(response, xml_attribs=True)
            json_response = json.loads(json.dumps(soap_response, indent=4).replace('"@', '"'))
            if "classification-list" in json_response:
                return json_response["classification-list"]
            else:
                return None

    ############################################################################################################
    # Retrieve the system audit log
    ############################################################################################################
    def get_audit_log_events(self, start_datetime, end_datetime, internal_users_only=None, user_location=None,
                             audit_event_category_id=None, surpress_std_out=None):
        response = None
        uri = 'https://' + self.__smc_ip + '/smc/admin-json/common/getAuditLogByCriteria'
        request_data = {}
        if start_datetime is not None:
            start_timestamp = int(start_datetime.strftime('%s') + "000")
        request_data["newStartDate"] = start_timestamp
        if end_datetime is not None:
            end_timestamp = int(end_datetime.strftime('%s') + "000")
        request_data["newEndDate"] = end_timestamp
        user_type = ""
        if internal_users_only is not None and str(internal_users_only).lower().strip() == "true":
            user_type = "Internal"
        request_data["user"] = user_type
        if user_location is None:
            user_location = ""
        request_data["newIp"] = user_location
        if audit_event_category_id is None:
            audit_event_category_id = -1
        request_data["category"] = str(audit_event_category_id)
        response = self.__execute_query(uri, json.dumps(request_data), rest_method="post")
        if self.DEBUG:
            print('Stealthwatch API get_audit_log_events: \n' + json.dumps(response, indent=4,
                                                                           sort_keys=True))
        if response is None:
            if surpress_std_out is None or surpress_std_out is False:
                print("ERROR: Unable to get_audit_log_events.")
            return None
        else:
            return response

    ############################################################################################################
    # Retrieve the system application mappings
    ############################################################################################################
    def get_intergroup_locking_data(self):
        response = None
        uri = 'https://' + self.__smc_ip + '/smc/files/smc/config/domain_' + str(
            self.__domain_id) + '/intergroup_locking.xml'
        response = self.__get_file_as_string(uri)
        if self.DEBUG:
            print('Stealthwatch API call response: \n' + response)
        if response is None:
            print("ERROR: Unable to get intergroup locking data.")
            return None
        else:
            soap_response = xmltodict.parse(response, xml_attribs=True)
            json_response = json.loads(json.dumps(soap_response, indent=4).replace('"@', '"'))
            if "intergroup-locking-list" in json_response:
                return json_response["intergroup-locking-list"]
            else:
                return None

    ############################################################################################################
    # Retrieve information about the appliance
    ############################################################################################################
    def get_smc_logins(self):
        response = None
        results = []
        uri = 'https://' + self.__smc_ip + '/smc/files/logs/audit.log'
        response = self.__get_file_as_string(uri)
        if self.DEBUG:
            print(
                'Stealthwatch API get_number_of_smc_logins: \n' + json.dumps(response, indent=4,
                                                                             sort_keys=True))
        if response is None:
            print("ERROR: Unable to get_number_of_smc_logins.")
            return None
        else:
            for line in response.splitlines():
                if ",Login successful" in line or ",Login on Web UI successful" in line:
                    loginMessage = line.replace("\n", "").replace("\r", "").replace("\\n", "").replace("\\r",
                                                                                                       "").strip().split(
                        ",")
                    login = {}
                    login["Timestamp"] = loginMessage[2].replace("\n", "").replace("\r", "").replace("\\n", "").replace(
                        "\\r", "").strip()
                    login["Username"] = loginMessage[3].replace("\n", "").replace("\r", "").replace("\\n", "").replace(
                        "\\r", "").strip()
                    results.append(login)
            return results

    ############################################################################################################
    # Retrieve the service definitions
    ############################################################################################################
    def get_service_definitions(self):
        results = []
        uri = 'https://' + self.__smc_ip + '/smc/files/smc/config/domain_' + str(
            self.__domain_id) + '/service_definitions.xml'
        response = self.__get_file_as_string(uri)
        if self.DEBUG:
            print('Stealthwatch API get_service_definitions: \n' + json.dumps(response, indent=4, sort_keys=True))
        if response is None:
            print("ERROR: Unable to get_service_definitions.")
            return None
        else:
            soap_response = xmltodict.parse(response, xml_attribs=True)
            json_response = json.loads(json.dumps(soap_response, indent=4).replace('"@', '"'))
            return json_response

    ############################################################################################################
    # Retrieve flow trend for the system
    ############################################################################################################
    def get_flow_trend(self, number_days_back=None):
        response = None
        if number_days_back is None:
            number_days_back = 1
        uri = 'https://' + self.__smc_ip + '/smc/rest/domains/' + str(
            self.__domain_id) + '/dashboard/flowTrend?days=' + str(number_days_back)
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch API get_appliance_homepage_info: \n' + json.dumps(response, indent=4,
                                                                                  sort_keys=True))
        if response is None:
            print("ERROR: Unable to get_appliance_homepage_info.")
            return None
        else:
            return response

    ############################################################################################################
    ############################################################################################################
    ############################################################################################################
    # NEXTGEN REST API
    ############################################################################################################
    ############################################################################################################
    ############################################################################################################

    ############################################################################################################
    # Get the tenants/domains using an API query
    ############################################################################################################
    def get_tenants(self):
        if self.version_before(6, 9):
            return self.get_domains()

        response = None
        try:
            url = "https://" + self.__smc_ip + "/sw-reporting/v1/tenants"
            response = self.__execute_query(url, None)
        except Exception as e:
            print('Could not get SMC tenants: {}'.format(e))
            return None

        if self.DEBUG:
            print(
                "Stealthwatch API get_tenants() call response: \n"
                + json.dumps(response, indent=2, sort_keys=True)
            )

        if not response:
            print('Could not get SMC tenants')
            return None

        if self.DEBUG:
            print("SMC tenants:\n{}".format(json.dumps(response, indent=2, sort_keys=True)))

        return response

    ############################################################################################################
    # Retrieves all External Geo Tags for the specific Tenant.
    ############################################################################################################
    def get_external_geo_tags(self):
        if self.__version[0] <= 6 and self.__version[1] < 10:
            self.__api_session.close()
            raise Exception("Error: This function is not supported by this version of Stealthwatch.")
        response = None
        uri = 'https://' + self.__smc_ip + '/sw-reporting/v1/tenants/' + str(
            self.__domain_id) + '/externalGeos/tags'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print(
                'Stealthwatch get external geo tags API call response: \n' + json.dumps(response, indent=4,
                                                                                        sort_keys=True))
        if response is None:
            print("ERROR: Unable to get all external geo tags.")
            return None
        else:
            return response

    ############################################################################################################
    # Retrieves all External Geo Tags for the specific Tenant (tenantId) organized in a hierarchy.
    ############################################################################################################
    def get_external_geo_tree(self):
        if self.__version[0] <= 6 and self.__version[1] < 10:
            self.__api_session.close()
            raise Exception("Error: This function is not supported by this version of Stealthwatch.")
        response = None
        uri = 'https://' + self.__smc_ip + '/sw-reporting/v1/tenants/' + str(
            self.__domain_id) + '/externalGeos/tags/tree'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print(
                'Stealthwatch get the tree for an External Geo API call response: \n' + json.dumps(response,
                                                                                                   indent=4,
                                                                                                   sort_keys=True))
        if response is None:
            print("ERROR: Unable to get tree for an External Geo tree")
            return None
        else:
            return response

    ############################################################################################################
    # Retrieves all External Threats Tags for the specific Tenant (tenantId) organized in a hierarchy.
    ############################################################################################################
    def get_external_threats_tree(self):
        if self.__version[0] <= 6 and self.__version[1] < 10:
            self.__api_session.close()
            raise Exception("Error: This function is not supported by this version of Stealthwatch.")
        response = None
        uri = 'https://' + self.__smc_ip + '/sw-reporting/v1/tenants/' + str(
            self.__domain_id) + '/externalThreats/tags/tree'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print(
                'Stealthwatch get the tree for an External Threats API call response: \n' + json.dumps(response,
                                                                                                       indent=4,
                                                                                                       sort_keys=True))
        if response is None:
            print("ERROR: Unable to get tree for an External Threats tree")
            return None
        else:
            return response

    ############################################################################################################
    # Retrieves top alarming hosts for External Geo Tags of a Tenant (tenantId).
    ############################################################################################################
    def get_external_geo_top_alarming_hosts(self):
        if self.__version[0] <= 6 and self.__version[1] < 10:
            self.__api_session.close()
            raise Exception("Error: This function is not supported by this version of Stealthwatch.")
        response = None
        uri = 'https://' + self.__smc_ip + '/sw-reporting/v1/tenants/' + str(
            self.__domain_id) + '/externalGeos/alarms/topHosts'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print(
                'Stealthwatch get the top alarming hosts for External Geo Tags API call response: \n' + json.dumps(
                    response,
                    indent=4,
                    sort_keys=True))
        if response is None:
            print("ERROR: Unable to get top alarming hosts for External Geo Tags")
            return None
        else:
            return response

    ############################################################################################################/tenants/
    # Retrieves the top alarming hosts for an External Geo Tag (tagId) of a Tenant (tenantId).
    ############################################################################################################
    def get_external_geo_top_alarming_hosts_by_tag(self, tag_id):
        if self.__version[0] <= 6 and self.__version[1] < 10:
            self.__api_session.close()
            raise Exception("Error: This function is not supported by this version of Stealthwatch.")
        response = None
        uri = 'https://' + self.__smc_ip + '/sw-reporting/v1/tenants/' + str(
            self.__domain_id) + '/externalGeos/tags/' + str(tag_id) + '/alarms/topHosts'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print(
                'Stealthwatch retrieve top alarming hosts for an External Geo Tag (tagId) of a Tenant (tenantId). API call response: \n' + json.dumps(
                    response, indent=4, sort_keys=True))
        if response is None:
            print(
                "ERROR: Unable to Retrieves top alarming hosts for an External Geo Tag (tagId): " + str(tag_id))
            return None
        else:
            return response

    ############################################################################################################
    # Retrieves all External Host Tags for the specific Tenant (tenantId).
    ############################################################################################################
    def get_external_hosts_tags(self):
        if self.__version[0] <= 6 and self.__version[1] < 10:
            self.__api_session.close()
            raise Exception("Error: This function is not supported by this version of Stealthwatch.")
        response = None
        uri = 'https://' + self.__smc_ip + '/sw-reporting/v1/tenants/' + str(
            self.__domain_id) + '/externalHosts/tags'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch get external hosts tags API call response: \n' + json.dumps(response, indent=4,
                                                                                            sort_keys=True))
        if response is None:
            print("ERROR: Unable to get all external host tags.")
            return None
        else:
            return response

    ############################################################################################################
    # Retrieves all External Host Tags for the specific Tenant (tenantId) organized in a hierarchy.
    ############################################################################################################
    def get_external_hosts_tree(self):
        if self.__version[0] <= 6 and self.__version[1] < 10:
            self.__api_session.close()
            raise Exception("Error: This function is not supported by this version of Stealthwatch.")
        response = None
        uri = 'https://' + self.__smc_ip + '/sw-reporting/v1/tenants/' + str(
            self.__domain_id) + '/externalHosts/tags/tree'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print(
                'Stealthwatch get the tree for an External Host API call response: \n' + json.dumps(response,
                                                                                                    indent=4,
                                                                                                    sort_keys=True))
        if response is None:
            print("ERROR: Unable to get tree for an External Host tree.")
            return None
        else:
            return response

    ############################################################################################################
    # Retrieves the top alarming hosts for an External Host Tag of a Tenant (tenantId).
    ############################################################################################################
    def get_external_hosts_top_alarming_hosts(self):
        if self.__version[0] <= 6 and self.__version[1] < 10:
            self.__api_session.close()
            raise Exception("Error: This function is not supported by this version of Stealthwatch.")
        response = None
        uri = 'https://' + self.__smc_ip + '/sw-reporting/v1/tenants/' + str(
            self.__domain_id) + '/externalHosts/alarms/topHosts'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch get the top alarming hosts API call response: \n' + json.dumps(response, indent=4,
                                                                                               sort_keys=True))
        if response is None:
            print("ERROR: Unable to get the top alarming hosts.")
            return None
        else:
            return response

    ############################################################################################################
    # Retrieves top alarming hosts for an External Host Tag (tagId) of a Tenant (tenantId).
    ############################################################################################################
    def get_external_hosts_top_alarming_hosts_by_tag(self, tag_id):
        if self.__version[0] <= 6 and self.__version[1] < 10:
            self.__api_session.close()
            raise Exception("Error: This function is not supported by this version of Stealthwatch.")
        response = None
        uri = 'https://' + self.__smc_ip + '/sw-reporting/v1/tenants/' + str(
            self.__domain_id) + '/externalHosts/tags/' + str(tag_id) + '/alarms/topHosts'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print(
                'Stealthwatch retrieve top alarming hosts for an External Host Tag (tagId) of a Tenant (tenantId). API call response: \n' + json.dumps(
                    response, indent=4, sort_keys=True))
        if response is None:
            print(
                "ERROR: Unable to Retrieves top alarming hosts for an External Host Tag (tagId): " + str(tag_id))
            return None
        else:
            return response

    ############################################################################################################
    # Retrieves all Internal Host Tags for the specific Tenant (tenantId).
    ############################################################################################################
    def get_internal_hosts_tags(self):
        if self.__version[0] <= 6 and self.__version[1] < 10:
            self.__api_session.close()
            raise Exception("Error: This function is not supported by this version of Stealthwatch.")
        response = None
        uri = 'https://' + self.__smc_ip + '/sw-reporting/v1/tenants/' + str(
            self.__domain_id) + '/internalHosts/tags'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch get Internal hosts tags API call response: \n' + json.dumps(response, indent=4,
                                                                                            sort_keys=True))
        if response is None:
            print("ERROR: Unable to get all Internal host tags.")
            return None
        else:
            return response
            #
            #

    ############################################################################################################
    # Retrieves all Internal Host Tags for the specific Tenant (tenantId) organized in a hierarchy.
    ############################################################################################################
    def get_internal_hosts_tree(self):
        if self.__version[0] <= 6 and self.__version[1] < 10:
            self.__api_session.close()
            raise Exception("Error: This function is not supported by this version of Stealthwatch.")
        response = None
        uri = 'https://' + self.__smc_ip + '/sw-reporting/v1/tenants/' + str(
            self.__domain_id) + '/internalHosts/tags/tree'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print(
                'Stealthwatch get the tree for an Internal Host API call response: \n' + json.dumps(response,
                                                                                                    indent=4,
                                                                                                    sort_keys=True))
        if response is None:
            print("ERROR: Unable to get tree for Internal Hosts.")
            return None
        else:
            return response

    ############################################################################################################
    # Retrieves all Custom Host Tags for the specific Tenant (tenantId) organized in a hierarchy.
    ############################################################################################################
    def get_custom_hosts_tree(self):
        if self.__version[0] <= 6 and self.__version[1] < 10:
            self.__api_session.close()
            raise Exception("Error: This function is not supported by this version of Stealthwatch.")
        response = None
        uri = 'https://' + self.__smc_ip + '/sw-reporting/v1/tenants/' + str(
            self.__domain_id) + '/customHosts/tags/tree'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print(
                'Stealthwatch get the tree for an Custom Host API call response: \n' + json.dumps(response,
                                                                                                  indent=4,
                                                                                                  sort_keys=True))
        if response is None:
            print("ERROR: Unable to get tree for Custom Hosts.")
            return None
        else:
            return response

    ############################################################################################################
    # Retrieves the top alarming hosts for an Internal Host Tag of a Tenant (tenantId).
    ############################################################################################################
    def get_internal_hosts_top_alarming_hosts(self):
        if self.__version[0] <= 6 and self.__version[1] < 10:
            self.__api_session.close()
            raise Exception("Error: This function is not supported by this version of Stealthwatch.")
        response = None
        uri = 'https://' + self.__smc_ip + '/sw-reporting/v1/tenants/' + str(
            self.__domain_id) + '/internalHosts/alarms/topHosts'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch get the top alarming hosts API call response: \n' + json.dumps(response, indent=4,
                                                                                               sort_keys=True))
        if response is None:
            print("ERROR: Unable to get the top alarming hosts.")
            return None
        else:
            return response

    ############################################################################################################
    # Retrieves top alarming hosts for an Internal Host Tag (tagId) of a Tenant (tenantId).
    ############################################################################################################
    def get_internal_hosts_top_alarming_hosts_by_tag(self, tag_id):
        if self.__version[0] <= 6 and self.__version[1] < 10:
            self.__api_session.close()
            raise Exception("Error: This function is not supported by this version of Stealthwatch.")
        response = None
        uri = 'https://' + self.__smc_ip + '/sw-reporting/v1/tenants/' + str(
            self.__domain_id) + '/internalHosts/tags/' + str(tag_id) + '/alarms/topHosts'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print(
                'Stealthwatch retrieve top alarming hosts for an Internal Host Tag (tagId) of a Tenant (tenantId). API call response: \n' + json.dumps(
                    response, indent=4, sort_keys=True))
        if response is None:
            print(
                "ERROR: Unable to Retrieves top alarming hosts for an Internal Host Tag (tagId): " + str(tag_id))
            return None
        else:
            return response

    ############################################################################################################
    # Initiates a flow report API query
    ############################################################################################################
    def __initiate_flow_report_query(self, report_type, request_data):
        query_id = None
        uri = 'https://' + self.__smc_ip + '/sw-reporting/v1/tenants/' + str(
            self.__domain_id) + '/flow-reports/' + report_type + '/queries'
        query_id_response = self.__execute_query(uri, json.dumps(request_data), rest_method="post")
        if self.DEBUG:
            print('Stealthwatch API initiate_flow_report_query call response: \n' + json.dumps(query_id_response,
                                                                                               indent=4,
                                                                                               sort_keys=True))
        if query_id_response is None:
            print("ERROR: Unable to initiate_flow_report_query.")
            return None
        if 'queryId' in query_id_response:
            query_id = query_id_response['queryId']
        if query_id is None:
            print("ERROR: Unable to fetch query ID.")
            return None
        else:
            return query_id

    ############################################################################################################
    # Initiates an interface flow report API query
    ############################################################################################################
    def __initiate_interface_flow_report_search(self, report_type, request_data):
        search_id = None
        uri = 'https://' + self.__smc_ip + '/smc/rest/domains/' + str(
            self.__domain_id) + '/searches'
        search_id_response = self.__execute_query(uri, json.dumps(request_data), rest_method="post")
        if self.DEBUG:
            print('Stealthwatch API initiate_flow_report_search call response: \n' + json.dumps(search_id_response,
                                                                                                indent=4,
                                                                                                sort_keys=True))
        if search_id_response is None:
            print("ERROR: Unable to initiate_flow_report_search.")
            return None
        if 'id' in search_id_response:
            search_id = search_id_response['id']
        if search_id is None:
            print("ERROR: Unable to fetch search ID.")
            return None
        else:
            return search_id

    ############################################################################################################
    # Initiates an interface flow report API query
    ############################################################################################################
    def __initiate_interface_flow_report_job(self, search_id):
        job_id = None
        uri = 'https://' + self.__smc_ip + '/smc/rest/domains/' + str(
            self.__domain_id) + '/searches/' + search_id + "/jobs"
        job_id_response = self.__execute_query(uri, json.dumps({"secondsToWait": 1, "disableChunking": True}),
                                               rest_method="post")
        if self.DEBUG:
            print('Stealthwatch API initiate_flow_report_job call response: \n' + json.dumps(job_id_response,
                                                                                             indent=4,
                                                                                             sort_keys=True))
        if job_id_response is None:
            print("ERROR: Unable to initiate_flow_report_job.")
            return None
        if 'id' in job_id_response:
            job_id = job_id_response['id']
        if job_id is None:
            print("ERROR: Unable to fetch job ID.")
            return None
        else:
            return job_id

    ############################################################################################################
    # Checks the status of a flow report API query
    ############################################################################################################
    def __check_flow_report_query_status(self, report_type, query_id):
        query_status = None
        uri = 'https://' + self.__smc_ip + '/sw-reporting/v1/tenants/' + str(
            self.__domain_id) + '/flow-reports/' + report_type + '/queries/' + str(query_id)
        query_status_response = self.__execute_query(uri, None)
        if self.DEBUG:
            print(
                'Stealthwatch API call response: \n' + json.dumps(query_status_response, indent=4, sort_keys=True))
        if query_status_response is None:
            print("ERROR: Unable to initiate query.")
            return None
        if 'status' in query_status_response:
            query_status = query_status_response['status']
        if query_status is None:
            print("ERROR: Unable to fetch query status.")
            return None
        else:
            return query_status

    ############################################################################################################
    # Checks the status of a flow report API query
    ############################################################################################################
    def __check_interface_flow_report_query_status(self, search_id, job_id):
        query_status = None
        uri = 'https://' + self.__smc_ip + '/smc/rest/domains/' + str(
            self.__domain_id) + '/searches/' + search_id + '/jobstatus/' + job_id
        query_status_response = self.__execute_query(uri, None)
        if self.DEBUG:
            print(
                'Stealthwatch API call response: \n' + json.dumps(query_status_response, indent=4, sort_keys=True))
        if query_status_response is None:
            print("ERROR: Unable to initiate query.")
            return None
        if 'searchJobStatus' in query_status_response:
            query_status = query_status_response['searchJobStatus']
        if query_status is None:
            print("ERROR: Unable to fetch query status.")
            return None
        else:
            return query_status

    ############################################################################################################
    # Gets the results of a flow report API query
    ############################################################################################################
    def __get_flow_report_query_results(self, report_type, query_id):
        uri = 'https://' + self.__smc_ip + '/sw-reporting/v1/tenants/' + str(
            self.__domain_id) + '/flow-reports/' + report_type + '/results/' + str(query_id)
        results = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch API call response: \n' + json.dumps(results, indent=4, sort_keys=True))
        return results

    ############################################################################################################
    # Gets the results of a flow report API query
    ############################################################################################################
    def __get_interface_flow_report_query_results(self, search_id, job_id):
        uri = 'https://' + self.__smc_ip + '/smc/rest/domains/' + str(
            self.__domain_id) + '/searches/' + search_id + '/jobs/' + job_id + '/results?page=0&resultsPerPage=5000&sort=rank'
        results = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch API call response: \n' + json.dumps(results, indent=4, sort_keys=True))
        if "page" in results and "content" in results["page"]:
            results = {"results": results["page"]["content"]}
        return results

    ############################################################################################################
    # Performs the necessary operations for a flow report API query
    ############################################################################################################
    def __perform_flow_report_query(self, report_type, request_data, status_check_frequency):
        results = None
        if status_check_frequency <= 0:
            status_check_frequency = 1000
        if self.__domain_id is None:
            print("ERROR: Unable to perform flow report API query.")
            return results
        if "searchType" not in request_data:
            query_id = self.__initiate_flow_report_query(report_type, request_data)
            if query_id is None:
                return results
            query_status = self.__check_flow_report_query_status(report_type, query_id)
            while query_status is not None and query_status != "FAILED" and query_status != "COMPLETED":
                time.sleep(status_check_frequency / 1000.0)
                query_status = self.__check_flow_report_query_status(report_type, query_id)
            if query_status is None or query_status != "COMPLETED":
                print("ERROR: Unable to perform flow report API query.")
                return results
            else:
                results = self.__get_flow_report_query_results(report_type, query_id)
                return results
        else:
            search_id = self.__initiate_interface_flow_report_search(report_type, request_data)
            if search_id is None:
                return results
            job_id = self.__initiate_interface_flow_report_job(search_id)
            if job_id is None:
                return results
            query_status = self.__check_interface_flow_report_query_status(search_id, job_id)
            while query_status is not None and query_status != "FAILED" and query_status != "COMPLETED":
                time.sleep(status_check_frequency / 1000.0)
                query_status = self.__check_interface_flow_report_query_status(search_id, job_id)
            if query_status is None or query_status != "COMPLETED":
                print("ERROR: Unable to perform flow report API query.")
                return results
            else:
                results = self.__get_interface_flow_report_query_results(search_id, job_id)
                return results

    ############################################################################################################
    # Get the top ports using a flow report API query
    ############################################################################################################
    def __generate_flow_report_request_data(self, report_type, search_name, start_datetime, end_datetime,
                                            subject_tags_includes,
                                            subject_tags_excludes, subject_addresses_includes,
                                            subject_addresses_excludes, peer_tags_includes, peer_tags_excludes,
                                            peer_addresses_includes, peer_addresses_excludes, subject_orientation,
                                            connection_direction, connection_applications_includes,
                                            connection_applications_excludes, connection_ports_protocols_includes,
                                            connection_ports_protocols_excludes, flow_collectors,
                                            interface_flow_collector_id, interface_exporter_ip, interface_id,
                                            order_by, max_rows, exclude_bps_pps, exclude_others, exclude_counts,
                                            utc_offset):
        request_data = None

        if subject_tags_includes is None:
            subject_tags_includes = []
        if subject_tags_excludes is None:
            subject_tags_excludes = []
        if subject_addresses_includes is None:
            subject_addresses_includes = []
        if subject_addresses_excludes is None:
            subject_addresses_excludes = []
        if peer_tags_includes is None:
            peer_tags_includes = []
        if peer_tags_excludes is None:
            peer_tags_excludes = []
        if peer_addresses_includes is None:
            peer_addresses_includes = []
        if peer_addresses_excludes is None:
            peer_addresses_excludes = []

        if max_rows is None or max_rows <= 0:
            max_rows = 50
        if max_rows > 5000:
            max_rows = 5000
        if subject_orientation is None or subject_orientation.upper() not in self.__orientation_list:
            subject_orientation = "EITHER"
        if flow_collectors is None:
            flow_collectors = []
        if order_by is None or order_by.upper() not in self.__order_by_list:
            order_by = "TOTAL_BYTES"

        standard_options = True
        if exclude_bps_pps is None:
            exclude_bps_pps = True
        if exclude_others is None:
            exclude_others = True
        if exclude_counts is None:
            exclude_counts = False
        if exclude_bps_pps is False or exclude_others is False or exclude_counts is True:
            standard_options = False

        if connection_direction is None or connection_direction.upper() not in self.__connection_direction_list:
            connection_direction = "INBOUND_PLUS_OUTBOUND"
        if connection_applications_includes is None:
            connection_applications_includes = []
        if connection_applications_excludes is None:
            connection_applications_excludes = []
        if connection_ports_protocols_includes is None:
            connection_ports_protocols_includes = []
        if connection_ports_protocols_excludes is None:
            connection_ports_protocols_excludes = []

        if utc_offset is None:
            utc_offset = "+0000"

        if interface_id is not None and (interface_flow_collector_id is None or interface_exporter_ip is None):
            interface_id = None

        use_new_rest_api = True
        if self.__version[0] <= 6 and self.__version[1] < 10:
            use_new_rest_api = False

        if not use_new_rest_api and interface_id is not None:
            self.__api_session.close()
            raise Exception(
                "Error: Filtering Top Reports by Interface is not supported in this version of Stealthwatch.")

        if interface_id is None and use_new_rest_api is True:
            if start_datetime is not None:
                start_timestamp = start_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f')
                while len(start_timestamp.split('.')[1]) > 3:
                    start_timestamp = start_timestamp[:-1]
            if end_datetime is not None:
                end_timestamp = end_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f')
                while len(end_timestamp.split('.')[1]) > 3:
                    end_timestamp = end_timestamp[:-1]
            request_data = {
                "searchName": search_name,
                "startTime": start_timestamp,
                "endTime": end_timestamp,
                "connection": {
                    "applications": {
                        "includes": connection_applications_includes,
                        "excludes": connection_applications_excludes
                    },
                    "direction": "INBOUND_PLUS_OUTBOUND",
                    "portProtocols": {
                        "includes": connection_ports_protocols_includes,
                        "excludes": connection_ports_protocols_excludes
                    }
                },
                "subject": {
                    "tags": {
                        "includes": subject_tags_includes,
                        "excludes": subject_tags_excludes
                    },
                    "ipAddresses": {
                        "includes": subject_addresses_includes,
                        "excludes": subject_addresses_excludes
                    }
                },
                "peer": {
                    "tags": {
                        "includes": peer_tags_includes,
                        "excludes": peer_tags_excludes
                    },
                    "ipAddresses": {
                        "includes": peer_addresses_includes,
                        "excludes": peer_addresses_excludes
                    }
                },
                "orientation": subject_orientation,
                "maxRows": max_rows,
                "flowCollectors": flow_collectors,
                "orderBy": order_by,
                "excludeBpsPps": exclude_bps_pps,
                "excludeOthers": exclude_others,
                "excludeCounts": exclude_counts,
                "standardOptions": standard_options
            }
        else:
            if start_datetime is not None:
                start_timestamp = start_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f')
                while len(start_timestamp.split('.')[1]) > 3:
                    start_timestamp = start_timestamp[:-1]
                start_timestamp += utc_offset
            if end_datetime is not None:
                end_timestamp = end_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f')
                while len(end_timestamp.split('.')[1]) > 3:
                    end_timestamp = end_timestamp[:-1]
                end_timestamp += utc_offset
            if interface_id is None:
                searchType = ""
                if report_type == "top-applications":
                    searchType = "topFlowApplications"
                elif report_type == "top-conversations":
                    searchType = "topFlowConversations"
                elif report_type == "top-hosts":
                    searchType = "topFlowHosts"
                elif report_type == "top-peers":
                    searchType = "topFlowPeers"
                elif report_type == "top-ports":
                    searchType = "topFlowPorts"
                elif report_type == "top-protocols":
                    searchType = "topFlowProtocols"
                elif report_type == "top-services":
                    searchType = "topFlowServices"
                request_data = {
                    "searchDisplayName": search_name,
                    "searchType": searchType,
                    "savedByUser": False,
                    "user": self.__smc_username,
                    "searchContext": {
                        "topReportFilter": {
                            "name": search_name,
                            "description": "",
                            "absolute": {
                                "from": start_timestamp,
                                "to": end_timestamp
                            },
                            "connection": {
                                "applications": {
                                    "includes": connection_applications_includes,
                                    "excludes": connection_applications_excludes
                                },
                                "byteRates": [],
                                "bytes": [],
                                "deviceIds": {
                                    "includes": flow_collectors,
                                    "excludes": []
                                },
                                "packetRates": [],
                                "packets": [],
                                "tcpConnections": [],
                                "urls": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "portProtocols": {
                                    "includes": connection_ports_protocols_includes,
                                    "excludes": connection_ports_protocols_excludes
                                }
                            },
                            "domainId": self.__domain_id,
                            "object": {
                                "byteRates": [],
                                "bytes": [],
                                "deviceIds": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "devices": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "hostGroups": {
                                    "includes": subject_tags_includes,
                                    "excludes": subject_tags_excludes
                                },
                                "ipAddresses": {
                                    "includes": subject_addresses_includes,
                                    "excludes": subject_addresses_excludes
                                },
                                "orientation": subject_orientation,
                                "packetRates": [],
                                "packets": [],
                                "portProtocols": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "processHashes": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "processNames": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "ratios": [],
                                "trustSecIds": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "trustSecNames": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "users": {
                                    "includes": [],
                                    "excludes": []
                                }
                            },
                            "peer": {
                                "byteRates": [],
                                "bytes": [],
                                "deviceIds": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "devices": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "hostGroups": {
                                    "includes": peer_tags_includes,
                                    "excludes": peer_tags_excludes
                                },
                                "ipAddresses": {
                                    "includes": peer_addresses_includes,
                                    "excludes": peer_addresses_excludes
                                },
                                "packetRates": [],
                                "packets": [],
                                "portProtocols": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "processHashes": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "processNames": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "ratios": [],
                                "trustSecIds": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "trustSecNames": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "users": {
                                    "includes": [],
                                    "excludes": []
                                }
                            },
                            #### "relativeSecondsFromCurrent": 300,
                            "searchDisplayName": search_name,
                            "advanced": {
                                "direction": "INBOUND_PLUS_OUTBOUND",
                                "maxRows": max_rows,
                                "excludeBpsPps": exclude_bps_pps,
                                "excludeOthers": exclude_others,
                                "orderBy": order_by,
                                "defaultColumns": True,
                                "performanceOption": "Standard",
                                "excludeCounts": exclude_counts
                            }
                        }
                    }
                }
            else:
                searchType = ""
                if report_type == "top-applications":
                    searchType = "topInterfaceApplications"
                elif report_type == "top-conversations":
                    searchType = "topInterfaceConversations"
                elif report_type == "top-hosts":
                    searchType = "topInterfaceHosts"
                elif report_type == "top-peers":
                    searchType = "topInterfacePeers"
                elif report_type == "top-ports":
                    searchType = "topInterfacePorts"
                elif report_type == "top-protocols":
                    searchType = "topInterfaceProtocols"
                elif report_type == "top-services":
                    searchType = "topInterfaceServices"
                request_data = {
                    "searchDisplayName": search_name,
                    "searchType": searchType,
                    "savedByUser": False,
                    "user": self.__smc_username,
                    "searchContext": {
                        "topReportFilter": {
                            "name": search_name,
                            "description": "",
                            "absolute": {
                                "from": start_timestamp,
                                "to": end_timestamp
                            },
                            "connection": {
                                "applications": {
                                    "includes": connection_applications_includes,
                                    "excludes": connection_applications_excludes
                                },
                                "byteRates": [],
                                "bytes": [],
                                "deviceIds": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "devices": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "packetRates": [],
                                "packets": [],
                                "tcpConnections": [],
                                "urls": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "portProtocols": {
                                    "includes": connection_ports_protocols_includes,
                                    "excludes": connection_ports_protocols_excludes
                                },
                                "interfaces": {
                                    "includes": [{
                                        "deviceId": interface_flow_collector_id,
                                        "exporterIpAddress": interface_exporter_ip,
                                        "interfaceId": interface_id
                                    }]
                                },
                                "protocols": [],
                                "cipherSuite": {
                                    "messageAuthCode": [],
                                    "keyExchange": [],
                                    "authAlgorithm": [],
                                    "encAlgorithm": [],
                                    "keyLength": []
                                },
                                "tlsVersion": [],
                                "totalTcpConnections": [],
                                "totalTcpRetransmissions": [],
                                "roundTripTime": [],
                                "serverResponseTime": [],
                                "isDownload": False,
                                "includeInterfaceData": False
                            },
                            "domainId": self.__domain_id,
                            "object": {
                                "byteRates": [],
                                "bytes": [],
                                "deviceIds": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "devices": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "hostGroups": {
                                    "includes": subject_tags_includes,
                                    "excludes": subject_tags_excludes
                                },
                                "ipAddresses": {
                                    "includes": subject_addresses_includes,
                                    "excludes": subject_addresses_excludes
                                },
                                "orientation": subject_orientation,
                                "packetRates": [],
                                "packets": [],
                                "portProtocols": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "processHashes": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "processNames": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "ratios": [],
                                "trustSecIds": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "trustSecNames": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "users": {
                                    "includes": [],
                                    "excludes": []
                                }
                            },
                            "peer": {
                                "byteRates": [],
                                "bytes": [],
                                "deviceIds": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "devices": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "hostGroups": {
                                    "includes": peer_tags_includes,
                                    "excludes": peer_tags_excludes
                                },
                                "ipAddresses": {
                                    "includes": peer_addresses_includes,
                                    "excludes": peer_addresses_excludes
                                },
                                "packetRates": [],
                                "packets": [],
                                "portProtocols": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "processHashes": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "processNames": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "ratios": [],
                                "trustSecIds": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "trustSecNames": {
                                    "includes": [],
                                    "excludes": []
                                },
                                "users": {
                                    "includes": [],
                                    "excludes": []
                                }
                            },
                            #### "relativeSecondsFromCurrent": 300,
                            "relativeSecondsFromCurrent": None,
                            "searchDisplayName": search_name,
                            "advanced": {
                                "direction": "INBOUND_PLUS_OUTBOUND",
                                "maxRows": max_rows,
                                "excludeBpsPps": exclude_bps_pps,
                                "excludeOthers": exclude_others,
                                "orderBy": order_by,
                                "defaultColumns": True,
                                "performanceOption": "Standard",
                                "excludeCounts": exclude_counts
                            },
                            # "hasRulesPacked": True
                        }
                    }
                }
        return request_data

    ############################################################################################################
    # Get the top ports using a flow report API query
    ############################################################################################################
    def get_top_ports(self, start_datetime, end_datetime, subject_tags_includes=None, subject_tags_excludes=None,
                      subject_addresses_includes=None, subject_addresses_excludes=None,
                      peer_tags_includes=None, peer_tags_excludes=None, peer_addresses_includes=None,
                      peer_addresses_excludes=None, subject_orientation=None,
                      connection_direction=None, connection_applications_includes=None,
                      connection_applications_excludes=None, connection_ports_protocols_includes=None,
                      connection_ports_protocols_excludes=None, flow_collectors=None, interface_flow_collector_id=None,
                      interface_exporter_ip=None, interface_id=None, order_by=None, max_rows=None,
                      exclude_bps_pps=None, exclude_others=None, exclude_counts=None, status_check_frequency=0,
                      utc_offset=None):
        report_type = "top-ports"
        current_time = time.ctime()
        search_name = "API flow report (" + self.__smc_username + "): " + report_type + " [" + current_time + "]"
        request_data = self.__generate_flow_report_request_data(report_type, search_name, start_datetime, end_datetime,
                                                                subject_tags_includes, subject_tags_excludes,
                                                                subject_addresses_includes,
                                                                subject_addresses_excludes, peer_tags_includes,
                                                                peer_tags_excludes, peer_addresses_includes,
                                                                peer_addresses_excludes, subject_orientation,
                                                                connection_direction,
                                                                connection_applications_includes,
                                                                connection_applications_excludes,
                                                                connection_ports_protocols_includes,
                                                                connection_ports_protocols_excludes,
                                                                flow_collectors, interface_flow_collector_id,
                                                                interface_exporter_ip, interface_id,
                                                                order_by, max_rows, exclude_bps_pps, exclude_others,
                                                                exclude_counts, utc_offset)
        results = self.__perform_flow_report_query(report_type, request_data, status_check_frequency)
        return results

    ############################################################################################################
    # Get the top applications using a flow report API query
    ############################################################################################################
    def get_top_applications(self, start_datetime, end_datetime, subject_tags_includes=None,
                             subject_tags_excludes=None, subject_addresses_includes=None,
                             subject_addresses_excludes=None,
                             peer_tags_includes=None, peer_tags_excludes=None, peer_addresses_includes=None,
                             peer_addresses_excludes=None, subject_orientation=None,
                             connection_direction=None, connection_applications_includes=None,
                             connection_applications_excludes=None, connection_ports_protocols_includes=None,
                             connection_ports_protocols_excludes=None, flow_collectors=None,
                             interface_flow_collector_id=None, interface_exporter_ip=None, interface_id=None,
                             order_by=None,
                             max_rows=None, exclude_bps_pps=None, exclude_others=None, exclude_counts=None,
                             status_check_frequency=0, utc_offset=None):
        report_type = "top-applications"
        current_time = time.ctime()
        search_name = "API flow report (" + self.__smc_username + "): " + report_type + " [" + current_time + "]"
        request_data = self.__generate_flow_report_request_data(report_type, search_name, start_datetime, end_datetime,
                                                                subject_tags_includes, subject_tags_excludes,
                                                                subject_addresses_includes,
                                                                subject_addresses_excludes, peer_tags_includes,
                                                                peer_tags_excludes, peer_addresses_includes,
                                                                peer_addresses_excludes, subject_orientation,
                                                                connection_direction,
                                                                connection_applications_includes,
                                                                connection_applications_excludes,
                                                                connection_ports_protocols_includes,
                                                                connection_ports_protocols_excludes,
                                                                flow_collectors, interface_flow_collector_id,
                                                                interface_exporter_ip, interface_id,
                                                                order_by, max_rows, exclude_bps_pps, exclude_others,
                                                                exclude_counts, utc_offset)
        results = self.__perform_flow_report_query(report_type, request_data, status_check_frequency)
        return results

    ############################################################################################################
    # Get the top protocols using a flow report API query
    ############################################################################################################
    def get_top_protocols(self, start_datetime, end_datetime, subject_tags_includes=None,
                          subject_tags_excludes=None,
                          subject_addresses_includes=None, subject_addresses_excludes=None,
                          peer_tags_includes=None, peer_tags_excludes=None, peer_addresses_includes=None,
                          peer_addresses_excludes=None, subject_orientation=None,
                          connection_direction=None, connection_applications_includes=None,
                          connection_applications_excludes=None, connection_ports_protocols_includes=None,
                          connection_ports_protocols_excludes=None, flow_collectors=None,
                          interface_flow_collector_id=None,
                          interface_exporter_ip=None, interface_id=None, order_by=None,
                          max_rows=None,
                          exclude_bps_pps=None, exclude_others=None, exclude_counts=None,
                          status_check_frequency=0, utc_offset=None):
        report_type = "top-protocols"
        current_time = time.ctime()
        search_name = "API flow report (" + self.__smc_username + "): " + report_type + " [" + current_time + "]"
        request_data = self.__generate_flow_report_request_data(report_type, search_name, start_datetime, end_datetime,
                                                                subject_tags_includes, subject_tags_excludes,
                                                                subject_addresses_includes,
                                                                subject_addresses_excludes, peer_tags_includes,
                                                                peer_tags_excludes, peer_addresses_includes,
                                                                peer_addresses_excludes, subject_orientation,
                                                                connection_direction,
                                                                connection_applications_includes,
                                                                connection_applications_excludes,
                                                                connection_ports_protocols_includes,
                                                                connection_ports_protocols_excludes,
                                                                flow_collectors, interface_flow_collector_id,
                                                                interface_exporter_ip, interface_id,
                                                                order_by, max_rows, exclude_bps_pps, exclude_others,
                                                                exclude_counts, utc_offset)
        results = self.__perform_flow_report_query(report_type, request_data, status_check_frequency)
        return results

    ############################################################################################################
    # Get the top hosts using a flow report API query
    ############################################################################################################
    def get_top_hosts(self, start_datetime, end_datetime, subject_tags_includes=None, subject_tags_excludes=None,
                      subject_addresses_includes=None, subject_addresses_excludes=None,
                      peer_tags_includes=None, peer_tags_excludes=None, peer_addresses_includes=None,
                      peer_addresses_excludes=None, subject_orientation=None,
                      connection_direction=None, connection_applications_includes=None,
                      connection_applications_excludes=None, connection_ports_protocols_includes=None,
                      connection_ports_protocols_excludes=None, flow_collectors=None, interface_flow_collector_id=None,
                      interface_exporter_ip=None, interface_id=None, order_by=None, max_rows=None,
                      exclude_bps_pps=None, exclude_others=None, exclude_counts=None, status_check_frequency=0,
                      utc_offset=None):
        report_type = "top-hosts"
        current_time = time.ctime()
        search_name = "API flow report (" + self.__smc_username + "): " + report_type + " [" + current_time + "]"
        request_data = self.__generate_flow_report_request_data(report_type, search_name, start_datetime, end_datetime,
                                                                subject_tags_includes, subject_tags_excludes,
                                                                subject_addresses_includes,
                                                                subject_addresses_excludes, peer_tags_includes,
                                                                peer_tags_excludes, peer_addresses_includes,
                                                                peer_addresses_excludes, subject_orientation,
                                                                connection_direction,
                                                                connection_applications_includes,
                                                                connection_applications_excludes,
                                                                connection_ports_protocols_includes,
                                                                connection_ports_protocols_excludes,
                                                                flow_collectors, interface_flow_collector_id,
                                                                interface_exporter_ip, interface_id,
                                                                order_by, max_rows, exclude_bps_pps, exclude_others,
                                                                exclude_counts, utc_offset)
        results = self.__perform_flow_report_query(report_type, request_data, status_check_frequency)
        return results

    ############################################################################################################
    # Get the top peers using a flow report API query
    ############################################################################################################
    def get_top_peers(self, start_datetime, end_datetime, subject_tags_includes=None, subject_tags_excludes=None,
                      subject_addresses_includes=None, subject_addresses_excludes=None,
                      peer_tags_includes=None, peer_tags_excludes=None, peer_addresses_includes=None,
                      peer_addresses_excludes=None, subject_orientation=None,
                      connection_direction=None, connection_applications_includes=None,
                      connection_applications_excludes=None, connection_ports_protocols_includes=None,
                      connection_ports_protocols_excludes=None, flow_collectors=None, interface_flow_collector_id=None,
                      interface_exporter_ip=None, interface_id=None, order_by=None, max_rows=None,
                      exclude_bps_pps=None, exclude_others=None, exclude_counts=None, status_check_frequency=0,
                      utc_offset=None):
        report_type = "top-peers"
        current_time = time.ctime()
        search_name = "API flow report (" + self.__smc_username + "): " + report_type + " [" + current_time + "]"
        request_data = self.__generate_flow_report_request_data(report_type, search_name, start_datetime, end_datetime,
                                                                subject_tags_includes, subject_tags_excludes,
                                                                subject_addresses_includes,
                                                                subject_addresses_excludes, peer_tags_includes,
                                                                peer_tags_excludes, peer_addresses_includes,
                                                                peer_addresses_excludes, subject_orientation,
                                                                connection_direction,
                                                                connection_applications_includes,
                                                                connection_applications_excludes,
                                                                connection_ports_protocols_includes,
                                                                connection_ports_protocols_excludes,
                                                                flow_collectors, interface_flow_collector_id,
                                                                interface_exporter_ip, interface_id,
                                                                order_by, max_rows, exclude_bps_pps, exclude_others,
                                                                exclude_counts, utc_offset)
        results = self.__perform_flow_report_query(report_type, request_data, status_check_frequency)
        return results

    ############################################################################################################
    # Get the top conversations using a flow report API query
    ############################################################################################################
    def get_top_conversations(self, start_datetime, end_datetime, subject_tags_includes=None,
                              subject_tags_excludes=None, subject_addresses_includes=None,
                              subject_addresses_excludes=None,
                              peer_tags_includes=None, peer_tags_excludes=None, peer_addresses_includes=None,
                              peer_addresses_excludes=None, subject_orientation=None,
                              connection_direction=None, connection_applications_includes=None,
                              connection_applications_excludes=None, connection_ports_protocols_includes=None,
                              connection_ports_protocols_excludes=None, flow_collectors=None,
                              interface_flow_collector_id=None, interface_exporter_ip=None, interface_id=None,
                              order_by=None,
                              max_rows=None, exclude_bps_pps=None, exclude_others=None, exclude_counts=None,
                              status_check_frequency=0, utc_offset=None):
        report_type = "top-conversations"
        current_time = time.ctime()
        search_name = "API flow report (" + self.__smc_username + "): " + report_type + " [" + current_time + "]"
        request_data = self.__generate_flow_report_request_data(report_type, search_name, start_datetime, end_datetime,
                                                                subject_tags_includes, subject_tags_excludes,
                                                                subject_addresses_includes,
                                                                subject_addresses_excludes, peer_tags_includes,
                                                                peer_tags_excludes, peer_addresses_includes,
                                                                peer_addresses_excludes, subject_orientation,
                                                                connection_direction,
                                                                connection_applications_includes,
                                                                connection_applications_excludes,
                                                                connection_ports_protocols_includes,
                                                                connection_ports_protocols_excludes,
                                                                flow_collectors, interface_flow_collector_id,
                                                                interface_exporter_ip, interface_id,
                                                                order_by, max_rows, exclude_bps_pps, exclude_others,
                                                                exclude_counts, utc_offset)
        results = self.__perform_flow_report_query(report_type, request_data, status_check_frequency)
        return results

    ############################################################################################################
    # Get the top services using a flow report API query
    ############################################################################################################
    def get_top_services(self, start_datetime, end_datetime, subject_tags_includes=None, subject_tags_excludes=None,
                         subject_addresses_includes=None, subject_addresses_excludes=None,
                         peer_tags_includes=None, peer_tags_excludes=None, peer_addresses_includes=None,
                         peer_addresses_excludes=None, subject_orientation=None,
                         connection_direction=None, connection_applications_includes=None,
                         connection_applications_excludes=None, connection_ports_protocols_includes=None,
                         connection_ports_protocols_excludes=None, flow_collectors=None,
                         interface_flow_collector_id=None,
                         interface_exporter_ip=None, interface_id=None, order_by=None,
                         max_rows=None,
                         exclude_bps_pps=None, exclude_others=None, exclude_counts=None,
                         status_check_frequency=0, utc_offset=None):
        report_type = "top-services"
        current_time = time.ctime()
        search_name = "API flow report (" + self.__smc_username + "): " + report_type + " [" + current_time + "]"
        request_data = self.__generate_flow_report_request_data(report_type, search_name, start_datetime, end_datetime,
                                                                subject_tags_includes, subject_tags_excludes,
                                                                subject_addresses_includes,
                                                                subject_addresses_excludes, peer_tags_includes,
                                                                peer_tags_excludes, peer_addresses_includes,
                                                                peer_addresses_excludes, subject_orientation,
                                                                connection_direction,
                                                                connection_applications_includes,
                                                                connection_applications_excludes,
                                                                connection_ports_protocols_includes,
                                                                connection_ports_protocols_excludes,
                                                                flow_collectors, interface_flow_collector_id,
                                                                interface_exporter_ip, interface_id,
                                                                order_by, max_rows, exclude_bps_pps, exclude_others,
                                                                exclude_counts, utc_offset)
        results = self.__perform_flow_report_query(report_type, request_data, status_check_frequency)
        return results

    ############################################################################################################
    # Retrieve the status of specified interface.
    ############################################################################################################
    def get_interface_status(self, flow_collector_id=None, exporter_ip_address=None, interface_id=None,
                             status_datetime=None, direction=None):
        if self.__version[0] <= 6 and self.__version[1] < 10:
            self.__api_session.close()
            raise Exception("Error: This function is not supported by this version of Stealthwatch.")
        response = None
        request_data = {}
        interface_list = {}
        if flow_collector_id is not None:
            interface_list['swaId'] = flow_collector_id
        if exporter_ip_address is not None:
            interface_list['exporterIpAddress'] = exporter_ip_address
        if interface_id is not None:
            interface_list['id'] = interface_id
        if interface_list != {}:
            request_data['interfaceList'] = [interface_list]
        if status_datetime is not None:
            status_timestamp = status_datetime.strftime('%Y-%m-%d')
            request_data['date'] = status_timestamp
        if direction is not None:
            request_data['direction'] = direction
        uri = 'https://' + self.__smc_ip + '/sw-reporting/v1/tenants/' + str(
            self.__domain_id) + '/netops/interface-status'
        response = self.__execute_query(uri, json.dumps(request_data), rest_method="post")
        if self.DEBUG:
            print('Stealthwatch API call response: \n' + json.dumps(response, indent=4, sort_keys=True))
        if response is None:
            print("ERROR: Unable to get interface status.")
            return None
        else:
            return response

    ############################################################################################################
    # Get exporters
    ############################################################################################################
    def get_exporters(self):
        if self.__version[0] <= 6 and self.__version[1] < 10:
            self.__api_session.close()
            raise Exception("Error: This function is not supported by this version of Stealthwatch.")
        response = None
        uri = 'https://' + self.__smc_ip + '/sw-reporting/v1/tenants/' + str(
            self.__domain_id) + '/netops/exporters/details/True'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch API call response: \n' + json.dumps(response, indent=4, sort_keys=True))
        if response is None:
            print("ERROR: Unable to get exporters.")
            return None
        else:
            return response

    ############################################################################################################
    # Retrieve the information about a list of interfaces.
    ############################################################################################################
    def get_interfaces(self):
        if self.__version[0] <= 6 and self.__version[1] < 10:
            self.__api_session.close()
            raise Exception("Error: This function is not supported by this version of Stealthwatch.")
        response = None
        uri = 'https://' + self.__smc_ip + '/sw-reporting/v1/tenants/' + str(
            self.__domain_id) + '/netops/interfaces'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch API call response: \n' + json.dumps(response, indent=4, sort_keys=True))
        if response is None:
            print("ERROR: Unable to get interfaces.")
            return None
        else:
            return response

    ############################################################################################################
    # Retrieve descriptions of security events.
    ############################################################################################################
    def get_security_event_descriptions(self):
        if self.__version[0] <= 6 and self.__version[1] < 10:
            self.__api_session.close()
            raise Exception("Error: This function is not supported by this version of Stealthwatch.")
        response = None
        uri = 'https://' + self.__smc_ip + '/sw-reporting/v1/tenants/' + str(
            self.__domain_id) + '/security-events/templates'
        response = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch API call response: \n' + json.dumps(response, indent=4, sort_keys=True))
        if response is None:
            print("ERROR: Unable to get security events descriptions.")
            return None
        else:
            return response

    ############################################################################################################
    # Initiates a security events API query
    ############################################################################################################
    def __initiate_security_events_query(self, request_data):
        query_id = None
        uri = 'https://' + self.__smc_ip + '/sw-reporting/v1/tenants/' + str(
            self.__domain_id) + '/security-events/queries'
        query_id_response = self.__execute_query(uri, json.dumps(request_data), rest_method="post")
        if self.DEBUG:
            print('Stealthwatch API call response: \n' + json.dumps(query_id_response, indent=4, sort_keys=True))
        if query_id_response is None:
            print("ERROR: Unable to initiate query.")
            return None
        if 'searchJob' in query_id_response and 'id' in query_id_response['searchJob']:
            query_id = query_id_response['searchJob']['id']
        if query_id is None:
            print("ERROR: Unable to fetch query ID.")
            return None
        else:
            return query_id

    ############################################################################################################
    # Checks the status of a security events API query
    ############################################################################################################
    def __check_security_events_query_status(self, query_id):
        query_status = None
        uri = 'https://' + self.__smc_ip + '/sw-reporting/v1/tenants/' + str(
            self.__domain_id) + '/security-events/queries/' + str(query_id)
        query_status_response = self.__execute_query(uri, None)
        if self.DEBUG:
            print(
                'Stealthwatch API call response: \n' + json.dumps(query_status_response, indent=4, sort_keys=True))
        if query_status_response is None:
            print("ERROR: Unable to initiate query.")
            return None
        if 'status' in query_status_response:
            query_status = query_status_response['status']
        if query_status is None:
            print("ERROR: Unable to fetch query status.")
            return None
        else:
            return query_status

    ############################################################################################################
    # Gets the results of a security events API query
    ############################################################################################################
    def __get_security_events_query_results(self, query_id):
        uri = 'https://' + self.__smc_ip + '/sw-reporting/v1/tenants/' + str(
            self.__domain_id) + '/security-events/results/' + str(query_id)
        results = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch API call response: \n' + json.dumps(results, indent=4, sort_keys=True))
        return results

    ############################################################################################################
    # Performs the necessary operations for a security events API query
    ############################################################################################################
    def __perform_security_events_query(self, request_data, status_check_frequency):
        results = None
        if status_check_frequency <= 0:
            status_check_frequency = 1000
        if self.__domain_id is None:
            print("ERROR: Unable to perform security events API query.")
            return results
        query_id = self.__initiate_security_events_query(request_data)
        if query_id is None:
            return results
        query_status = self.__check_security_events_query_status(query_id)
        while query_status is not None and query_status != "FAILED" and query_status != "COMPLETED":
            time.sleep(status_check_frequency / 1000.0)
            query_status = self.__check_security_events_query_status(query_id)
        if query_status is None or query_status != "COMPLETED":
            print("ERROR: Unable to perform security events API query.")
            return results
        else:
            results = self.__get_security_events_query_results(query_id)
            return results

    ############################################################################################################
    # Get the top ports using a security events API query
    ############################################################################################################
    def __generate_security_events_request_data(self, start_datetime, end_datetime, hosts, source_or_target,
                                                security_event_type_ids):
        if hosts is None:
            hosts = []
        if isinstance(hosts, str):
            hosts = [hosts]
        if source_or_target is None:
            source_or_target = []
        if isinstance(source_or_target, str):
            source_or_target = [source_or_target]
        if security_event_type_ids is None:
            security_event_type_ids = []
        if isinstance(security_event_type_ids, str):
            security_event_type_ids = [security_event_type_ids]

        start_timestamp = start_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_timestamp = end_datetime.strftime('%Y-%m-%dT%H:%M:%SZ')

        request_data = {}
        timerange = {"from": start_timestamp, "to": end_timestamp}
        request_data["timeRange"] = timerange
        if len(security_event_type_ids) > 0:
            request_data["securityEventTypeIds"] = security_event_type_ids
        i = 0
        hosts_list = []
        while i < len(hosts):
            this_host = {"ipAddress": hosts[i], "type": source_or_target[i]}
            hosts_list.append(this_host)
            i += 1
        if len(hosts_list) > 0:
            request_data["hosts"] = hosts_list
        return request_data

    ############################################################################################################
    # Get the security events for a given IP(s)
    ############################################################################################################
    def get_security_events(self, start_datetime, end_datetime, hosts=None, source_or_target=None,
                            security_event_type_ids=None, status_check_frequency=0):
        if self.__version[0] <= 6 and self.__version[1] < 10:
            self.__api_session.close()
            raise Exception("Error: This function is not supported by this version of Stealthwatch.")
        if hosts is not None and isinstance(hosts, list):
            if source_or_target is None or not isinstance(source_or_target, list) or len(hosts) != len(
                    source_or_target):
                print("ERROR: Unable to get security events. 'hosts' and 'source_or_target' not defined properly")
                return None
        request_data = self.__generate_security_events_request_data(start_datetime, end_datetime, hosts,
                                                                    source_or_target, security_event_type_ids)
        results = self.__perform_security_events_query(request_data, status_check_frequency)
        return results

    ############################################################################################################
    # Initiates an interface flow report API query
    ############################################################################################################
    def __initiate_alarm_report_search(self, request_data):
        search_id = None
        uri = 'https://' + self.__smc_ip + '/smc/rest/domains/' + str(
            self.__domain_id) + '/searches'
        search_id_response = self.__execute_query(uri, json.dumps(request_data), rest_method="post")
        if self.DEBUG:
            print('Stealthwatch API initiate_alarm_report_search call response: \n' + json.dumps(search_id_response,
                                                                                                 indent=4,
                                                                                                 sort_keys=True))
        if search_id_response is None:
            print("ERROR: Unable to initiate_alarm_report_search.")
            return None
        if 'id' in search_id_response:
            search_id = search_id_response['id']
        if search_id is None:
            print("ERROR: Unable to fetch search ID.")
            return None
        else:
            return search_id

    ############################################################################################################
    # Initiates an interface alarm report API query
    ############################################################################################################
    def __initiate_alarm_report_job(self, search_id):
        job_id = None
        uri = 'https://' + self.__smc_ip + '/smc/rest/domains/' + str(
            self.__domain_id) + '/searches/' + search_id + "/jobs"
        job_id_response = self.__execute_query(uri, json.dumps({"secondsToWait": 1, "disableChunking": True}),
                                               rest_method="post")
        if self.DEBUG:
            print('Stealthwatch API initiate_alarm_report_job call response: \n' + json.dumps(job_id_response,
                                                                                              indent=4,
                                                                                              sort_keys=True))
        if job_id_response is None:
            print("ERROR: Unable to initiate_alarm_report_job.")
            return None
        if 'id' in job_id_response:
            job_id = job_id_response['id']
        if job_id is None:
            print("ERROR: Unable to fetch job ID.")
            return None
        else:
            return job_id

    ############################################################################################################
    # Checks the status of a flow report API query
    ############################################################################################################
    def __check_alarm_report_query_status(self, search_id, job_id):
        query_status = None
        uri = 'https://' + self.__smc_ip + '/smc/rest/domains/' + str(
            self.__domain_id) + '/searches/' + search_id + '/jobstatus/' + job_id
        query_status_response = self.__execute_query(uri, None)
        if self.DEBUG:
            print(
                'Stealthwatch API call response: \n' + json.dumps(query_status_response, indent=4,
                                                                  sort_keys=True))
        if query_status_response is None:
            print("ERROR: Unable to initiate query.")
            return None
        if 'searchJobStatus' in query_status_response:
            query_status = query_status_response['searchJobStatus']
        if query_status is None:
            print("ERROR: Unable to fetch query status.")
            return None
        else:
            return query_status

    ############################################################################################################
    # Gets the results of a flow report API query
    ############################################################################################################
    def __get_alarm_report_query_results(self, search_id, job_id, delete_after_fetched=False):
        uri = 'https://' + self.__smc_ip + '/smc/rest/domains/' + str(
            self.__domain_id) + '/searches/' + search_id + '/jobs/' + job_id + '/results?page=0&resultsPerPage=5000&sort=rank'
        results = self.__execute_query(uri, None)
        if self.DEBUG:
            print('Stealthwatch API call response: \n' + json.dumps(results, indent=4, sort_keys=True))
        if "page" in results and "content" in results["page"]:
            results = {"results": results["page"]["content"]}

        # Will delete the search/job/results once the data is fetched, this is in order to keep the SNA DB from filling
        # up with excessive job searches
        if delete_after_fetched:
            del_results_uri = "https://{}/smc/rest/domains/{}/searches/{}/jobs/{}/results".format(self.__smc_ip,
                                                                                                  self.__domain_id,
                                                                                                  search_id, job_id)
            del_search_uri = "https://{}/smc/rest/domains/{}/searches/{}".format(self.__smc_ip, self.__domain_id,
                                                                                 search_id)
            del_jobs_uri = "https://{}/smc/rest/domains/{}/searches/{}/jobs/{}".format(self.__smc_ip, self.__domain_id,
                                                                                       search_id, job_id)

            del_res_results = self.__execute_query(del_results_uri, rest_method='delete')
            del_search_results = self.__execute_query(del_search_uri, rest_method='delete')
            del_job_results = self.__execute_query(del_jobs_uri, rest_method='delete')

        return results

    ############################################################################################################
    # Get the request data for an alarm report
    ############################################################################################################
    def __generate_alarm_report_request_data(self, search_name, is_active, alarm_category_id, ip_address,
                                             start_datetime, end_datetime):

        if alarm_category_id is None or len(str(alarm_category_id)) <= 0 or int(alarm_category_id) <= 0:
            alarm_category_id = None

        if ip_address is None or len(ip_address) <= 0 or ip_address == "*":
            ip_address = None

        request_data = {}
        request_data["domainId"] = self.__domain_id
        request_data["searchDisplayName"] = search_name
        request_data["searchType"] = "alarmDetail"
        request_data["searchContext"] = {}

        start_timestamp = start_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f')
        while len(start_timestamp.split('.')[1]) > 3:
            start_timestamp = start_timestamp[:-1]
        start_timestamp += "+0000"
        request_data["searchContext"]["alarmStartDateTime"] = start_timestamp

        end_timestamp = end_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f')
        while len(end_timestamp.split('.')[1]) > 3:
            end_timestamp = end_timestamp[:-1]
        end_timestamp += "+0000"
        request_data["searchContext"]["alarmEndDateTime"] = end_timestamp

        if is_active is not None:
            request_data["searchContext"]["isActive"] = is_active
        if alarm_category_id is not None:
            request_data["searchContext"]["alarmCategory"] = alarm_category_id

        if ip_address is not None:
            request_data["searchContext"]["ipAddress"] = ip_address
        return request_data

    ############################################################################################################
    # Performs the necessary operations for a alarm report API query
    ############################################################################################################
    def __perform_alarm_report_query(self, request_data, status_check_frequency):
        results = None
        if status_check_frequency <= 0:
            status_check_frequency = 1000
        if self.__domain_id is None:
            print("ERROR: Unable to perform alarm report API query.")
            return results

        search_id = self.__initiate_alarm_report_search(request_data)
        if search_id is None:
            return results
        job_id = self.__initiate_alarm_report_job(search_id)
        if job_id is None:
            return results
        query_status = self.__check_alarm_report_query_status(search_id, job_id)
        while query_status is not None and query_status != "FAILED" and query_status != "COMPLETED":
            time.sleep(status_check_frequency / 1000.0)
            query_status = self.__check_alarm_report_query_status(search_id, job_id)
        if query_status is None or query_status != "COMPLETED":
            print("ERROR: Unable to perform flow report API query.")
            return results
        else:
            results = self.__get_alarm_report_query_results(search_id, job_id, delete_after_fetched=True)
            return results

    ############################################################################################################
    # Get the alarms using a flow report API query
    ############################################################################################################
    def get_alarms(self, start_datetime, end_datetime, is_active=None, alarm_category_id=None, ip_address=None,
                   status_check_frequency=0):
        current_time = time.ctime()
        search_name = "API alarm report (" + self.__smc_username + "): alarmDetail [" + current_time + "]"
        request_data = self.__generate_alarm_report_request_data(search_name, is_active, alarm_category_id,
                                                                 ip_address, start_datetime, end_datetime)
        results = self.__perform_alarm_report_query(request_data, status_check_frequency)
        return results

    ############################################################################################################
    # Get the request data for an top alarming host report
    ############################################################################################################
    def __generate_top_alarming_report_request_data(self, search_type, search_name, host_group_id):
        if host_group_id is None or len(str(host_group_id)) <= 0 or int(host_group_id) <= -1:
            host_group_id = None

        request_data = {}
        request_data["domainId"] = self.__domain_id
        request_data["searchDisplayName"] = search_name
        request_data["searchType"] = search_type
        request_data["searchContext"] = {}
        if host_group_id is not None:
            request_data["searchContext"]["hostGroupId"] = int(host_group_id)
        return request_data

    ############################################################################################################
    # Get the top alarming host using a flow report API query
    ############################################################################################################
    def get_top_alarming_hosts(self, host_group_id=None, status_check_frequency=0):
        current_time = time.ctime()
        search_name = "API top alarming report (" + self.__smc_username + "): hostEntityList [" + current_time + "]"
        request_data = self.__generate_top_alarming_report_request_data("hostEntityList", search_name, host_group_id)
        results = self.__perform_alarm_report_query(request_data, status_check_frequency)
        return results

    ############################################################################################################
    # Get the top alarming users using a flow report API query
    ############################################################################################################
    def get_top_alarming_users(self, host_group_id=None, status_check_frequency=0):
        current_time = time.ctime()
        search_name = "API top alarming report (" + self.__smc_username + "): userEntityList [" + current_time + "]"
        request_data = self.__generate_top_alarming_report_request_data("userEntityList", search_name, host_group_id)
        results = self.__perform_alarm_report_query(request_data, status_check_frequency)
        return results
