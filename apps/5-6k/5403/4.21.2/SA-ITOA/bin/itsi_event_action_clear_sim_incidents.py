# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.
import sys
import json
import requests

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path
import itsi_py3

from SA_ITOA_app_common.splunklib.client import Service
from ITOA.itoa_config import get_supported_objects
from ITOA.setup_logging import getLogger
from ITOA.event_management.notable_event_utils import Audit

from itsi.event_management.sdk.grouping import EventGroup
from itsi.event_management.sdk.custom_group_action_base import CustomGroupActionBase

from integrations.commons.splunk.server import Splunk
from integrations.commons.itsi.utils import get_notable_events, get_group_time_range


class SIMConnection:
    # Constants
    SPLUNK_KV_STORE_SIM_CONFIG_COLLECTION_NAME = 'sim_api_config'
    SPLUNK_PASSWORDS_STORAGE_SIM_API_TOKEN_REALM = 'splunk_ta_sim'
    SPLUNK_SIM_CONFIG_API_URL_KEY_OLD = 'api_url'
    SPLUNK_PASSWORDS_STORAGE_SIM_API_TOKEN_USER_NAME_OLD = 'access_token'
    SPLUNK_PASSWORDS_STORAGE_SIM_API_TOKEN_REALM_OLD = 'sim_search_command'
    SPLUNK_SIM_API_TEST_CONNECTION_URL = 'https://api.{0}.signalfx.com/v2/organization'
    SPLUNK_SIM_API_URL = 'https://api.{0}.signalfx.com'
    SPLUNK_SIM_STREAM_URL = 'https://stream.{0}.signalfx.com'

    def __init__(self, service, org_id=None):
        self.org_id = org_id
        self.is_default = not org_id
        self.org_name = None
        self.realm = None
        self.access_token = None
        self.__load_sim_connection(service)

    def __load_sim_connection(self, service):
        is_old_sim_api_config = False
        sim_api_url = None
        sim_api_config_record = None
        # Get get SIM API connection details from KV store
        try:
            sim_api_config_collection = service.kvstore.get(self.SPLUNK_KV_STORE_SIM_CONFIG_COLLECTION_NAME, None)
            if sim_api_config_collection is not None:
                collection = service.kvstore[self.SPLUNK_KV_STORE_SIM_CONFIG_COLLECTION_NAME]
                sim_api_config_records = collection.data.query()
                for conf_record in sim_api_config_records:
                    if self.is_default and conf_record.get('default', False):
                        sim_api_config_record = conf_record
                        break
                    elif self.org_id is not None and self.org_id == conf_record.get('org_id', None):
                        sim_api_config_record = conf_record
                        break
                    # Backward compatability logic. Old Single Account SIM connection format.
                    elif conf_record.get(self.SPLUNK_SIM_CONFIG_API_URL_KEY_OLD, None) is not None:
                        sim_api_config_record = conf_record
                        sim_api_url = conf_record.get(self.SPLUNK_SIM_CONFIG_API_URL_KEY_OLD, None)
                        is_old_sim_api_config = True
                        self.is_default = True
                        break
        except Exception as e:
            # self.caller.logger.error('status=error, action=get_sim_connection, error_msg=' + str(e), exc_info=True)
            raise e

        if sim_api_config_record is None:
            # self.caller.logger.error('status=error, action=get_sim_connection, error_msg=Splunk Infrastructure Monitoring API Connection not configured.')
            raise Exception('Infrastructure Monitoring API connection not configured.')

        if not is_old_sim_api_config:
            # Multi Account SIM connection Data collection disabled
            if not bool(conf_record.get('enable', True)):
                raise Exception('Data collection is disabled on this Infrastructure Monitoring account.')

            # Multi Account SIM connection format
            self.org_id = conf_record.get('org_id', None)
            self.is_default = conf_record.get('default', False)
            self.org_name = conf_record.get('org_name', None)
            self.realm = conf_record.get('realm', None)

            if self.org_id is None:
                # self.caller.logger.error('status=error, action=get_sim_connection, error_msg=org_id is not found in Splunk Infrastructure Monitoring API Connection.')
                raise Exception('Organization ID not found in Infrastructure Monitoring API connection.')

            if self.realm is None:
                # self.caller.logger.error('status=error, action=get_sim_connection, error_msg=realm is not found in Splunk Infrastructure Monitoring API Connection.')
                raise Exception('Realm not found in Infrastructure Monitoring API connection.')

            # Get get SIM API connection AccessToken from KV store
            try:
                for credential in service.storage_passwords:
                    if credential.content.get('realm', None) == self.SPLUNK_PASSWORDS_STORAGE_SIM_API_TOKEN_REALM and credential.content.get('username', None) == self.org_id :
                        self.access_token = credential.content.get('clear_password', None)
                        break
            except Exception as e:
                # caller.logger.error('status=error, action=get_sim_connection, error_msg=' + str(e), exc_info=True)
                raise e

            if self.access_token is None:
                # self.caller.logger.error('status=error, action=get_sim_connection, error_msg=access_token is not found in Splunk Infrastructure Monitoring API Connection.')
                raise Exception('Access token not found in Infrastructure Monitoring API connection.')
        else:
            # Backward compatability logic. Old Single Account SIM connection format.
            url_segments = sim_api_url.split('.')
            if len(url_segments) < 4:
                # self.caller.logger.error('status=error, action=get_sim_connection, error_msg=Invalid Splunk Infrastructure Monitoring API Connection.')
                raise Exception('Invalid Infrastructure Monitoring API connection.')
            self.realm = url_segments[-3]

            try:
                for credential in service.storage_passwords:
                    if (credential.content.get('realm', None) == self.SPLUNK_PASSWORDS_STORAGE_SIM_API_TOKEN_REALM_OLD
                            and credential.content.get('username', None) == self.SPLUNK_PASSWORDS_STORAGE_SIM_API_TOKEN_USER_NAME_OLD):
                        self.access_token = credential.content.get('clear_password', None)
                        break
            except Exception as e:
                # caller.logger.error('status=error, action=get_sim_connection, error_msg=' + str(e), exc_info=True)
                raise e

            if self.access_token is None:
                # self.caller.logger.error('status=error, action=get_sim_connection, error_msg=access_token is not found in Splunk Infrastructure Monitoring API Connection.')
                raise Exception('Access token not found in Infrastructure Monitoring API connection.')

            # Test SIM Connection
            try:
                res_json = self.test_sim_connection()
                org_id = res_json.get('id', None)
                if not self.org_id:
                    self.org_id = org_id
                elif self.org_id != org_id:
                    raise Exception('Organization ID not found in Infrastructure Monitoring API connection.')
                self.org_name = res_json.get('organizationName', None)
            except Exception as e:
                # self.caller.logger.error('status=error, action=get_sim_connection, error_msg=' + str(e), exc_info=True)
                raise e

    def test_sim_connection(self):
        try:
            session = self.get_sim_request_session()
            test_connection_url = self.SPLUNK_SIM_API_TEST_CONNECTION_URL.format(self.realm)
            response = session.get(test_connection_url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            # self.caller.logger.error('status=error, action=test_sim_connection, error_msg=' + str(e), exc_info=True)
            raise e

    @property
    def sim_api_url(self):
        if self.realm is not None:
            return self.SPLUNK_SIM_API_URL.format(self.realm)
        raise Exception('Infrastructure Monitoring API connection not configured.')


class ClearSfxIncidents(CustomGroupActionBase):
    # Constants
    SIM_INCIDENTID_KEY = 'sf_incidentId'
    SIM_ORGANIZATION_ID = 'sf_organizationID'

    def __init__(self, input_params, audit_token_name='Auto Generated ITSI Notable Index Audit Token'):
        """
        Initialize the object
        @type settings: dict/basestring
        @param settings: incoming settings for this alert action that splunkd
            passes via stdin.

        @returns Nothing
        """
        self.logger = getLogger(logger_name="itsi.event_action.clear_sim_incidents")
        super(ClearSfxIncidents, self).__init__(input_params, self.logger)
        self.service = Service(token=self.get_session_key(), app='splunk_ta_sim')
        self.splunk_server = Splunk(self.get_session_key())
        # Initialize auditor
        self.auditor = Audit(self.get_session_key(), audit_token_name)
        self.input_params = json.loads(input_params)
        self.sim_api_connections = {}

    def clear_sim_incident(self, access_token, api_url, incident_id):
        try:
            endpoint_url = api_url + "/v2/incident/" + incident_id + "/clear"
            response = requests.put(
                endpoint_url,
                headers={
                    'Content-Type': 'application/json',
                    # 'Accept': 'application/json',
                    'X-SF-TOKEN': access_token
                }
            )
            return response
        except Exception as e:
            self.logger.error('status=error, step=clear_sim_incident, incident_id={0}, error_msg={1}'.format(incident_id, str(e)), exc_info=True)
            return None

    def execute(self):
        # self.logger.info('Received settings from splunkd=`%s`',json.dumps(self.input_params))
        itsi_group_id = ''
        # Init counters for stats on clear action
        clear_incident_request_count = 0
        clear_incident_success_count = 0
        clear_success_incidents = set()
        clear_failed_incidents = set()
        try:
            input_params_result = self.input_params.get('result', None)
            itsi_group_id = self.input_params['result'].get('itsi_group_id', None) if input_params_result else None
            if not itsi_group_id:
                self.logger.warning('Event does not have an `itsi_group_id`. No-op.')
                raise('Event does not have an `itsi_group_id`')
            self.logger.info('status=start, step=clear_sim_action, itsi_group_id=' + itsi_group_id)
            self.auditor.send_activity_to_audit({'event_id': itsi_group_id}, 'status=start', 'Clear Splunk Infrastructure Monitoring Incident')

            itsi_earliest_event_time = float(input_params_result.get('itsi_earliest_event_time'))
            time_range = get_group_time_range(input_params_result['start_time'],
                                              input_params_result['last_time'],
                                              input_params_result['itsi_first_event_time'],
                                              input_params_result['itsi_last_event_time'],
                                              itsi_earliest_event_time)
            self.logger.info('status=complete, step=get_time_range_for_notable_event_search, time_range={0}, itsi_group_id={1}'.format(str(time_range), itsi_group_id))

            notable_events_search_string = 'search `itsi_event_management_group_index` itsi_group_id={0} | stats latest(is) as status by sf_organizationID, sf_incidentId | where status!="ok"'.format(itsi_group_id)
            notable_events = get_notable_events(splunk_server=self.splunk_server,
                                                itsi_group_id=input_params_result['itsi_group_id'],
                                                earliest_time=time_range['earliest_time'],
                                                latest_time=time_range['latest_time'],
                                                page_size=1000,
                                                results_max_limit=None,
                                                search_string=notable_events_search_string)

            self.logger.info('status=complete, step=get_notable_events, itsi_group_id={0}, search_string={1}'.format(itsi_group_id, notable_events_search_string))

            for notable_events_subset in notable_events:
                for notable_event in notable_events_subset:
                    try:
                        clear_incident_request_count += 1
                        incident_id = notable_event.get(self.SIM_INCIDENTID_KEY, None)
                        org_id = notable_event.get(self.SIM_ORGANIZATION_ID, None)
                        incident_status = notable_event.get('status', None)
                        self.logger.info('status=start, step=clear_sim_incident, itsi_group_id={0}, incident_id={1}, incident_status={2}, clear_incident_request_count={3}, clear_incident_success_count={4}, org_id={5}'.format(
                            itsi_group_id, str(incident_id or ''), str(incident_status or ''), str(clear_incident_request_count), str(clear_incident_success_count), str(org_id or '')))

                        if org_id not in self.sim_api_connections:
                            self.sim_api_connections[org_id] = None
                            self.sim_api_connections[org_id] = SIMConnection(self.service, org_id)

                        sim_api_connection = self.sim_api_connections.get(org_id)

                        if sim_api_connection is None:
                            raise Exception('Splunk Infrastructure Monitoring API connection not configured for organization ID=' + str(org_id or ''))

                        response = self.clear_sim_incident(sim_api_connection.access_token, sim_api_connection.sim_api_url, incident_id)

                        if response and response.status_code == 200:
                            clear_incident_success_count += 1
                            clear_success_incidents.add(incident_id)
                            # self.auditor.send_activity_to_audit({'event_id': itsi_group_id}, 'status=success, clear_incident_request_count={0}, incident_id={1}'.format(str(clear_incident_request_count), incident_id), 'Clear Splunk Infrastructure Monitoring Incident')
                            self.logger.info('status=complete, step=clear_sim_incident, itsi_group_id={0}, incident_id={1}, clear_incident_request_count={2}, response={3}, org_id={4}'.format(
                                itsi_group_id, incident_id, str(clear_incident_request_count), str(response or ''), str(org_id or '')))
                        else:
                            clear_failed_incidents.add(incident_id)
                            self.auditor.send_activity_to_audit({'event_id': itsi_group_id}, 'status=failed, incident_id={0}'.format(incident_id), 'Clear Splunk Infrastructure Monitoring Incident')
                            self.logger.error('status=failed, step=clear_sim_incident, itsi_group_id={0}, incident_id={1}, clear_incident_request_count={2}, response={3}, org_id={4}'.format(
                                itsi_group_id, incident_id, str(clear_incident_request_count), str(response or ''), str(org_id or '')))

                        if clear_incident_request_count % 100 == 0:
                            self.auditor.send_activity_to_audit({'event_id': itsi_group_id}, 'status=running, Number of clear incident requests sent = {0}, Number of incidents successfully cleared = {1}'.format(str(clear_incident_request_count), str(clear_incident_success_count)), 'Clear Splunk Infrastructure Monitoring Incident')

                    except Exception as e:
                        self.auditor.send_activity_to_audit({'event_id': itsi_group_id}, 'status=error, incident_id={0}, org_id={1}'.format(incident_id, str(org_id or '')), 'Clear Splunk Infrastructure Monitoring Incident')
                        self.logger.error('status=error, step=clear_sim_incident, itsi_group_id={0}, incident_id={1}, clear_incident_request_count={2}, org_id={3}, error_msg={4}'.format(
                            itsi_group_id, incident_id, str(clear_incident_request_count), str(org_id or ''), str(e)), exc_info=True)

            str_clear_success_incidents = ', '.join(clear_success_incidents)
            str_clear_failed_incidents = ', '.join(clear_failed_incidents)
            action_status = ('partially_complete' if clear_incident_success_count > 0 else 'failed') if clear_incident_request_count != clear_incident_success_count else 'complete'

            self.auditor.send_activity_to_audit({'event_id': itsi_group_id}, """status={0} \nNo. of uncleared incidents in episode: {1} \nNo. of clear incident requests sent: {1}\nNo. of incidents successfully cleared: {2} \n\nIncidents successfully cleared by action: [{3}] \n\nIncidents failed to clear by action: [{4}]\n""".format(
                action_status, str(clear_incident_request_count), str(clear_incident_success_count), str_clear_success_incidents, str_clear_failed_incidents), 'Clear Splunk Infrastructure Monitoring Incident')

            self.logger.info('status={0}, step=clear_sim_action, itsi_group_id={1}, clear_incident_request_count={2}, clear_incident_success_count={3}'.format(action_status, itsi_group_id, str(clear_incident_request_count), str(clear_incident_success_count)))

            if clear_incident_request_count != clear_incident_success_count:
                sys.exit(1)

        except Exception as e:
            self.auditor.send_activity_to_audit({'event_id': itsi_group_id}, """status=error \nNo. of uncleared incidents in episode: {0} \nNo. of clear incident requests sent: {0} \nNo. of incidents successfully cleared: {1} \n\nIncidents successfully cleared by action: [{2}] \n\nIncidents failed to clear by action: [{3}]\n""".format(
                str(clear_incident_request_count), str(clear_incident_success_count), ', '.join(clear_success_incidents), ', '.join(clear_failed_incidents)), 'Clear Splunk Infrastructure Monitoring Incident')
            self.logger.error('status=error, step=clear_sim_action, itsi_group_id={0}, clear_incident_request_count={1}, clear_incident_success_count={2}, error_msg={3}'.format(itsi_group_id, str(clear_incident_request_count), str(clear_incident_success_count), str(e)), exc_info=True)
            sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        input_params = sys.stdin.read()
        clear_sfx_incidents = ClearSfxIncidents(input_params)
        clear_sfx_incidents.execute()
