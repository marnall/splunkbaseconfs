import sys
import os
import urllib.parse
from state_store import Credentials
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.modularinput import *
from splunk.clilib import cli_common as cli
import sys
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
from cyberintegrations import TIPoller
import validators
from cyberintegrations import ParserHelper
import logging

APP_NAME = 'facct_ti'
SEQUPDATE_FILE = os.environ['SPLUNK_HOME'] + '/etc/apps/facct_ti/bin/seqUpdate_storage.json'
LOG_FILE_DIRECTORY = os.environ['SPLUNK_HOME'] + '/var/log/splunk/' + APP_NAME

logger = logging.getLogger(APP_NAME)
logging.propagate = False
logger.setLevel(logging.DEBUG)
if not os.path.exists(LOG_FILE_DIRECTORY):
    os.makedirs(LOG_FILE_DIRECTORY)
log_path = os.path.join(LOG_FILE_DIRECTORY,"modinput_search.log")
file_handler = logging.handlers.RotatingFileHandler(log_path)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.debug("Logger Initialized")




@Configuration(type="reporting")
class facctsearch(GeneratingCommand):
    search = Option(require=True)
    path_list = [
        'malware/cnc',
        'malware/malware',
        'attacks/ddos',
        'attacks/deface',
        'attacks/phishing_kit',
        'attacks/phishing_group',
        'common/threat',
        'apt/threat',
        'hi/threat',
        'osi/public_leak',
        'suspicious_ip/tor_node',
        'suspicious_ip/socks_proxy',
        'suspicious_ip/open_proxy',
        'suspicious_ip/scanner',
        'suspicious_ip/vpn',
        'ioc/common',
        # 'malware/config'
    ]
    ip = {
        'Attribution': {'Collection name': 'api.collection',
                        'Threat actor': 'api.threatActor.name'},
        'Details': {'Source': 'api.source',
                    'Categories': 'api.categories'},
        'Activity Dates': {
            # 'CreatedAt': 'graph.createdAt',
            # 'updatedAt': 'graph.updatedAt',
            'dateFirstSeen': 'api.dateFirstSeen',
            'dateLastSeen': 'api.dateLastSeen',
            'dateBegin': 'api.dateBegin',
            'dateEnd': 'api.dateEnd',
            'dateReg': 'api.dateReg',
            'dateAdd': 'api.dateAdd',
            'dateIncident': 'api.dateIncident',
            'dateDetected': 'api.dateDetected',
            'dataCompromised': 'api.dataCompromised'
        },

        'Graph whois data': 'graph'
            # 'Hostname': 'graph.whois_summary.netname',
            # 'Provider': 'graph.provider',
            # 'Name': 'graph.whois.name',
            # 'Org': 'graph.whois.org',
            # 'Phone': 'graph.whois_summary.phone',
            # 'Email': 'graph.whois.email',
            # 'Address': 'graph.whois.address',
            # 'City': 'graph.whois.city',
            # 'Country': 'graph.whois_summary.country',
            # 'Person': 'graph.whois_summary.person',
            # 'ISP': "graph.whois_summary.isp",
            # 'asn': 'graph.whois_summary.asn',
        ,

        'credibility/reliability/admiraltyCode': {
            'credibility': 'api.evaluation.credibility',
            'reliability': 'api.evaluation.reliability',
            'admiraltyCode': 'api.evaluation.admiraltyCode',
        },
        'TLP': 'api.evaluation.tlp',

    }
    domain = {
        'Attribution': {'Collection name': 'api.collection',
                        'Threat actor': 'api.threatActor.name'},
        'Activity Dates': {
            # 'createdAt': 'graph.createdAt',
            # 'updatedAt': 'graph.updatedAt',
            'dateFirstSeen': 'api.dateFirstSeen',
            'dateLastSeen': 'api.dateLastSeen',
            'dateBegin': 'api.dateBegin',
            'dateEnd': 'api.dateEnd',
            'dateReg': 'api.dateReg',
            'dateAdd': 'api.dateAdd',
            'dateIncident': 'api.dateIncident',
            'dateDetected': 'api.dateDetected',
            'dataCompromised': 'api.dataCompromised'
        },

        'Graph whois data': {
            'createdAt': 'graph.createdAt',
            'updatedAt': 'graph.updatedAt',
            'NameServer': 'graph.whois.nameServers',
            'Registrar': 'graph.whois.registrar',
            'Name': 'graph.whois.name',
            'Org': 'graph.whois.org',
            'Phone': 'graph.whois.phone',
            'Email': 'graph.whois.email',
            'Address': 'graph.whois.address',
            'Status': 'graph.whois.status',
            'City': 'graph.whois.city',
            'Country': 'graph.whois.country',
            'Zone': 'graph.zone',
            'Aliases': 'api.aliases',
            'Category': 'api.category'
        },
        'credibility/reliability/admiraltyCode': {
            'credibility': 'api.evaluation.credibility',
            'reliability': 'api.evaluation.reliability',
            'admiraltyCode': 'api.evaluation.admiraltySCode',
        },
        'TLP': 'api.evaluation.tlp',
        # 'Hashes': {
        #     'hash': 'api.hash',
        #     'md5': 'api.params.hashes.md5',
        #     'sha1': 'api.params.hashes.sha1',
        #     'sha256': 'api.params.hashes.sha256',
        # },
        'Related  URLs': 'api.url',
    }
    hash = {
        'Attribution': {'Collection name': 'api.collection',
                        'Threat actor': 'api.threatActor.name',
                        'Threat actor list': 'api.threatActorList.name',
                        'TA list': 'api.threatList.name',
                        'Title': 'api.threatList.title',
                        },
        'Name/Aliases': {
            'Name': 'api.name',
            'Malware list': 'api.malwareList.name',
            'Aliases': 'api.aliases',
            'Aliases list': 'api.malwareAliasList',

            'Category': 'api.category'},
        'Activity Dates': {
            'createdAt': 'graph.created_at',
            'updatedAt': 'graph.updated_at',
            'dateFirstSeen': 'api.dateFirstSeen',
            'dateLastSeen': 'api.dateLastSeen',
            'dateBegin': 'api.dateBegin',
            'dateEnd': 'api.dateEnd',
            'dateReg': 'api.dateReg',
            'dateAdd': 'api.dateAdd',
            'dateIncident': 'api.dateIncident',
            'dateDetected': 'api.dateDetected',
            'dataCompromised': 'api.dataCompromised'
        },
        'File details': {'Author': 'contacts.account',
                         'Сountry': 'threatActor.sourceCountry',
                         'Type': 'api.type'},
        'Info': {
            'Credibility': 'api.evaluation.credibility',
            'Reliability': 'api.evaluation.reliability',
            'AdmiraltyCode': 'api.evaluation.admiraltyCode',
            'Threat level': 'api.threatLevel',
        },
        'CVE': {
            'name':'api.cveList.name',
            'vendor': 'api.cveList.products.vendor',
            'product':'api.cveList.products.product'
        },
        'Tags': 'api.expertise',
        'Hashes': {
            'md5': 'api.params.hashes.md5',
            'sha1': 'api.params.hashes.sha1',
            'sha256': 'api.params.hashes.sha256',

        }
    }
    ip_graph={'Graph whois data':{
                'firstSeen': 'firstSeen',
                'lastSeen':'lastSeen',
                'created':'valuesRaw.created',
                'modified':'valuesRaw.modified',
                'org': 'values.org',
                'organisation': 'values.organisation',
                'org-name': 'valuesRaw.org-name',
                'md5':'md5',
                'address':'values.address',
                'addr':'valuesRaw.address',
                'contact':'values.contact',
                'country':'values.country',
                'descr': 'values.descr',
                'email': 'values.email',
                'inetnum': 'values.inetnum',
                'nethandle': 'values.nethandle',
                'netname': 'values.netname',

                'origin': 'values.origin',
                'parent': 'values.parent',
                'phone': 'values.phone',
                'role': 'values.role',
                'source': 'values.source',
                'status': 'values.status',
                'type': 'values.type',
    }}

    def select_mask(self, tip):
        if tip == 'domain':
            return self.domain
        elif tip == 'ip':
            return self.ip
        elif tip == 'hash':
            return self.hash
        elif tip == 'ip_graph':
            return self.ip_graph

    def read_conf(self, path):
        with open("../local/inputs.conf") as conf:
            for item in conf:
                if path in item:
                    c = item.split('=')
                    return c[1].strip()

    def reform_data(self, item):
        for key, value in item.items():
            if type(value) == dict:
                reform = item[key]
                item[key] = ''
                _ = {k: v for k, v in reform.items() if v}
                for k, v in _.items():
                    if type(v) == list:
                        if type(v[0]) == list:
                            if len([i for i in v[0] if i]) > 0:
                                item[key] += f'{k}: {", ".join(i for i in v[0] if i)}\n'
                        else:
                            if len([i for i in v if i])>0:
                                item[key] += f'{k}: {", ".join(i for i in v if i)}\n'
                    else:
                        item[key] += f'{k}: {v}\n'
                # for k, v in _.items():
                #     if type(v) == list:
                #         item[key] += f'{k}: {", ".join(v)}\n'
                #     else:
                #         item[key] += f'{k}: {v}\n'
            elif type(value) == list:
                reform = item[key]
                item[key] = ''
                item[key] = '\n'.join(reform)
            elif type(value) is None:
                item[key] = ''
        return item

    def reform_graph_domain(self, item):
        whois_list = ParserHelper.find_element_by_key(item, 'whois.values')
        list_list = []
        update_whois_list = [whois_item for whois_item in whois_list if whois_item is not None]
        if update_whois_list:  # [None]
            for whois_item in update_whois_list:
                list_list.append(len([i for i in whois_item.values() if i]))
            ParserHelper.set_element_by_key(item, 'whois', whois_list[list_list.index(max(list_list))])
            return item
        else:
            item['whois'] = ''
            return item

    def reform_graph_ip(self, item, tip):
        logger.info("Start graph search")
        whois_story = ParserHelper.find_element_by_key(item,'whoisHistory.data')[0]
        values = ParserHelper.find_element_by_key(whois_story, 'values')
        values_raw = ParserHelper.find_element_by_key(whois_story, 'valuesRaw')
        parse_item = ''
        for i in range(len(whois_story)):

            whois_story[i].pop('parsed')
            pared_ip = ParserHelper.find_by_template(whois_story[i], self.select_mask('ip_graph'))
            for key, value in pared_ip.items():
                if type(value) == dict:
                    a = {k: v for k, v in pared_ip[key].items() if v}
                    for k, v in a.items():
                        if type(v) == list:
                            parse_item += f'{k}: {", ".join(v)}\n'
                        else:
                            parse_item += f'{k}: {v}\n'
                    parse_item += '\n'
        return parse_item



    def search_data(self, poller, tip, api_update_response, graph_response, search_value):
        main_response = []
        comb_response = {'api': '', 'graph': graph_response}

        if api_update_response:
            for response in api_update_response:
                api_path = response['apiPath']
                label = response['label']
                generation = poller.create_update_generator(api_path, query=f'{tip}:{search_value}')
                for portion in generation:
                    for item in portion.raw_dict['items']:
                        comb_response['api'] = item
                        result = ParserHelper.find_by_template(comb_response, self.select_mask(tip))

                        if api_path == 'ioc/common' and tip == 'hash':
                            result['Hashes'] = {
                                'md5': item['hash'][0],
                                'sha1': item['hash'][1],
                                'sha256': item['hash'][2]
                            }
                        result['Attribution']['Collection name'] = label

                        main_response.append(self.reform_data(result))
            logger.info(main_response)

            return main_response
        else:
            result = ParserHelper.find_by_template(comb_response, self.select_mask(tip))
            # result['Attribution'] = "WHOIS information"
            main_response.append(self.reform_data(result))
            return main_response

    def create_comb_response(self, poller, search_value, graph_response, tip):
        api_response = poller.global_search(search_value)
        api_update_response = [response for response in api_response if response['apiPath'] in self.path_list]

        result = self.search_data(poller, tip, api_update_response, graph_response, search_value)
        logger.info("Response from api {}".format(result))

        return result

    def generate(self):
        session_key = super().service.__dict__.get('token')
        USERNAME = Credentials.get_username(session_key)
        logger.info("Start uploading data")

        API_KEY = Credentials.get_api_key(session_key, USERNAME)

        PROXY_ENABLED = self.read_conf('enable_proxy')
        SEARCH_VALUE = self.search
        logger.info("Search for value {}".format(SEARCH_VALUE))
        try:
            poller = TIPoller(username=USERNAME, api_key=API_KEY,api_url='https://ti.facct.ru/api/v2/')
            poller.set_verify(True)
            poller.set_product(
                product_type="SIEM",
                product_name="Splunk",
                integration_name="FACCT Threat Intelligence",
                integration_version='1.4.2'
                )
            if PROXY_ENABLED == '1':
                PROXY_ADDRESS = self.read_conf('proxy_address')
                PROXY_PORT = self.read_conf('proxy_port')
                PROXY_PROTOCOL = self.read_conf('proxy_protocol')
                poller.set_proxies(
                    PROXY_PROTOCOL,PROXY_ADDRESS,PROXY_PORT
                )

            if validators.domain(SEARCH_VALUE):
                graph_response = self.reform_graph_domain(poller.graph_domain_search(SEARCH_VALUE))
                response = self.create_comb_response(poller, SEARCH_VALUE, graph_response, 'domain')
                for item in response:
                    yield item
            elif validators.ipv4(SEARCH_VALUE):
                logger.info("Value detected as IP")
                graph_response = self.reform_graph_ip(poller.graph_ip_search(SEARCH_VALUE), 'ip_graph')
                response = self.create_comb_response(poller, SEARCH_VALUE, graph_response, 'ip')
                logger.info("Response from api {}".format(response))
                for item in response:
                    logger.info(item)
                    yield item
            elif validators.sha256(SEARCH_VALUE) or validators.sha1(SEARCH_VALUE) or validators.md5(SEARCH_VALUE):
                response = self.create_comb_response(poller, SEARCH_VALUE, '', 'hash')

                for item in response:
                    yield item
            elif validators.url(SEARCH_VALUE):
                SEARCH_VALUE = urllib.parse.urlsplit(SEARCH_VALUE).netloc
                if validators.domain(SEARCH_VALUE):
                    graph_response = self.reform_graph_domain(poller.graph_domain_search(SEARCH_VALUE))
                    response = self.create_comb_response(poller, SEARCH_VALUE, graph_response, 'domain')
                    for item in response:
                        yield item
                elif validators.ipv4(SEARCH_VALUE):
                    graph_response = poller.graph_ip_search(SEARCH_VALUE)
                    response = self.create_comb_response(poller, SEARCH_VALUE, graph_response, 'ip')
                    for item in response:
                        yield item
            else:
                yield 'Our team is working on adding new fields'

        finally:
            poller.close_session()


dispatch(facctsearch, sys.argv, sys.stdin, sys.stdout, __name__)
