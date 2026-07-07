# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath, join
sys.path.append(dirname(abspath(__file__)))

import collections
import requests
import json
from datetime import datetime, timedelta
import dateutil.parser
import pytz
import time
import validator
import six
if sys.version_info.major == 3:
    from six.moves.configparser import ConfigParser, NoOptionError
else:
    from configparser import ConfigParser, NoOptionError
from splunklib.modularinput import *
from service.app_kvstore_service import KVStoreService
from logger import Logger
from common import Common
from io import open
from token_service import TokenService

session_key = ''
cloudlock_settings = None
cloudlock_index = None
KEY_AND_VALUE_CHANGE = 3
KEY_CHANGE_ONLY = 2
EventIndex = collections.namedtuple('EventIndex', ['datetime', 'offset'])
severity_mapping = {'INFO': 1, 'WARNING': 3, 'ALERT': 5, 'CRITICAL': 10}
mapping_types = {
    KEY_CHANGE_ONLY: lambda data, old_key, new_key: (new_key, data[old_key]),
    KEY_AND_VALUE_CHANGE: lambda data, old_key, new_key, convert: (
        new_key, convert(data[old_key]))
}


def flatten(d, parent_key='', sep='_'):
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
            items.extend(list(flatten(v, new_key, sep=sep).items()))
        else:
            items.append((new_key, v))
    return dict(items)


def transform_dict(mapping, data):
    flat_data = flatten(data, sep='.')
    for mapper in mapping:
        mapper_type = len(mapper)
        extract_fn = mapping_types[mapper_type]
        new_key, value = extract_fn(flat_data, *mapper)
        yield new_key, value


class CLAPIClient(object):
    """
    CloudLock API Client
    """

    def __init__(self, token, base_url):
        self.token = token
        self.base_url = base_url

    @staticmethod
    def to_datetime(value):
        # return datetime.strptime(value[:-6], '%Y-%m-%dT%H:%M:%S.%f')
        ts_tz_aware = dateutil.parser.parse(value)
        utc_ts = ts_tz_aware.astimezone(
            pytz.timezone('UTC')).replace(tzinfo=None)
        return utc_ts

    @staticmethod
    def get_latest_incident(results):
        latest_updated_at = results[-1]['updated_at']
        last_second = CLAPIClient.to_datetime(latest_updated_at)
        offset = len([x for x in results if last_second ==
                      CLAPIClient.to_datetime(x['updated_at'])])
        return EventIndex(latest_updated_at, offset)

    def _request(self, relative_url, params=None, data=None, method='get', verify_ssl=False):
        global session_key
        relative_url = '{0}/{1}'.format(self.base_url, relative_url)
        headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer {}'.format(self.token),
                   'User-Agent': 'CiscoCloudSecurityAppForSplunk/python-requests/3x'}
        response = getattr(requests, method.lower())(relative_url, headers=headers, params=params, data=data)

        Logger().info("Received HTTP Code: " + str(response.status_code))
        if response.status_code == 888:
            msg = "There is a new version of the Cisco Secure Access App for Splunk Application. In order to continue receiving CloudLock information, please upgrade the Application."
            Logger().error(msg)
            endpoint = '/services/messages'
            postArgs = {'name': 'message', 'severity': 'warn', 'value': msg}
            response2, content2 = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=session_key,
                                                            raiseAllErrors=False, postargs=postArgs)
            Logger().error(
                "Disabling 'cloudlock/incidents': will cause a broken pipe - ignore")
            endpoint = '/servicesNS/nobody/cisco-cloud-security/data/inputs/cloudlock/incidents/disable'
            response2, content2 = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=session_key,
                                                            raiseAllErrors=False)
        response.raise_for_status()
        return response.json()

    def get_incidents(self, **payload):
        return self._request('incidents?count_total=false', params=payload)['items']

    def get_incident(self, incident_id, **payload):
        r = self._request('incidents/%s' % incident_id, params=payload)
        incident = r['results'][0]
        return incident

    def get_all_incidents(self, incident_index, stop_date_index=None, limit=100):
        try:
            while True:
                dt_ntz = None
                dt_ntz2 = None
                updated_after = None
                updated_before = None

                if incident_index.datetime:
                    dt = CLAPIClient.to_datetime(incident_index.datetime)
                    dt_ntz = six.text_type(dt.replace(tzinfo=None))
                    updated_after = dt_ntz

                if stop_date_index is not None:
                    if stop_date_index.datetime:
                        dt2 = CLAPIClient.to_datetime(stop_date_index.datetime)
                        dt_ntz2 = six.text_type(dt2.replace(tzinfo=None))
                        updated_before = dt_ntz2

                results = self.get_incidents(updated_after=updated_after,
                                             updated_before=updated_before,
                                             offset=incident_index.offset,
                                             limit=limit,
                                             order='updated_at', count_total='false')
                if not results:
                    Logger().info('CloudLock: No new incidents found')
                    raise StopIteration()

                Logger().info(
                    'CloudLock: {} new incidents found'.format(len(results)))
                incident_index = self.get_latest_incident(results)
                # TODO:: why this time.sleep, which does not make any sense
                time.sleep(10)
                return incident_index, results
        except Exception as error_in_get_all_incidents:
            Logger().error("Exception reported in get_all_incidents: {0}".format(
                error_in_get_all_incidents))


