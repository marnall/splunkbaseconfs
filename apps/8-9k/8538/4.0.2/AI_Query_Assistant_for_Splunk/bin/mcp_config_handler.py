"""MCP Config Handler"""
import sys, os, json, re, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
import splunk.admin as admin
import splunk.entity as entity
from mcp_base import MCPBaseHandler
from validators import validate_string, ValidationError

logger = logging.getLogger(__name__)

# Allowed config key pattern
CONFIG_KEY_RE = re.compile(r'^[a-zA-Z0-9_]{1,50}$')

class MCPConfigHandler(MCPBaseHandler):

    def setup(self):
        for arg in ('config', 'output_mode'):
            self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        try:
            config = self._get_config()

            if 'ai' in config and 'api_key' in config['ai']:
                api_key = config['ai']['api_key']
                if api_key:
                    config['ai']['api_key'] = api_key[:8] + '...' + api_key[-4:]

            if 'integration' in config and 'api_token' in config['integration']:
                token = config['integration']['api_token']
                if token:
                    config['integration']['api_token'] = token[:8] + '...' + token[-4:]

            confInfo['config'].append('data', json.dumps(config))

        except Exception as e:
            logger.exception("Failed to list config")
            confInfo['config'].append('error', str(e))

    def handleEdit(self, confInfo):
        try:
            config_data = json.loads(self.callerArgs.data.get('config', ['{}'])[0])

            allowed_stanzas = {'ai', 'security', 'integration', 'query'}
            for stanza_name, stanza_data in config_data.items():
                if stanza_name not in allowed_stanzas:
                    raise admin.ArgValidationException(f"Invalid config stanza: {stanza_name}")
                ent = entity.getEntity(
                    '/configs/conf-mcp', stanza_name,
                    namespace='AI_Query_Assistant_for_Splunk', owner='nobody',
                    sessionKey=self.getSessionKey()
                )
                for key, value in stanza_data.items():
                    if not CONFIG_KEY_RE.match(key):
                        raise admin.ArgValidationException(f"Invalid config key: {key}")
                    if not isinstance(value, str):
                        value = str(value)
                    if len(value) > 500:
                        raise admin.ArgValidationException(f"Config value for '{key}' exceeds 500 characters")
                    ent[key] = value
                entity.setEntity(ent, sessionKey=self.getSessionKey())

            confInfo['config'].append('success', 'true')
            confInfo['config'].append('message', 'Configuration updated successfully')

        except admin.ArgValidationException:
            raise
        except Exception as e:
            logger.exception(f"{self._log_prefix()} Failed to update config")
            confInfo['config'].append('error', str(e))

admin.init(MCPConfigHandler, admin.CONTEXT_APP_AND_USER)
