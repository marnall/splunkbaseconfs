import import_declare_test
import splunk.admin as admin
import splunk.entity as en
import splunk.rest as rest
import os

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

import requests
from requests.auth import HTTPBasicAuth

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
myapp = __file__.split(os.sep)[-3]


class ConfigApp(admin.MConfigHandler):

    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['username', 'password', 'host']:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        confDict = self.readConf("xtremioappsetup")
        if confDict is not None:
            for stanza, settings in confDict.items():
                for key, val in settings.items():
                    if stanza == 'setupentity':
                        confInfo[stanza].append(key, val)

    def handleEdit(self, confInfo):

        inputConfParser = configparser.ConfigParser()
        inputConf = SPLUNK_HOME + "/etc/apps/" + myapp + "/local/inputs.conf"

        incConf = configparser.ConfigParser()
        incFile = SPLUNK_HOME + "/etc/apps/" + myapp + "/default/include.conf"
        incConf.read(incFile)

        if incConf.has_section('include'):
            incStr = incConf.get('include', 'types')

        incList = incStr.split(',')

        username = self.callerArgs.data['username'][0]
        password = self.callerArgs.data['password'][0]
        host = self.callerArgs.data['host'][0]

        sessionKey = self.getSessionKey()
        owner = self.userName
        namespace = self.appName

        endpoint = "https://" + host + "/api/json/types"
        auth = HTTPBasicAuth(username, password)
        req_args = {"verify": False, "stream": False}
        if auth:
            req_args["auth"] = auth

        try:
            r = requests.get(endpoint, **req_args)
            r.raise_for_status()
            check_existing_creds = 0
            try:
                # list all credentials
                entities = en.getEntities(['admin', 'passwords'], namespace=namespace,
                                          owner='nobody', sessionKey=sessionKey)
            except Exception as e:
                raise e
            else:
                # compare with existing credentials
                for i, c in entities.items():
                    if host == c['realm'] and username == c['username']:
                        if password == c['clear_password']:
                            check_existing_creds = 1
                        else:
                            check_existing_creds = 2
                            en.deleteEntity(['admin', 'passwords'], i, namespace=namespace,
                                            owner='nobody', sessionKey=sessionKey)
                        break
            try:
                if check_existing_creds != 1:
                    # Set XtremIO user name in splunk storage/password for encrypted security
                    mon = en.getEntity('storage/passwords', '_new', sessionKey=sessionKey)
                    mon["name"] = username
                    mon["password"] = password
                    mon["realm"] = host
                    mon.namespace = namespace
                    mon.owner = owner
                    en.setEntity(mon, sessionKey=sessionKey)
            except Exception as e:
                raise e
            else:
                if check_existing_creds == 0:
                    json_types = r.json()
                    children = json_types["children"]
                    for child in children:

                        if child['name'] not in incList:
                            continue

                        name = "xtremio://" + host + '::' + child["name"]
                        inputConfParser.add_section(name)
                        if child["name"] != "events":
                            endpoint = child["href"] + "/$get_ids$"
                        else:
                            endpoint = child["href"]
                        inputConfParser.set(name, 'endpoint', endpoint)
                        inputConfParser.set(name, 'sourcetype', "emc:xtremio:rest")
                        inputConfParser.set(name, 'polling_interval', "120")

                    with open(inputConf, 'a+') as inputConfig:
                        inputConfParser.write(inputConfig)
                    try:
                        rest.simpleRequest(
                            "/servicesNS/nobody/{}/configs/conf-app/install".format(namespace),
                            sessionKey=sessionKey,
                            postargs={"is_configured": "1"},
                            method="POST",
                            timeout=180,
                            raiseAllErrors=True,
                        )
                        rest.simpleRequest(
                            "/servicesNS/nobody/system/apps/local/{}/_reload".format(namespace),
                            sessionKey=sessionKey,
                            postargs=None,
                            method="POST",
                            timeout=180,
                            raiseAllErrors=True,
                        )
                    except Exception as e:
                        raise e
        except requests.exceptions.HTTPError as e:
            raise e
        except requests.exceptions.Timeout as e:
            raise e
        except Exception as e:
            raise e


# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
