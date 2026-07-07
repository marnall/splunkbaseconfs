"""Intsights client class."""
import time
import requests
from requests.exceptions import HTTPError

MAX_RESPONSE_SIZE_IN_MB = 100
MAX_SESSION_TIME_IN_SECONDS = 30 * 60
HEADERS = {
    'X-App-Name': 'Splunk_1.1.5'
}


class IntSightsConnector:
    """IntSights class to connect to API."""

    def __init__(self, logger):
        """Create private var for splunk sessions."""
        self._sessions_map = {}
        self._logger = logger

    def _create_new_session(self, username, password):
        # attempt to create session with basic auth
        try:
            session = requests.session()
            session.auth = requests.auth.HTTPBasicAuth(
                username=username,
                password=password
            )

        except Exception as e:
            self._logger.debug('Could not authenticate to IntSights. Exception - {} '.format(e))
            raise e

        return session

    def get_session(self, username, password):
        """Get sessions."""
        # attempt to create new session if current is timed out
        try:
            current_time = time.time()
            session_info = self._sessions_map.get(username)

            if session_info:
                created_time = session_info['created_time']

                if current_time - created_time <= MAX_SESSION_TIME_IN_SECONDS:
                    return session_info['session_obj']

            session_obj = self._create_new_session(username, password)

            self._sessions_map[username] = {
                'created_time': current_time,
                'session_obj': session_obj
            }

            return session_obj

        except Exception as e:
            self._logger.debug('Could not get_session to IntSights. Exception - {} '.format(e))
            raise e


class IntSightsClient:
    """IntSights class to connect to API."""

    def __init__(self, username, password, logger, proxy):
        """Create local vars for connector and sessions."""
        self._connector = IntSightsConnector(logger)
        self._session = self._connector.get_session(username, password)
        self._logger = logger
        self._proxy = proxy

    def send_request(self, method, url, params, json_data, headers, stream, retry=3):
        """Wrap request calls."""
        retry -= 1
        try:
            self._logger.debug(
                'Sending request with parameters '
                'method: "{0}" '
                'url: "{1}" '
                'params: "{2}" '
                'json_data: "{3}" '.format(str(method).split()[2][8:], url, params, json_data)
            )

            response = method(url=url, data=json_data, params=params, headers=headers, stream=stream, verify=True, proxies=self._proxy)
            response.raise_for_status()

            if response.status_code == 204:
                return []

        except HTTPError as http_err:
            self._logger.error(
                'HTTP error: "{0}" occurred when handling '
                'method: "{1}" '
                'url: "{2}" '
                'params: "{3}" '
                'retry: "{4}" '
                'json_data: "{5}" '.format(http_err, str(method).split()[2][8:], url, params, retry, json_data)
            )
            if retry <= 0:
                return None

            status_code = http_err.response.status_code
            if status_code == 429:
                raise http_err

            if status_code not in [400, 401, 402, 403, 404]:
                time.sleep(10)
                return self.send_request(method, url, params, json_data, headers, stream, retry)

            return None

        except Exception as e:
            self._logger.error(
                'Exception: "{0}" occurred when handling '
                'method: "{1}" '
                'url: "{2}" '
                'params: "{3}" '
                'json_data: "{4}" '.format(e, str(method).split()[2][8:], url, params, retry, json_data)
            )

            return None

        else:
            self._logger.debug('response code: {}'.format(response.status_code))
            if stream:
                return response
            else:
                return response.json()

    def get_complete_alert_by_id(self, alert_id, params, headers=HEADERS):
        """Wrap request calls to get alert."""
        try:
            response = self.send_request(
                method=self._session.get,
                url='https://api.intsights.com/public/v1/data/alerts/get-complete-alert/' + alert_id,
                json_data={},
                params=params,
                headers=headers,
                stream=False
            )
            return response

        except Exception:
            self._logger.error('Could not get complete alert by id')
            return None

    def get_alerts(self, params, headers=HEADERS):
        """Wrap request calls to get alert."""
        try:
            response = self.send_request(
                method=self._session.get,
                url='https://api.intsights.com/public/v1/data/alerts/alerts-list',
                json_data={},
                params=params,
                headers=headers,
                stream=False
            )
            return response

        except Exception:
            self._logger.error('Could not get alerts')
            return None

    def get_ioc_details_csv(self, params, headers=HEADERS):
        """Wrap request calls to get iocs."""
        start_time = time.time()
        wait_time = 60 * 60
        while True:
            try:
                response = self.send_request(
                    method=self._session.get,
                    url='https://api.intsights.com/public/v1-1/iocs/iocs-details-csv',
                    json_data={},
                    params=params,
                    headers=headers,
                    stream=True
                )
                return response

            except HTTPError as http_err:
                status_code = http_err.response.status_code
                if status_code != 429:
                    return None

                if time.time() - start_time > wait_time:
                    return None

                self._logger.info('Retrying request')
                time.sleep(10)
                continue

            except Exception as e:
                self._logger.error('Could not get ioc details csv. Text: {}'.format(e))
                return None

    def get_ioc_sources(self, params={}, headers=HEADERS):
        """Wrap request calls to get ioc sources."""
        try:
            response = self.send_request(
                method=self._session.get,
                url='https://api.intsights.com/public/v1/iocs/sources',
                json_data={},
                params=params,
                headers=headers,
                stream=True
            )
            return response

        except Exception as e:
            self._logger.error('Could not get ioc sources. Text: {}'.format(e))
            return None
