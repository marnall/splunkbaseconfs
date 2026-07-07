import os, sys
from settings import get_app_home
sys.path.append(os.path.join(get_app_home(), 'lib', 'python2.7', 'site-packages'))
import splunklib.client as client
import json

class TSSplunkConfigManager(object):

    def __init__(self, sessionKey, app='threatstream', owner='nobody', logger=None, service=None):
        self.sessionKey = sessionKey
        self.app_name = app
        self.owner = owner
        if service:
            self.service = service
        else:
            self.service = client.Service(token=sessionKey, owner=owner, app=app)
        self.dm_url = "datamodel/model/TS_Optic"
        self.summary_index_name = 'threatstream_summary'
        self.summary_searches = ['ThreatStream Summary - Generating Hourly Indicator Matches',
                                 'ThreatStream Summary - Generating Hourly Indicator Matches By URL']
        self.logger=logger

    def get_app_version(self):
        app = self.service.apps[self.app_name]
        return app.content['version']

    def enable_acceleration(self, flag=0, earliest_time='-1w'):
        value = '{"enabled":0, "earliest_time":"%s"}' % earliest_time
        if flag in [1, '1']:
            value = '{"enabled":1, "earliest_time":"%s"}' % earliest_time
        response = self.service.post(self.dm_url, output_mode='json', acceleration=value)
        if response['status'] not in (200, 201):
            if self.logger:
                self.logger.error("Failed to enable acceleration, reason=%s, status=%d" % (response['reason'], response['status']))
            else:
                print("Failed to enable acceleration, reason=%s, status=%d" % (response['reason'], response['status']))
        else:
            if self.logger:
                self.logger.info("Successfully enable acceleration (flag=%s, value=%s) " % (flag, value))
            else:
                print("Successfully enable acceleration (flag=%s, value=%s) " % (flag, value))

    def get_dm_acceleration(self):
        response = self.service.get(self.dm_url, output_mode='json')
        if response['status'] not in (200, 201):
            if self.logger:
                self.logger.error("Failed to get data model definition, reason=%s, status=%d" % (response['reason'], response['status']))
            else:
                print("Failed to get data model definition, reason=%s, status=%d" % (response['reason'], response['status']))
            return 0
        else:
            body = response['body']
            dm = body.readall()
            dm_json = json.loads(dm)
            dm_acce = dm_json['entry'][0]['content']['acceleration']
            if self.logger:
                self.logger.info("data model acceleration: %s" % dm_acce)
            else:
                print("data model acceleration: %s" % dm_acce)
            dm_acce_json = json.loads(dm_acce)
            return (dm_acce_json['enabled'], dm_acce_json['earliest_time'])

    def is_upload_enabled(self):
        response = self.service.get("admin/ts_setup/default", output_mode='json')
        if response['status'] not in (200, 201):
            if self.logger:
                self.logger.error("Failed to get myconfig, reason=%s, status=%d" % (response['reason'], response['status']))
            else:
                print("Failed to get myconfig, reason=%s, status=%d" % (response['reason'], response['status']))
            return 0
        else:
            body = response['body']
            myconfig = body.readall()
            myconfig_json = json.loads(myconfig)
            return myconfig_json['entry'][0]['content']['upload_enabled']

    def enable_saved_search(self, saved_search_name=None, flag=0):
        if self.logger:
            self.logger.info("enable_saved_search (saved_search_name=%s, flag=%s)" % (saved_search_name, flag))
        else:
            print("enable_saved_search (saved_search_name=%s, flag=%s)" % (saved_search_name, flag))
        if saved_search_name is None:
            return
        mysearch = self.service.saved_searches[saved_search_name]
        if flag in [0, '0']:
            mysearch.disable()
        else:
            mysearch.enable()

    def update_search_attributes(self, saved_search_name=None, attrs=None):
        if self.logger:
            self.logger.info("update_search_attributes (saved_search_name=%s, attr=%s)" % (saved_search_name, attrs))
        else:
            print("update_search_attributes (saved_search_name=%s, attr=%s)" % (saved_search_name, attrs))
        if attrs:
            mysearch = self.service.saved_searches[saved_search_name]
            mysearch.update(**attrs).refresh()

    def enable_summary_index(self, flag=0):
        if self.logger:
            self.logger.info("enable_summary_index(flag=%s)" % flag)
        else:
            print("enable_summary_index(flag=%s)" % flag)
        if flag in [1, '1']:
            index = self.service.indexes[self.summary_index_name]
            index.enable()
            for search_name in self.summary_searches:
                search = self.service.saved_searches[search_name]
                search.enable()
        else:
            index = self.service.indexes[self.summary_index_name]
            index.disable()
            for search_name in self.summary_searches:
                search = self.service.saved_searches[search_name]
                search.disable()

    def get_proxy(self):
        try:
            response = self.service.get("mycustom/customendpoint/setupentity", output_mode='json')
        except Exception as e:
            self.logger.exception(e)
            return (None, None)
            
        if response['status'] not in (200, 201):
            self.logger.error("Failed to get ts_setup/default, reason=%s, status=%d" % (response['reason'], response['status']))
            return (None, None)
        else:
            body = response['body']
            myconfig = body.readall()
            myconfig_json = json.loads(myconfig)
            return (myconfig_json['entry'][0]['content'].get('proxy_host'), myconfig_json['entry'][0]['content'].get('proxy_port'))
        
    def get_myconfig(self, name):
        response = self.service.get("mycustom/customendpoint/setupentity", output_mode='json')
        if response['status'] not in (200, 201):
            self.logger.error("Failed to get myconfig, reason=%s, status=%d" % (response['reason'], response['status']))
            return None
        else:
            body = response['body']
            myconfig = body.readall()
            myconfig_json = json.loads(myconfig)
            return myconfig_json['entry'][0]['content'][name]
