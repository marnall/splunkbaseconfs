# coding=utf-8
#
# collect attributes or events as events in Splunk
# Author: Remi Seguy <remg427@gmail.com>
#
# Copyright: LGPLv3 (https://www.gnu.org/licenses/lgpl-3.0.txt)
# Feel free to use the code, but please share the changes you've made

from __future__ import absolute_import, division, print_function, unicode_literals
import ta_thehive_ce_declare

from collections import OrderedDict
from itertools import chain
import json
import logging
from hive_common import logging_level, prepare_config
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
# from splunklib.searchcommands import splunklib_logger as logger
import sys
from splunklib.six.moves import map
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

__author__ = "Remi Seguy"
__license__ = "LGPLv3"
__version__ = "1.1.4"
__maintainer__ = "Remi Seguy"
__email__ = "remg427@gmail.com"


@Configuration(retainsevents=True, type='events', distributed=False)
class HiveCollectCommand(GeneratingCommand):
    """ get the attributes from a TheHive instance.
    ##Syntax
    .. code-block::
        | mispgetioc hive_instance=<input> last=<int>(d|h|m)
        | mispgetioc hive_instance=<input> event=<id1>(,<id2>,...)
        | mispgetioc hive_instance=<input> date=<<YYYY-MM-DD>
                                           (date_to=<YYYY-MM-DD>)

    """
    # MANDATORY TheHive instance for this search
    hive_instance = Option(
        doc='''
        **Syntax:** **hive_instance=instance_name*
        **Description:** TheHive instance parameters
        as described in lookup/thehive_instance_list.csv.''',
        require=True)
    endpoint = Option(
        doc='''
        **Syntax:** **endpoint=***alert|case*
        **Description:**endpoint of TheHive API''',
        require=False, validate=validators.Match("endpoint", r"^(alert|case)$"))
    objectid = Option(
        doc='''
        **Syntax:** **objectid=***id*
        **Description:**ID.''',
        require=False, validate=validators.Match("objectid", r"^([0-9a-f]|\w{20})+$"))
    range = Option(
        doc='''
        **Syntax:** **range=***all|start_number-end_number*
        **Description:**A range describing the number of rows to be returned.
        for example range=all or range=10-100''',
        require=False, validate=validators.Match("range", r"^(all|\d+\-\d+)$"))
    sort = Option(
        doc='''
        **Syntax:** **sort=***[+field1,-field2,...]*
        **Description:** Comma-seperated list of fields to sort the result with.
         Prefix the field name with `-` for descending order and `+` for ascending order''',
        require=False)

    def log_error(self, msg):
        logging.error(msg)

    def log_info(self, msg):
        logging.info(msg)

    def log_debug(self, msg):
        logging.debug(msg)

    def log_warn(self, msg):
        logging.warning(msg)

    def set_log_level(self):
        logging.root
        loglevel = logging_level('TA_thehive_ce')
        logging.root.setLevel(loglevel)
        logging.error('[CO-101] logging level is set to %s', loglevel)
        logging.error('[CO-102] PYTHON VERSION: ' + sys.version)

    @staticmethod
    def _record(serial_number, time_stamp, host, attributes, attribute_names, encoder):

        raw = encoder.encode(attributes)
        # Formulate record
        fields = dict()
        for f in attribute_names:
            if f in attributes:
                fields[f] = attributes[f]

        if serial_number > 0:
            fields['_serial'] = serial_number
            fields['_time'] = time_stamp
            fields['_raw'] = raw
            fields['host'] = host
            return fields

        record = OrderedDict(chain(
            (('_serial', serial_number), ('_time', time_stamp),
             ('_raw', raw), ('host', host)),
            map(lambda name: (name, fields.get(name, '')), attribute_names)))

        return record

    def displayResponse(results, action, host):

        encoder = json.JSONEncoder(ensure_ascii=False, separators=(',', ':'))
        if action == 'list_alert' or action == 'list_case':
            attribute_names = list()
            serial_number = 0
            for a in results:
                if serial_number == 0:
                    for k in list(a.keys()):
                        attribute_names.append(k)
                if action == 'list_alert':
                    timestamp = int(a['date'] / 1000)
                elif action == 'list_case':
                    timestamp = int(a['startDate'] / 1000)
                yield HiveCollectCommand._record(
                    serial_number, timestamp, host, a, attribute_names, encoder)
                serial_number += 1
                GeneratingCommand.flush
        elif action == 'get_an_alert' or action == 'get_a_case':
            attribute_names = list()
            serial_number = 0
            a = results
            if serial_number == 0:
                for k in list(a.keys()):
                    attribute_names.append(k)
            if action == 'get_an_alert':
                timestamp = int(a['date'] / 1000)
            elif action == 'get_a_case':
                timestamp = int(a['startDate'] / 1000)
            yield HiveCollectCommand._record(
                serial_number, timestamp, host, a, attribute_names, encoder)
            serial_number += 1
            GeneratingCommand.flush

    def generate(self):
        # Phase 1: Preparation
        logging.root
        loglevel = logging_level(self, 'TA_thehive_ce')
        logging.root.setLevel(loglevel)
        self.log_error('[CO-101] logging level is set to {}'.format(loglevel))
        storage = self.service.storage_passwords
        my_args = prepare_config(self, 'TA_thehive_ce', self.hive_instance, storage)
        if my_args is None:
            raise Exception("Sorry, no configuration for hive_instance={}".format(self.hive_instance))
        my_args['host'] = my_args['thehive_url'].replace('https://', '')
        params = {}
        if self.endpoint == 'case':
            my_args['thehive_url'] = my_args['thehive_url'] + '/api/case'
        else:
            self.endpoint = 'alert'
            my_args['thehive_url'] = my_args['thehive_url'] + '/api/alert'
        if self.objectid not in [None, '']:
            my_args['thehive_url'] = my_args['thehive_url'] + '/' + str(self.objectid).strip()
        if self.range not in [None, '']:
            params["range"] = str(self.range)
        else:
            params["range"] = "0-10"
        if self.sort not in [None, '']:
            params["sort"] = str(self.sort).split(',')
        headers = {
            "Authorization": "Bearer {}".format(my_args['thehive_key'])
        }
        r = requests.get(my_args['thehive_url'],
                         headers=headers,
                         params=params,
                         verify=my_args['thehive_verifycert'],
                         cert=my_args['client_cert_full_path'],
                         proxies=my_args['proxies'])
        # check if status is anything other than 200;
        # throw an exception if it is
        r.raise_for_status()
        # response is 200 by this point or we would have thrown an exception
        encoder = json.JSONEncoder(ensure_ascii=False, separators=(',', ':'))
        if isinstance(r.json(), list):
            response = r.json()
        else:
            response = []
            response.append(r.json())
        attribute_names = list()
        serial_number = 0
        for a in response:
            if serial_number == 0:
                for k in list(a.keys()):
                    attribute_names.append(k)
            if self.endpoint == 'alert':
                timestamp = int(a['date'] / 1000)
            elif self.endpoint == 'case':
                timestamp = int(a['startDate'] / 1000)
            yield HiveCollectCommand._record(
                serial_number, timestamp, my_args['host'], a, attribute_names, encoder)
            serial_number += 1
            GeneratingCommand.flush


if __name__ == "__main__":
    # set up custom logger for the app commands
    dispatch(HiveCollectCommand, sys.argv, sys.stdin, sys.stdout, __name__)
