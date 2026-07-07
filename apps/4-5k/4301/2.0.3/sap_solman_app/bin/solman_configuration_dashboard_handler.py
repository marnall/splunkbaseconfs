""" Copyright © 2019-2020, EPAM Systems, all rights reserved. """

""" This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/. """

import json
import os
import sys
import logging

APP_NAME = "sap_solman_app"

sys.path.insert(
    0,
    "{}/etc/apps/{}/lib/".format(
        os.environ.get("SPLUNK_HOME", "/opt/splunk"), APP_NAME
    ),
)

import six.moves.urllib.parse
import splunklib.client as splunk_client
import splunklib.results as results
from splunklib.binding import HTTPError

import epmspln_utils.checkpoint as checkpoint_utils
import epmspln_utils.log2 as log_utils
import epmspln_utils.password as password_utils
import rest_utils
from splunk import rest


import common
addon_path = common.get_addon_path()
enterprise_libs_folder = os.path.join(addon_path, 'lib', 'enterprise_libs')
if os.path.isdir(enterprise_libs_folder):
    import enterprise_libs.limitations as limitations
else: 
    import community_libs.limitations as limitations

METRICS_COLLECTION = "odata_metrics"

CHECKPOINT_FORMAT = "_v2"

HTTP_ERROR_STATUS = 500

log_utils.init_modular_input_logging()
logger = logging.getLogger("solman_configuration_dashboard_handler")


def get_kv_entry(collection, query):
    """Get entry from KV store

    :param collection: collection object in KV store
    :param query: dict from which query formulated
    :returns: object or None

    """

    items = collection.data.query(query=json.dumps(query))
    if items:
        return items[0]
    else:
        return None


def insert_kv_entry(collection, data):
    collection.data.insert(json.dumps(data))


def update_kv_entry(collection, key, data):
    collection.data.update(key, data)


def bulk_update_kv(collection, data):
    for el in data:
        update_kv_entry(collection, el["_key"], json.dumps(el))


def remove_kv_entry(collection, key):
    try:
        collection.data.delete_by_id(key)
    except HTTPError as ex:
        if ex.status == 404:
            logger.error("Trying to remove not existing system")
        raise ex

class Filter(rest.BaseRestHandler):
    def handle_POST(self):
        try:
            service = rest_utils.get_client(self, APP_NAME)
            payload = json.loads(self.request["payload"])
            
            inputs_conf_results = service.jobs.oneshot(
                "| rest /servicesNS/-/-/configs/conf-inputs "
                "| search title=sap_solman_mi* disabled=0"
            )
            inputs_conf_reader = results.ResultsReader(inputs_conf_results)
            # TODO: handle multiple modular input setups
            input_item = six.next(iter(inputs_conf_reader))
            
            if "main_input" not in input_item["title"]:
                input_item = six.next(iter(inputs_conf_reader))
            with open(
                checkpoint_utils.get_filename("sap_solman_mi", input_item["title"])
                + CHECKPOINT_FORMAT
            ) as c_file:
                checkpoint_data = json.load(c_file)
            metrics = service.kvstore[METRICS_COLLECTION]
            
            if limitations.exceeds_limits(metrics, payload):
                raise Exception(f"The number of tracked systems is limited to {limitations.SYSTEMS_LIMIT}, and the number of tracked metrics - to {limitations.METRICS_LIMIT} for the Community version of this app." + limitations.SUPPORT_MESSAGE)
            
            bulk_update_kv(metrics, payload)
            self.response.write("success")

        except Exception as e:
            logger.exception(e)
            self.response.setStatus(HTTP_ERROR_STATUS)
            messages = [{"text": six.text_type(e)}]
            self.response.write(
                json.dumps(
                {
                    "status": "error", 
                    "messages": messages
                }
                )
            )