import json
import sys
import urllib.parse

import requests
import splunk.entity as entity

from util import init_logger


logger = init_logger('base.conf')


def error_out(message):
    sys.stdout.write(message + '\n')
    sys.stderr.write(message + '\n')
    sys.exit(1)


class AvalonAPI(object):
    def __init__(self, url, proxies):
        self.base_url = make_https(url)
        self._session = requests.Session()
        # Base headers
        if proxies:
            self._session.proxies.update(proxies)
        self._session.headers.update({
            'User-Agent': 'Avalon Splunk Connector',
        })

    def login(self, token):
        # NOTE: This does not account for 2FA
        self._session.headers.update({
            'Authorization': 'Token ' + token,
        })

    def open(self, method, url, **kwargs):
        self._session.headers.update({
            'Content-Type': 'application/json',
        })
        if 'data' in kwargs:
            kwargs['data'] = json.dumps(kwargs['data'])
        target = urllib.parse.urljoin(self.base_url, url)
        logger.info("Target URL is"+target)
        return self._session.request(method, target, **kwargs, verify=True)

    @classmethod
    def from_config(cls, app, entity_path, login=True):
        api_key = ""
        proxy_password = ""
        proxies = ""
        storage_passwords=app.service.storage_passwords
        for credential in storage_passwords:
            try:
                if json.loads(credential.content.get('clear_password'))['avalon_api_key']:
                    api_key = json.loads(credential.content.get('clear_password'))['avalon_api_key']
            except:
                pass
            try:
                if json.loads(credential.content.get('clear_password'))['proxy_password']:
                    proxy_password = json.loads(credential.content.get('clear_password'))['proxy_password']
            except:
                pass
        app_name = app._metadata.searchinfo.app
        session_key = app._metadata.searchinfo.session_key
        configs = entity.getEntities('/admin/conf-splunk_ta_avalon_settings', namespace=app_name,
                                    sessionKey=session_key, owner='nobody')
        try:
            proxy_enabled = int(configs['proxy']['proxy_enabled'])
        except:
            proxy_enabled = 0
        if proxy_enabled:
            try:
                proxy_username = configs['proxy']['proxy_username']
            except:
                proxy_username = ""
            if proxy_username and proxy_password:
                logger.info("username and password for proxy available")
                proxies = {'https': configs['proxy']['proxy_type']+'://'+proxy_username +':'+ proxy_password+'@'+configs['proxy']['proxy_url']+':'+configs['proxy']['proxy_port']}
            else:
                logger.info("username and password for proxy not available")
                proxies = {'https': configs['proxy']['proxy_type']+'://'+configs['proxy']['proxy_url']+':'+configs['proxy']['proxy_port']}
        instance = cls(configs['additional_parameters']['api_url'],proxies)
        if login:
            instance.login(api_key)
            #instance.login(avalon_conf['token'])
        #cls._node_limit = avalon_conf['node_limit']
        return instance


class Workspace(object):
    endpoint = '/api/graph'

    @staticmethod
    def list(api):
        resp = api.open('GET', '{}/token'.format(Workspace.endpoint))
        resp = resp.json()
        if not resp or 'data' not in resp:
            error_out('Failed to call API to list workspaces.'+str(resp))
        workspaces = resp['data']
        return workspaces

    @staticmethod
    def get(api, wid):
        resp = api.open('GET', '{}/{}/token'.format(Workspace.endpoint, wid))
        resp = resp.json()
        if not resp or 'data' not in resp:
            error_out('Failed to call API to get workspace by ID.')
        return resp

    @staticmethod
    def create(api, name, tlp='r'):
        data = {
            'Title': name,
            'Summary': 'Workspace created via Splunk connector.',
            'TLP': tlp,
        }
        resp = api.open(
            'POST', '{}/new/token'.format(Workspace.endpoint), data=data)
        # TODO: Follow the path returned (Avalon demo returns bad path for now)
        resp = resp.json()
        if not resp or 'data' not in resp:
            error_out('Failed to call API to create workspace.')
        wid = resp['data']['path'].split('/')[-2]
        return wid

    @staticmethod
    def add_nodes(api, wid, nodes):
        #node_limit = getattr(api, '_node_limit', 50)
        #if len(nodes) > int(node_limit):
        #    raise RuntimeError('Only {} entries may be submitted at a time'
        #                       .format(node_limit))
        # TODO: Add node attributes and edges!
        data = {
            'nodes': [{"term": n} for n in nodes],
            'edges': [],
        }
        resp = api.open(
            'POST', '{}/{}/bulkimport/token'.format(Workspace.endpoint, wid),
            data=data)
        resp = resp.json()
        if not resp or 'data' not in resp:
            error_out('Failed to call API to add nodes to workspace.')
        return resp

    @staticmethod
    def get_nodes(api, wid, wuuid):
        # resp = api.open('GET', '/export/graph/{}/{}/json'.format(wid, wuuid))
        resp = api.open('GET', '/api/workspaces/{}/'.format(wid, wuuid))
        resp = resp.json()
        if not resp or 'data' not in resp:
            error_out('Failed to call API to get nodes from workspace.')
        return resp

def make_https(url):
    url_prefix = url.split(":")
    if url_prefix[0] == "http":
        logger.info("Replacing http to https in url.")
        url = url.replace("http", "https")
        logger.info("Modified url is {}".format(url))
    elif url_prefix[0] == "https":
        logger.info("Url is valid.")
    else:
        error_out('Invalid URL. Please check API URL in Configuration Tab --> Add-on Settings. if unsure set URL to: `https://avalon.kingandunion.com/`')
    return url
