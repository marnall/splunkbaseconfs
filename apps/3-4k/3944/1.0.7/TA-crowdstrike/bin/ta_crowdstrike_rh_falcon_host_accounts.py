import base64
import datetime
import hashlib
import hmac
import urllib
import urlparse
import uuid
import os
import sys

import splunk.admin as admin

LIB_FOLDER_NAME = 'ta_crowdstrike'
folder_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(folder_path, LIB_FOLDER_NAME))

from ta_crowdstrike import requests
from splunktaucclib.rest_handler import base
from splunktalib.common import util
from splunktaucclib.rest_handler import validator
import crowdstrike_utils as csutils


util.remove_http_proxy_env_vars()


def _prepare_url(url, app_id, query=None):
    query = query or {}
    query['appId'] = app_id
    url_parsed = urlparse.urlparse(url)
    url_parsed = getattr(url_parsed, '_replace')(query=urllib.urlencode(query))
    return urlparse.urlunparse(url_parsed)


def _get_auth_headers(url, api_key, api_uuid):
    date = datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    content_md5 = ""
    canonical_uri, canonical_query = _canonicalize_url(url)
    request_string = "\n".join(['GET', content_md5, date, canonical_uri, canonical_query])
    digest = hmac.new(str(api_key), str(request_string), digestmod=hashlib.sha256).digest()
    signature = base64.b64encode(digest).decode()
    return [
        ('Authorization', 'cs-hmac %s:%s:customers' % (api_uuid, signature)),
        ('Date', date)
    ]


def _falcon_host_api_auth_gen(api_uuid, api_key):
    def _auth_api(request):
        for key, value in _get_auth_headers(request.url, api_key, api_uuid):
            request.headers[key] = value
        return request
    return _auth_api


def _canonicalize_query(query):
    query_items = sorted(urlparse.parse_qsl(query), key=lambda q: q[0])
    return urllib.urlencode(query_items)


def _canonicalize_url(url):
    url_parsed = urlparse.urlparse(url)
    port = None
    if url_parsed.port:
        if url_parsed.scheme == 'https' and url_parsed.port != 443:
            port = url_parsed.port
        elif url_parsed.scheme == 'http' and url_parsed.port != 80:
            port = url_parsed.port

    if port:
        canonical_uri = "%s:%d" % (url_parsed.hostname, port)
    else:
        canonical_uri = url_parsed.hostname

    canonical_uri = canonical_uri.strip('/')
    if url_parsed.path:
        path = url_parsed.path.strip('/')
        path = urllib.quote(path)
        canonical_uri = "%s/%s" % (canonical_uri, path)
    elif not canonical_uri.endswith('/'):
        canonical_uri += '/'

    return canonical_uri, _canonicalize_query(url_parsed.query)


class GetSessionKey(admin.MConfigHandler):
    def __init__(self):
        self.session_key = self.getSessionKey()


class CheckValidation(validator.Validator):

    def validate(self, value, data):
        # Initialize object of "GetSessionKey" class
        session_key_obj = GetSessionKey()
        # Obtain session key
        session_key = session_key_obj.session_key
        # Obtain proxy configurations
        proxies = csutils.get_proxy_info(session_key)
        # Get API type Query/Streaming
        api_type = data["api_type"]
        # Validate credentials according to the selected API type
        if api_type == "Query":
            base64string = base64.b64encode('%s:%s' % (data["api_uuid"], data["api_key"]))
            headers = {"Authorization": "Basic " + base64string, "Content-Type": "application/json"}
            rest_resp = requests.get("https://falconapi.crowdstrike.com/detects/queries/detects/v1", headers=headers,
                                     proxies=proxies)
            if rest_resp.status_code != 200:
                self._msg = "Authorization Failed! Please verify Username and Password of Query API"
                return False
        else:
            app_id = str(uuid.uuid4())[:8]
            url = _prepare_url('https://firehose.crowdstrike.com/sensors/entities/datafeed/v1', app_id)
            rest_resp = requests.get(url, timeout=30, auth=_falcon_host_api_auth_gen(data["api_uuid"], data["api_key"]),
                                     proxies=proxies)
            if rest_resp.status_code != 200:
                self._msg = "Authorization Failed! Please verify API UUID and API Key of Streaming API"
                return False
        return True


class Servers(base.BaseModel):
    """REST Endpoint of Server in Splunk Add-on UI Framework.
    """
    rest_prefix = 'ta_crowdstrike'
    endpoint = "configs/conf-crowdstrike_falcon_host_accounts"
    requiredArgs = {'api_uuid', 'api_key', 'endpoint', 'api_type'}
    validation_object = CheckValidation()
    validators = {'api_key': validation_object}
    encryptedArgs = {'api_key'}
    cap4endpoint = ''
    cap4get_cred = ''


if __name__ == "__main__":
    admin.init(base.ResourceHandler(Servers), admin.CONTEXT_APP_AND_USER)
