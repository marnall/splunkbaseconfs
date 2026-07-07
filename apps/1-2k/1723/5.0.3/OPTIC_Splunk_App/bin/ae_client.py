import os, os.path, sys, tarfile, shutil
import urllib, json, time
import settings
sys.path.append(os.path.join(settings.get_app_home(), 'lib', 'python2.7', 'site-packages'))
import requests
import settings
from util import utils
from report_download_handler import Report_download_handler

IOC_TYPES = set(['ip', 'domain', 'url', 'email', 'md5'])
IOC_FIELDS = ['asn', 'classification', 'confidence', 'country', 'date_first', 'date_last', 'detail', 'id', 'itype', 
              'lat', 'lon', 'lookup_key_value', 'maltype', 'org', 'resource_uri', 'severity', 'source',
              'actor', 'campaign', 'tipreport', '_time', 'last_time', 'link', 'type']

IOC_FILED_MAP = {
                'classification': 'is_public', #(true: public, false: private)
                'date_first': 'created_ts',
                'date_last': 'modified_ts',
                'detail': 'tags',
                'lat': 'latitude',
                'lon': 'longitude' 
                }

def _parse_time(timestr, logger):
    return utils._parse_time(timestr, logger)
    
def clearn_down_tm_files():
    tmp_dir = settings.get_working_dir()
    for f in os.listdir(tmp_dir):
        if f.startswith('threat_model'):
            f_path = os.path.join(tmp_dir, f)
            if os.path.isdir(f_path):
                shutil.rmtree(f_path)
            else:
                os.remove(f_path)

