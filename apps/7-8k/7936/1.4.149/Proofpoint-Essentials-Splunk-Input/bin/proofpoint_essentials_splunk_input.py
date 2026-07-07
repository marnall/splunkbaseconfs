#!/usr/bin/env python
from __future__ import absolute_import, division, print_function
import sys
import os
from time import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import splunklib.client as client
import logger_manager
import json
import dateutil.parser
import dateutil.tz
import re
import requests
from splunklib.modularinput import Argument, Script, Scheme, Event
from datetime import datetime, timedelta
from requests.compat import quote_plus
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
if sys.version_info[0] < 3:
    import urllib
else:
    import urllib.parse as urllib

_LOGGER = logger_manager.setup_logging("proofpoint_essentials_splunk_siem")


def _utcnow():
    """
    Helper method which allows us to mock datetime.utcnow() responses in our test suite.

    Datetime is written in C code and apparently can't be mocked as a result. Who knew?
    :return datetime:
    """
    return datetime.now(dateutil.tz.tzutc())


class PfptSiemScript(Script):
    """Main class for Proofpoint Essentials Splunk Input."""

    APP = 'Proofpoint-Essentials-Splunk-Input'
    MASK = '<encrypted>'
    SIEM_URL_PROTOCOL = 'https://'
    SIEM_URL_DEFAULT_HOST = 'us-siem.proofpointessentials.com'
    SIEM_URL_PATH = '/v2/siem/all'
    SIEM_URL_QUERY_PARAMS = '?'
    INPUT_TYPE = "proofpoint_essentials_splunk_input"
    VALIDATE_SSL = True
    YOUR_DATA_DEFAULT = True
    CUSTOMER_DATA_DEFAULT = False
    max_past = _utcnow() - timedelta(hours=70, minutes=59)
    collection_name = APP
    input_kv_key = None
    token = None
    session = None
    total_event_count = 0
    nobody_client = None
    admin_client = None
    input_name = None
    full_input_name = None
    ew = None

    def get_scheme(self):
        """
        Returns a ``Scheme`` object which is used to define new inputs.

        :return Scheme: the modular input's scheme
        """
        scheme = Scheme('Proofpoint Essentials SIEM Modular Input')
        scheme.description = 'Modular Input which pulls data from the Proofpoint Essentials SIEM API'
        name_arg = Argument(name='name',
                            title='Name',
                            description='The name of the Splunk input stanza.',
                            data_type=Argument.data_type_string,
                            required_on_create=True,
                            required_on_edit=True)
        scheme.add_argument(name_arg)
        username_arg = Argument(name='username',
                                title='API Key',
                                description='The API Key generated in your Proofpoint Essentials UI.',
                                data_type=Argument.data_type_string,
                                required_on_create=True,
                                required_on_edit=True)
        scheme.add_argument(username_arg)
        password_arg = Argument(name='password',
                                title='Secret',
                                description='The API Key secret generated in your Proofpoint Essentials UI.',
                                data_type=Argument.data_type_string,
                                required_on_create=True,
                                required_on_edit=True)
        scheme.add_argument(password_arg)
        your_data_arg = Argument(name='your_data',
                                title='Retrieve Your Data',
                                description='Ingest events from your Proofpoint Essentials tenant.',
                                data_type=Argument.data_type_string,
                                required_on_create=True,
                                required_on_edit=True)
        scheme.add_argument(your_data_arg)
        customer_data_arg = Argument(name='customer_data',
                                title='Retrieve Your Customers\' Data',
                                description='Ingest events from all customers underneath your Proofpoint Essentials tenant.',
                                data_type=Argument.data_type_string,
                                required_on_create=True,
                                required_on_edit=True)
        scheme.add_argument(customer_data_arg)
        proxy_protocol_arg = Argument(
                                name='proxy_protocol',
                                title='Proxy Protocol',
                                description='(Optional) Proxy Protocol to use (http or https). Default will be https.',
                                data_type=Argument.data_type_string,
                                required_on_create=False,
                                required_on_edit=False)
        scheme.add_argument(proxy_protocol_arg)
        proxy_server_arg = Argument(name='proxy_server',
                                    title='Proxy Hostname',
                                    description='(Optional) Hostname of the proxy that the Splunk server uses '
                                                'to connect to the internet.',
                                    data_type=Argument.data_type_string,
                                    required_on_create=False,
                                    required_on_edit=False)
        scheme.add_argument(proxy_server_arg)
        proxy_port_arg = Argument(name='proxy_port',
                                  title='Proxy Port',
                                  description='(Optional) The port number of the proxy.',
                                  data_type=Argument.data_type_number,
                                  required_on_create=False,
                                  required_on_edit=False)
        scheme.add_argument(proxy_port_arg)
        proxy_username_arg = Argument(name='proxy_username',
                                      title='Proxy Username',
                                      description='(Optional) The username used to connect to the proxy.',
                                      data_type=Argument.data_type_string,
                                      required_on_create=False,
                                      required_on_edit=False)
        scheme.add_argument(proxy_username_arg)
        proxy_password_arg = Argument(name='proxy_password',
                                      title='Proxy Password',
                                      description='(Optional) The password used to authenticate to the proxy.',
                                      data_type=Argument.data_type_string,
                                      required_on_create=False,
                                      required_on_edit=False)
        scheme.add_argument(proxy_password_arg)
        siem_url_host_arg = Argument(name='siem_url_host',
                                     title='SIEM URL Host',
                                     description='The location of the Proofpoint Essentials SIEM API.',
                                     data_type=Argument.data_type_string,
                                     required_on_create=True,
                                     required_on_edit=True)
        scheme.add_argument(siem_url_host_arg)
        return scheme

    def encrypt_password(self, username, password, input_name):
        """
        Saves a cleartext password into Splunk's secure password storage service.

        :param str username: the username associated with the password
        :param str password: the cleartext password to encrypt
        :raise Exception: if any issue is encountered while communicating with the storage passwords service
        """
        try:
            for storage_password in self.admin_client.storage_passwords:
                if storage_password.username == username:
                    self.admin_client.storage_passwords.delete(
                        username=storage_password.username)
                    break
            self.admin_client.storage_passwords.create(password, username)
            _LOGGER.info(f'{input_name}: Credentials updated successfully.')
        except Exception as e:
            raise ValueError(
                "An error occurred while updating credentials. Please ensure your user account has admin_all_objects"
                " and/or list_storage_passwords capabilities. Error: {}".format(str(e)))

    def mask_password(self, location, input_name):
        """
        Replaces a password configuration item with a masked version and re-saves the input definition.

        :param str location:  the location of the password configuration item
        :raise Exception: if any error is encountered while saving inputs.conf
        """
        unsupported_keys = ['disabled', 'host_resolved', 'python.version']
        try:
            for input_def in self.admin_client.inputs.list(self.INPUT_TYPE):
                if input_def.name != input_name:
                    continue
                new_input_content = input_def.content.copy()
                new_input_content[location] = self.MASK
                for key in unsupported_keys:
                    if key in new_input_content:
                        del new_input_content[key]
                new_input = input_def.update(**new_input_content)
                new_input.refresh()
                _LOGGER.info(f'{input_name}: inputs.conf updated successfully.')
                break
        except Exception as e:
            raise ValueError(f'An error occured while updating inputs.conf: {str(e)}')

    def get_password(self, username):
        """
        Retrieves the cleartext password from Splunk's password storage service.

        :param str username: the username corresponding to the password we want to retrieve
        :return str: the cleartext password
        :raise ValueError: if the username is not found in the password storage service
        """
        for storage_password in self.admin_client.storage_passwords:
            if storage_password.username == username:
                return storage_password.content.clear_password
        raise ValueError(f'Could not find user record for {username} in storage_passwords for {self.input_name}')

    def set_authentication_information(self, items):
        """
        Sets all the information required to authenticate, based on the input definition. If the input definition's.

        passwords are not masked, it encrypts and masks them. Usually, this would only be done the first time the
        input definition is run after it is created.

        :param dict items: a dictionary containing input definition configuration
        """
        username = items['username']
        password = items['password']
        self.YOUR_DATA = items.get('your_data', self.YOUR_DATA_DEFAULT)
        self.CUSTOMER_DATA = items.get('customer_data', self.CUSTOMER_DATA_DEFAULT)
        proxy_protocol = items.get('proxy_protocol', 'https')
        if proxy_protocol is not None:
            proxy_protocol = proxy_protocol.lower().strip().replace(" ", "")
        proxy_server = items.get('proxy_server', None)
        proxy_port = items.get('proxy_port', None)
        proxy_username = items.get('proxy_username', None)
        proxy_password = items.get('proxy_password', None)
        self.SIEM_URL_HOST = items.get('siem_url_host', self.SIEM_URL_DEFAULT_HOST)
        proxy_password_storage_key = '_'.join([self.INPUT_TYPE, self.input_name, str(proxy_username)])
        if password != self.MASK:
            self.encrypt_password(username, password, self.input_name)
            self.mask_password('password', self.input_name)
        clear_password = self.get_password(username)
        clear_proxy_password = ''
        if proxy_password:
            if proxy_password != self.MASK:
                # So that we don't accidentally stomp on any other input's stored
                # passwords, we'll prepend the "username" with the INPUT_TYPE and
                # input_name and use that to store the password.
                self.encrypt_password(proxy_password_storage_key, proxy_password, self.input_name)
                self.mask_password('proxy_password', self.input_name)
            clear_proxy_password = self.get_password(proxy_password_storage_key)
        self.set_siem_url()
        self.session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        # July 31,2023: removed session.verify as self.session.verify is set to true by default
        # self.session.verify = self.VALIDATE_SSL
        self.session.proxies = self.get_proxies(
            proxy_protocol, proxy_server, proxy_port, proxy_username, clear_proxy_password
        )
        self.session.headers.update(self.get_headers())
        self.session.auth = (username, clear_password)

    def set_siem_url(self):
        """
        Builds the appropriate URL and turns on or off SSL validation, based on settings.

        :return None:
        """
        self.VALIDATE_SSL = True if (self.SIEM_URL_HOST == self.SIEM_URL_DEFAULT_HOST) else False
        self.SIEM_URL = self.SIEM_URL_PROTOCOL + self.SIEM_URL_HOST + self.SIEM_URL_PATH + self.SIEM_URL_QUERY_PARAMS

    def get_headers(self):
        """
        Called when building the SIEM request, to set version information in the request header.

        :return dict: contains the User-Agent string to user
        """
        ta_version = self.admin_client.apps[self.APP]['version']
        ta_user_agent = f'{self.APP}/{ta_version}'
        return {'User-Agent': ta_user_agent, 'Accept': 'application/json; charset=utf-8'}

    def validate_input(self, definition):
        """
        Called by Splunk to validate that the user-supplied input is correct.

        :definition (param splunklib.modularinput.InputDefinition ): the input definition being validated
        :raise ValueError: if the status code returned by the SIEM API does not indicate success
        """
        # We may need to set the token admin_client here as well, since validation happens in a separate
        # invocation of the script that doesn't go through the stream_events method, and we use
        # the get_password method here.
        try:
            input_name = definition.metadata['name']
            mgmt_port = int(definition.metadata.get('server_uri').split(":")[-1])
            if self.admin_client is None:
                self.token = definition.metadata['session_key']
                self.admin_client = client.connect(token=self.token, port=mgmt_port, autologin=True)
            username = definition.parameters['username']
            password = definition.parameters['password']
            proxy_protocol = definition.parameters.get('proxy_protocol', 'https')
            proxy_server = definition.parameters.get('proxy_server', None)
            proxy_port = definition.parameters.get('proxy_port', None)
            proxy_username = definition.parameters.get('proxy_username', None)
            proxy_password = definition.parameters.get('proxy_password', None)
            self.SIEM_URL_HOST = definition.parameters.get('siem_url_host', self.SIEM_URL_DEFAULT_HOST)
            self.YOUR_DATA = definition.parameters.get('your_data', self.YOUR_DATA_DEFAULT)
            self.CUSTOMER_DATA = definition.parameters.get('customer_data', self.CUSTOMER_DATA_DEFAULT)

            if proxy_server is not None and proxy_server.strip() == "":
                proxy_server = None
                del definition.parameters["proxy_server"]
            if proxy_port is not None and str(proxy_port).strip() == "":
                proxy_port = None
                del definition.parameters["proxy_port"]
            if proxy_username is not None and proxy_username.strip() == "":
                proxy_username = None
                del definition.parameters["proxy_username"]
            if proxy_password is not None and proxy_password.strip() == "":
                proxy_password = None
                del definition.parameters["proxy_password"]
            if ((proxy_server is None and (proxy_port is not None))
                    or (proxy_port is None and (proxy_server is not None))):
                raise ValueError('Either provide Proxy Hostname and Proxy Port both or none.')
            if (proxy_server is None and proxy_port is None):
                if ((proxy_username is not None) or (proxy_password is not None)):
                    raise ValueError('Please provide Proxy Hostname and Proxy Port.')
            if ((proxy_server is not None)):
                if proxy_protocol is None or proxy_protocol.lower().strip().replace(" ", "") not in ["http", "https"]:
                    raise ValueError('Provide one of http or https in Proxy Protocol field.')
                if ((proxy_username is None and (proxy_password is not None))
                        or (proxy_password is None and (proxy_username is not None))):
                    raise ValueError('Either provide Proxy Username and Proxy Password both or none.')
            if proxy_port:
                try:
                    proxy_port_value = int(proxy_port)
                except ValueError:
                    raise ValueError('Proxy port should be a numeric value.')
                if proxy_port_value <= 0:
                    raise ValueError('Proxy port should be a positive integer.')
            self.set_siem_url()
            url = self.SIEM_URL + urllib.urlencode(
                {'sinceSeconds': 300,
                 'ownData': self.YOUR_DATA,
                 'customerData': self.CUSTOMER_DATA})
            if password == self.MASK:
                password = self.get_password(username)
            if proxy_password == self.MASK:
                proxy_password_storage_key = '_'.join([self.INPUT_TYPE, input_name, str(proxy_username)])
                proxy_password = self.get_password(proxy_password_storage_key)
            auth = (username, password)
            if proxy_protocol is not None:
                proxy_protocol = proxy_protocol.lower().strip().replace(" ", "")
            proxies = self.get_proxies(
                proxy_protocol,
                proxy_server,
                proxy_port,
                proxy_username,
                proxy_password)
            headers = self.get_headers()
            # July 31,2023: removed verify=self.VALIDATE_SSL to meet Splunk's compatibility criteria)
            # resp = requests.get(url, auth=auth, proxies=proxies, headers=headers, verify=self.VALIDATE_SSL, )
            resp = requests.get(url, auth=auth, proxies=proxies, headers=headers, )
            if resp.status_code not in (200, 204):
                raise ValueError(f'Could not access Essentials SIEM API using provided credentials. Status code: {str(resp.status_code)} : {resp.reason}  URL: {url}')
        except Exception as e:
            _LOGGER.error(f'{input_name}: {str(e)}')
            raise ValueError(e)

    def retrieve_last_poll_time(self):
        """
        Returns the last successful poll time from the Splunk KV store.

        :return datetime: either the last poll time or the maximum time into the past which can be successfully queried
        """
        kv = self.nobody_client.kvstore[self.collection_name]
        query_args = {'query': '{{"input_name":"{}"}}'.format(self.full_input_name)}
        results = kv.data.query(**query_args)
        if len(results) == 0:
            return self.max_past
        if len(results) > 1:
            raise ValueError(
                'When trying to retrieve the last poll time, '
                'multiple kvstore records were found')
        self.input_kv_key = results[0]['_key']
        last_poll_time_s = results[0]['last_poll_time']
        last_poll_time_dt = dateutil.parser.parse(last_poll_time_s)
        if last_poll_time_dt < self.max_past:
            _LOGGER.warning(
                f'{self.input_name}: Previous poll time {last_poll_time_dt}, is too far in the past. Returning maximum data available.')
            return self.max_past
        return last_poll_time_dt

    def update_last_poll_time(self, last_poll_time):
        """
        Updates the last successful poll time in the Splunk KV store.

        :param str last_poll_time: A string containing the last successful poll time
        """
        data = json.dumps({'input_name': self.full_input_name, 'last_poll_time': last_poll_time})
        kv = self.nobody_client.kvstore[self.collection_name]
        if self.input_kv_key is None:
            result = kv.data.insert(data)
            self.input_kv_key = result['_key']
        else:
            kv.data.update(self.input_kv_key, data)

    def query_and_save(self, start_time_s, end_time_s):
        """
        Performs a single request to the Proofpoint Essentials SIEM API, using any configured proxy.

        After a successful query, it updates the last successful poll time.

        :param datetime start_time_s: the start of the query interval (inclusive)
        :param datetime end_time_s: the end of the query interval (exclusive)
        """
        args = urllib.urlencode({'interval': f'{start_time_s}/{end_time_s}',
                                 'ownData': self.YOUR_DATA,
                                 'customerData': self.CUSTOMER_DATA})
        url = self.SIEM_URL + args
        try:
            resp = self.session.get(url)
        except Exception as e:
            _LOGGER.error(self.ew.ERROR, f'{self.input_name}: Could not query Essentials SIEM API - {url} ({e})')
            sys.exit(1)
        if resp.status_code == 204:
            _LOGGER.info(f'{self.input_name}: Empty content returned from {start_time_s} to {end_time_s}')
        elif resp.status_code != 200:
            _LOGGER.error(f'Querying from {start_time_s} to {end_time_s}, but SIEM server returned status code: {resp.status_code}, message: {resp.reason}: {url}')
            return
        _LOGGER.info(f'{self.input_name}: Successful query from {start_time_s} to {end_time_s}')
        self.save_events(resp.json())
        self.update_last_poll_time(last_poll_time=end_time_s)

    def save_events(self, data):
        """
        Processes a single content query's return value. Adds the eventType attribute to each event before logging it.

        :param dict data: a dictionary containing events to be logged
        """
        # Python's default isoformat uses +00:00 instead of Z, so replace it for consistency.
        default_event_time = re.sub('(?<=[0-9]{3})([0-9]{3})?\+00:00', 'Z', _utcnow().isoformat())  # noqa W605
        event_count = 0
        for key in data.keys():
            if key in ['clicksBlocked', 'clicksPermitted', 'messagesBlocked',
                       'messagesDelivered']:
                evdata = data[key]
                for row in evdata:
                    if 'eventType' not in row:
                        row.update({'eventType': key})
                    if 'eventTime' not in row:
                        row.update({'eventTime': default_event_time})
                    event = Event()
                    event.stanza = self.full_input_name
                    event.data = json.dumps(row, ensure_ascii=False)
                    self.ew.write_event(event)
                    event_count = event_count + 1
        self.total_event_count += event_count
        _LOGGER.info(f'{self.input_name}: Collected {event_count} events.')

    def stream_events(self, inputs, ew):
        """
        The main procedure which is invoked by Splunk to initiate event download.

        :param splunklib.modularinput.InputDefinition inputs: an InputDefinition sourced from Splunk
        :param splunklib.modularinput.EventWriter ew: an EventWriter object which will be used to log events
        :return:
        """
        _LOGGER.info('Starting data collection.')
        start_time = time()
        self.token = inputs.metadata['session_key']
        mgmt_port = int(inputs.metadata.get('server_uri').split(":")[-1])
        self.nobody_client = client.connect(token=self.token, port=mgmt_port,
                                            owner='nobody', app=self.APP, autologin=True)
        self.admin_client = client.connect(token=self.token, port=mgmt_port, autologin=True)
        self.ew = ew

        for full_input_name, items in inputs.inputs.items():
            self.full_input_name = full_input_name
            self.input_name = self.full_input_name.split('://')[-1]
            try:
                self.set_authentication_information(items)
                self.download_intervals()
            except Exception as e:
                _LOGGER.error(f'{self.input_name}: {e}')
                continue
        _LOGGER.info(f'Collected a total of {self.total_event_count} events for {self.input_name}')
        _LOGGER.info(f'Completed data collection for {self.input_name} in {str(time() - start_time)} seconds.')

    def download_intervals(self):
        """
        Sequentially initiates downloads of SIEM logs in tranches of one hour at a time.

        :return: None
        :raise ValueError: if the interval is too long, too short, or if the end is before the start
        """
        initial_time_dt = self.retrieve_last_poll_time()
        final_time_dt = _utcnow()

        if final_time_dt <= initial_time_dt:
            raise ValueError(
                f'End of interval must be after start of interval. Interval Range : {initial_time_dt} to {final_time_dt}')
        if (final_time_dt - initial_time_dt) > timedelta(hours=72):
            raise ValueError(f'Interval cannot be greater than 72 hours. Interval Range : {initial_time_dt} to {final_time_dt}')
        hours, seconds = divmod(
            int((final_time_dt - initial_time_dt).total_seconds()), 3600)

        for hour in range(hours):
            start_secs_offset = (3600 * hour) + 1
            start_time_dt = initial_time_dt + timedelta(seconds=start_secs_offset)
            start_time_s = self.fmtdate(start_time_dt)
            end_secs_offset = start_secs_offset + 3599
            end_time_dt = initial_time_dt + timedelta(seconds=end_secs_offset)
            end_time_s = self.fmtdate(end_time_dt)
            self.query_and_save(start_time_s, end_time_s)
        # This is cheating, but if we have exactly one second left over, we'll end up having the same
        # start and end times, which the SIEM service will throw an error on. So, we'll tack on an
        # extra second, why not?
        if seconds > 0:
            if seconds == 1:
                seconds = 2
            start_secs_offset = (3600 * hours) + 1
            start_time_dt = initial_time_dt + timedelta(seconds=start_secs_offset)
            start_time_s = self.fmtdate(start_time_dt)
            end_secs_offset = start_secs_offset + seconds - 1
            end_time_dt = initial_time_dt + timedelta(seconds=end_secs_offset)
            end_time_s = self.fmtdate(end_time_dt)
            # The previous cheat should make this exception unreachable, but I'll leave it here for
            # when we solve the problem which makes the cheat necessary.
            if start_time_s == end_time_s:
                raise ValueError('Cannot fetch data for a single second.')
            self.query_and_save(start_time_s, end_time_s)

    @staticmethod
    def fmtdate(ts):
        """
        Utility method to return UTC timestamps in ISO8601 format.

        :param ts datetime: a ``datetime`` object
        :return str: a string containing the ISO8601 formatted time in UTC
        """
        return ts.strftime('%Y-%m-%dT%H:%M:%SZ')

    # noinspection PyMethodMayBeStatic
    def get_proxies(
        self,
        proxy_protocol=None,
        proxy_server=None,
        proxy_port=None,
        proxy_username=None,
        proxy_password=None
    ):
        """
        Values of proxy parameters are returned.

        :param proxy_protocol: Protocol used when communicating to proxy.
        :param proxy_server: Hostname of the proxy that the Splunk server uses to connect to the internet.
        :param proxy_port: The port number of the proxy.
        :param proxy_username: The username used to connect to the proxy.
        :param proxy_password: The password used to authenticate to the proxy.
        :return:
        """
        auth = ''
        port = ''
        if proxy_server is None:
            return None
        if proxy_username is not None:
            auth = urllib.quote(proxy_username)
        if proxy_password is not None and auth != '':
            auth += ':' + urllib.quote(proxy_password)
        if auth != '':
            auth += '@'
        if proxy_port is not None:
            port = ':' + str(proxy_port)
        return {proxy_protocol: f'{proxy_protocol}://{auth}{proxy_server}{port}'}


if __name__ == '__main__':
    exitcode = PfptSiemScript().run(sys.argv)
    sys.exit(exitcode)
