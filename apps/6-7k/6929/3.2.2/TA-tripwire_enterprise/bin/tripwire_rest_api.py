import configparser
import inspect
import json
import logging
import os
import time
from distutils.version import LooseVersion
from urllib.parse import quote_plus, urlencode

import requests
from requests.auth import HTTPBasicAuth

# In Ubuntu 20.04, the version of OpenSSL fails the SSL connection to TE, because it tries to use DH with a small key
# The following statement disables DH in favor of a "better" cipher
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += ":!DH"


def ensure_list(obj):
    if not isinstance(obj, list):
        obj = [obj]
    return obj


logger = logging.getLogger('tripwire')


class TWRestAPI:
    """Provides the means to easily call the TE Rest API."""

    def __init__(
        self, url, hostname, username, password, port=443, ssl=True, adapter=None, verify_ssl_cert=True
    ):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        self.base_url = 'http%s://%s:%d/%s' % ('s' if ssl else '', hostname, port, url)
        self.num_calls = 0
        self.urls = set()
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(username, password)

        cwd = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        cfg = configparser.ConfigParser()
        configpath = os.path.join(os.path.split(cwd)[0], 'local', 'te_setup.conf')
        cfg.read(configpath, encoding="utf-8-sig")

        if (verify_ssl_cert): 
            try:
                location = cfg.get('te_parameters','te_ssl_cert_path',fallback="")
                logger.info("Enabling cert validatation")
                #location = cfg.get('te_parameters', 'doesnotexist')
                if (location == ""): 
                    location = True
                    import certifi
                    logger.info(f"looking in {certifi.where()}")
                else:
                    logger.info(f"looking in {location}")
                
            except:
                logger.warning("Could not get location of cert, make sure the te_ssl_cert_path is set in te_setup.conf")
        else:
            location = verify_ssl_cert
            logger.info("Certificate validation is disabled.  Please enable verification for increased security.")

        self.kwargs = {
            'verify': location,
            'headers': {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            },
        }

        if adapter:
            logger.info("Mounting REST API session")
            self.session.mount('http://', adapter)
            self.session.mount('https://', adapter)
        self.log_rest_calls = False
        try:
            self.log_rest_calls = (
                cfg.get('te_parameters', 'tripwire_rest_logging', fallback='0') == '1'
            )
        except ImportError:
            pass
        self.page_limit = 1000

    @staticmethod
    def parse_json(result):
        try:
            return json.loads(result)
        except ValueError:
            return result

    @staticmethod
    def make_timestamp(date):
        # TE 8.4.2 couldn't handle 6 digits for microseconds...
        return date.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

    @staticmethod
    def make_date_range(start, end):
        return '%s,%s' % (
            TWRestAPI.make_timestamp(start),
            TWRestAPI.make_timestamp(end),
        )

    @staticmethod
    def make_list(json):
        """The TE Rest API will return a dict if there's a single item,
        and a list if there are multiple items, even in the case of a
        GET to /assets/.  This will ensure everything is a list to make
        results easier to deal with.
        """
        if not isinstance(json, list):
            return [json]
        return json

    def full_url(self, url):
        """Returns the full URL to be called.
        If url is a tuple, escape each item in the url and build it.
        """
        if isinstance(url, tuple):
            url = '/'.join([quote_plus(item) for item in url])
        return '%s%s' % (self.base_url, url)

    def handle_response(self, response, key=None):
        if 200 <= response.status_code < 300:
            result = self.parse_json(response.text)
            if key:
                return self.make_list(result[key])
            return result
        # Raise an exception if we didn't get a 2xx response
        response.raise_for_status()

    def call(self, method, url, data=None, ret_key=None):
        """
        The result we care about in the JSON is sometimes encompassed
        in a superfluous dict, where we usually just need the value.
        Pass in a ret_key to return the value instead of the dict.
        """
        self.num_calls += 1
        url = self.full_url(url)
        args = [url]
        if data:
            args.append(data)
        # There's no way right now to enable trace logging
        if self.log_rest_calls:
            logger.info('%s: %s', method.upper(), url)
        now = time.time()
        response = getattr(self.session, method)(*args, **self.kwargs)
        if self.log_rest_calls:
            logger.info(
                '%s took %.3f seconds, got response: %d',
                url,
                time.time() - now,
                response.status_code,
            )
        return self.handle_response(response, ret_key)

    def get_pages(
        self,
        url,
        params=None,
        dupe_params=None,
        page_interval=1,
        page_offset=0,
        max_pages=0,
        queue=None,
        thread_id=0,
    ):
        """
        page_offset is the offset of the starting page for this process
        page_interval is the number of pages to skip on each iteration
        max_pages can be used to specify the maximum number of pages to retrieve
        """
        on_page = self.page_limit * page_offset
        num_pages = 0
        results = []
        if not params:
            params = {}
        while True:
            params['pageLimit'] = self.page_limit
            params['pageStart'] = on_page
            logger.debug(
                'page_interval %d, page_offset %d, ' 'pageLimit: %s, pageStart: %s',
                page_interval,
                page_offset,
                self.page_limit,
                on_page,
            )
            result = self.get(url, params, dupe_params)
            if result:
                if queue:
                    queue.put((thread_id, result))
                else:
                    results += result
                on_page += self.page_limit * page_interval
                num_pages += 1
                if max_pages and num_pages >= max_pages:
                    break
                if len(result) < self.page_limit:
                    break
                continue
            break
        return results

    def get(self, url, params=None, dupe_params=None, ret_key=None):
        num_params = 0
        url += '?'
        if params:
            url += urlencode(params)
            num_params += 1
        if dupe_params:
            for param in dupe_params:
                if num_params > 0:
                    url += '&'
                url += urlencode(param)
                num_params += 1
        return self.call('get', url, ret_key=ret_key)

    def post(self, url, data=None):
        if not data:
            data = {}
        data = json.dumps(data)
        return self.call('post', url, data=data)

    def delete(self, url):
        return self.call('delete', url)

    def put(self, url, data=None):
        if not data:
            data = {}
        data = json.dumps(data)
        return self.call('put', url, data=data)

    def close(self):
        self.session.close()


class TEAssetViewAPI(TWRestAPI):
    def __init__(self, hostname, username, password, port=443, ssl=True, adapter=None, verify_ssl_cert=True):
        super().__init__(
            'assetview/api/', hostname, username, password, port, ssl, adapter, verify_ssl_cert
        )


class TEV1RestAPI(TWRestAPI):
    def __init__(self, hostname, username, password, port=443, ssl=True, adapter=None, verify_ssl_cert=True):
        super().__init__(
            'api/v1/', hostname, username, password, port, ssl, adapter, verify_ssl_cert
        )
        self._te_version = None
        # The default pagelimit for TE 8.5.2 is bumped to 10k
        #logger.info("Checking TE version")
        looseVer = LooseVersion(self.te_version)
        #logger.info(str(looseVer))
        if looseVer >= LooseVersion('8.5.2'):
            self.page_limit = 10000

    @property
    def te_version(self):
        if self._te_version:
            return self._te_version
        te_status = self.get('status')
        te_version = te_status['teVersion']
        self._te_version = '.'.join(te_version.split('.')[:3])
        return self._te_version
