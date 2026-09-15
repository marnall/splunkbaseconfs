import urllib.parse
import splunk.admin as admin
import splunk.rest


class AIKnowledgeBaseHandler(admin.MConfigHandler):
    def setup(self):
        if self.requestedAction in (admin.ACTION_CREATE, admin.ACTION_EDIT):
            self.supportedArgs.addOptArg('description')
            self.supportedArgs.addOptArg('context_data')

    def handleList(self, confInfo):
        try:
            confDict = self.readConf("ai_knowledge_base")
            if confDict:
                for stanza, settings in confDict.items():
                    desc = (settings.get('description', '') or '').strip()
                    ctx = (settings.get('context_data', '') or '').strip()
                    
                    
                    if stanza != 'system_prompt' and not desc and not ctx:
                        continue
                    for key, val in settings.items():
                        confInfo[stanza].append(key, str(val))
        except Exception:
            pass

    def handleCreate(self, confInfo):
        self.save_rule()

    def handleEdit(self, confInfo):
        self.save_rule()

    def save_rule(self):
        name = self.callerArgs.id
        args = self.callerArgs.data

        conf_args = {}
        for k, v in args.items():
            if v and v[0] != '':
                conf_args[k] = v[0]

        self.writeConf('ai_knowledge_base', name, conf_args)

    def _disable_stanza(self, name):
        
        
        self.writeConf('ai_knowledge_base', name, {'description': '', 'context_data': ''})

    def handleRemove(self, confInfo):
        name = self.callerArgs.id

        
        if name == 'system_prompt':
            raise admin.ArgValidationException(
                "system_prompt is a protected record and cannot be deleted. You can edit its content."
            )

        session_key = self.getSessionKey()
        stanza = urllib.parse.quote(str(name), safe='')
        url = '/servicesNS/nobody/dv_ai_assistant/configs/conf-ai_knowledge_base/%s' % stanza

        try:
            splunk.rest.simpleRequest(url, sessionKey=session_key, method='DELETE', raiseAllErrors=True)
            return
        except Exception as e:
            msg = str(e)
            
            
            if ('cannot be deleted' in msg) or ('400' in msg) or ('409' in msg):
                try:
                    self._disable_stanza(name)
                    return
                except Exception as e2:
                    raise admin.ArgValidationException("The record could not be disabled: %s" % str(e2))
            raise admin.ArgValidationException("The record could not be deleted: %s" % msg)


admin.init(AIKnowledgeBaseHandler, admin.CONTEXT_APP_AND_USER)
