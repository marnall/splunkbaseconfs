import logging
import logging.handlers

import sn_tokens as tokens
import splunklib.client as client


def getAppName():
    return tokens.APP_NAME


def setWorkflowLabel(sessionKey, realm, text):
    stanza_map = {
        "splunk_primary": "splunk_primary_workflow",
        "splunk_secondary": "splunk_secondary_workflow",
    }
    try:
        service = client.connect(token=sessionKey, app=getAppName())
        for action in service.confs.list("workflow_actions"):
            for stanza in action.list(search=stanza_map.get(realm)):
                stanza.submit({"label": text})
    except Exception as excpt:
        logging.error("Unable to update label: {}".format(excpt))


def getRealm(instance):
    return "splunk_{}".format(instance)


def setCredentials(sessionKey, realm, snPwd, prxPwd):
    service = client.connect(token=sessionKey, app=getAppName())
    try:
        service.storage_passwords.delete("instance", realm=realm)
    except Exception as excpt:
        logging.error("Unable to delete storage_passwords main: {}".format(excpt))
    try:
        service.storage_passwords.delete("proxy", realm=realm)
    except Exception as excpt:
        logging.error("Unable to delete storage_passwords proxy: {}".format(excpt))

    storage_password = ""
    if snPwd not in [None, '']:
        storage_password = service.storage_passwords.create(snPwd, "instance", realm=realm)
    if prxPwd not in [None, '']:
        service.storage_passwords.create(prxPwd, "proxy", realm=realm)


def getCredentials(sessionKey, realm):
    snPwd = ""
    prxPwd = ""
    try:
        service = client.connect(token=sessionKey, app=getAppName())
        for password in service.storage_passwords:
            if password.name == realm + ":instance:":
                snPwd = password.clear_password
            if password.name == realm + ":proxy:":
                prxPwd = password.clear_password
    except Exception as excpt:
        logging.error("Unable to get storage_passwords: {}".format(excpt))

    if snPwd is None:
        snPwd = ""
    if prxPwd is None:
        prxPwd = ""
    return snPwd, prxPwd