class Recorder(object):
    """
    stores latest polling data. implemented with python config parser.
    """
    config_section = 'CL_POLLING'

    def __init__(self, name):
        self.file = join(Common().ini_path, 'cl_polling_{0}.ini'.format(name))
        self.config = ConfigParser(allow_no_value=True)
        self.config.read(self.file)
        if not self.config.has_section(self.config_section):
            with open(self.file, 'w', encoding="utf-8") as f:
                self.config.add_section(self.config_section)
                self.config.set(self.config_section, 'Emptys', None)
                self.config.write(f)
            self.config.read(self.file)

    def save(self, key, value):
        with open(self.file, 'w', encoding="utf-8") as f:
            self.config.set(self.config_section, str(key), str(value))
            self.config.write(f)

    def get(self, key, is_int=False):
        try:
            func = self.config.getint if is_int else self.config.get
            return func(self.config_section, key)
        except (NoOptionError, ValueError):
            return None

    def get_last_call(self):
        last_call = self.get('last_call')
        last_call = last_call if last_call and last_call != 'None' else None
        last_offset = self.get('last_offset', is_int=True)

        return EventIndex(last_call, last_offset)

    def get_last_call_changed(self):
        last_call_changed = self.get('last_call_changed')
        last_call_changed = last_call_changed if last_call_changed and last_call_changed != 'None' else None
        last_offset_changed = self.get('last_offset_changed', is_int=True)

        return EventIndex(last_call_changed, last_offset_changed)

    def save_last_call(self, event_index):
        self.save('last_call', event_index.datetime)
        self.save('last_offset', event_index.offset)

    def save_last_call_changed(self, event_index):
        self.save('last_call_changed', event_index.datetime)
        self.save('last_offset_changed', event_index.offset)

    def save_main_date(self, main_date):
        self.save('main_date', main_date)


