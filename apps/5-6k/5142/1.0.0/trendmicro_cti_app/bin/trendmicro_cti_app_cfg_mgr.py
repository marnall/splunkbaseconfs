import os
import sys
import time
import uuid
import requests
import json
import logging
from importlib import import_module
import splunk
import splunk.rest as rest
from shutil import copyfile
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunk.clilib import cli_common as cli
from splunk.persistconn.application import PersistentServerConnectionApplication
from base64 import b64encode

if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

APP_NAME = 'trendmicro_cti_app'
SPLUNK_HOME = os.environ['SPLUNK_HOME']
LIB_PATH = os.path.join(SPLUNK_HOME, 'etc', 'apps',
                        APP_NAME, 'bin', 'lib')
COMMON_PATH = os.path.join(SPLUNK_HOME, 'etc', 'apps',
                        APP_NAME, 'bin', 'common')
sys.path.append(LIB_PATH)
RSA = import_module('rsa')
PYAES = import_module('pyaes')
LOGGER = import_module('logger')

LOG = LOGGER.setup_logging(logging.DEBUG)

class TMCFGManager(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        LOG.info('BEGIN handle()')

        try:
            input = json.loads(in_string)
            session_key = input['session']['authtoken']
        except Exception as e:
            LOG.exception('Parse error of in_string')
            return {'payload': {"status": "error early", "message": str(e)},
                    'status': 200          # HTTP status code
                    }
        try:
            cfg_filename = 'tmcfg.conf'

            default_cfg_file = os.path.join(
                SPLUNK_HOME, 'etc', 'apps', APP_NAME, 'default', cfg_filename)
            default_cfg = cli.readConfFile(default_cfg_file)
            LOG.info('default_cfg_file={0}'.format(default_cfg_file))
            local_cfg_file = os.path.join(
                SPLUNK_HOME, 'etc', 'apps', APP_NAME, 'local', cfg_filename)

            os.makedirs(os.path.dirname(local_cfg_file), exist_ok=True)
            if not os.path.exists(local_cfg_file):
                copyfile(default_cfg_file, local_cfg_file)

            local_cfg = cli.readConfFile(local_cfg_file)
            for name, content in local_cfg.items():
                LOG.info(
                    'local name={0}, content={1}'.format(name, content))
                if name in default_cfg:
                    default_cfg[name].update(content)
                else:
                    default_cfg[name] = content
            if default_cfg['tmconfig']['cid'] == '':
                default_cfg['tmconfig']['cid'] = '{0}'.format(uuid.uuid4())

        except Exception:
            LOG.exception('Fail to parse configurations file')
            return {'payload': {"status": "error", "message": str(e)},
                    'status': 200          # HTTP status code
                    }
        try:
            threshold = 604800
            last_bif_time = default_cfg['tmconfig']['bif_time']
            last_bif_time = float(0 if last_bif_time == '' else last_bif_time)
            if abs(time.time() - last_bif_time) > threshold:
                current_time = '{0}'.format(time.time())
                bif_obj_head = {'timestamp': current_time,
                                'cid': default_cfg['tmconfig']['cid']}
                bif_obj = self.get_BIF_obj(session_key)
                bif_obj.update(bif_obj_head)
                enc = EncryptHelper()
                msg = enc.encrypt_message(json.dumps(bif_obj))
                self.feedback_BIF_data(msg, default_cfg['tmconfig']['cid'])
                default_cfg['tmconfig']['bif_time'] = current_time

            cli.writeConfFile(local_cfg_file, default_cfg)
        except Exception:
            LOG.exception('Fail to feedback BIF data')

        return {'payload': {"status": "ok", "message": 'ok'},
                'status': 200          # HTTP status code
                }

    def search_splunk(self, session_key, search_query):
        try:
            url = '/services/search/jobs/?output_mode=json'
            args = {'search': search_query}
            _, content = rest.simpleRequest(url, postargs=args, method='POST',
                                            sessionKey=session_key, raiseAllErrors=True)
            sid = json.loads(content)['sid']
            url_check = '/services/search/jobs/{0}/?output_mode=json'.format(
                sid)
            result_ready = False
            while not result_ready:
                time.sleep(0.5)
                _, c = rest.simpleRequest(url_check, method='GET',
                                          sessionKey=session_key, raiseAllErrors=True)
                result_ready = json.loads(
                    c)['entry'][0]['content']['isDone']

            url_result = '/services/search/jobs/{0}/results/?output_mode=json'.format(
                sid)
            _, results = rest.simpleRequest(url_result, method='GET',
                                            sessionKey=session_key, raiseAllErrors=True)
            return json.loads(results)['results']
        except Exception:
            LOG.exception('Fail to search in splunk')
            return ''

    def get_BIF_obj(self, session_key):
        try:
            search_query_app_list = "| rest /services/apps/local |dedup label | table label version"
            app_list = self.search_splunk(session_key, search_query_app_list)
            search_query_src_list = "| metadata type=sourcetypes index=* OR index=_*"
            src_list = self.search_splunk(session_key, search_query_src_list)
            bif_obj = {'app_list': app_list, 'src_list': src_list}
            return bif_obj
        except Exception:
            LOG.exception('Fail to get BIF data')
            return ''

    def feedback_BIF_data(self, bif_data, cid):
        try:
            url = ConfigMgr().getBIFSvrUrl(cid)
            headers = {'x-amz-acl': 'bucket-owner-full-control'}
            result = requests.put(url=url, data=bif_data, headers=headers)
            LOG.info('upload result:{0}'.format(result))
            current_time = '{0}'.format(time.time())
            return current_time
        except Exception:
            LOG.exception('Fail to feedback BIF data')
            return '0'


class EncryptHelper():
    _RSA_PUBKEY = '-----BEGIN RSA PUBLIC KEY-----\nMIICCgKCAgEAgmWsycvJOjm7oMQID0xt7I7vHYjufGpHDvBiMhrL5KN62e6dLEwH\ny6rXlhZzfrYy4JghTkbgQvPaN4nTubAmBp4XGsBwSFy3BmoL61IbDQdj0jCg07iK\npnNVv+C++g1Z6DlnZXfG6OpTZPU2eX4aeL2EbzqyNfWxbeHpm+If/q4QuaCzJiRU\nGAu9RUjSq1LLDN9LDgqqQsvTL3OtDEZkpvnKG2xrguj5IuoUm+hMshP1qCYYL2fY\nmU11yhtuGlecG32MwKq6sHLMAugjouLkFcQozBFdTVoDtp4wVck7p99cGG6EGk7l\nT93C+udXAtv1ZG9j3WDaMtXYI7Ir53HgvsrYP05lU6TRLQ9lXOrzHp5ZkFG1VjPr\noNA54bEE+cKpqdSUQv3eAxyi/+LbL/qtIuL2NK8VEqsueEh7QstN7I2aqLxlQIG2\nFewpYH4L9ann6HkhF9HjuG9H7QjtFm3vgV24zuRcz8kIs4CvXpU/2sGFaqzNmYH2\nT2SkW1Ye1uaWwiuDd8+o6EIv6KqNnlIlsuBGRpHZ/aSY3QvKg2PH9Njc73E37y0T\nJPkqVOK1HU4RAQlHyIrXCDM6lE0FKys2t37gTEDPbewPgLMmVRi9DErYXgHRc/Y5\nbtKNB99L35+sFrqBjJuhImW+XFdINL4IQPDjDD7+uWeHWrU60ZVS9dsCAwEAAQ==\n-----END RSA PUBLIC KEY-----\n'

    def encrypt_message(self, plain_text):
        try:
            key256 = os.urandom(32)
            key256_b64 = self.encrypt_with_rsa_b64(key256)
            encrypted_b64 = self.encrypt_with_aes256_b64(key256, plain_text)
            result = {'AES_KEY': key256_b64.decode(
            ), 'MSG': encrypted_b64.decode()}
            return json.dumps(result)
        except Exception:
            LOG.exception('Fail to encrypt message')
            return ''

    def encrypt_with_aes256_b64(self, key256, plain_text):
        try:
            aes = PYAES.AESModeOfOperationCTR(key256)
            cipher_text_b64 = b64encode(aes.encrypt(plain_text))
            return cipher_text_b64
        except Exception:
            LOG.exception('Fail to encrypt with AES256')
            return ''

    def encrypt_with_rsa_b64(self, data_bytes):
        try:
            pubkey = RSA.PublicKey.load_pkcs1(self._RSA_PUBKEY)
            secret_obj = RSA.encrypt(data_bytes, pubkey)
            return b64encode(secret_obj)
        except Exception:
            LOG.exception('Fail to encrypt with RSA')
            return ''

class ConfigMgr():
    def getBIFDomainName(self):
        try:
            jsonPath = os.path.join(COMMON_PATH, 'config', 'pkg.json')
            LOG.info('config path: {0}'.format(jsonPath))
            with open(jsonPath) as jsonfile:
                input = json.load(jsonfile)
                env = input['bif']['domain_name']
            LOG.info('BIF domain name:{0}'.format(env))
            return env
        except Exception:
            LOG.exception('Fail to get environment config')
            return ''

    def getBIFSvrUrl(self, cid):
        try:
            bifDomainName = self.getBIFDomainName()
            url = '{0}/tmupload/splunk_users/{1}/{2}'.format(
                bifDomainName, cid, 'data.bif')
            LOG.info('url:{0}'.format(url))
            return url
        except Exception:
            LOG.exception('Fail to compose BIF url')
            return ''