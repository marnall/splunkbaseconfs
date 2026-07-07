import jira_declare
import sys
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

from common import logger

SYNC_CHECKPOINT_DATE = 'jira_last_synced'
SYNC_CHECKPOINT_INDEX = 'jira_sync_start_at'
SYNC_CHECKPOINT_STATUS = 'jira_sync_status'
SYNC_STATUS = {
    'IN PROGRESS': 'IN PROGRESS',
    'DONE': 'DONE'
}
SYNC_EVENTS_PER_PAGE = 1000

log = logging.getLogger(__name__)


def translate_arg(temp_string, param_dict):
    t = mako.template.Template(temp_string)
    return t.render(**param_dict)


class JIRAModInput(modinput_wrapper.base_modinput.SingleInstanceModInput):

    def __init__(self):
        super(JIRAModInput, self).__init__("libs", "jira")

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = smi.Scheme("jira")
        scheme.title = ("jira")
        scheme.description = ("")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        desc_server = "JIRA server"
        scheme.add_argument(smi.Argument("server", title="server",
                                         description=desc_server,
                                         required_on_create=True))
        desc_username = 'username is used to query REST API'
        scheme.add_argument(smi.Argument("username", title="username",
                                         description=desc_username,
                                         required_on_create=True))
        desc_password = 'password is used to query REST API'
        scheme.add_argument(smi.Argument("password", title="password",
                                         description=desc_password,
                                         required_on_create=True))
        desc_protocol = 'REST API protocol, e.g., https'
        scheme.add_argument(smi.Argument("protocol", title="protocol",
                                         description=desc_protocol,
                                         required_on_create=True))
        desc_port = 'REST API port, e.g., 443'
        scheme.add_argument(smi.Argument("port", title="port",
                                         description=desc_port,
                                         required_on_create=True))
        desc_jql = "JQL query to filter tickets which are indexed, " \
                   "e.g., issueType in (epic, story)"
        scheme.add_argument(smi.Argument("jql", title="jql",
                                         description=desc_jql,
                                         required_on_create=True))
        desc_fields = "Fields to be indexed, a comma separated field list" \
            "e.g., key, summary, project, updated"
        scheme.add_argument(smi.Argument("fields", title="fields",
                                         description=desc_fields,
                                         required_on_create=True))
        return scheme

    def get_app_name(self):
        return "jira"

    def sync(self, ew):
        """
        Sync all JIRA ticket data with indexer. Tickets are fetched by
        JQL query, by default 1000 tickets per request, order by
        created time in ascending order. Sync progress is written
        to checkpoint
        :param ew: EventWriter object
        """
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
            data = {}
            # Sync data from oldest one
            data['jql'] = "%s ORDER BY createdDate asc" % self.jql
            data['maxResults'] = str(SYNC_EVENTS_PER_PAGE)
            data['startAt'] = str(start_at)

            events = self.get_jira_events(data)
            if len(events) > 0:
                map((lambda e: ew.write_event(self.create_event(e))), events)

            if len(events) < SYNC_EVENTS_PER_PAGE:
                # reach all events
                self.delete_check_point(SYNC_CHECKPOINT_INDEX)
                self.save_check_point(
                    SYNC_CHECKPOINT_STATUS, SYNC_STATUS['DONE'])
                break
            else:
                start_at += SYNC_EVENTS_PER_PAGE
                self.save_check_point(SYNC_CHECKPOINT_INDEX, start_at)

    def get_jira_events(self, body_data):
        """
        Making POST query to get JIRA tickets
        :param body_data: POST's body,
        e.g., {"jql":"project = QA","startAt":0}
        :return: List of raw JIRA ticket data
        """
        header = {}
        header['Content-Type'] = 'application/json'
        header['Authorization'] = 'Basic ' + \
            base64.b64encode(self.username + ":" + self.password)

        # get history for startWorkDate value
        body_data['expand'] = '[\"changelog\"]'
        if self.fields != '*':
            fields_list = self.fields.split(', ')
            fields = '[' + ', '.join('"' + f + '"' for f in fields_list) + ']'
            body_data['fields'] = fields

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
        try:
            args = {}
            if translated_data:
                args['data'] = json.dumps(translated_data)
            if translated_header:
                args['headers'] = translated_header
            resp = requests.post(translated_url, **args)

            resp.raise_for_status()
            try:
                resp_obj = json.loads(resp.text)['issues']
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

    def get_start_work_date(self, event):
        """
        Get datetime when developer starts working on ticket
        :param event: event data
        :return: datatime string or None
        """
        data_obj = json.loads(event)
        start_work = None
        try:
            histories = data_obj['changelog']['histories']
            for h in histories:
                items = h['items']
                found = False
                for i in items:
                    if i['toString'] == 'In Progress':
                        found = True
                        break
                if found:
                    start_work = h['created']
                    break
        except ValueError as e:
            log.error('Failed on getting startWorkDate: %s.',
                      traceback.format_exc(e))

        return start_work

    def get_close_ticket_date(self, event):
        """
        Get datetime when tester closes ticket
        :param event: event data
        :return: datatime string or None
        """
        data_obj = json.loads(event)
        close_time = None
        try:
            histories = data_obj['changelog']['histories']
            for h in histories:
                items = h['items']
                found = False
                for i in items:
                    if i['toString'] == 'Closed' or i['toString'] == 'Done':
                        found = True
                if found:
                    close_time = h['created']
        except ValueError as e:
            log.error('Failed on getting close ticket date: %s.',
                      traceback.format_exc(e))

        return close_time

    def extract(self, inputs):
        """
        Extract data from provided inputs
        :param inputs: inputs_items object
        """
        self.input_name, self.input_items = inputs.inputs.popitem()
        # TAG-12110 TODO: Encrypt password with storage/passwords endpoint
        self.server = self.input_items['server']
        self.protocol = self.input_items['protocol']
        self.port = self.input_items['port']
        self.username = self.input_items['username']
        self.password = self.input_items['password']
        self.jql = self.input_items['jql']
        self.fields = self.input_items['fields']
        self.post_url = '%s://%s:%s/rest/api/2/search' % (
            self.protocol, self.server, self.port)
        self.output_index = self.input_items['index'] or 'main'
        self.output_sourcetype = self.input_items['sourcetype'] or 'jira'

    def create_event(self, data):
        """
        Create an event object from raw event data
        :param data: raw event data
        :return: Event object
        """
        # override time
        data_obj = json.loads(data)
        updated = data_obj['fields']['updated']
        indexed_date = datetime.now(tzlocal())
        min_date = parser.parse("1970-01-01T00:00:00.000-0000")

        if updated is not None:
            indexed_date = parser.parse(updated)

        # add time_start_work field
        start_work = self.get_start_work_date(data)
        if start_work is not None:
            data_obj['time_started_work'] = start_work
        close_date = self.get_close_ticket_date(data)
        if close_date is not None:
            data_obj['time_closed'] = close_date

        # remove change log, it's unnecessary
        del data_obj['changelog']
        data = json.dumps(data_obj)

        return self.new_event(
            index=self.output_index,
            sourcetype=self.output_sourcetype,
            source=self.input_name,
            host=self.server,
            time="%.3f" % (indexed_date - min_date).total_seconds(),
            data=data)

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
        self.extract(inputs)

        sync_status = self.get_check_point(SYNC_CHECKPOINT_STATUS)
        if sync_status is None or sync_status == SYNC_STATUS['IN PROGRESS']:
            # never sync or last sync is in progress
            self.sync(ew)
            return

        last_synced = self.get_check_point(SYNC_CHECKPOINT_DATE)
        current_checkpoint = datetime.now()
        # checkpoint is saved as string, convert it to object
        last_synced_obj = datetime.strptime(last_synced, '%Y-%m-%d %H:%M:%S')
        delta = current_checkpoint - last_synced_obj
        # timedelta object has only days, seconds, microseconds
        delta_in_min = delta.days * 60 * 24 + delta.seconds / 60
        data = {}
        # query issues in last delta_in_min minutes
        data['jql'] = '%s and updated > -%dm' % (self.jql, delta_in_min)

        events = self.get_jira_events(data)

        if len(events) > 0:
            map((lambda e: ew.write_event(self.create_event(e))), events)

        # update checkpoint to now
        self.save_check_point(SYNC_CHECKPOINT_DATE, datetime.strftime(
            current_checkpoint, '%Y-%m-%d %H:%M:%S'))
        log.info("ADDED %d events", len(events))


if __name__ == "__main__":
    exitcode = JIRAModInput().run(sys.argv)
    sys.exit(exitcode)
    pass