class AeClient(object):
    def __init__(self, splunka, username, apikey, client_type='tm_data', **kwargs):
        self.username = username
        self.apikey = apikey
        
        self.type =  kwargs.get('client_type')
        self.root_url = kwargs.get('root_url')
        self.base_url =  self.root_url + 'threat_model_reports'
        
        self.proxy_host = kwargs.get('proxy_host')
        self.proxy_port = kwargs.get('proxy_port')
        self.proxy_user = kwargs.get('proxy_user')
        self.proxy_password = kwargs.get('proxy_password')
        self.https_proxy = 'https://%s:%s@%s:%s' % (self.proxy_user, self.proxy_password, self.proxy_host, self.proxy_port)
        self.proxy_dict = None
        self.logger = kwargs.get('logger')
        
        if self.proxy_host and self.proxy_port:
            self.proxy_dict = {'https':self.https_proxy}
        self.splunka = splunka
        self.kvsm = splunka.get_kvsm()
        
        if client_type == 'reports':
            self.report_download_handler = Report_download_handler(self)
            return
        
        self.kvs_data = {}
        for kvs in self._get_kvs_names():
            self.kvs_data[kvs] = []
        self.id_ioc_map = {}
        self.nested_tip_set = set()
        self.tipreport_download_versions = []
        
    def _get_kvs_names(self):
        kvs_names = ['ts_iocs_%s' % t for t in IOC_TYPES]
        kvs_names.extend(['tm_tipreport'])
        return kvs_names
    
    def _get_auth_paras(self):
        data = {"username":self.username, "api_key":self.apikey}
        data = urllib.urlencode(data)
        return data
          
    def _get_tm_url(self, endpoint):
        url = '%s/%s/?%s' % (self.base_url, endpoint, self._get_auth_paras())
        if endpoint == 'breach':
            url += '&snapshot_ts__gt=2016-03-29'
        return url
    
    def _get_snapshot_file(self, download_url):
        try:
            i1 = download_url.index('threat_model_')
            i2 = download_url.index('?')
            return os.path.join(settings.get_working_dir(), download_url[i1:i2])
        except Exception as e:
            self.logger.error('Failed to extract snapshot file string from download_url: %s' % download_url)
            self.logger.exception(e)
            
    def _load_tm_data(self, endpoint, json_files):
        for json_file in json_files:
            with open(json_file, 'r') as file_handler:
                response_content = file_handler.read()
                json_obj = json.loads(response_content);
                self._load_json(endpoint, json_obj)
                
    def _get_tm_name(self, endpoint):
        tm_name = endpoint
        if endpoint == 'bulletins' or endpoint == 'breach':
            tm_name = 'tipreport'
        return tm_name
    
    def _get_mapped_ioc(self, ioc):
        mapped_ioc = {}
        for key in IOC_FIELDS:
            ioc_key = IOC_FILED_MAP.get(key)
            if not ioc_key:
                ioc_key = key
            value = ioc.get(ioc_key)
            if ioc_key == 'is_public':
                value = 'public' if value else 'private'
            elif ioc_key == 'tags' and value:
               value = [str(v.get('name')) for v in value]
               value = ','.join(value)
                
            if not value:
                value = ''
            mapped_ioc[key] = value
                  
        mapped_ioc['_key'] = ioc['id']     
        mapped_ioc['lookup_key_value'] = ioc.get('value')
        mapped_ioc['_time'] = _parse_time(ioc.get('created_ts'), self.logger)
        meta= ioc.get('meta')
        if meta:
            mapped_ioc['severity'] = meta.get('severity')
            
        if self.ioc_actor_map:
            actor = self.ioc_actor_map.get(ioc['id'])
            if actor:
                mapped_ioc['actor'] = actor
            
        return mapped_ioc
    
    def _load_json(self, endpoint, json_obj):
        tm_row = json_obj
        self._load_one_row(endpoint, tm_row)
    
    def _load_one_row(self, endpoint, tm_row):
        tm_id = tm_row['id']
        data = {}
        for key, value in tm_row.items():
            if key == 'intelligence':
                new_value = []
                for ioc in value:
                    if not ioc.get('status') == 'active': 
                        continue
                    ioc_type = ioc['type']
                    if ioc_type not in IOC_TYPES: 
                        continue
                    ioc_id = int(ioc.get('id'))  
                    mapped_ioc = self.id_ioc_map.get(ioc_id)
                    if mapped_ioc:
                        pass    #to do: test timestamp for get replace the older one?
                    else: 
                        mapped_ioc = self._get_mapped_ioc(ioc)
                        self.id_ioc_map[ioc_id] = mapped_ioc
                        self.kvs_data['ts_iocs_%s' % ioc_type].append(mapped_ioc)      
                    new_value.append(ioc_id)
                value = new_value
                data['ioc_list'] = value
            elif key == 'tags':
                if value:
                    value = [str(v) for v in value]
                    value = ','.join(value)

            data[key] = '%s' % value
            
        data['_key'] = tm_id
        data['endpoint'] = endpoint
        data['owner_org_name'] = 'Anomali Labs'
        data['_time'] = _parse_time(data.get('created_ts'), self.logger)
#         data['link'] = '%s%s' % ('https://ui.threatstream.com/tip/', tm_id)
        data['last_time'] = data.get('modified_ts')
        
        #repalce links
        body = data.get('body')
        if body:
            data['body'] = self.replace_tipreport_links(body)
            
        kvs = 'tm_%s' % self._get_tm_name(endpoint)
        self.kvs_data[kvs].append(data)

    #to redo: use regylar expression 
    def replace_tipreport_links(self, body):
        old_link_1 = 'href="https://ui.threatstream.com/tip/'
        new_link = 'href="/app/%s/_ts_bulletin_detail?bid=' % settings.APP_NAME
        body_1 = self._replace_tipreport_links(body, old_link_1, new_link)
        old_link_2 = 'href="/tip/'
        body_2 = self._replace_tipreport_links(body_1, old_link_2, new_link)
        return body_2
    
    #to redo: use regylar expression 
    def _replace_tipreport_links(self, body, old_link, new_link):   
