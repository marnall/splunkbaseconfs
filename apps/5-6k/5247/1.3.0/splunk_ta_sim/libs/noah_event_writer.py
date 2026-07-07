#
# Copyright 2021 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""This module provides two kinds of event writers (ClassicEventWriter,
NoahHECEventWriter) to write Splunk modular input events."""
import os
import logging
import multiprocessing
import sys
import threading
import time
import traceback
from abc import ABCMeta, abstractmethod
from random import randint
from typing import List, Union

current_path = os.path.dirname(__file__)
sys.path.append(os.path.join(current_path, 'external'))

from splunklib import binding

import stack_info
from solnlib import splunk_rest_client as rest_client
from solnlib import utils
from noah_hec_config import NoahHECConfig
from solnlib.splunkenv import get_splunkd_access_info
from solnlib.utils import retry
from solnlib.modular_input.event import HECEvent, XMLEvent
from solnlib.modular_input.event_writer import EventWriter

__all__ = ["NoahHECEventWriter"]


class NoahHECEventWriter(EventWriter):
    """HEC event writer.

    Use Splunk HEC as the output.

    Examples:
        >>> from solnlib.modular_input import noah_event_writer
        >>> ew = noah_event_writer.NoahHECEventWriter(hec_input_name, session_key)
        >>> ew.write_events([event1, event2])
    """

    WRITE_EVENT_RETRIES = 5
    HTTP_INPUT_CONFIG_ENDPOINT = "/servicesNS/nobody/splunk_httpinput/data/inputs/http"
    HTTP_EVENT_COLLECTOR_ENDPOINT = "/services/collector"
    TOO_MANY_REQUESTS = 429  # we exceeded rate limit
    SERVICE_UNAVAILABLE = 503  # remote service is temporary unavailable

    description = "NoahHECEventWriter"

    headers = [("Content-Type", "application/json")]

    def __init__(
        self,
        hec_input_name: str,
        session_key: str,
        scheme: str = None,
        host: str = None,
        port: int = None,
        hec_uri: str = None,
        hec_token: str = None,
        logger: logging.Logger = None,
        **context: dict
    ):
        """Initializes NoahHECEventWriter.

        Arguments:
            hec_input_name: Splunk HEC input name.
            session_key: Splunk access token.
            scheme: (optional) The access scheme, default is None.
            host: (optional) The host name, default is None.
            port: (optional) The port number, default is None.
            hec_uri: (optional) If hec_uri and hec_token are provided, they will
                higher precedence than hec_input_name.
            hec_token: (optional) HEC token.
            logger: Logger object.
            context: Other configurations for Splunk rest client.
        """
        super().__init__()
        self._session_key = session_key
        self._stack_info = stack_info.StackInfo(session_key)
        if logger:
            self.logger = logger
        else:
            self.logger = logging

        if not all([scheme, host, port]):
            scheme, host, port = get_splunkd_access_info()

        if hec_uri and hec_token:
            scheme, host, hec_port = utils.extract_http_scheme_host_port(hec_uri)
        else:
            hec_port, hec_token = self._get_hec_config(
                hec_input_name, session_key, scheme, host, port, **context
            )

        if not context.get("pool_connections"):
            context["pool_connections"] = 10

        if not context.get("pool_maxsize"):
            context["pool_maxsize"] = 10

        self._rest_client = rest_client.SplunkRestClient(
            hec_token, app="-", scheme=scheme, host=host, port=hec_port, **context
        )

    @staticmethod
    def create_from_token(
        hec_uri: str, hec_token: str, **context: dict
    ) -> "NoahHECEventWriter":
        """Given HEC URI and HEC token, create NoahHECEventWriter object. This
        function simplifies the standalone mode NoahHECEventWriter usage (not in a
        modinput).

        Arguments:
            hec_uri: HTTP Event Collector URI, like https://localhost:8088.
            hec_token: HTTP Event Collector token.
            context: Other configurations.

        Returns:
            Created NoahHECEventWriter.
        """

        return NoahHECEventWriter(
            None,
            None,
            None,
            None,
            None,
            hec_uri=hec_uri,
            hec_token=hec_token,
            **context
        )

    @staticmethod
    def create_from_input(
        hec_input_name: str, splunkd_uri: str, session_key: str, **context: dict
    ) -> "NoahHECEventWriter":
        """Given HEC input stanza name, splunkd URI and splunkd session key,
        create NoahHECEventWriter object. HEC URI and token etc will be discovered
        from HEC input stanza. When hitting HEC event limit, the underlying
        code will increase the HEC event limit automatically by calling
        corresponding REST API against splunkd_uri by using session_key.

        Arguments:
            hec_input_name: Splunk HEC input name.
            splunkd_uri: Splunkd URI, like https://localhost:8089
            session_key: Splunkd access token.
            context: Other configurations.

        Returns:
            Created NoahHECEventWriter.
        """

        scheme, host, port = utils.extract_http_scheme_host_port(splunkd_uri)
        return NoahHECEventWriter(
            hec_input_name, session_key, scheme, host, port, **context
        )

    @staticmethod
    def create_from_token_with_session_key(
        splunkd_uri: str,
        session_key: str,
        hec_uri: str,
        hec_token: str,
        **context: dict
    ) -> "NoahHECEventWriter":
        """Given Splunkd URI, Splunkd session key, HEC URI and HEC token,
        create NoahHECEventWriter object. When hitting HEC event limit, the event
        writer will increase the HEC event limit automatically by calling
        corresponding REST API against splunkd_uri by using session_key.

        Arguments:
            splunkd_uri: Splunkd URI, like https://localhost:8089.
            session_key: Splunkd access token.
            hec_uri: Http Event Collector URI, like https://localhost:8088.
            hec_token: Http Event Collector token.
            context: Other configurations.

        Returns:
            Created NoahHECEventWriter.
        """

        scheme, host, port = utils.extract_http_scheme_host_port(splunkd_uri)
        return NoahHECEventWriter(
            None,
            session_key,
            scheme,
            host,
            port,
            hec_uri=hec_uri,
            hec_token=hec_token,
            **context
        )

    @retry(exceptions=[binding.HTTPError])
    def _get_hec_config(
        self, hec_input_name, session_key, scheme, host, port, **context
    ):
        # Classic cloud stack and Noah(Victoria) stack differences:
        #   1. HEC token management app:
        #     - Classic: `splunk_httpinput`
        #     - Noah: `000-self-service` (use wildcard `-` app to create tokens)
        #   2. HEC token creation API header:
        #     - Classic: Splunk Auth
        #     - Noah: Splunk Auth + 'Content-type: application/x-www-form-urlencoded'
        #   3. Global HEC feature flag:
        #     - Classic: apps and addons can enable/disable the feature flag
        #     - Noah: apps and addons are not allowed to control such feature flag
        #   4. HEC event endpoint:
        #     - Classic: use IDM to forward HEC events
        #     - Noah: use HEC Elastic Load Balancer (ELB) to forward HEC events

        # Set HEC token management app & HEC token API headers
        hec_request_headers = None
        hec_token_manage_app = 'splunk_httpinput'
        if self._stack_info.is_noah_stack:
            hec_request_headers = [('Content-Type', 'application/x-www-form-urlencoded')]
            hec_token_manage_app = '-'

        hc = NoahHECConfig(
            session_key, app=hec_token_manage_app, scheme=scheme, host=host, port=port, **context
        )

        # Only enable global HEC for non-Noah stacks
        settings, limits = {}, {}
        if not self._stack_info.is_noah_stack:
            settings = hc.get_settings()
            limits = hc.get_limits()
            if utils.is_true(settings.get("disabled")):
                # Enable HEC input
                self.logger.info("Enabling HEC")
                settings["disabled"] = "0"
                settings["enableSSL"] = context.get("hec_enablessl", "1")
                settings["port"] = context.get("hec_port", "8088")
                hc.update_settings(settings)

        hec_input = hc.get_input(hec_input_name)
        if not hec_input:
            # Create HEC input
            self.logger.info("Create HEC datainput, name=%s", hec_input_name)
            hinput = {
                "index": context.get("index", "main"),
            }

            if context.get("sourcetype"):
                hinput["sourcetype"] = context["sourcetype"]

            if context.get("token"):
                hinput["token"] = context["token"]

            if context.get("source"):
                hinput["source"] = context["source"]

            if context.get("host"):
                hinput["host"] = context["host"]

            hec_input = hc.create_input(hec_input_name, hinput, headers=hec_request_headers)

        HECEvent.max_hec_event_length = int(limits.get("max_content_length", 1000000))

        return settings.get('port', '8088'), hec_input['token']

    def create_event(
        self,
        data: dict,
        time: float = None,
        index: str = None,
        host: str = None,
        source: str = None,
        sourcetype: str = None,
        fields: dict = None,
        stanza: str = None,
        unbroken: bool = False,
        done: bool = False,
    ) -> HECEvent:
        """Create a new HECEvent object.

        Arguments:
            data: Event data.
            time: (optional) Event timestamp, default is None.
            index: (optional) The index event will be written to, default is None.
            host: (optional) Event host, default is None.
            source: (optional) Event source, default is None.
            sourcetype: (optional) Event sourcetype, default is None.
            fields: (optional) Event fields, default is None.
            stanza: (optional) Event stanza name, default is None.
            unbroken: (optional) Event unbroken flag, default is False.
                It is only meaningful when for XMLEvent when using ClassicEventWriter.
            done: (optional) The last unbroken event, default is False.
                It is only meaningful when for XMLEvent when using ClassicEventWriter.

        Returns:
            Created HECEvent.
        """

        return HECEvent(
            data,
            time=time,
            index=index,
            host=host,
            source=source,
            sourcetype=sourcetype,
            fields=fields,
        )

    def write_events(
        self,
        events: List,
        retries: int = WRITE_EVENT_RETRIES,
        event_field: str = "event",
    ):
        """Write events to index in bulk.

        Arguments:
            events: List of events.
            retries: Number of retries for writing events to index.
            event_field: Event field.
        """
        if not events:
            return

        last_ex = None
        for event in HECEvent.format_events(events, event_field):
            for i in range(retries):
                try:
                    # Use HEC ELB for Noah stacks and IDM for non-Noah stacks
                    if self._stack_info.is_noah_stack:
                        logging.debug('class=HECEventWrite action=write_hec_event_by_elb, status=start')
                        self._stack_info.send_hec_events(
                            self._rest_client.token,
                            event.encode("utf-8")
                        )
                    else:
                        logging.debug('class=HECEventWrite action=write_hec_event_by_collector, status=start')
                        self._rest_client.post(
                            self.HTTP_EVENT_COLLECTOR_ENDPOINT,
                            body=event.encode("utf-8"),
                            headers=self.headers,
                        )
                except binding.HTTPError as e:
                    self.logger.warn(
                        "Write events through HEC failed. Status=%s", e.status
                    )
                    last_ex = e
                    if e.status in [self.TOO_MANY_REQUESTS, self.SERVICE_UNAVAILABLE]:
                        # wait time for n retries: 10, 20, 40, 80, 80, 80, 80, ....
                        sleep_time = min(((2 ** (i + 1)) * 5), 80)
                        if i < retries - 1:
                            random_millisecond = randint(0, 1000) / 1000.0
                            time.sleep(sleep_time + random_millisecond)
                    else:
                        raise last_ex
                else:
                    break
            else:
                # When failed after retry, we reraise the exception
                # to exit the function to let client handle this situation
                self.logger.error(
                    "Write events through HEC failed: %s. status=%s",
                    traceback.format_exc(),
                    last_ex.status,
                )
                raise last_ex
