# -*- coding: utf-8 -*-
from requests.api import request
import abc
import six


class ResponseErrorException(Exception):
    def __init__(self, msg):
        self.msg = msg


@six.add_metaclass(abc.ABCMeta)
class Endpoint():
    BASE_URI = "https://api.cymon.co/v2"

    def __init__(self, api_key, proxies=None):
        self.api_key = api_key
        self.proxies = proxies
        self.useragent = "CyjaxSplunk/2.2.1"

    @abc.abstractmethod
    def get_entries(self, since=None, until=None, page=1, per_page=20, *args, **kwargs):
        pass

    @abc.abstractmethod
    def get_name(self):
        pass

    def _rest_request(self, method, url, params=None, data=None):
        if data is None:
            data = []
        if params is None:
            params = []
        response = request(method, self.BASE_URI + '/' + url, params=params, data=data, timeout=15,
                           headers={'Authorization': 'Bearer ' + self.api_key, "User-Agent": self.useragent}, proxies=self.proxies)
        if response.status_code != 200:
            try:
                json_data = response.json()
                raise ResponseErrorException(
                    json_data['message'] if 'message' in json_data else 'Unknown')
            except:
                raise ResponseErrorException(
                    'Error parsing JSON message %s' % response.text)

        return response

    def _build_timestamp_params(self, params, since, until):
        if since:
            params.update({'since': since})
        if until:
            params.update({'until': until})

    def get_collection(self, method, url, params=None, page=1, per_page=20):
        params.update({
            'page': page,
            'per-page': per_page
        })
        return self._rest_request(method, url, params=params)


class IndicatorOfCompromiseEndpoint(Endpoint):
    INCIDENT_REPORT = "incident-report"
    LIVE_INTELLIGENCE = "my-report"

    def __init__(self, *args, **kwargs):
        super(IndicatorOfCompromiseEndpoint, self).__init__(*args, **kwargs)

    def get_name(self):
        return 'Indicator of Compromise'

    def get_entries(self, since=None, until=None, page=1, per_page=20, *args, **kwargs):

        params = {}
        self._build_timestamp_params(params, since, until)

        return self.get_collection(method='get', url='indicator-of-compromise', params=params, page=page,
                                   per_page=per_page)


class TweetmonEndpoint(Endpoint):

    def __init__(self, *args, **kwargs):
        super(TweetmonEndpoint, self).__init__(*args, **kwargs)

    def get_name(self):
        return 'Tweetmon'

    def get_entries(self, since=None, until=None, page=1, per_page=20, *args, **kwargs):
        params = {}
        self._build_timestamp_params(params, since, until)
        return self.get_collection(method='get', url='tweet', params=params, page=page, per_page=per_page)


class IncidentReportEndpoint(Endpoint):

    def __init__(self, *args, **kwargs):
        super(IncidentReportEndpoint, self).__init__(*args, **kwargs)

    def get_name(self):
        return 'Incident reports'

    def get_entries(self, since=None, until=None, page=1, per_page=20, *args, **kwargs):
        params = {}
        self._build_timestamp_params(params, since, until)
        return self.get_collection(method='get', url='report/incident', params=params, page=page, per_page=per_page)


class LeakedCredentialsEndpoint(Endpoint):

    def __init__(self, *args, **kwargs):
        super(LeakedCredentialsEndpoint, self).__init__(*args, **kwargs)

    def get_name(self):
        return 'Data leaks'

    def get_entries(self, since=None, until=None, page=1, per_page=20, *args, **kwargs):
        params = {}
        self._build_timestamp_params(params, since, until)
        return self.get_collection(method='get', url='data-leak/credentials', params=params, page=page, per_page=per_page)


class TorExitNodeEndpoint(Endpoint):

    def __init__(self, *args, **kwargs):
        super(TorExitNodeEndpoint, self).__init__(*args, **kwargs)

    def get_name(self):
        return 'TOR exit nodes'

    def get_entries(self, since=None, until=None, page=1, per_page=20, *args, **kwargs):
        params = {}
        self._build_timestamp_params(params, since, until)
        return self.get_collection(method='get', url='blacklists/tor-node', params=params, page=page, per_page=per_page)


class PotentialMaliciousDomainsEndpoint(Endpoint):

    def __init__(self, *args, **kwargs):
        super(PotentialMaliciousDomainsEndpoint,
              self).__init__(*args, **kwargs)

    def get_name(self):
        return 'Potential malicious domains'

    def get_entries(self, since=None, until=None, page=1, per_page=20, *args, **kwargs):
        params = {}
        self._build_timestamp_params(params, since, until)
        return self.get_collection(method='get', url='domain-monitor/potential-malicious-domain', params=params, page=page, per_page=per_page)


class RansomwareOperationsEndpoint(Endpoint):

    def __init__(self, *args, **kwargs):
        super(RansomwareOperationsEndpoint, self).__init__(*args, **kwargs)

    def get_name(self):
        return 'Ransomware Operations'

    def get_entries(self, since=None, until=None, page=1, per_page=20, *args, **kwargs):
        params = {}
        self._build_timestamp_params(params, since, until)
        return self.get_collection(method='get', url='webpages/ransomware', params=params, page=page, per_page=per_page)
