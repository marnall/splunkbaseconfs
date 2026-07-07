""" Copyright © 2019-2020, EPAM Systems, all rights reserved. """

""" This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/. """

import json
import sys
import logging
import six
import os

APP_NAME = "sap_solman_app"

sys.path.insert(
    0,
    "{}/etc/apps/{}/lib/".format(
        os.environ.get("SPLUNK_HOME", "/opt/splunk"), APP_NAME
    ),
)


# import splunklib.client as splunk_client
from splunk import rest
from splunklib.binding import HTTPError
from  urllib.parse import urlparse

import epmspln_utils.log2 as log_utils
import rest_utils

INPUT_PATH = "data/inputs"
MI_KIND = "sap_solman_mi"
MI_CONFIG_STANZA = "main_input"
HTTP_ERROR_STATUS = 500
CONF_RELOAD_URL = "apps/local/_reload"
CONF_NAME = "app"
CONF_STANZA_NAME = "install"

log_utils.init_modular_input_logging()
logger = logging.getLogger("setup_handler")


def create_mi(service_inputs, mi_name, mi_kind, data):
    service_inputs.create(mi_name, mi_kind, **data)


def update_mi(service_inputs, data):
    service_inputs.list(MI_KIND)[0].update(**data)


def parse_error_message(message, inputs_params):
    if inputs_params.get(six.u("use_new_server_version")):
        exception, status_code = message.split()[-5:-3]
    else:
        exception, status_code = message.split()[-3:-1]

    return {"original_exception": exception, "status_code": status_code}


def check_secure_connection(inputs):
    url_base = urlparse(inputs['services_base'])
    
    if url_base.scheme != 'https':
        raise Exception('Required https for base connection')


class Setup(rest.BaseRestHandler):
    def handle_POST(self):
        service = rest_utils.get_client(self, APP_NAME)
        inputs_data = json.loads(self.request["payload"])

        try:
            check_secure_connection(inputs_data)
            create_mi(service.inputs, MI_CONFIG_STANZA, MI_KIND, inputs_data)
            service.confs[CONF_NAME][CONF_STANZA_NAME].update(is_configured=1)
            service.get(CONF_RELOAD_URL)
            status_message = "Done"
            actual_exception = None

        except HTTPError as e:
            logger.exception(e)
            actual_exception = parse_error_message(six.text_type(e), inputs_data)
            self.response.setStatus(HTTP_ERROR_STATUS)
            status_message = six.text_type(e)

        self.response.write(
            json.dumps(
                {"message": status_message, "actual_exception": actual_exception}
            )
        )

    def handle_GET(self):
        service_inputs = rest_utils.get_client(self, APP_NAME).inputs.list(MI_KIND)
        logger.info("Getting inputs")

        if service_inputs:
            data = service_inputs[0].content()
        else:
            data = {}

        self.response.write(json.dumps(data))

    def handle_PUT(self):
        service_inputs = rest_utils.get_client(self, APP_NAME).inputs
        inputs_data = json.loads(self.request["payload"])

        try:
            check_secure_connection(inputs_data)
            update_mi(service_inputs, inputs_data)
            logger.info("Inputs updated")
            status_message = "Done"
            actual_exception = None

        except HTTPError as e:
            logger.exception(e)
            actual_exception = parse_error_message(six.text_type(e), inputs_data)
            self.response.setStatus(HTTP_ERROR_STATUS)
            status_message = six.text_type(e)

        self.response.write(
            json.dumps(
                {"message": status_message, "actual_exception": actual_exception}
            )
        )
