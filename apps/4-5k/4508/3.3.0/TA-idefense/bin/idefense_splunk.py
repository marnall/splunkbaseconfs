from idefense_sdk import idefense_vulnerability
import json
from idefense_sdk import idefense_threatindicator
import logging
import os
import sys
import time
import uuid
import csv
import unicodedata
import copy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import splunklib.client
from splunklib.searchcommands import Option, validators
from splunk.clilib import cli_common as cli

APP_NAME = "TA-idefense"

def convertlist_to_string(item):
    if type(item) == list:
        return "|".join(item)
    else:
        return item

class iDefense_splunk_base():
    '''Base class for idefense splunk objects'''

    def __init__(self, logfilename=APP_NAME):
        self.__APP_NAME = APP_NAME
        self.__CONF_NAME = "idefense"
        self.TIMEFORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
        self.TIMEFORMATstrftime = "%Y-%m-%dT%H:%M:%S.000Z"

        self.THREATLIST_FILE_PATH = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', self.__APP_NAME, 'lookups')

        self.IP_INTEL_FIELD_MAP = {"_key": "ip", "confidence": "weight", "last_published": "time",
                                   "threat_types": "description", "domain": "domain"}

        self.VULN_INTEL_FIELD_MAP = {"_key": "cve", "cvss2_base_score": ["cvss2_base_score", "cvss"],
                                     "cvss3_base_score": "cvss3_base_score", "severity": "severity",
                                     "title": "signature", "uuid": "signature_id"}

        self.DOMAIN_INTEL_FIELD_MAP = {"_key": "domain", "confidence": "weight", "last_published": "time",
                                       "threat_types": "description", "ip": "ip"}
        self.URL_INTEL_FIELD_MAP = {"_key": ["url", "http_referrer"], "confidence": "weight", "last_published": "time",
                                    "threat_types": "description", "ip": "ip", "domain": "domain"}
        self.FILE_INTEL_FIELD_MAP = {'key': {'inherits': False, 'maps': 'key'},
                                     'md5': {'inherits': False, 'maps': 'key'},
                                     'threat_types': {'inherits': True, 'maps': 'threat_types'},
                                     'severity': {'inherits': True, 'maps': 'severity'},
                                     'last_seen_as': {'inherits': True, 'maps': 'last_seen_as'},
                                     'confidence': {'inherits': False, 'maps': 'confidence'},
                                     'last_published': {'inherits': False, 'maps': 'relationship_last_published'},
                                     'last_seen': {'inherits': False, 'maps': 'last_seen'},
                                     'uuid': {'inherits': False, 'maps': 'uuid'},
                                     'sha1': {'inherits': False, 'maps': 'sha1'},
                                     'sha256': {'inherits': False, 'maps': 'sha256'},
                                     'parent_relationship': {'inherits': False, 'maps': 'relationship'},
                                     'parent_key': {'inherits': True, 'maps': '_key'},
                                     'parent_type': {'inherits': True, 'maps': 'type'},
                                     'type': {'inherits': False, 'maps': 'type'},
                                     'malware_family': {'inherits': False, 'maps': 'malware_family'},
                                     'threat_campaigns': {'inherits': True, 'maps': 'threat_campaigns'},
                                     'mentioned_by': {'inherits': True, 'maps': 'mentioned_by'},
                                     'seen_at': {'inherits': True, 'maps': 'seen_at'}}

        self.FILE_INTEL_THREAT_FIELD_MAP_MD5 = {"_key": "file_hash", "confidence": "weight", "last_published": "time",
                                                "threat_types": "description"}
        self.FILE_INTEL_THREAT_FIELD_MAP_SHA1 = {"sha1": "file_hash", "confidence": "weight", "last_published": "time",
                                                 "threat_types": "description"}
        self.FILE_INTEL_THREAT_FIELD_MAP_SHA256 = {"sha256": "file_hash", "confidence": "weight",
                                                   "last_published": "time", "threat_types": "description"}

        self.IP_THREATLIST_FILE_NAME = "acti_ip_ioc.csv"
        self.DOMAIN_THREATLIST_FILE_NAME = "acti_domain_ioc.csv"
        self.URL_THREATLIST_FILE_NAME = "acti_url_ioc.csv"
        self.FILE_THREATLIST_FILE_NAME = "acti_file_ioc.csv"
        self.VULN_FILE_NAME = "acti_vuln.csv"

        self.IP_KVSTORE = "acti_threatindicator_ip"
        self.DOMAIN_KVSTORE = "acti_threatindicator_domain"
        self.URL_KVSTORE = "acti_threatindicator_url"
        self.FILE_KVSTORE = "acti_threatindicator_file"
        self.VULN_KVSTORE = "acti_vulnerability"

        self.DOWNLOAD_LIMIT = 50000
        self.MAX_KEY_SIZE = 1000

        self.__logfilename = logfilename      # Default Log File

        self.logger = self.__setlogger()

        self.__setproxy()

        self.params = {}
        self.Output_Threatlist = False
        self.Output_KVstore = False

        self.results = None

    def connect(self, splunk_service, end_point_type="Threat_Indciator"):
        # sessionkey depends on how the class is accessed, hence needs to be passed in
        self.splunk_service = splunk_service
        self.splunk_service.namespace.update({'owner': 'nobody'})
        self.__api_key = self.__getapikey()
        self.idefense = self.__setidefenseobject(end_point_type)

        splunk_info = self.splunk_service.info
        Splunk_Version = splunk_info['version']
        self.logger.info(f"The Client Splunk Version is {Splunk_Version}")

        TA_Version = self.splunk_service.apps[APP_NAME]['version']
        self.logger.info(f"The TA version is {TA_Version}")

        Splunk_Product_Type = splunk_info['product_type']
        self.logger.info(f"Running on Splunk {Splunk_Product_Type}")

        self.idefense.session.headers.update(
            {"User-Agent":
             f'ACTI-TA/{TA_Version} Splunk {Splunk_Product_Type}/{Splunk_Version}'
             }
        )
        self.logger.info(
            f"User Agent was set to: ACTI-TA/{TA_Version} Splunk {Splunk_Product_Type}/{Splunk_Version}")

    def __setlogger(self):
        self.log_level = cli.getConfStanza(self.__CONF_NAME, 'default')['log_level']
        logger = logging.getLogger('iDefense')
        FORMAT = "[%(levelname)-8s|%(asctime)s|%(filename)s|%(lineno)s|ID:{}] Method %(funcName)s %(message)s".\
                 format(uuid.uuid4())
        logging_file = f'{os.getenv("SPLUNK_HOME", "/opt/splunk")}/var/log/splunk/{self.__logfilename}.log'
        console_handler = logging.StreamHandler()
        file_handler = logging.FileHandler(logging_file)
        formatter = logging.Formatter(FORMAT)
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        logger.setLevel(self.log_level)
        console_handler.setLevel(self.log_level)
        file_handler.setLevel(self.log_level)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        return logger

    def __setproxy(self):
        cfg = cli.getConfStanza(self.__CONF_NAME, 'proxy')
        self.HTTP_PROXY = cfg.get('http_proxy')
        self.HTTPS_PROXY = cfg.get('https_proxy')
        self.NO_PROXY = cfg.get('no_proxy')
        self.enable_proxy = False
        enable_proxy = cfg.get('enable')
        if enable_proxy in ["true", "True"]:
            self.enable_proxy = True

    def __getapikey(self):
        self.logger.debug('Getting API Key')
        storage_passwords = self.splunk_service.storage_passwords
        for credential in storage_passwords:
            if credential.realm == 'idefense':
                # get cleartext pwd if present, else get the encrypted one
                self.logger.debug(
                    'Auth token successfully retrieved from passwords store')
                return credential.content.get('clear_password', 'password')
        else:
            self.logger.warning('No credentials found in the store, exiting.')
            raise AttributeError("API Key not found for iDefense")

    def __setidefenseobject(self, end_point_type=None):
        '''
        params: end_point_type to choose various IDefense apis (fundamental, vulnerability etc)
        '''
        proxies = None
        if any((len(self.HTTP_PROXY) > 0, len(self.HTTPS_PROXY) > 0, len(self.NO_PROXY) > 0)) and self.enable_proxy:
            if 'localhost' not in self.NO_PROXY:
                self.NO_PROXY = self.NO_PROXY + ", localhost"

            if '127.0.0.1' not in self.NO_PROXY:
                self.NO_PROXY = self.NO_PROXY + ", 127.0.0.1"

            proxies = {'http': self.HTTP_PROXY,
                       'https': self.HTTPS_PROXY,
                       'no_proxy': self.NO_PROXY}

        if end_point_type and end_point_type.upper() == "VULN":

            idefense_object = idefense_vulnerability.Vulnerability(auth_token=self.__api_key,
                                                                   logger_level=self.log_level, proxies=proxies)
        else:

            idefense_object = idefense_threatindicator.ThreatIndicator(auth_token=self.__api_key,
                                                                       logger_level=self.log_level, proxies=proxies)

        return idefense_object

    def Output_threatlist(self, field_map, file_path, filename):
        threatlist = []
        fields = list(field_map.values())
        # flatten fields
        fields_flat = []
        for sublist in fields:
            if type(sublist) == str:
                fields_flat.append(sublist)
            else:
                for item in sublist:
                    fields_flat.append(item)

        fields = fields_flat

        if not os.path.exists(file_path):
            os.makedirs(file_path)

        relationship_keys = ["mentioned_by", "seen_at", "threat_campaigns"]

        for result in self.results:
            threat_dict = {}
            for key, value in field_map.items():
                if key in result.keys():
                    if type(value) == list:
                        for val in value:
                            threat_dict.update({val: convertlist_to_string(result[key])})
                    if type(value) == str:
                        threat_dict.update({value: convertlist_to_string(result[key])})
                if key in ("domain", "ip"):
                    for key_rel in relationship_keys:
                        if key_rel in result.keys():
                            for items in result[key_rel]:
                                if items["type"] == key:
                                    if key in threat_dict.keys():
                                        threat_dict["key"] = threat_dict["key"] + \
                                            "," + convertlist_to_string(items["key"])
                                    else:
                                        threat_dict.update(
                                            {value: convertlist_to_string(items["key"])})
            threatlist.append(threat_dict)

        header_needed = False
        if not(os.path.exists(os.path.join(file_path, filename))):
            header_needed = True
        else:
            file_is_empty = os.stat(os.path.join(file_path, filename)).st_size == 0
            if file_is_empty:
                header_needed = True

        with open(os.path.join(file_path, filename), "a+") as threatlist_file:
            writer = csv.DictWriter(
                threatlist_file, fieldnames=fields, quoting=csv.QUOTE_NONE, escapechar="\\")
            if header_needed:
                writer.writeheader()
            writer.writerows(threatlist)

        self.logger.info(f"Data written to csv file {filename} successfully")

    def uploadResultstoKVStore(self, kvname):
        """
        Writes data directly into specified kvstore.

        Args:
            results (list):
                Data to be inserted into splunk kvstore
            kvname (str)
                name of the kv store
        """
        self.logger.debug('called with kvname:{}'.format(kvname))

        kvstore = self.splunk_service.kvstore[kvname].data

        local_results = copy.deepcopy(self.results)

        for item_result in local_results:
            item_result.update({'_key': truncateUTF8length(item_result["_key"], self.MAX_KEY_SIZE)})

        for i in range(0, len(local_results), 100):
            retry_count = 5
            while retry_count > 0:
                try:
                    self.logger.info(f"Pushing {i} to {i+100} records to KV store")
                    kvstore.batch_save(*local_results[i:i + 100])
                    break
                except splunklib.binding.HTTPError as e:
                    retry_count = retry_count -1
                    self.logger.error(f"HTTP Error occured when updating Splunk KV store {kvname} when pushing records at position {i} to {i+500}. Retries left {retry_count}")
                except Exception as ex:
                    retry_count = retry_count -1
                    self.logger.error(f"Error occured when updating Splunk KV store {kvname} when pushing records at position {i} to {i+100}. Exception {sys.exc_info()[0]}. Retries left {retry_count}")
        
        self.logger.info(f"KV store {kvname} updated with the results.")

    def converttoepoch(self, isotimestamp):
        return int(time.mktime(time.strptime(isotimestamp, self.TIMEFORMAT)))