#         self.logger.debug('body: %s' % body)
        if body.find(old_link) <= 0:
            return body
        
        old_link_len = len(old_link)
        new_body = ''
        i0 = 0
        
        while True:
            new_string= None
            link_ix = i0 + body[i0:].find(old_link)
            if link_ix > 0:
                id_ix0 = link_ix + old_link_len
                id_len = body[id_ix0:].find('"')
                if id_len > 0:
                    id_ix1 = id_ix0 + id_len
                    id = body[id_ix0:id_ix1]
                    old_string = body[link_ix: id_ix1 + 1]
                    new_string = new_link + id + '" target="_blank"'
#                     self.logger.debug('old_string: %s, new_string: %s' % (old_string, new_string))
#                     self.logger.debug('id: %s, link_ix: %s, id_ix1: %s, body[link_ix: id_ix1]: %s ' % (id, link_ix, id_ix1, body[link_ix: id_ix1]))

            if new_string:
                new_body += body[i0:link_ix] + new_string
                i0 = id_ix1 + 1
            else: 
                new_body += body[i0:]
                break
                
        return new_body
                    

    def _download_tm_data(self, endpoint):
        url = self._get_tm_url(endpoint)
        response = requests.get(url, headers={'Content-Type':'application/json'}, proxies=self.proxy_dict)
        if response.status_code >= 400:
            self.logger.error("Failed to retrieve url error_code=%s reason=%s url=%s" % (response.status_code, response.content, url))
            raise Exception("Failed to retrieve url error_code=%s reason=%s" % (response.status_code, response.content))
        result = response.content
        content_json = json.loads(result)
#         self.logger.debug('content_json: %s' % content_json)
        objects = content_json['objects']
        self.logger.info('aeclient> %s items in the downloaded list for %s' % (len(objects), endpoint))
