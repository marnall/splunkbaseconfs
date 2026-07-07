import bamboo_declare
from bamboo_service import BambooService
import os
import sys
import time
from time import gmtime, strftime
from dateutil.parser import parse
import datetime
import base64
import logging
import json
import urllib
import requests
import traceback
import mako.template

import modinput_wrapper.base_modinput
from datetime import datetime
from dateutil import parser
from dateutil.tz import tzlocal

from splunklib import modularinput as smi

import common
from common import logger

SYNC_CHECKPOINT_DATE = 'bamboo_last_synced'
SYNC_CHECKPOINT_INDEX = 'bamboo_sync_start_at'
SYNC_CHECKPOINT_STATUS = 'bamboo_sync_status'
SYNC_STATUS = {
    'IN PROGRESS': 'IN PROGRESS',
    'DONE': 'DONE'
}
SYNC_EVENTS_PER_PAGE = 1000

log = logging.getLogger(__name__)

BAMBOO_BUILD_SERVICE = '/rest/api/latest/result'
BAMBOO_RESULT_SERVICE = '/rest/api/latest/result'
BAMBOO_PLAN_SERVICE = '/rest/api/latest/plan'

def _get_url(endpoint):
    return endpoint+'.json' + "?max-results="+str(SYNC_EVENTS_PER_PAGE)


def translate_arg(temp_string, param_dict):
    t = mako.template.Template(temp_string)
    return t.render(**param_dict)


