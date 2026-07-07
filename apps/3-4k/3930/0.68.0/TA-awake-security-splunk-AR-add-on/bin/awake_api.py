# encoding = utf-8

import sys
sys.path.insert(0,'/opt/splunk/etc/apps/TA-awake-splunk-add-on/bin/')

import abc
import json
import pprint
import weakref

import requests

# Avoid messages like
# .../connectionpool.py:821: InsecureRequestWarning:
#   Unverified HTTPS request is being made.
#   Adding certificate verification is strongly advised.
# pylint: disable=ungrouped-imports
try:
    import requests.packages.urllib3 as urllib3
except ImportError:
    import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ApiConnection(object):
    DEFAULT_URI_PREFIX = 'https://'

    def __init__(self, helper=None):
        self.hostname = helper.get_global_setting("awake_host")
        self.user = helper.get_global_setting("username")
        self.passwd = helper.get_global_setting("password")
        self._verify_https = False  # To ignore the https certs
        self._login_api = LoginApi(self.hostname, helper=helper, verify=self._verify_https)
        self.api = UnconnectedApi(weakref.proxy(self), helper=helper)
        self._helper = helper

    def connect(self):
        self.api = ConnectedApi(
            self.hostname, self.get_auth(), helper=self._helper,
            verify=self._verify_https)

    def get_auth(self):
        return self._get_access_auth()

    def _get_access_auth(self):
        headers = {'Content-Type': 'application/json;charset=utf-8'}
        data = {
            'loginUsername': self.user,
            'loginPassword': self.passwd
        }
        # access auth lasts 1 hour
        authtoken_info = self._login_api.authtoken.post(headers=headers, data=data)
        if 'token' not in authtoken_info:
            raise RuntimeError('Failed to get authtoken: %s' %
                               pprint.pformat(authtoken_info))
        return authtoken_info['token']['value']

class UnconnectedApi(object):
    # pylint: disable=too-few-public-methods

    def __init__(self, parent, helper=None):
        self._parent = parent
        self._helper = helper

    def __getattr__(self, attr):
        # This will override the pointer (self.api) to this instance, then
        # attempt to continue with the call
        self._parent.connect()
        return getattr(self._parent.api, attr)


class Api(object):
    __metaclass__ = abc.ABCMeta

    POST = 'post'
    ALLOWED_METHODS = set([POST])

    def __init__(self, hostname, helper=None, verify=False):
        self.hostname = hostname
        self._helper = helper
        self._verify = verify

    def _rest_uri(self, path):
        return 'https://%s/%s' % (self.hostname, path)

    @abc.abstractmethod
    def _rest_headers(self, extra_headers=None):
        pass

    def _rest_resource(self, path, methods):
        return ApiRestResource(weakref.proxy(self), self._rest_uri(path),
                               methods, helper=self._helper)

class ConnectedApi(Api):
    def __init__(self, base_uri, access_auth, helper=None, verify=False):
        super(ConnectedApi, self).__init__(base_uri, helper=helper, verify=verify)
        self._access_auth = access_auth
        self._helper = helper

        # Endpoints
        srr = self._rest_resource

        # v2/awakeapi
        self.awakeapi = ApiMidpoint()
        self.awakeapi.lookup = ApiMidpoint()
        self.awakeapi.lookup.ip = srr(
            '/api/v2/GetDeviceByIPAndTimestamp', [self.POST])
        self.awakeapi.lookup.email = srr(
            'awakeapi/v1/lookup/email', [self.POST])
        self.awakeapi.lookup.device = srr(
            'awakeapi/v1/lookup/device', [self.POST])
        self.awakeapi.lookup.domain = srr(
            '/api/v2/GetDomainDetails', [self.POST])

    def _rest_headers(self, extra_headers=None):
        ret = {
            'Authentication': 'access %s' % self._access_auth,
            'Content-Type': 'application/json;charset=utf-8',
        }
        if extra_headers is not None:
            ret.update(extra_headers)
        return ret

class LoginApi(Api):
    def __init__(self, base_uri, helper=None, verify=False):
        super(LoginApi, self).__init__(base_uri, helper=helper, verify=verify)
        # Endpoints
        self.authtoken = self._rest_resource('awakeapi/v1/authtoken', [self.POST])

    def _rest_headers(self, extra_headers=None):
        ret = {}
        if extra_headers is not None:
            ret.update(extra_headers)
        return ret

def _invalid_endpoint(*a, **kw):
    # This means we have not specified this value as a method
    raise LookupError('Invalid endpoint')


class ApiRestResource(object):
    ALLOWED_METHODS = Api.ALLOWED_METHODS
    post = _invalid_endpoint

    def __init__(self, api, uri, methods, helper=None):
        self._api = api
        self._uri = uri
        for method in methods:
            func = self._endpoint_method(method)
            setattr(self, method, ApiEndpoint(api, uri, func))
        self._helper = helper

    def _endpoint_method(self, method):
        if method not in self.ALLOWED_METHODS:
            raise ValueError('Invalid method: %s, expected a member of %s' %
                             (method, sorted(self.ALLOWED_METHODS)))
        return {
            Api.POST: self._gen_post,
        }[method]

    def _gen_post(self, uri):
        ''' Helper for ApiRestEndpoint instances '''
        # Drop the 'json' argument as the 'data' is always formated as json
        # object and gets passed to as 'json=' in 'requests.post()' call.
        def post(data=None, params=None, headers=None):
            req = requests.post(
                uri, headers=self._api._rest_headers(extra_headers=headers),
                params=params, json=data, verify=self._api._verify)
            try:
                return req.json()
            except ValueError as e:
                return {'__error': repr(e), '__resp': req.content, '__status_code': req.status_code}
        return post

class ApiEndpoint(object):
    def __init__(self, api, uri, method):
        self._api = api
        self._uri = uri
        self._method = method

    @property
    def __call__(self):
        return self._method(self._uri)

class ApiMidpoint(object):
    ''' Just a placeholder to store attributes on '''
