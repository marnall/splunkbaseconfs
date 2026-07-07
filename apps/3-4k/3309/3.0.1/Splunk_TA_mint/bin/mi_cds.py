import inspect
import json
import os
import re
import requests
import sys
import time

from splunk.clilib.bundle_paths import make_splunkhome_path
import splunklib.client as client
import mint.mi_base as mi
import splunk.entity as en

import cds_tokens_handler as token_handle
import mint.utils as utils
import splunklib.six as six
logger = utils.logger


SCHEME = """
<scheme>
    <title>Splunk MINT Data Collector</title>
    <description>Connect to Splunk MINT Data Collector and start fetching your mobile data from the cloud.</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <use_single_instance>false</use_single_instance>

    <endpoint>
        <args>
            <arg name="name">
                <title>Input Name</title>
                <description>Splunk MINT Data Collector</description>
            </arg>
            <arg name="polling_interval">
                <title>Polling Interval</title>
                <description>Polling interval in seconds, defaults to 5</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
                <validation>is_pos_int('polling_interval')</validation>
            </arg>
            <arg name="request_limit">
                <title>Request Limit</title>
                <description>Request limit in number of Data Transfer Objects (DTO), defaults to 15000</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
                <validation>is_pos_int('request_limit')</validation>
            </arg>
            <arg name="request_timeout">
                <title>Request Timeout</title>
                <description>Request timeout in seconds, defaults to 30</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
                <validation>is_pos_int('request_timeout')</validation>
            </arg>
            <arg name="backoff_time">
                <title>Backoff Time</title>
                <description>Time in seconds to wait for retry after error or timeout, defaults to 10</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
                <validation>is_pos_int('backoff_time')</validation>
            </arg>
            <arg name="cds_token">
                <title>MINT Data Collector Token</title>
                <description>MINT Data Collector Token</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="https_proxy">
                <title>HTTPS Proxy Address</title>
                <description>HTTPS proxy address to use for communication with the Splunk MINT Data Collector, e.g. http://10.10.1.10:3128 or https://user:pass@10.10.1.10:3128</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="verify_ssl">
                <title>Verify SSL</title>
                <description>Make it true in case of do secure API call. Default value is true.</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="cds_url">
                <title>CDS Url</title>
                <description>CDS endpoint from where all events get collected</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="cloud_install">
                <title>Cloud Install</title>
                <description>Make it true in case of cloud install</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
        </args>
    </endpoint>
</scheme>
"""


def get_chunks(l, n):
    for i in six.moves.range(0, len(l), n):
        yield l[i:i+n]


