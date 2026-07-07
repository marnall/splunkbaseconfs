import os, sys
from settings import get_app_home
import splunklib.client as client
from logger import setup_logger
import json
import urllib

logger = setup_logger('ts_collector_install')

class TSConfigManager(object):

    def __init__(self, sessionKey=None, app='threatstream_dc', owner='nobody', port=8089, **kwargs):
        self.sessionKey = sessionKey
        self.app_name = app
        self.owner = owner
        if sessionKey:
            self.service = client.Service(token=sessionKey, owner=owner, app=app, port=port)
        else:
            host = kwargs.get('host') if kwargs.get('host') else 'localhost'
            port = int(kwargs.get('port')) if kwargs.get('port') else 8089
            username=kwargs.get('username')
            password = kwargs.get('password')
            self.service = client.connect(host=host, port=port, username=username, password=password, owner=owner, app=app)

    def get_app_version(self):
        app = self.service.apps[self.app_name]
        return app.content['version']

    def enable_acceleration(self, dm_name, flag=0):
        dm_url = 'datamodel/model/%s' % dm_name
        value = '{"enabled":0, "earliest_time":"-1w"}'
        if flag in [1, '1']:
            value = '{"enabled":1, "earliest_time":"-1w"}'
        response = self.service.post(dm_url, output_mode='json', acceleration=value)
        if response['status'] not in (200, 201):
            logger.error("Failed to enable acceleration, reason=%s, status=%d" % (response['reason'], response['status']))
        else:
            logger.info("Successfully enable acceleration (flag=%s, value=%s) " % (flag, value))

    def is_acceleration_enabled(self, dm_name):
        dm_url = 'datamodel/model/%s' % dm_name
        response = self.service.get(dm_url, output_mode='json')
        if response['status'] not in (200, 201):
            logger.error("Failed to get data model definition, reason=%s, status=%d" % (response['reason'], response['status']))
            return 0
        else:
            body = response['body']
            dm = body.readall()
            dm_json = json.loads(dm)
            dm_acce = dm_json['entry'][0]['content']['acceleration']
            logger.info("data model acceleration: %s" % dm_acce)
            dm_acce_json = json.loads(dm_acce)
            return dm_acce_json['enabled']

    def is_upload_enabled(self):
        response = self.service.get("mycustom/customendpoint/setupentity", output_mode='json')
        if response['status'] not in (200, 201):
            logger.error("Failed to get myconfig, reason=%s, status=%d" % (response['reason'], response['status']))
            return 0
        else:
            body = response['body']
            myconfig = body.readall()
            myconfig_json = json.loads(myconfig)
            return myconfig_json['entry'][0]['content']['upload_enabled']

    def enable_saved_search(self, saved_search_name=None, flag=0):
        if saved_search_name is None:
            return
        mysearch = self.service.saved_searches[saved_search_name]
        if flag in [0, '0']:
            mysearch.disable()
        else:
            mysearch.enable()

    def get_proxy(self):
        response = self.service.get("mycustom/customendpoint/setupentity", output_mode='json')
        if response['status'] not in (200, 201):
            logger.error("Failed to get myconfig, reason=%s, status=%d" % (response['reason'], response['status']))
            return (None, None)
        else:
            body = response['body']
            myconfig = body.readall()
            myconfig_json = json.loads(myconfig)
            return (myconfig_json['entry'][0]['content'].get('proxy_host'), myconfig_json['entry'][0]['content'].get('proxy_port'))

    def get_configured_saved_searches(self):
        response = self.service.get("mycustom/customendpoint/setupentity", output_mode='json')
        if response['status'] not in (200, 201):
            logger.error("Failed to get myconfig, reason=%s, status=%d" % (response['reason'], response['status']))
            return None
        else:
            body = response['body']
            myconfig = body.readall()
            myconfig_json = json.loads(myconfig)
            search_string = myconfig_json['entry'][0]['content'].get('saved_searches')
            saved_searches = search_string.split(",")
            return saved_searches       

    def get_myconfig(self, name):
        response = self.service.get("mycustom/customendpoint/setupentity", output_mode='json')
        if response['status'] not in (200, 201):
            logger.error("Failed to get myconfig, reason=%s, status=%d" % (response['reason'], response['status']))
            return None
        else:
            body = response['body']
            myconfig = body.readall()
            myconfig_json = json.loads(myconfig)
            return myconfig_json['entry'][0]['content'][name]

    def update_dm_acl(self, dm_name, sharing='app', owner='nobody', app=None):
        url = "datamodel/model/%s/acl" % dm_name
        kwargs = {"output_mode":"json", "sharing":sharing, "owner":"nobody", "perms.read":"*", "perms.write":"admin"}
        response = self.service.request(url, method="post", headers=None, body=urllib.urlencode(kwargs), owner=owner, app=app, sharing=sharing)
        if response['status'] not in (200, 201):
            logger.error("Failed to update data model acl, reason=%s, status=%d" % (response['reason'], response['status']))
        else:
            logger.info("Successfully update data model acl (permission=%s) " % (sharing))
