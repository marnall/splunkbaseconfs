import os, json, requests, csv
import settings
from util import utils
from _ast import TryExcept

IOC_FIELDS = ['asn', 'classification', 'confidence', 'country', 'date_first', 'date_last', 'detail', 'id', 'itype', 
              'lat', 'lon', 'lookup_key_value', 'maltype', 'org', 'resource_uri', 'severity', 'source',
              'actor', 'campaign', 'tipreport', '_time', 'last_time', 'link', 'type']

kvs_csv_fields_map = {
    '_time' : 'event_time',
    'sourcetype' : 'event.sourcetype',
    'source' : 'source',
    'host' : 'event.host',
#     'count' : 'string'
    'action' : 'event.action',
    'src' : 'event.src',
    'dest' : 'event.dest',
    'url' : 'event.url',
    'src_port' : 'event.src_port',
    'dest_port' : 'event.dest_port',
    'file_hash' : 'event.filehash',
    'src_user' : 'event.sender',
    'recipient' : 'event.receiver',
#threatstream enrichment
    'ts_asn' : 'asn',
    'ts_classification' : 'classification',
    'ts_confidence' : 'confidence',
    'ts_country' : 'country',
    'ts_date_first' : 'date_first',
    'ts_date_last' : 'date_last',
    'ts_detail' : 'detail',
    'ts_id' : 'id',
    'ts_itype' : 'itype',
    'ts_lat' : 'lat',
    'ts_lon' : 'lon',
    'ts_lookup_key_value' : 'indicator',
    'ts_maltype' : 'maltype',
    'ts_org' : 'org',
    'ts_resource_uri' : 'resource_uri',
    'ts_severity' : 'severity',
    'ts_source' : 'source',
    'ts_type' : 'type'
#     'ts_victim' : 'string'
#     'ts_actor_id' : 'string'
#     'ts_campaign_id' : 'string'
#     'ts_tb_id' : 'string'
#other enrichment
#     'anotation' : 'string'
#     'status' : 'string'
#     'updated_by' : 'string'
#     'last_modified' : 'string'
#     'match_type' : 'string'
    }

match_ts_fiels = [
    'ts_asn',
    'ts_classification',
    'ts_confidence',
    'ts_country',
    'ts_date_first',
    'ts_date_last',
    'ts_detail',
    'ts_itype',
    'ts_lat',
    'ts_lon',
    'ts_lookup_key_value',
    'ts_maltype',
    'ts_org',
    'ts_resource_uri',
    'ts_severity',
    'ts_source',
    'ts_type',
    'ts_victim',
    'ts_actor_id',
    'ts_campaign_id',
    'ts_tb_id']

def get_ioc_field(match_field):
    if not match_field.startswith('ts_'):
        return None
    if match_field == 'ts_actor_id':
        return 'actor'
    if match_field == 'ts_campaign_id':
        return 'campaign'
    if match_field == 'ts_tb_id':
        return 'tipreport'
    return match_field[3:]

