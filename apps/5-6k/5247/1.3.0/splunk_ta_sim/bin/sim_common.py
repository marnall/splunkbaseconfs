import requests


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
            sim_api_config_collection = service.kvstore.get(
                self.SPLUNK_KV_STORE_SIM_CONFIG_COLLECTION_NAME, None
            )
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
            raise e

        if sim_api_config_record is None:
            raise Exception('Splunk Infrastructure Monitoring API Connection not configured.')

        if not is_old_sim_api_config:
            # Multi Account SIM connection Data collection disabled
            if not bool(conf_record.get('enable', True)):
                raise Exception('Data collection disabled on this Infrastructure Monitoring Account.')

            # Multi Account SIM connection format
            self.org_id = conf_record.get('org_id', None)
            self.is_default = conf_record.get('default', False)
            self.org_name = conf_record.get('org_name', None)
            self.realm = conf_record.get('realm', None)

            if self.org_id is None:
                raise Exception('Org_Id is not found in Splunk Infrastructure Monitoring API Connection.')

            if self.realm is None:
                raise Exception('realm is not found in Splunk Infrastructure Monitoring API Connection.')

            # Get get SIM API connection Access Token from KV store
            try:
                for credential in service.storage_passwords:
                    cred_realm = credential.content.get('realm', None)
                    cred_username = credential.content.get('username', None)
                    realm_matches = cred_realm == self.SPLUNK_PASSWORDS_STORAGE_SIM_API_TOKEN_REALM
                    username_matches = cred_username == self.org_id
                    if realm_matches and username_matches:
                        self.access_token = credential.content.get('clear_password', None)
                        break
            except Exception as e:
                raise e

            if self.access_token is None:
                raise Exception(
                    'access_token is not found in Splunk Infrastructure Monitoring API Connection.'
                )
        else:
            # Backward compatability logic. Old Single Account SIM connection format.
            url_segments = sim_api_url.split('.')
            if len(url_segments) < 4:
                raise Exception('Invalid Splunk Infrastructure Monitoring API Connection.')
            self.realm = url_segments[-3]

            try:
                for credential in service.storage_passwords:
                    cred_realm = credential.content.get('realm', None)
                    cred_username = credential.content.get('username', None)
                    realm_matches = cred_realm == self.SPLUNK_PASSWORDS_STORAGE_SIM_API_TOKEN_REALM_OLD
                    user_matches = cred_username == self.SPLUNK_PASSWORDS_STORAGE_SIM_API_TOKEN_USER_NAME_OLD
                    if realm_matches and user_matches:
                        self.access_token = credential.content.get('clear_password', None)
                        break
            except Exception as e:
                raise e

            if self.access_token is None:
                raise Exception(
                    'access_token is not found in Splunk Infrastructure Monitoring API Connection.'
                )

            # Test SIM Connection
            try:
                res_json = self.test_sim_connection()
                org_id = res_json.get('id', None)
                if not self.org_id:
                    self.org_id = org_id
                elif self.org_id != org_id:
                    raise Exception(
                        'Org_Id is not found in Splunk Infrastructure Monitoring API Connection.'
                    )
                self.org_name = res_json.get('organizationName', None)
            except Exception as e:
                raise e

    def test_sim_connection(self):
        try:
            session = self.get_sim_request_session()
            test_connection_url = self.SPLUNK_SIM_API_TEST_CONNECTION_URL.format(self.realm)
            response = session.get(test_connection_url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise e

    @property
    def sim_api_url(self):
        if self.realm is not None:
            return self.SPLUNK_SIM_API_URL.format(self.realm)
        raise Exception('Splunk Infrastructure Monitoring API Connection not configured.')

    @property
    def sim_stream_url(self):
        if self.realm is not None:
            return self.SPLUNK_SIM_STREAM_URL.format(self.realm)
        raise Exception('Splunk Infrastructure Monitoring API Connection not configured.')

    def get_sim_request_session(self):
        if self.access_token is not None:
            session = requests.Session()
            session.headers.update({
                'Content-Type': 'application/json',
                'X-SF-Token': self.access_token,
            })
            return session
        raise Exception('Splunk Infrastructure Monitoring API Connection not configured.')


def get_conf_stanza(service, conf_name, stanza_name):
    try:
        stanza_settings = service.confs[conf_name][stanza_name]
        return stanza_settings.content or {}
    except Exception as e:
        raise e
    return {}


def normalize_time(timestamp):
    if timestamp is not None:
        if len(str(round(float(timestamp)))) == 10:
            # ex: 1586473882.963976
            return float(timestamp)
        else:
            ts_str = str(timestamp)
            if len(ts_str) > 10 and '.' not in ts_str:
                return float(ts_str[:10] + '.' + ts_str[10:])
