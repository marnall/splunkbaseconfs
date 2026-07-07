import json, os, sys, requests, logging
from logging.config import fileConfig
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunk.persistconn.application import PersistentServerConnectionApplication
from urllib import quote_plus
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'niddel2_imports'))
from niddelutil import get_app_config, get_splunk_version
from magnetsdk2 import __version__ as magnetsdk_version

if sys.platform == "win32":
    # Binary mode is required for persistent mode on Windows.
    import msvcrt

    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)


def get_proxies_dict(proxy, proxy_port=None, proxy_user=None, proxy_pass=None,
                     proxy_proto='https'):
    """Return requests proxy dict with URL for given parameters.
    :param proxy: string containing the proxy hostname or iP address
    :param proxy_port: integer containing the proxy port to connect to (optional)
    :param proxy_user: string containing the username to use for basic authentication to the
    proxy (optional)
    :param proxy_pass: string containing the password to use for basic authentication to the
    proxy (optional)
    :param proxy_proto: string containing the proxy protocol equal to either 'http' or 'https'
    :return: the proxy URL dict as expected by requests
    """
    if not isinstance(proxy_proto, (str, unicode)) or proxy_proto not in ('http', 'https'):
        raise ValueError("proxy protocol must be a string")
    proxy_url = proxy_proto + '://'
    if proxy_user and proxy_pass:
        if not isinstance(proxy_user, (str, unicode)):
            raise ValueError("proxy username must be a string")
        if not isinstance(proxy_pass, (str, unicode)):
            raise ValueError("proxy password must be a string")
        proxy_url += quote_plus(proxy_user) + ':' + quote_plus(proxy_pass) + '@'
    elif proxy_user:
        if not isinstance(proxy_user, (str, unicode)):
            raise ValueError("proxy username must be a string")
        proxy_url += quote_plus(proxy_user) + '@'
    if not isinstance(proxy, (str, unicode)):
        raise ValueError("proxy hostname or IP address must be a string")
    proxy_url += proxy
    if proxy_port:
        if isinstance(proxy_port, (str, unicode)):
            proxy_port = int(proxy_port)
        if not (isinstance(proxy_port, (int, long)) and 1 <= proxy_port <= 65535):
            raise ValueError("invalid proxy port")
        proxy_url += ":%i" % proxy_port
    return {'http': proxy_url, 'https': proxy_url}


class ApiMe(PersistentServerConnectionApplication):
    """Custom endpoint that allows credentials configuration to be tested
    without logging the API key anywhere."""

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)
        fileConfig(make_splunkhome_path(['etc', 'apps', 'niddel2', 'default', 'logging.conf']),
                   {'SPLUNK_HOME': os.getenv('SPLUNK_HOME')}, False)
        self.logger = logging.getLogger('NiddelREST')

    def handle(self, in_string):
        try:
            self.logger.debug('using requests version ' + requests.__version__)
            body = json.loads(json.loads(in_string).get('payload', '{}'))
            apiKey = body.get('apiKey', None)
            if apiKey:
                if body.get('proxyAddress', None):
                    proxies = get_proxies_dict(proxy=body['proxyAddress'],
                                               proxy_port=body.get('proxyPort', None),
                                               proxy_user=body.get('proxyUser', None),
                                               proxy_pass=body.get('proxyPassword', None))
                else:
                    proxies = None
                appcfg = get_app_config()
                splversion = get_splunk_version()

                _user_agent = "Splunk App/v%s-build_%s; %s" % (appcfg['app_version'], appcfg['app_build'], str(splversion))
                _user_agent = "Magnet SDK Python/v%s; %s" % (magnetsdk_version, _user_agent)
                response = requests.get("https://api.global.niddel.com/v2/me",
                                        proxies=proxies,
                                        headers={"x-api-key": apiKey, 'User-Agent': _user_agent},
                                        verify=make_splunkhome_path(
                                            ['etc', 'apps', 'niddel2', 'bin', 'niddel2_imports', 'certifi', 'cacert.pem']))
                if response.status_code != 200:
                    response.raise_for_status()
                self.logger.error("API key test successful!")
                return {
                    'status': 200,
                    'payload': json.loads(response.text),
                    'log': False
                }
            else:
                self.logger.error("No API key found")
                return {
                    'status': 400,
                    'payload': 'No API key found',
                    'log': False
                }
        except requests.exceptions.RequestException, reqexc:
            self.logger.exception(reqexc)
            if reqexc.response and reqexc.response.status_code:
                status_code = reqexc.response.status_code
            else:
                status_code = 500
            return {
                'status': status_code,
                'payload': str(reqexc),
                'log': False
            }

        except Exception, e:
            self.logger.exception(e)
            return {
                'status': 500,
                'payload': str(e),
                'log': False
            }
