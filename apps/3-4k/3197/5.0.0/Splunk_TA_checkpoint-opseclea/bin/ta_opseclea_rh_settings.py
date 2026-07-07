"""Test global setting REST handler
"""

import ta_opseclea_import_declare

import splunk.admin as admin

from splunktaucclib.rest_handler import base, multimodel, normaliser, validator
from splunktalib.common import util

util.remove_http_proxy_env_vars()


class Logging(base.BaseModel):
    requiredArgs = {'level'}
    defaultVals = {
        'level': 'INFO'
    }
    validators = {
        'level': validator.Enum(('DEBUG', 'INFO', 'ERROR'))
    }
    outputExtraFields = ('eai:acl', 'acl', 'eai:attributes',
                         'eai:appName', 'eai:userName')


class Proxy(base.BaseModel):
    requiredArgs = {'proxy_enabled', }
    optionalArgs = {'proxy_url',
                    'proxy_port',
                    'proxy_username',
                    'proxy_password',
                    'proxy_rdns',
                    'proxy_type'}
    encryptedArgs = {'proxy_password'}
    defaultVals = {
        'proxy_enabled': 'false',
        'proxy_rdns': 'false',
        'proxy_type': 'http',
    }
    validators = {
        'proxy_enabled': validator.RequiredIf(('proxy_url', 'proxy_port'),
                                              ('1', 'true', 'yes')),
        'proxy_url': validator.AllOf(validator.Host(),
                                     validator.RequiredIf(('proxy_port', ))),
        'proxy_port': validator.AllOf(validator.Port(),
                                      validator.RequiredIf(('proxy_url', ))),
        'proxy_type': validator.Enum(("socks4",
                                      "socks5",
                                      "http",
                                      "http_no_tunnel")),
    }
    normalisers = {
        'proxy_enabled': normaliser.Boolean(),
    }
    outputExtraFields = ('eai:acl', 'acl', 'eai:attributes',
                         'eai:appName', 'eai:userName')


class Setting(multimodel.MultiModel):
    endpoint = "configs/conf-opseclea_settings"
    modelMap = {
        'logging': Logging,
        'proxy': Proxy
    }
    cap4endpoint = ''
    cap4get_cred = ''


if __name__ == "__main__":
    admin.init(multimodel.ResourceHandler(Setting),
               admin.CONTEXT_APP_AND_USER)