class Runner(mi.BaseRunner):

    def print_scheme(self):
        six.print_(SCHEME, flush=True)

    def run(self):
        # To begin, has a token been provided? If not, exit this process
        logger.info('Trying token...')
        token = self.config.get("cds_token")
        if token == 'false':
            logger.error("Invalid token: %s" % str(token))
            sys.exit(1)

        # Next, if the token is not masked on disk, mask it.
        try:
            if token != self.MASK:
                logger.info(
                    'Token was not masked...encrypting and masking token now.')
                self.encrypt_token(self.NAME, token, self.sessionKey)
                self.mask_token(self.sessionKey, self.NAME)
            # Then, grab the clear text token.
            token = self.get_clear_token(self.sessionKey, self.NAME)
        except Exception as e:
            logger.error("Error: %s" % str(e))

        self.CLEAR_TOKEN = token

        # Do we have SSL keys locally? If not, obtain them and the CDS endpoint
        cloud_install = bool(self.config.get("cloud_install"))
        https_proxy = self.config.get("https_proxy")
        auth_path = make_splunkhome_path(
            ['etc', 'apps', 'Splunk_TA_mint', 'auth'])
        cert_path = auth_path + os.sep + 'mint.pem'
        key_path = auth_path + os.sep + 'mint.key'
        if not os.path.isfile(cert_path) or not os.path.isfile(key_path):
            endpoint = token_handle.get_cds_and_ssl(
                token, self.userName, self.sessionKey, https_proxy, cloud_install)
        else:
            # Grab CDS endpoint from config if it has already been persisted before
            endpoint = self.config.get("cds_url")

        # Read params from inputs.conf
        request_limit = self.config.get("request_limit")
        request_timeout = int(self.config.get("request_timeout", 30))
        backoff_time = int(self.config.get("backoff_time", 10))
        polling_interval = int(self.config.get("polling_interval", 5))
        event_break_rx = re.compile('\{\^1\^([a-z]+?)\^([0-9]+?)\}')
        verify_ssl = bool(self.config.get("verify_ssl"))

        # Set request params
        data = {}

        headers = {
            "content-type": "application/json",
            "accept-encoding": "gzip"
        }

        req_args = {
            "verify": verify_ssl,
            "stream": False,
            "timeout": request_timeout
        }

        if not request_limit is None:
            data["limit"] = int(request_limit)

        if https_proxy:
            req_args["proxies"] = {"https": https_proxy}

        while True:

            # If Splunk is no longer the parent process, then it has shut down and this input needs to terminate
            if hasattr(os, 'getppid') and os.getppid() == 1:
                logger.warn(
                    "Modular input [%s] is no longer running under Splunk; script will now exit" % self.name)
                self.shutdown()
                sys.exit(2)

            try:
                start_time = time.time()
                # If this installation is on cloud, do not use ssl keys. If it is on-prem instead, then use the ssl keys.
                if cloud_install:
                    data["guid"] = token
                    r = requests.put(endpoint, data=json.dumps(
                        data), headers=headers, **req_args)
                else:
                    r = requests.put(endpoint, data=json.dumps(data), headers=headers,
                                     cert=(auth_path + os.sep + 'mint.pem',
                                           auth_path + os.sep + 'mint.key'),
                                     **req_args)
                r.raise_for_status()
            except requests.exceptions.Timeout as e:
                logger.error("HTTP Request timeout: %s" % str(e))
                time.sleep(backoff_time)
                continue
            except requests.exceptions.HTTPError as e:
                logger.error("HTTP Request error: %s" % str(e))
                time.sleep(backoff_time)
                continue
            except Exception as e:
                logger.error("Exception performing HTTP request: %s" % str(e))
                time.sleep(backoff_time)
                continue

            end_time = time.time()
            duration = (end_time - start_time) * 1000
            size = float(r.headers.get('content-length')) / 1024
            logger.info("Modular input [%s] in progress: phase=fetch ms=%.2f KB=%.3f" %
                        (self.name, duration, size))

            content = r.content.decode('utf-8')
            if content:
                events_num = 0
                events_size = 0
                start_time = time.time()
                data_list = event_break_rx.split(content)[:-1]
                for item in get_chunks(data_list, 3):
                    event = item[0]
                    event_type = item[1]
                    ts = int(item[2])
                    # Determine timestamp unit (s vs ms) given it's not consistent across all MINT SDKs.
                    # The following condition checks if timestamp has 36 bits or more (2^36-1=68719476735),
                    # in which case it is interpreted as ms. This works provided:
                    # - Timestamp in seconds is not more than (2^36-1), i.e. before 08/20/4147 @ 7:32am (UTC)
                    # - Timestamp in milliseconds is not less than (2^36-1), i.e. after 03/06/1972 @ 8:44am (UTC)
                    # And that gives us the (rather large) data time range constraints.
                    if ts > 68719476735:
                        ts = int(ts / 1000)
                    mi.print_xml_stream(ts, 'mint:' + event_type, event)
                    events_num += 1
                    events_size += sys.getsizeof(event)

                end_time = time.time()
                duration = (end_time - start_time) * 1000
                size = float(events_size) / 1024
                logger.info("Modular input [%s] in progress: phase=process ms=%.2f KB=%.3f ev=%d" %
                            (self.name, duration, size, events_num))

            # Sleep for a bit
            try:
                time.sleep(polling_interval)
            except IOError:
                pass  # Exceptions such as KeyboardInterrupt and IOError can be thrown in order to interrupt sleep calls

    # Functions relating to enrypting & decrypting the token are below.
    def encrypt_token(self, username, token, session_key):
        args = {'token': session_key}
        service = client.connect(**args)

        try:
            # If the token already exists, delete it.
            for storage_password in service.storage_passwords:
                if storage_password.username == username:
                    service.storage_passwords.delete(
                        username=storage_password.username)
                    logger.info(
                        'Encrypted token already existed, replacing it now.')
                    break

            # Create the token.
            service.storage_passwords.create(token, username)

        except Exception as e:
            raise Exception(
                "An error occurred updating token. Please ensure your user account has admin_all_objects and/or list_storage_passwords capabilities. Details: %s" % str(e))

    def mask_token(self, session_key, username):
        try:
            args = {'token': session_key}
            service = client.connect(**args)
            kind = "mi_cds"
            input_name = "default"
            item = service.inputs.__getitem__((input_name, kind))

            # Refresh cds_token field in the [mi_cds://default] stanza in inputs.conf
            logger.info('Masking token on disk...')

            kwargs = {
                "cds_token": self.MASK
            }
            item.update(**kwargs).refresh()

        except Exception as e:
            raise Exception("Error updating inputs.conf: %s" % str(e))

    def get_clear_token(self, session_key, username):
        args = {'token': session_key}
        service = client.connect(**args)

        # Retrieve the token from the storage/passwords endpoint
        for storage_password in service.storage_passwords:
            if storage_password.username == username:
                return storage_password.content.clear_password


if __name__ == '__main__':
    mi.run(Runner())
    sys.exit(0)