class BambooModInput(modinput_wrapper.base_modinput.SingleInstanceModInput):
    def __init__(self):
        super(BambooModInput, self).__init__("libs", "bamboo")

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = smi.Scheme("bamboo")
        scheme.title = ("bamboo")
        scheme.description = ("")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        desc_server = "Bamboo server"
        scheme.add_argument(smi.Argument("server", title="server",
                                         description=desc_server,
                                         required_on_create=True))
        desc_username = 'User name used to query Bamboo REST API'
        scheme.add_argument(smi.Argument("username", title="username",
                                         description=desc_username,
                                         required_on_create=True))
        desc_password = 'Password used to query Bamboo REST API'
        scheme.add_argument(smi.Argument("password", title="password",
                                         description=desc_password,
                                         required_on_create=True))
        desc_protocol = 'REST API protocol, e.g., https or http'
        scheme.add_argument(smi.Argument("protocol", title="protocol",
                                         description=desc_protocol,
                                         required_on_create=True))
        desc_port = 'REST API port, e.g., 443'
        scheme.add_argument(smi.Argument("port", title="port",
                                         description=desc_port,
                                         required_on_create=True))
        return scheme

    def get_app_name(self):
        return "ta-bamboo"

    def sync(self, ew):
        """
        Sync all Bamboo build data with indexer. Builds are fetched by
        API call, by default 1000 tickets per request, order by
        created time in ascending order. Sync progress is written
        to checkpoint
        :param ew: EventWriter object
        """
        log.info("Entering sync ...")
        current_checkpoint = datetime.now()
        # update last checkpoint to now
        self.save_check_point(SYNC_CHECKPOINT_DATE, datetime.strftime(
            current_checkpoint, '%Y-%m-%d %H:%M:%S'))
        self.save_check_point(SYNC_CHECKPOINT_STATUS,
                              SYNC_STATUS['IN PROGRESS'])
        start_at = self.get_check_point(SYNC_CHECKPOINT_INDEX)

        if start_at is None:
            start_at = 0

        while True:
            log.info("While loop in sync")
            data = {}
            # Sync data from oldest one
            data['max-results'] = str(SYNC_EVENTS_PER_PAGE)
            data['start-index'] = str(start_at)
            plans_data = self.get_bamboo_plans(data)

            if len(plans_data) > 0:
                for plans_data_entry in plans_data:
                    data_obj = json.loads(plans_data_entry)
                    plans=data_obj['plan']
                    log.info("Loaded " + str(len(plans)) + " plans!")
                    for plan in plans:
                        plan_key = plan['key']
                        log.info("Plan key " + str(plan_key))
                        builds = self.get_builds(plan_key)
                        for build in builds:
                            ew.write_event(self.create_event(build))

            if len(plans) < SYNC_EVENTS_PER_PAGE:
                # reach all events
                log.info("Reached all " + str(len(plans)) + " events")
                self.delete_check_point(SYNC_CHECKPOINT_INDEX)
                self.save_check_point(
                    SYNC_CHECKPOINT_STATUS, SYNC_STATUS['DONE'])
                break
            else:
                start_at += SYNC_EVENTS_PER_PAGE
                self.save_check_point(SYNC_CHECKPOINT_INDEX, start_at)

    def get_bamboo_plans(self, body_data):
        """
        Making POST query to get Bamboo builds
        :param body_data: POST's body,
        :return: List of raw Bamboo build data
        """
        log.info("Getting bamboo events ...")
        header = {}
        header['Content-Type'] = 'application/json'
        header['Authorization'] = 'Basic ' + \
            base64.b64encode(self.username + ":" + self.password)
        # parametrize the url and related arguments
        url_encoded_items = {k: urllib.quote(
            v) for k, v in self.input_items.iteritems()}

        temp = mako.template.Template(self.post_url)
        translated_url = temp.render(**url_encoded_items)
        # parametrize the data and the header
        translated_data = {translate_arg(k, self.input_items): translate_arg(
            v, self.input_items) for k, v in body_data.iteritems()}
        translated_header = {translate_arg(k, self.input_items): translate_arg(
            v, self.input_items) for k, v in header.iteritems()}

        # translated_data should support nesting json
        parsed_data = {}
        for k, v in translated_data.iteritems():
            try:
                parsed_data[k] = json.loads(v)
            except:
                parsed_data[k] = v
        translated_data = parsed_data
        log.info("Translated data:" + str(translated_data))
        log.info("Translated header:" + str(translated_header))
        try:
            args = {}
            if translated_data:
                 args['data'] = json.dumps(translated_data)
            if translated_header:
                args['headers'] = translated_header
            log.info("Posting to " + translated_url)
            resp = requests.get(translated_url, **args)

            resp.raise_for_status()
            try:
                resp_obj = json.loads(resp.text)['plans']
                if isinstance(resp_obj, list):
                    return list(map((lambda x: json.dumps(x)), resp_obj))
                else:
                    return [json.dumps(resp_obj)]
            except ValueError as e:
                logger.error('Failed on write event: %s.',
                             traceback.format_exc(e))

        except Exception as e:
            logger.error('Failed on request: %s.',
                         traceback.format_exc(e))
            raise e

        return []

    def extract(self, inputs):
        """
        Extract data from provided inputs
        :param inputs: inputs_items object
        """
        log.info("Inside extract ...")
        self.input_name, self.input_items = inputs.inputs.popitem()
        self.server = self.input_items['server']
        self.protocol = self.input_items['protocol']
        self.port = self.input_items['port']
        self.username = self.input_items['username']
        self.password = self.input_items['password']
        self.bamboo_service = BambooService(self.username, self.password, self.server, self.port, self.protocol)
        #self.jql = self.input_items['jql']
        post_endpoint = '%s://%s:%s/rest/api/latest/plan' % (
            self.protocol, self.server, self.port)
        self.post_url = _get_url(post_endpoint)
        log.info("PostURL: " + self.post_url)
        self.output_index = self.input_items['index'] or 'main'
        self.output_sourcetype = self.input_items['sourcetype'] or 'bamboo'

    def create_event(self, build):
        """
        Create an event object from raw event data
        :param data: raw event data
        :return: Event object
        """
        # override time
        log.info("Inside create_event")
        log.info("Build data:" + str(build))
        detailed_results = self.get_results(build['buildResultKey'])
        log.info("Detailed result:" +str(detailed_results) )
        updated = detailed_results['buildCompletedDate']
        indexed_date = datetime.now(tzlocal())
        min_date = parser.parse("1970-01-01T00:00:00.000-0000")

        if updated is not None:
            indexed_date = parser.parse(updated)

        return self.new_event(
            index=self.output_index,
            sourcetype=self.output_sourcetype,
            source=self.input_name,
            host=self.server,
            time="%.3f" % (indexed_date - min_date).total_seconds(),
            data=json.dumps(detailed_results))

    def validate_input(self, definition):
        """overloaded splunklib modularinput method"""
        pass

    def collect_events(self, inputs, ew):
        """
        Main loop function, run every "interval" seconds,
        fetch new updated tickets.
        Checkpoint is datetime of last query
        :param inputs: Inputs object
        :param ew: Event objects
        """

        log.info("Inside collect_event")
        self.extract(inputs)

        sync_status = self.get_check_point(SYNC_CHECKPOINT_STATUS)
        if sync_status is None or sync_status == SYNC_STATUS['IN PROGRESS']:
            # never sync or last sync is in progress
            self.sync(ew)
            return

        last_synced = self.get_check_point(SYNC_CHECKPOINT_DATE)
        current_checkpoint = datetime.now()
        # checkpoint is saved as string, convert it to object with offset
        last_synced_tz = last_synced + strftime("%z", gmtime())
        last_synced_obj = parse(last_synced_tz)
        start_at = self.get_check_point(SYNC_CHECKPOINT_INDEX)
        if start_at is None:
            start_at = 0
        data =  {}
        data['max-results'] = str(SYNC_EVENTS_PER_PAGE)
        data['start-index'] = str(start_at)
        plans_data = self.get_bamboo_plans(data)

        if len(plans_data) > 0:
            for plans_data_entry in plans_data:
                data_obj = json.loads(plans_data_entry)
                plans=data_obj['plan']
                log.info("Loaded " + str(len(plans)) + " plans!")
                for plan in plans:
                    plan_key = plan['key']
                    log.info("Plan key " + str(plan_key))
                    builds = self.get_builds(plan_key)
                    for build in builds:
                        log.info("Looking at build data")
                        detailed_results = self.get_results(build['buildResultKey'])
                        log.info("Looking at detailed result")
                        buildCompleteDateValue = detailed_results['buildCompletedDate']
                        buildCompleteDate = parser.parse(buildCompleteDateValue)
                        log.info("Build complete date:" + buildCompleteDateValue + " Last sync date:" + last_synced_tz)
                        # only write event if there is an udpate
                        if(buildCompleteDate > last_synced_obj):
                            log.info("Writing event after checking the build complete date.")
                            ew.write_event(self.create_event(build))
                        else:
                            log.info("Not writing this event because it is already indexed")

        # update checkpoint to now
        self.save_check_point(SYNC_CHECKPOINT_DATE, datetime.strftime(
            current_checkpoint, '%Y-%m-%d %H:%M:%S'))
        #log.info("ADDED %d events", len(events))


    def validate_input(self, definition):
        """overloaded splunklib modularinput method"""
        pass

    def get_builds(self,plan_key=None, expand=False):
        log.info("Inside get_builds")
        path = BAMBOO_BUILD_SERVICE
        # Get url
        if plan_key:
            # All builds for one plan
            url = _get_url('{}/{}'.format(path, plan_key))
        else:
            # Latest build for all plans
            url = _get_url(path)

        # Get page, update page and size
        builds_raw = self.bamboo_service.request(url)
        builds= builds_raw['results']['result']

        return builds

    def get_results(self,buildresultkey=None):
        url = _get_url("{}/{}".format((BAMBOO_RESULT_SERVICE), buildresultkey))
        results = self.bamboo_service.request(url)
        return results

if __name__ == "__main__":
    exitcode = BambooModInput().run(sys.argv)
    sys.exit(exitcode)
    pass