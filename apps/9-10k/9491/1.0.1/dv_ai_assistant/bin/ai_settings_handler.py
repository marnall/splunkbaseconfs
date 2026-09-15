import urllib.parse

import splunk.admin as admin
import splunk.rest

class AISettingsHandler(admin.MConfigHandler):
    def setup(self):
        if self.requestedAction in (admin.ACTION_CREATE, admin.ACTION_EDIT):
            self.supportedArgs.addOptArg('es_url')
            self.supportedArgs.addOptArg('es_token')
            self.supportedArgs.addOptArg('auto_triage')
            self.supportedArgs.addOptArg('auto_interval')
            self.supportedArgs.addOptArg('language')

    def handleList(self, confInfo):
        
        try:
            confDict = self.readConf("ai_settings")
            if confDict and 'global_settings' in confDict:
                for key, val in confDict['global_settings'].items():
                    confInfo['global_settings'].append(key, str(val))
        except Exception:
            pass

        
        session_key = self.getSessionKey()
        realm = 'dv_ai_es_integration'
        try:
            _, pwd_content = splunk.rest.simpleRequest(
                f'/servicesNS/nobody/dv_ai_assistant/storage/passwords?output_mode=json&search=realm="{realm}"',
                sessionKey=session_key, method='GET'
            )
            import json
            passwords = json.loads(pwd_content).get('entry', [])
            for p in passwords:
                if p.get('content', {}).get('username') == 'es_url':
                    confInfo['global_settings'].append('es_url', p.get('content', {}).get('clear_password', ''))
        except Exception:
            pass

    def handleEdit(self, confInfo):
        self.save_settings()

    def handleCreate(self, confInfo):
        self.save_settings()

    def save_settings(self):
        args = self.callerArgs.data
        session_key = self.getSessionKey()
        realm = 'dv_ai_es_integration'

        
        es_url = args.get('es_url', [''])[0]
        es_token = args.get('es_token', [''])[0]

        def replace_secret(name, value):
            password_id = urllib.parse.quote(f'{realm}:{name}:', safe='')
            base = '/servicesNS/nobody/dv_ai_assistant/storage/passwords'
            try:
                splunk.rest.simpleRequest(
                    base,
                    sessionKey=session_key,
                    postargs={'name': name, 'password': value, 'realm': realm},
                    method='POST', raiseAllErrors=True
                )
            except Exception:
                splunk.rest.simpleRequest(
                    f'{base}/{password_id}',
                    sessionKey=session_key,
                    postargs={'password': value},
                    method='POST', raiseAllErrors=True
                )

        if es_url:
            replace_secret('es_url', es_url)

        if es_token:
            replace_secret('es_token', es_token)

        
        auto_triage = args.get('auto_triage', ['0'])[0]
        auto_interval = args.get('auto_interval', ['120'])[0]
        language = str(args.get('language', ['auto'])[0] or 'auto').strip().lower()
        allowed_languages = {'auto', 'en', 'tr', 'de', 'fr', 'es', 'it', 'pt', 'nl', 'pl', 'ru', 'ar', 'ja', 'ko', 'zh'}
        if language not in allowed_languages:
            language = 'auto'
        
        
        try:
            if int(auto_interval) < 120:
                auto_interval = '120'
        except ValueError:
            auto_interval = '120'

        conf_args = {
            'auto_triage': auto_triage,
            'auto_interval': auto_interval,
            'language': language
        }
        self.writeConf('ai_settings', 'global_settings', conf_args)

admin.init(AISettingsHandler, admin.CONTEXT_APP_AND_USER)