class iDefense_search_commands(iDefense_splunk_base):
    def __init__(self, logfilename="TA-iDefense"):
        iDefense_splunk_base.__init__(self, logfilename)

    def indexresults(self, index, sourcetype):
        self.logger.debug(
            'called with index:{}, sourcetype:{}'.format(index, sourcetype))
        splunk_index = self.splunk_service.indexes[index]
        with splunk_index.attached_socket(source=self.__APP_NAME, sourcetype=sourcetype) as sock:
            for result in self.results:
                try:
                    sock.send(json.dumps(result))
                except Exception:
                    import traceback
                    stack = traceback.format_exc()
                    self.logger.error(
                        "Exception occured while indexing data: {}".format(stack))

    def formatresults(self, type):
        ''' Formats results from IG to something Splunk Data Model'''
        results_new = []
        for result in self.results:

            if type == "vuln":
                result["key"] = result["key"].lower()
            result.update({"_key": result.pop("key")})
            if "last_published" in result.keys():
                result.update({"last_published": self.converttoepoch(result.pop("last_published"))})
            if "last_modified" in result.keys():
                result.update({"last_modified": self.converttoepoch(result.pop("last_modified"))})
            if "last_seen" in result.keys():
                result.update({"last_seen": self.converttoepoch(result.pop("last_seen"))})
            results_new.append(result)
        self.results = results_new

    def outputSearchResultsGenerator(self):
        ''' Generator used to output reults from IG as search results in Splunk UI'''
        for result in self.results:
            yield {'_time': result['last_published'], '_raw': json.dumps(result)}

    def setVulnOptions(self):
        '''Validates and sets options passed in the search'''
        earliest = Option(
            doc='''
            **Syntax:** **earliest=***Earliest time in epoch time*
            **Description:**Earliest time to get from''',
            require=False, validate=validators.Match("earliest", r"^[0-9]+.[0-9]+$")
        )

        latest = Option(
            doc='''
            **Syntax:** **latest=***Latest time in epoch time*
            **Description:**Latest time to get from''',
            require=False, validate=validators.Match("latest", r"^[0-9]+.[0-9]+$")
        )

        severity_from = Option(
            doc='''
            **Syntax:** **severity_from =***Serverity rating between 1 and 5
            **Description:**Minimum severity''',
            require=False, validate=validators.Match("severity_from", r"^[0-9]+$")
        )

        severity_to = Option(
            doc='''
            **Syntax:** **severity_from =***Serverity rating between 1 and 5*
            **Description:**Max severity''',
            require=False, validate=validators.Match("severity_to", r"^[0-9]+$")
        )

        cvss2_base_score_from = Option(
            doc='''
            **Syntax:** **severity_from =***cvss2_base_score rating between 1 and 10
            **Description:**Minimum severity''',
            require=False, validate=validators.Match("severity_from", r"^[0-9]+$")
        )

        cvss2_base_score_to = Option(
            doc='''
            **Syntax:** **severity_from =***cvss2_base_score rating between 1 and 10*
            **Description:**Max severity''',
            require=False, validate=validators.Match("severity_to", r"^[0-9]+$")
        )

        cvss3_base_score_from = Option(
            doc='''
            **Syntax:** **severity_from =***cvss3_base_score rating between 1 and 10
            **Description:**Minimum severity''',
            require=False, validate=validators.Match("severity_from", r"^[0-9]+$")
        )

        cvss3_base_score_to = Option(
            doc='''
            **Syntax:** **severity_from =***cvss3_base_score rating between 1 and 10*
            **Description:**Max severity''',
            require=False, validate=validators.Match("severity_to", r"^[0-9]+$")
        )

        Output_KVstore = Option(
            doc='''
            **Syntax:** **fields=***True/False....*
            **Description:**Updates results to iDefense KVstore if set to true''',
            require=False, validate=validators.Boolean()
        )

        Output_Threatlist = Option(
            doc='''
            **Syntax:** **fields=***True/False....*
            **Description:**saves result as threatlist if set to true''',
            require=False, validate=validators.Boolean()
        )

        cve_id = Option(
            doc='''
            **Syntax:** **fields=***cve-2020-11234*
            **Description:**CVE ID''',
            require=False, validate=validators.Fieldname()
        )

        return (earliest, latest, severity_from, severity_to, cvss2_base_score_from,
                cvss2_base_score_to, cvss3_base_score_from, cvss3_base_score_to, cve_id, Output_KVstore,
                Output_Threatlist)

    def setoptions(self):
        '''Validates and sets options passed in the search'''
        earliest = Option(
            doc='''
            **Syntax:** **earliest=***Earliest time in epoch time*
            **Description:**Earliest time to get from''',
            require=False, validate=validators.Match("earliest", r"^[0-9]+.[0-9]+$")
        )

        latest = Option(
            doc='''
            **Syntax:** **latest=***Latest time in epoch time*
            **Description:**Latest time to get from''',
            require=False, validate=validators.Match("latest", r"^[0-9]+.[0-9]+$")
        )

        confidence_from = Option(
            doc='''
            **Syntax:** **confidence_from =***Confidence Score between 0 and 100*
            **Description:**Minimum Confidence''',
            require=False, validate=validators.Match("confidence_from", r"^[0-9]+$")
        )

        confidence_to = Option(
            doc='''
            **Syntax:** **confidence_to=***Confidence Score between 0 and 100*
            **Description:**Maximum Confidence''',
            require=False, validate=validators.Match("confidence_to", r"^[0-9]+$")
        )

        severity_from = Option(
            doc='''
            **Syntax:** **severity_from=***Severity Score between 0 and 3*
            **Description:**Minimum Severity''',
            require=False, validate=validators.Match("severity_from", r"^[0-9]+$")
        )

        severity_to = Option(
            doc='''
            **Syntax:** **confidence_to=***Confidence Score between 0 and 3*
            **Description:**Maximum Severity''',
            require=False, validate=validators.Match("severity_to", r"^[0-9]+$")
        )

        fields = Option(
            doc='''
            **Syntax:** **fields=***field1+field2+field3....*
            **Description:**Fields to get back'''
        )

        Output_Threatlist = Option(
            doc='''
            **Syntax:** **fields=***True/False....*
            **Description:**saves result as threatlist if set to true''',
            require=False, validate=validators.Boolean()
        )

        Output_KVstore = Option(
            doc='''
            **Syntax:** **fields=***True/False....*
            **Description:**Updates results to iDefense KVstore if set to true''',
            require=False, validate=validators.Boolean()
        )

        return (earliest, latest, severity_to, severity_from, confidence_from, confidence_to, fields,
                Output_Threatlist, Output_KVstore)

    def format_options_file(self, earliest, latest, Output_Threatlist, Output_KVstore):
        if earliest:
            self.params.update({"last_published__from": earliest})

        if latest:
            self.params.update({"last_published__to": latest})

        if Output_Threatlist:
            self.Output_Threatlist = True

        if Output_KVstore:
            self.Output_KVstore = True

    def format_options(self, earliest, latest, severity_to, severity_from, confidence_from, confidence_to, fields,
                       Output_Threatlist, Output_KVstore):
        '''formats search passed during search to queries that IG can understand'''
        if earliest:
            self.params.update({"last_published__from": time.strftime(self.TIMEFORMATstrftime,
                                                                      time.gmtime(int(float(earliest))))})

        if latest:
            self.params.update({"last_published__to": time.strftime(self.TIMEFORMATstrftime,
                                                                    time.gmtime(int(float(latest))))})

        if confidence_from:
            self.params.update({"confidence__from": confidence_from})

        if confidence_to:
            self.params.update({"confidence__to": confidence_to})

        if severity_from:
            self.params.update({"severity__from": severity_from})

        if severity_to:
            self.params.update({"severity__to": severity_to})

        if fields:
            self.params.update({"fields": fields})

        if Output_Threatlist:
            self.Output_Threatlist = True

        if Output_KVstore:
            self.Output_KVstore = True

    def format_vuln_options(self, earliest, latest, severity_from, severity_to,
                            cvss2_base_score_from, cvss2_base_score_to, cvss3_base_score_from, cvss3_base_score_to,
                            cve_id, Output_KVstore, Output_Threatlist):
        '''formats search passed during search to queries that IG can understand'''
        if earliest:
            self.params.update({"last_modified__from": time.strftime(self.TIMEFORMATstrftime,
                                                                     time.gmtime(int(float(earliest))))})

        if latest:
            self.params.update({"last_modified__to": time.strftime(self.TIMEFORMATstrftime,
                                                                   time.gmtime(int(float(latest))))})

        if severity_from:
            self.params.update({"severity__from": severity_from})

        if severity_to:
            self.params.update({"severity__to": severity_to})

        if cvss2_base_score_from:
            self.params.update({"cvss2_base_score__from": cvss2_base_score_from})

        if cvss2_base_score_to:
            self.params.update({"cvss2_base_score__to": cvss2_base_score_to})

        if cvss3_base_score_from:
            self.params.update({"cvss3_base_score__from": cvss3_base_score_from})

        if cvss3_base_score_to:
            self.params.update({"cvss3_base_score__to": cvss3_base_score_to})

        if cve_id:
            self.params.update({"key": cve_id})

        if Output_KVstore:
            self.Output_KVstore = True

        if Output_Threatlist:
            self.Output_Threatlist = True

    def collectfileintel(self, session_key, kvstorename):
        ''' Collects file intel from previously collected indicators that are stored in the specified kvstore.
        Parameters:
        Session_Key: Session Key to connect to Splunk Backend
        kvstorename: The KVstore from which to collect file intel
                    (ie URL, IP or Domain KVstore that was downloaded earlier )

        Returns: Nothing

        Updates: Self.Results with the file hashes dict
        '''
        self.connect(session_key)
        field_map = self.FILE_INTEL_FIELD_MAP
        more = True
        self.results = []
        delta = 2000
        skip = 0

        kvstore = self.splunk_service.kvstore[kvstorename].data

        query = {}
        query.update({'files': {"$ne": None}})
        query.update({'last_published': {}})
        if 'last_published__from' in self.params.keys():
            query['last_published'].update({"$gte": float(self.params['last_published__from'])})

        if 'last_published__to' in self.params.keys():
            query['last_published'].update({"$lte": float(self.params['last_published__to'])})

        files = {}
        while more and len(self.results) < self.DOWNLOAD_LIMIT:
            local_results = kvstore.query(query=json.dumps(query), limit=delta, skip=skip)

            if len(local_results) > 0:
                self.logger.info(f'Got {len(files)} results for TI query with params: {format(self.params)}')
            else:
                self.logger.info(f'Got no results for TI query with params: {format(self.params)}')

            for entry in local_results:

                for file_entry in entry['files']:
                    temp_dict = {}
                    for field in self.FILE_INTEL_FIELD_MAP:
                        if (self.FILE_INTEL_FIELD_MAP[field]['inherits']):
                            if self.FILE_INTEL_FIELD_MAP[field]['maps'] in entry:
                                temp_dict.update({field: entry[self.FILE_INTEL_FIELD_MAP[field]['maps']]})
                        else:
                            if self.FILE_INTEL_FIELD_MAP[field]['maps'] in file_entry:
                                temp_dict.update({field: file_entry[self.FILE_INTEL_FIELD_MAP[field]['maps']]})
                    files.update({temp_dict['key']: temp_dict})
            more = not(len(local_results) < delta)
            skip += delta

        self.results = list(files.values())
        self.formatresults(type = "file")

        if self.Output_Threatlist:
            for file_intel_map in [self.FILE_INTEL_THREAT_FIELD_MAP_MD5, self.FILE_INTEL_THREAT_FIELD_MAP_SHA1,
                                   self.FILE_INTEL_THREAT_FIELD_MAP_SHA256]:
                self.Output_threatlist(file_intel_map, self.THREATLIST_FILE_PATH, self.FILE_THREATLIST_FILE_NAME)

        if self.Output_KVstore:
            self.uploadResultstoKVStore(self.FILE_KVSTORE)

    def queryiDefense(self, session_key, type):
        ''' Queries IG indicator api for the speficied type
        Arguments:
            session_key: session_key for connecting to Splunk
            type: string to specify indicator type, ie "ip", "domain" or "url"'''

        self.connect(session_key, end_point_type=type)

        if type == "ip":
            field_map = self.IP_INTEL_FIELD_MAP
            threatlistfile = self.IP_THREATLIST_FILE_NAME
            query = self.idefense.queryIp
            kv_store = self.IP_KVSTORE

        if type == "domain":
            field_map = self.DOMAIN_INTEL_FIELD_MAP
            threatlistfile = self.DOMAIN_THREATLIST_FILE_NAME
            query = self.idefense.queryDomain
            kv_store = self.DOMAIN_KVSTORE

        if type == "url":
            field_map = self.URL_INTEL_FIELD_MAP
            threatlistfile = self.URL_THREATLIST_FILE_NAME
            query = self.idefense.queryUrl
            kv_store = self.URL_KVSTORE

        if type == "vuln":
            field_map = self.VULN_INTEL_FIELD_MAP
            threatlistfile = self.VULN_FILE_NAME
            query = self.idefense.queryVulnerability
            kv_store = self.VULN_KVSTORE

        more = True
        self.results = []
        page = 0
        result_size = 0

        while more and len(self.results) < self.DOWNLOAD_LIMIT:
            page = page + 1
            self.params.update({"page": page})
            results = query(self.params)

            if not("results" in results.keys()):
                self.logger.info(f'Got no results for TI query with params: {format(self.params)}')
                return

            result_size += len(results['results'])
            self.logger.info(f"Got {result_size}/{results['total_size']} results for TI query with params:\
                              {format(self.params)}")

            self.results.extend(results['results'])

            if len(self.results) == self.DOWNLOAD_LIMIT:
                self.logger.warn(
                    "Max Limit for TI query reached, not getting anymore results")

            more = results['more']

        self.formatresults(type = type)

        if self.Output_Threatlist:
            self.Output_threatlist(
                field_map, self.THREATLIST_FILE_PATH, threatlistfile)

        if self.Output_KVstore:
            self.uploadResultstoKVStore(kv_store)


class syswriter:
    def __init__(self):
        self.sysout = sys.stdout

    def write(self, s):
        if type(s) == str:
            self.sysout.write(s)
        if type(s) == bytes:
            self.sysout.buffer.write(s)

    def flush(self):
        return self.sysout.flush()

def truncateUTF8length(unicodeStr, maxsize):
    norm_string = unicodedata.normalize('NFC', unicodeStr)
    return norm_string.encode("utf-8")[:maxsize].decode("utf-8", errors="ignore")
