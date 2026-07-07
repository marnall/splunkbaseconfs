# encoding = utf-8
from __future__ import print_function, absolute_import

import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

import json
from validator import json_sanitizer, cummulative_validator, get_host
from datetime import datetime
from splunk.persistconn.application import PersistentServerConnectionApplication
from service.app_kvstore_service import KVStoreService
from logger import Logger
from common import Common
from reporting_api_client import ReportingAPIClient
from exceptions import ReportingAPIClientException


class Investigate(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def get_value(self, params, key, default=None):
        value = params.get(key, default)
        if not cummulative_validator(str(value)):
            raise Exception('{0} validation failed'.format(key))
        return value if value else ''

    def get_url(self, key, replace_dict):
        url_dict = {}
        url_dict['dns_RR_hist_ip_features'] = 'pdns/ip/<address>.json?limit=<lim>&recordType=A&includefeatures=true'
        url_dict['dns_RR_hist_ip_nameservers'] = 'pdns/ip/<address>.json?limit=<lim>&recordType=NS&includefeatures=true'
        url_dict['latest_mal_dom_ip'] = 'ips/<address>/latest_domains?count_total=false'
        url_dict['as_info_ip'] = 'bgp_routes/ip/<address>/as_for_ip.json?count_total=false'
        url_dict['security_info_domain'] = 'security/name/<address>?count_total=false'
        url_dict['related_domains'] = 'links/name/<address>.json?count_total=false'
        url_dict['co-occurences'] = 'recommendations/name/<address>.json?count_total=false'
        url_dict['whois_for_domain'] = 'whois/<address>?count_total=false'
        url_dict['status_for_blk_unblk'] = 'domains/categorization/<address>?count_total=false'
        url_dict['risk_score'] = 'domains/risk-score/<address>?count_total=false'
        url_dict['timeline'] = 'timeline/<address>'
        url_dict['nameserv'] = 'whois/nameservers/<address>?count_total=false'
        url_dict['samples_behaviour'] = 'sample/<address>/behaviors'
        url_dict['as_info_asn'] = 'bgp_routes/asn/<address>/prefixes_for_asn.json?count_total=false'
        url_dict['nameserver_associated_domain'] = 'whois/nameservers?limit=<lim>&nameServerList=<nsl>&count_total=false'
        url_dict['dns_RR_hist_type_dn'] = 'pdns/name/<address>.json?limit=<lim>&recordType=<record_type>&includefeatures=true'
        url_dict['domain_volume'] = 'domains/volume/<address>?start=<start>&stop=<stop>&match=<match>&count_total=false'
        url_dict['subdomains'] = 'domains/subdomains/<address>?parentcategories=<parent_categories>&count_total=false'
        url_dict['malicious_samples'] = 'samples/<address>?limit=<lim>&sortby=<srt_by>&offset=<offset>'
        url_dict['email_domain_name'] = 'whois/emails/<address>?limit=<lim>&offset=<offset>&count_total=false'
        url_dict['samples_connections'] = 'sample/<address>/connections?limit=<lim>&offset=<offset>'
        url_dict['samples_association'] = 'sample/<address>/artifacts?limit=<lim>'
        url_dict['sample_info'] = 'sample/<address>?limit=<lim>&offset=<offset>'
        url_dict['curr_info'] = 'autonomous_systems/<address>.json?history=<hist>&count_total=false'
        url_dict['whois_email_list'] = 'whois/emails?emailList=<request_whois_email>&limit=<lim>&count_total=false'
        url_dict['whois_nameserver_list'] = 'whois/nameservers?nameServerList=<nsls>&limit=<lim>&count_total=false'
        url_dict['category_classifier'] = 'domains/categorization/<address>?showLabels'
        url = url_dict.get(key, '')
        if url:
            import re
            for _key in re.findall(r'(?<=\<).+?(?=\>)', url):
                value = replace_dict.get(_key, '')
                url = url.replace('<{0}>'.format(_key), (value if value else ''))
        return url

    def handle(self, in_string):
        try:
            headers = None
            params = Common().parse_in_string(in_string)
            session_token = params['session']['authtoken']
            header = params.get('headers', [])
            host = get_host(header)
            endpoint = self.get_value(params, 'rest_path')
            if endpoint:
                endpoint = endpoint.split('/')[-1]
            api_client = ReportingAPIClient(session_token)
            # global investigate_settings
            # if investigate_settings is None:
            #     investigate_settings = KVStoreService('investigate_settings', session_token)
            # investigate_settings_data = json.loads(investigate_settings.query_items('investigate_settings', session_token))
            # if len(investigate_settings_data) == 0:
            #     raise Exception('Investigate settings are empty')
            
            headers = {}    
            query = params["query"]
            replace_dict = {}
            # we are not directly using query because of the validation and expected default values --Arjun
            replace_dict['address'] = self.get_value(query, "address")
            replace_dict['lim'] = self.get_value(query, "limit", 0)
            replace_dict['nsl'] = self.get_value(query, "nameServerList")
            replace_dict['record_type'] = self.get_value(query, "type")
            replace_dict['rtl'] = self.get_value(query, "realtime_lookup")
            replace_dict['start'] = self.get_value(query, "start")
            replace_dict['stop'] = self.get_value(query, "stop")
            replace_dict['match'] = self.get_value(query, "match")
            replace_dict['parent_categories'] = self.get_value(query, "parent_categories")
            replace_dict['srt_by'] = self.get_value(query, "sortby")
            replace_dict['offset'] = self.get_value(query, "offset")
            replace_dict['hist'] = self.get_value(query, "history")  
            if endpoint == 'whois_email_list' or endpoint == 'whois_nameserver_list':
                path =f"/investigate/v2/whois/{replace_dict['address']}"
                whois_response = api_client.send_request(path=path, method='get', headers=headers)
                whois_response = whois_response.json()
                replace_dict['request_whois_email'] = whois_response["administrativeContactEmail"] if endpoint == 'whois_email_list' else ''
                replace_dict['nsls'] = (','.join(whois_response["nameServers"])) if endpoint == 'whois_nameserver_list' else ''
            url_req = f'/investigate/v2/{self.get_url(endpoint, replace_dict)}'
            response = api_client.send_request(path=url_req, method='get', headers=headers)
            response_body = response.content if endpoint == 'subdomains' else json.dumps(json_sanitizer(response.json()))
            return {'payload': response_body, 'status': 200}
        
        except ReportingAPIClientException as e:
            Logger().error("API: investigate, Exception : {0}".format(str(e.error_msg)))
            return {'payload': {"message": str(e.error_msg)}, "status": e.error_code}
        except Exception as e:
            Logger().error("API: investigate, Exception : {0}".format(str(e)))
            return {'payload': {"message": str(e)}, "status": 500}
