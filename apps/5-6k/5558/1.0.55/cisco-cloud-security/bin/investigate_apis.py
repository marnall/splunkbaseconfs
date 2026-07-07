import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))
from asyncio.log import logger
import datetime, time
import requests
from logger import Logger
from enums import InvestigateAPIS, ProcessInvestigateAPIs
from reporting_api_client import ReportingAPIClient
from exceptions import ReportingAPIClientException


class InvestigateReports():
    '''Class implementation for mapping all the field types to respective APIs
    amd methods to process API
    '''
    SEARCH_ERR = ValueError("Start argument must be a datetime or a timedelta")
    API_ERROR = "Error querying {} for {}"

    def __init__(self, session_token, org_id: str):

        self.session_token = session_token
        self.org_id = org_id
        self.domain_uris = InvestigateAPIS.DOMAIN_URIS.value
        self.ip_uris = InvestigateAPIS.IP_URIS.value
        self.hash_uris = InvestigateAPIS.HASH_URIS.value
        self.url_uris = InvestigateAPIS.URL_URIS.value
        self.process_uris = ProcessInvestigateAPIs.PROCESS_METHODS.value
        self._session = requests.Session()
        self.api_client = ReportingAPIClient(session_token, org_id=self.org_id)
        self.headers = {'Content-Type': 'application/json',
                   'Accept': 'application/json',
                   'User-Agent': 'CiscoCloudSecurityAppForSplunk/python-requests/3x'}

    @staticmethod
    def merge_response(response1, response2):
        '''Function to merge two api responses.
        params: response1 , response2
        type: dict
        return: dict
        '''
        return {**response1, **response2}


    def process_categorization(self, field_name, field_type):
        '''Get the domain status and categorization of a domain or list of domains.
        'domains' can be either a single domain, or a list of domains.
        Setting 'showLabels' to True will give back categorizations in human-readable
        form.
        '''
        response_data = dict()
        try:
            for uri in self.domain_uris['domain_status_categorization']:
                uri = uri.format(field_name)
                params = {'showLabels': True}
                response = self.api_client.send_request(path=uri, method='get', params=params, headers=self.headers)
            if response.status_code == 200 and response.json():   
                response_data['Categorization'] = response.json()[field_name]
            return response_data
        except ReportingAPIClientException as e:
            Logger().error("API: investigate, Exception : {0}".format(str(e.error_msg)))
        except Exception as e:
            Logger().error(self.API_ERROR.format('process_categorization', field_name) +", "+ str(e))


    def process_domain_volume(self, field_name, field_type, start=None, stop=None, match='all'):
        '''Number of DNS queries made per hour to the specified domain by users'''
        response_data = dict()
        response_dict = dict()
        params = dict()
        try:
            if start is None:
                start = datetime.timedelta(days=30)
            if isinstance(start, datetime.timedelta):
                params['start'] = int(time.mktime((datetime.datetime.utcnow() - start).timetuple()) * 1000)
            elif isinstance(start, datetime.datetime):
                params['start'] = int(time.mktime(start.timetuple()) * 1000)
            elif isinstance(start, int) and (datetime.datetime.now()-datetime.datetime.fromtimestamp(start/1000)).days < 30:
                params['start'] = int(start)
            else:
                raise InvestigateReports.SEARCH_ERR

            if stop is None:
                stop = datetime.datetime.now()
            if isinstance(stop, datetime.timedelta):
                params['stop'] = int(time.mktime((datetime.datetime.utcnow() - stop).timetuple()) * 1000)
            elif isinstance(stop, datetime.datetime):
                params['stop'] = int(time.mktime(stop.timetuple()) * 1000)
            elif isinstance(stop, int) and (datetime.datetime.now() - datetime.datetime.fromtimestamp(stop/1000)).days < 30:
                params['stop'] = int(stop)
            else:
                raise InvestigateReports.SEARCH_ERR

            if match is not None and match in ('all' or 'component' or 'exact'):
                params['match'] = match
            for uri in self.domain_uris['domain_volume']:
                uri = uri.format(field_name)
                response = self.api_client.send_request(path=uri, method='get', params=params, headers=self.headers)
                if response.status_code == 200 and response.json():
                    response_dict = self.merge_response(response_dict, response.json())
            response_data['Volume'] = response_dict
            return response_data
        except ReportingAPIClientException as e:
            Logger().error("API: investigate, Exception : {0}".format(str(e.error_msg)))
        except Exception as e:
            Logger().error(self.API_ERROR.format('process_domain_volume', field_name) +", "+ str(e))


    def process_cooccurance(self, field_name, field_type):
        '''Get the cooccurrences of the given domain.
        '''
        response_data = dict()
        try:
            for uri in self.domain_uris['cooccurrences_domain']:
                uri = uri.format(field_name)
                response = self.api_client.send_request(path=uri, method='get', headers=self.headers)
                response = response.json()
            if 'found' in response and response.get('found') is True:
                response_data['Cooccurance'] = response['pfs2']
            return response_data
        except ReportingAPIClientException as e:
            Logger().error("API: investigate, Exception : {0}".format(str(e.error_msg)))
        except Exception as e:
            Logger().error(self.API_ERROR.format('process_cooccurance', field_name) +", "+ str(e))

    def process_pdns(self, field_name, field_type, limit=None, offset=0, sortorder='desc', sortby=None, recordType=None):
        '''Get the passive_dns of the given domain/ip.
        '''
        response_data = dict()
        try:
            response_dict = dict()
            if field_type == 'domain':
                for uri in self.domain_uris['passive_dns']:
                    params = {'limit': limit, 'offset': offset, 'sortorder': sortorder, 'sortby': sortby, 'recordType': recordType}
                    uri = uri.format(field_name)
                    response = self.api_client.send_request(path=uri, method='get', params=params, headers=self.headers)
                    if response.status_code == 200 and response.json():
                        response_dict = self.merge_response(response_dict, response.json())
            elif field_type == 'ip':
                for uri in self.ip_uris['passive_dns']:
                    params = {'limit': limit, 'offset': offset, 'sortorder': sortorder, 'sortby': sortby, 'recordType': recordType}
                    uri = uri.format(field_name)
                    response = self.api_client.send_request(path=uri, method='get', params=params, headers=self.headers)
                    if response.status_code == 200 and response.json():
                        response_dict = self.merge_response(response_dict, response.json())
            response_data['Pdns'] = response_dict
            return response_data
        except ReportingAPIClientException as e:
            Logger().error("API: investigate, Exception : {0}".format(str(e.error_msg)))
        except Exception as e:
            Logger().error(self.API_ERROR.format('process_pdns', field_name) +", "+ str(e))


    def process_related(self, field_name, field_type):
        '''Get the related_domain of the given domain.
        '''
        response_data = dict()
        try:
            for uri in self.domain_uris['related_domains']:
                uri = uri.format(field_name)
                response = self.api_client.send_request(path=uri, method='get', headers=self.headers)
                response = response.json()
            if 'found' in response and response.get('found') is True:
                response_data['Related'] = response['tb1']
            return response_data
        except ReportingAPIClientException as e:
            Logger().error("API: investigate, Exception : {0}".format(str(e.error_msg)))
        except Exception as e:
            Logger().error(self.API_ERROR.format('process_related', field_name) +", "+ str(e))

    def process_security_info(self, field_name, field_type):
        '''Get the Security informaton of the given domain.
        '''
        response_data =dict()
        response_dict = dict()
        try:
            for uri in self.domain_uris['security_information']:
                uri = uri.format(field_name)
                response = self.api_client.send_request(path=uri, method='get', headers=self.headers)
                if response.status_code == 200 and response.json():
                    response_dict = self.merge_response(response_dict, response.json())
            response_data['Security'] = response_dict
            return response_data
        except ReportingAPIClientException as e:
            Logger().error("API: investigate, Exception : {0}".format(str(e.error_msg)))
        except Exception as e:
            Logger().error(self.API_ERROR.format('process_security_info', field_name) +", "+ str(e))


    def process_whois_info(self, field_name, field_type, limit=None):
        '''Get Who is of the given domain.
        '''
        response_data = dict()
        response_dict = dict()
        try:
            for uri in self.domain_uris['whois_information']:
                uri = uri.format(field_name)
                response = self.api_client.send_request(path=uri, method='get', headers=self.headers)
                if response.status_code == 200 and response.json():
                    response_dict = self.merge_response(response_dict, response.json())
            response_data['Whois'] = response_dict
            return response_data
        except ReportingAPIClientException as e:
            Logger().error("API: investigate, Exception : {0}".format(str(e.error_msg)))
        except Exception as e:
            Logger().error(self.API_ERROR.format('process_whois_info', field_name) +", "+ str(e))


    def process_threat_grid(self, field_name, field_type):
        '''Get the threat_grid_integration of the given domain/ip/hash/url.
        '''
        response_data = dict()
        response_dict = dict()
        try:
            if field_type == 'domain':
                for uri in self.domain_uris['threat_grid_integration']:
                    uri = uri.format(field_name)
                    response = self.api_client.send_request(path=uri, method='get', headers=self.headers)
                    if response.status_code == 200 and response.json():
                        response_dict = self.merge_response(response_dict, response.json())
            elif field_type == 'ip':
                for uri in self.ip_uris['threat_grid_integration']:
                    uri = uri.format(field_name)
                    response = self.api_client.send_request(path=uri, method='get', headers=self.headers)
                    if response.status_code == 200 and response.json():
                        response_dict = self.merge_response(response_dict, response.json())
            elif field_type == 'hash':
                for uri in self.hash_uris['threat_grid_integration']:
                    uri = uri.format(field_name)
                    response = self.api_client.send_request(path=uri, method='get', headers=self.headers)
                    if response.status_code == 200 and response.json():
                        response_dict = self.merge_response(response_dict, response.json())
            elif field_type == 'url':
                for uri in self.url_uris['threat_grid_integration']:
                    uri = uri.format(field_name)
                    response = self.api_client.send_request(path=uri, method='get', headers=self.headers)
                    if response.status_code == 200 and response.json():
                        response_dict = self.merge_response(response_dict, response.json())
            response_data['Threat'] = response_dict
            return response_data
        except ReportingAPIClientException as e:
            Logger().error("API: investigate, Exception : {0}".format(str(e.error_msg)))
        except Exception as e:
            Logger().error(self.API_ERROR.format('process_threat_grid', field_name) +", "+ str(e))

    def process_as_info(self, field_name, field_type):
        '''Get the as_information of the ip.
        '''
        response_data = dict()
        response_dict = dict()
        try:
            for uri in self.ip_uris['as_information']:
                uri = uri.format(field_name)
                response = self.api_client.send_request(path=uri, method='get', headers=self.headers)
                if response.status_code == 200 and response.json():
                    response_dict = self.merge_response(response_dict, response.json())
            response_data['AsInfo'] = response_dict
            return response_data
        except ReportingAPIClientException as e:
            Logger().error("API: investigate, Exception : {0}".format(str(e.error_msg)))
        except Exception as e:
            Logger().error(self.API_ERROR.format('process_as_info', field_name) +", "+ str(e))
