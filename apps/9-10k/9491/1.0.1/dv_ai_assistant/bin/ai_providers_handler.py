import urllib.parse

import splunk.admin as admin
import splunk.rest

class AIProvidersHandler(admin.MConfigHandler):
    def setup(self):
        if self.requestedAction in (admin.ACTION_CREATE, admin.ACTION_EDIT):
            self.supportedArgs.addOptArg('url')
            self.supportedArgs.addOptArg('model')
            self.supportedArgs.addOptArg('engine_type')
            self.supportedArgs.addOptArg('api_key')
            self.supportedArgs.addOptArg('is_default')

    def handleList(self, confInfo):
        try:
            confDict = self.readConf("ai_providers")
            if confDict:
                for stanza, settings in confDict.items():
                    for key, val in settings.items():
                        confInfo[stanza].append(key, str(val))
        except Exception:
            pass

    def handleCreate(self, confInfo):
        self.save_provider()

    def handleEdit(self, confInfo):
        self.save_provider()

    def save_provider(self):
        name = self.callerArgs.id
        args = self.callerArgs.data

        api_key = ""
        if 'api_key' in args and args['api_key']:
            api_key = args['api_key'][0]
            del args['api_key'] 

        conf_args = {}
        for k, v in args.items():
            if v and v[0] != '':
                conf_args[k] = v[0]

        
        is_default = conf_args.get('is_default', '0')
        if is_default in ['1', 'true', 'True']:
            try:
                confDict = self.readConf("ai_providers")
                if confDict:
                    for stanza, settings in confDict.items():
                        if stanza != name and settings.get('is_default') in ['1', 'true', 'True']:
                            
                            preserved_settings = {}
                            for k, v in settings.items():
                                if not k.startswith('eai:'): 
                                    preserved_settings[k] = v
                            preserved_settings['is_default'] = '0'
                            self.writeConf('ai_providers', stanza, preserved_settings)
            except Exception:
                pass
                
        self.writeConf('ai_providers', name, conf_args)

        if api_key:
            session_key = self.getSessionKey()
            self._delete_stored_key(session_key, name)
            splunk.rest.simpleRequest(
                '/servicesNS/nobody/dv_ai_assistant/storage/passwords',
                sessionKey=session_key,
                postargs={'name': 'api_key', 'password': api_key, 'realm': f'dv_ai_provider_{name}'},
                method='POST',
                raiseAllErrors=True
            )

    @staticmethod
    def _delete_stored_key(session_key, name):
        realm = f'dv_ai_provider_{name}'
        password_id = urllib.parse.quote(f'{realm}:api_key:', safe='')
        try:
            splunk.rest.simpleRequest(
                f'/servicesNS/nobody/dv_ai_assistant/storage/passwords/{password_id}',
                sessionKey=session_key,
                method='DELETE',
                raiseAllErrors=True
            )
        except Exception:
            pass

    def handleRemove(self, confInfo):
        name = str(self.callerArgs.id or '').strip()
        if not name:
            raise admin.ArgValidationException("Provider name is required.")

        session_key = self.getSessionKey()
        stanza = urllib.parse.quote(name, safe='')
        url = f'/servicesNS/nobody/dv_ai_assistant/configs/conf-ai_providers/{stanza}'

        try:
            splunk.rest.simpleRequest(
                url,
                sessionKey=session_key,
                method='DELETE',
                raiseAllErrors=True
            )
        except Exception as e:
            raise admin.ArgValidationException(
                "Provider could not be deleted: %s" % str(e)
            )

        self._delete_stored_key(session_key, name)

admin.init(AIProvidersHandler, admin.CONTEXT_APP_AND_USER)