class Report_download_handler(object):

    def __init__(self, aeclient):
        self.aeclient = aeclient
        self.logger = aeclient.logger
        self.base_url =  self.aeclient.root_url + 'report'
        
    def _enrich_ioc_info(self, kvs_row):
        ioc_kv_stores = ['ts_iocs_ip', 'ts_iocs_domain', 'ts_iocs_url', 'ts_iocs_md5', 'ts_iocs_email'] 
        for ioc_kvs in ioc_kv_stores:
            id = kvs_row.get('ts_id')
            if not id:
                continue
            ioc = self.aeclient.kvsm.get_kvs_item_by_id(ioc_kvs, id)
            if ioc:
                for match_field in match_ts_fiels:
                    ioc_field = get_ioc_field(match_field)
                    if ioc_field:
                        kvs_row[match_field] = ioc.get(ioc_field)
                break
        kvs_row['match_type'] = 'reports'
            
    def _get_url(self):
        url = '%s/?%s&report_configuration__query_type=harmony&result_mime_type=text/csv' % (self.base_url, self.aeclient._get_auth_paras())
        return url

    def _get_report_file(self, download_url):
        try:
            i2 = download_url.index('.csv?')
            i1 = download_url[0:i2].rfind('/') + 1
            return os.path.join(settings.get_working_dir(), download_url[i1:i2 + 4])
        except Exception as e:
            self.logger.error('Failed to extract report file string from download_url: %s' % download_url)
            self.logger.exception(e)

    def download_reports(self):
        self._download_reports()
        
    def load_sample_reports(self):
        s_dir = settings.get_working_dir()
        csv_files = [os.path.join(s_dir, f)  for f in os.listdir(s_dir) if f.endswith('.csv')]
        self._load_reports(csv_files)
        
    def _load_csv(self, csv_rows):
        kvs_data_to_save = []
        for row in csv_rows:
            self._load_one_row(row, kvs_data_to_save)
        self.aeclient.kvsm.add_kvs_batch('ts_ioc_matches', kvs_data_to_save)
    
    def _load_one_row(self, row, kvs_data_to_save):
        kvs_row = {}
        for kvs_field, csv_field in kvs_csv_fields_map.items():
            kvs_row[kvs_field] = row.get(csv_field)
        is_false_pos = False
        indicator = kvs_row.get('ts_lookup_key_value')
        if not utils.is_false_pos(indicator, self.aeclient.kvsm):
            self._enrich_ioc_info(kvs_row)
            kvs_data_to_save.append(kvs_row)
        
    def _load_reports(self, csv_files):
        for csv_file in csv_files:
            with open(csv_file, "rb") as csv_file:
                csv_reader = csv.reader(csv_file)
                first_row = None
                try:
                    first_row = csv_reader.next()
                except e:
                    self.logger.error('%s' % e)
                    return
                csv_rows = [dict(zip(first_row, row)) for row in csv_reader]
                self._load_csv(csv_rows)
                
    def _download_reports(self):
        url = self._get_url()
        self.logger.debug('url: %s' % url)
        response = requests.get(url, headers={'Content-Type':'application/json'}, proxies=self.aeclient.proxy_dict)
        if response.status_code >= 400:
            self.logger.error("Failed to retrieve url error_code=%s reason=%s url=%s" % (response.status_code, response.content, url))
            raise Exception("Failed to retrieve url error_code=%s reason=%s" % (response.status_code, response.content))
        result = response.content
        content_json = json.loads(result)
        self.logger.debug('content_json: %s' % content_json)
        objects = content_json['objects']
        self.logger.debug('aeclient> %s items in the downloaded list' % len(objects))
        added = set()
        download_urls = []
        for item in objects:
            download_url = item.get('result_s3_url')
            if download_url not in added:
                added.add(download_url)
                download_urls.append(download_url)
        
        csv_files = []
        for download_url in download_urls:
            csv_file = self._download_report(download_url)
            if csv_file:
                csv_files.append(csv_file)
            
        self._load_reports(csv_files)
                
    def _download_report(self, download_url):
        dest = self._get_report_file(download_url)
        if os.path.exists(dest):
            msg = 'skip downloading ae report: downloaded before - file: %s' % dest
            self.logger.info(msg)
            print(msg)
            return None
        response = requests.get(download_url, stream=True, proxies=self.aeclient.proxy_dict)
        if response.status_code >= 400:
            raise Exception("Failed to retrieve url error_code=%s reason=%s" % (response.status_code, response.content))
        if not dest:
            return None
        with open(dest, "wb") as file_handler:
            for chunk in response.iter_content(chunk_size=16*1024):
                if chunk:
                    file_handler.write(chunk)
                    file_handler.flush()
        msg = 'Report file downloaded: %s' % dest
        self.logger.info(msg)
        print(msg)
        return dest                

        