class MyScript(Script):
    def get_scheme(self):
        scheme = Scheme("CASB Incident Extraction")
        scheme.description = "Access CloudLock Incidents"
        scheme.use_external_validation = True
        scheme.use_single_instance = False
        argument = Argument("Log_Level",
                            description="Setting the Log Level",
                            required_on_create=True)
        scheme.add_argument(argument)
        return scheme

    def validate_input(self, validation_definition):
        Log_level = validation_definition.parameters["Log_Level"]
        if not validator.cummulative_validator(Log_level):
            raise Exception('Enter Valid Modular Input Argument')
        if not Log_level:
            raise ValueError("Log Level must not be null.")

    #def event_writer(self, ew, cl_client, recorder, input_name, date1, date2,index):
    def event_writer(self, ew, cl_client, recorder, input_name, date1, date2):
        Logger().info('Incidents being fetched between two dates')
        incidents_from_query = ''
        last_event_date1 = EventIndex(
            str(date1).replace(" ", "T"), 0)  # .encode('utf-8')
        last_event_date2 = EventIndex(
            str(date2).replace(" ", "T"), 0)  # .encode('utf-8')
        Logger().info("EventIndex computation")
        lst_date, incidents_from_query = cl_client.get_all_incidents(
            last_event_date1, last_event_date2)
        Logger().info("lst_date, incidents_from_query")
        event = Event(sourcetype="cisco:cloud_security:cloudlock")
        event.stanza = input_name
        if incidents_from_query:
            for item in incidents_from_query:
                event.data = json.dumps(flatten(item))
                ew.write_event(event)
        else:
            pass
        recorder.save_main_date(date1)

    # def save_last_call(self, recorder, newDate, ew, cl_client, input_name, index,save_main=True):
    def save_last_call(self, recorder, newDate, ew, cl_client, input_name, save_main=True):
        if save_main:
            recorder.save_main_date(newDate)
        Logger().info("newDate received in save_last_call is " + str(newDate).replace(
            " ", "T"))
        newDateEvent = EventIndex(str(newDate).replace(
            " ", "T"), 0)  # .encode('utf-8')
        event = Event(sourcetype="cisco:cloud_security:cloudlock")
        event.stanza = input_name
        lst_date, incidents_from_query = cl_client.get_all_incidents(
            newDateEvent)
        if (incidents_from_query and lst_date) or (incidents_from_query and lst_date):
            for item in incidents_from_query:
                event.data = json.dumps(flatten(item))
                ew.write_event(event)
                recorder.save_last_call(lst_date)
        else:
            recorder.save_last_call(newDate)

    def stream_events(self, inputs, ew):
        global session_key
        try:
            session_token = inputs.metadata["session_key"]
            header = inputs.metadata.get('server_host', [])
            host = header.lower() if header else "localhost"
            global cloudlock_settings
            if cloudlock_settings is None:
                cloudlock_settings = KVStoreService(
                    'cloudlock_settings', session_token)
            cloudlock_settings_data = json.loads(
                cloudlock_settings.query_items('cloudlock_settings', session_token))
            if len(cloudlock_settings_data) == 0:
                raise Exception('No active cloudlock settings')
            # token = cloudlock_settings_data[-1]['token']  # .encode('utf-8')
            url = cloudlock_settings_data[-1]['url']  # .encode('utf-8')
            #index = cloudlock_settings_data[-1]['index']
            st_date = None
            # .encode('utf-8')
            if cloudlock_settings_data[-1]['cloudlock_start_date'] != '':
                # .encode('utf-8')
                st_date = cloudlock_settings_data[-1]['cloudlock_start_date'].split(
                    '/')
            else:
                # .encode('utf-8')
                st_date = cloudlock_settings_data[-1]['cloudlock_start_date']

            '''BELOW IS THE LOGIC FOR TAKING THE INDEX FROM MODULAR INPUT AND STORING IN A KVSTORE'''
            cld_index = list(inputs.inputs.items())[0][1]['index']
            if not validator.cummulative_validator(cld_index):
                raise Exception('cld_index validation failed')
            global cloudlock_index
            if cloudlock_index is None:
                cloudlock_index = KVStoreService('cloudlock_index', session_token)
            cloudlock_index_data = json.loads(cloudlock_index.query_items('cloudlock_index', session_token))
            if len(cloudlock_index_data)==0:
                cloudlock_index.insert_record('cloudlock_index',session_token,{'index':cld_index})
            elif cloudlock_index_data[-1]['index']!=cld_index:
                cloudlock_index.insert_record('cloudlock_index', session_token, {'index': cld_index})

            input_name = list(inputs.inputs.items())[0][0]
            if not validator.cummulative_validator(input_name):
                raise Exception('input_name validation failed')

            payload = TokenService.get_token(session_token, 'cloudlock_settings', host=host)
            if payload['payload']:
                cloudlock_token = payload['payload']['clear_token']
            else:
                raise Exception('Cloudlock Credentials not active')

            cl_client = CLAPIClient(cloudlock_token, url)
            # TODO:: why split here what input naem does not contain '//'
            recorder = Recorder(input_name.split("//")[1])
            theRecord = recorder.get_last_call()
            if theRecord.datetime is None:
                if st_date:
                    y = int(str(st_date[2]))
                    m = int(str(st_date[1]))
                    d = int(str(st_date[0]))
                    newDate = datetime(
                        y, m, d, 0, 0, 0, 182703, tzinfo=pytz.utc)
                    #self.save_last_call(recorder, newDate, ew, cl_client, input_name,index)
                    self.save_last_call(recorder, newDate, ew, cl_client, input_name)
                else:
                    if recorder.get('main_date') is None:
                        newDate = datetime.now() - timedelta(days=7)
                        localise_date = pytz.utc.localize(newDate)
                        #self.save_last_call(recorder, localise_date, ew, cl_client, input_name,index)
                        self.save_last_call(recorder, localise_date, ew, cl_client, input_name)
            else:
                new_st_date = cloudlock_settings_data[-1]['cloudlock_start_date']
                if new_st_date != '':
                    new_st_date = new_st_date.split('/')
                    y = int(str(new_st_date[2]))
                    m = int(str(new_st_date[1]))
                    d = int(str(new_st_date[0]))
                    new_st_date_formatted = datetime(
                        y, m, d, 0, 0, 0, 182703, tzinfo=pytz.utc)
                mn_dt = recorder.get('main_date').split(' ')[0].split('-')
                y1 = int(str(mn_dt[0]))
                m1 = int(str(mn_dt[1]))
                d1 = int(str(mn_dt[2]))
                dateime_mn_dt = datetime(
                    y1, m1, d1, 0, 0, 0, 182703, tzinfo=pytz.utc)

                if new_st_date == '':
                    fetched_date_from_polling = datetime.strptime(str(cl_client.to_datetime(theRecord.datetime)),
                                                                  "%Y-%m-%d %H:%M:%S.%f")  # + timedelta(milliseconds=10)
                    fetched_date_from_pollingDatetime = pytz.utc.localize(
                        fetched_date_from_polling)
                    #self.save_last_call(recorder, fetched_date_from_pollingDatetime, ew, cl_client, input_name, index,False)
                    self.save_last_call(recorder, fetched_date_from_pollingDatetime, ew, cl_client, input_name,False)
                elif dateime_mn_dt != new_st_date_formatted and new_st_date_formatted < dateime_mn_dt:
                    #self.event_writer(ew, cl_client, recorder, input_name, new_st_date_formatted, dateime_mn_dt,index)
                    self.event_writer(ew, cl_client, recorder, input_name, new_st_date_formatted, dateime_mn_dt)
                else:
                    if new_st_date and new_st_date_formatted > dateime_mn_dt:
                        Logger().info(
                            'Incidents already being fetched from given date')
                    fetched_date_from_polling = datetime.strptime(str(cl_client.to_datetime(
                        theRecord.datetime)),  "%Y-%m-%d %H:%M:%S.%f")  # + timedelta(milliseconds=10)
                    fetched_date_from_pollingDatetime = pytz.utc.localize(
                        fetched_date_from_polling)
                    self.save_last_call(recorder, fetched_date_from_pollingDatetime, ew, cl_client, input_name,False)
        except Exception as e:
            Logger().error("MI: cloudlock, Exception : {0}".format(str(e)))

if __name__ == "__main__":
    Logger().info("MI: cloudlock : execution started")
    sys.exit(MyScript().run(sys.argv))
    Logger().info("MI: cloudlock : execution completed")
