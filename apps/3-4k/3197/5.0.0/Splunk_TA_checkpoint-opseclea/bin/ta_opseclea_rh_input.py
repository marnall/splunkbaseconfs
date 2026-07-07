
import ta_opseclea_import_declare

import splunk.admin as admin

from splunktaucclib.rest_handler import base, normaliser
from splunktalib.common import util

util.remove_http_proxy_env_vars()


class DefaultInputs(base.BaseModel):
    """REST Endpoint of Server in Splunk Add-on UI Framework.
    """
    rest_prefix = 'ta_opsec'
    endpoint = "configs/conf-opseclea_inputs"
    requiredArgs = {'connection', 'data', 'mode', 'index', 'interval'}
    optionalArgs = {'starttime', 'host', 'disabled', 'noresolve', 'fields', 'filter', 'field_black_list', 'field_white_list'}
    normalisers = {
        "disabled": normaliser.Boolean()
    }
    defaultVals = {
        'noresolve': '0'
    }
    cap4endpoint = ''
    cap4get_cred = ''


if __name__ == "__main__":
    admin.init(base.ResourceHandler(DefaultInputs), admin.CONTEXT_APP_AND_USER)