#         download_urls = [item.get('download_url') for item in objects ]
        download_urls = [] 
        for item in objects:
            id = str(item.get('id'))
            version = str(item.get('intel_version'))
            prop = 'tipreport_download_version_%s' % id
            saved_version_state = utils.get_runtime_state(prop, self.kvsm)
            is_new = True
            if saved_version_state:
                prev_version = saved_version_state.get('value')
                if version == prev_version:
                   is_new = False 
            download_url = item.get('download_url')
            
            if is_new:
                self.tipreport_download_versions.append({'prop': prop, 'value': version})
            else:
                msg = 'skip downloading snapshot: downloaded before - id=%s download_url=%s' % (id, download_url)
                self.logger.info(msg)
                print(msg)
                continue
            
            custom_config = item.get('custom_config')
            if custom_config:
                associated_entities = custom_config.get('associated_entities')
                if associated_entities:
                    nested_list = associated_entities.get('tipreport')
                    for nested in nested_list:
                         self.nested_tip_set.add(str(nested))
            download_urls.append(download_url)

        gz_files = []
        for download_url in download_urls:
            self.logger.debug('aeclient> download_url: %s' % download_url)
            gz_file = self._download_tm_item_data(download_url)
            if gz_file:
                gz_files.append(gz_file)

        unzipped_gz_files = self.extract_gz_files(settings.get_working_dir(), gz_files)
        self._load_tm_data(endpoint, unzipped_gz_files)
           
    def _download_tm_item_data(self, download_url):
        response = requests.get(download_url, stream=True, proxies=self.proxy_dict)
        if response.status_code >= 400:
            raise Exception("Failed to retrieve url error_code=%s reason=%s" % (response.status_code, response.content))
        dest = self._get_snapshot_file(download_url)
        if not dest:
            return None
        with open(dest, "wb") as file_handler:
            for chunk in response.iter_content(chunk_size=16*1024):
                if chunk:
                    file_handler.write(chunk)
                    file_handler.flush()
        return dest
                    
    def fixup_tm_ids(self, tm_name):
        if not tm_name == 'tipreport':
            return
        tipreport_data = self.kvs_data.get('tm_tipreport')
        for tip in tipreport_data:
            if tip.get('id') in self.nested_tip_set:
                tip['composition'] = 'nested'
                
            ioc_list = tip.get('ioc_list')
            if ioc_list:
                for id in ioc_list:
                    ioc = self.id_ioc_map.get(id)
                    if ioc:
                        tip_list = ioc.get('tipreport')
                        if not tip_list:
                            tip_list = []
                        tip_list.append(int(tip.get('id')))
                        ioc['tipreport'] = tip_list
                
                del tip['ioc_list']
        
        for ioc in self.id_ioc_map.values():
            tip_list = ioc['tipreport']
            tip_list = '%s' % tip_list if tip_list else ''
            ioc['tipreport'] = tip_list
            

    def save_to_kv_stores(self):
        for kvs in self._get_kvs_names():
            data = self.kvs_data.get(kvs)
            if data:
                self.kvsm.add_kvs_batch(kvs, data)
                print('%s items saved to kvs: %s' % (len(data), kvs))
                self.logger.debug('%s items saved to kvs: %s' % (len(data), kvs))
                self.splunka.audit_log(type='download_tm_data', event='message:=data saved to kv store;kvs:=%s;data_sz=%s' % (kvs, len(data)))

        for data in self.tipreport_download_versions:
            data['_key'] = data.get('prop')
            data['_time'] = time.time()
            if not data.get('first_time'):
                data['first_time'] = data['_time']
           
        utils.set_runtime_states_batch(self.tipreport_download_versions, self.kvsm)

    def download_tm_data(self, ioc_actor_map):
        self.logger.debug('aeclient> download_tm_data...')
        self.ioc_actor_map = ioc_actor_map
        self._download_tm_data('bulletins')
        self._download_tm_data('breach')
        
        self.fixup_tm_ids('tipreport')
            
        self.save_to_kv_stores()  
        clearn_down_tm_files()

    def extract_gz_files(self, dest_dir, gz_files):
        tipreport_json_files = []
        for gz_file in gz_files:
            with tarfile.open(gz_file) as tar_handler:
                tar_handler.extractall(dest_dir)
                self.logger.info("extract tar file %s" % gz_file)
            unzip_dir = gz_file[:-7]
            tipreport_files = [os.path.join(unzip_dir, f) for f in os.listdir(unzip_dir) if f.startswith('tipreport') and f.endswith('.json')]
            if tipreport_files:
                tipreport_json_files.extend(tipreport_files)
        return tipreport_json_files

    def load_sample_tm_data(self, ioc_actor_map):
        self.logger.debug('aeclient> load_sample_tm_data...')
        self.ioc_actor_map = ioc_actor_map
                
        s_dir = settings.get_samples_dir()
        tipreport_files = [os.path.join(s_dir, f) for f in os.listdir(s_dir) if f.startswith('tipreport') and f.endswith('.json')]
        self._load_tm_data('bulletins', tipreport_files)
               
        self.fixup_tm_ids('tipreport')
            
        self.save_to_kv_stores()

    #This is not used - keep it for testing
    def load_sample_tm_data_by_tar_gz(self):
        self.logger.debug('aeclient> load_sample_tm_data...')
                
        s_dir = settings.get_samples_dir()
        bulletin_gz_files = [os.path.join(s_dir, f)  for f in os.listdir(s_dir) if f.startswith('threat_model_bulletin') and f.endswith('.tar.gz')]
        breach_gz_files = [os.path.join(s_dir, f)  for f in os.listdir(s_dir) if f.startswith('threat_model_breach') and f.endswith('.tar.gz')]
        
        bulletin_files = self.extract_gz_files(s_dir, bulletin_gz_files)
        breach_files = self.extract_gz_files(s_dir, breach_gz_files)
        
        self._load_tm_data('bulletins', bulletin_files)
        self._load_tm_data('breach', breach_files)
               
        self.fixup_tm_ids('tipreport')
            
        self.save_to_kv_stores()
        
        client.download_reports()
        
    def download_reports(self):
         self.report_download_handler.download_reports()
        
    def load_sample_reports(self):
       self.report_download_handler.load_sample_reports() 
   

              
