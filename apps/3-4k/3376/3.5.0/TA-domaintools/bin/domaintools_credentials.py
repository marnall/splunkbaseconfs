import json
import sys
import splunk.rest
import splunk.entity as en

from splunk.persistconn.application import PersistentServerConnectionApplication


def flatten_query_params(params):
    flattened = {}
    for i, j in params:
        flattened[i] = flattened.get(i) or j
    return flattened


class CredentialRestHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)
        self.package_id = 'TA-domaintools'

    def handle(self, in_string):
        try:
            request = json.loads(in_string)

            payload = {'payload': '', 'status': 500}
            sessionKey = request['system_authtoken']
            entities = en.getEntities(['admin', 'passwords'],
                                      namespace=self.package_id,
                                      search=self.package_id,
                                      count=-1,
                                      owner='nobody',
                                      sessionKey=sessionKey)

            for i, c in entities.items():
                if c['eai:acl']['app'] == self.package_id:
                    payload = {
                        'payload': {
                            'username': c['username'],
                            'password': c['clear_password']
                        },
                        'status': 200          # HTTP status code
                    }

        except Exception as ex:
            pass

        return json.dumps(payload)

    def done(self):
        pass

    def gen_message(self, message, sessionKey):
        splunk.rest.simpleRequest('/services/messages', method='POST',
                                  sessionKey=sessionKey,
                                  postargs={'name':
                                            'DomainTools error', 'value': message,
                                            'severity': 'error'})
