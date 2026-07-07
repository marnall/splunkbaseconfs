import json
import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

import splunk.admin
import splunk.entity as entity

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")

# set up logging to this location
LOG_FILENAME = os.path.join(
    SPLUNK_HOME, "var", "log", "splunk", "deviceinformation_app_setuphandler.log")

# Set up a specific logger
logger = logging.getLogger('lunahsmsetup')

# default logging level , can be overidden in stanza config
logger.setLevel(logging.DEBUG)

# log format
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

# Add the daily rolling log message handler to the logger
handler = TimedRotatingFileHandler(
    LOG_FILENAME, when="d", interval=1, backupCount=5)
handler.setFormatter(formatter)
logger.addHandler(handler)

getOperations = {'getappliancelist': [], 'checkconfignames': [
    'config_names']}  # GET: key -> operation id, value -> required args
postOperations = {'addappliances': ['appliances_to_add'], 'removeappliances': [
    'appliances_to_delete']}  # POST: key -> operation id, value -> required args

allOptArgs = []  # all optional args for all operations combined

optArgsDefaultValue = {
    'port': '161',
    'timeout': '5',
    'snmpinterval': '60',
    'ipv6': '0',
    'system_python_path': '/usr/bin/python'
}

snmpConfigArgsList = ['activation_key', 'destination', 'snmp_version', 'v3_securityName',
                      'v3_authKey', 'v3_authProtocol', 'v3_privKey', 'v3_privProtocol',
                      'port', 'ipv6', 'timeout', 'use_system_python',
                      'trap_rdns', 'system_python_path', 'snmpinterval']

configSuffixes = ['_luna_appliance', '_luna_hsm_operations', '_luna_hsm_client_addr',
                  '_luna_hsm_info', '_luna_hsm_partition_info', '_luna_hsm_network_info']

configIndexes = ['lunasa_appliance', 'hsm_operation', 'hsm_client_addr',
                 'hsm_information', 'hsm_partition_info', 'hsm_network_info']

snmpConfigVariableFields = {
    '_luna_appliance': {
        'mib_names': 'SAFENET-HSM-MIB,LM-SENSORS-MIB',
        'object_names': '.1.3.6.1.4.1.2021.13.16.3.1.3,.1.3.6.1.4.1.2021.13.16.4.1.3,.1.3.6.1.4.1.2021.13.16.2.1.3,.1.3.6.1.4.1.2021.13.16.5.1.3',
        'index': 'lunasa_appliance'
    },
    '_luna_hsm_operations': {
        'mib_names': 'SAFENET-HSM-MIB,CHRYSALIS-UTSP-MIB',
        'object_names': '.1.3.6.1.4.1.12383.3.1.1.1,.1.3.6.1.4.1.23629.1.5.1.2.1.19,.1.3.6.1.4.1.23629.1.5.1.2.1.20,.1.3.6.1.4.1.23629.1.5.1.2.1.21,.1.3.6.1.4.1.12383.3.1.1.2,.1.3.6.1.4.1.12383.3.1.2.1,.1.3.6.1.4.1.12383.3.1.2.2,.1.3.6.1.4.1.12383.3.1.2.4,.1.3.6.1.4.1.12383.3.1.2.5',
        'index': 'hsm_operation'
    },
    '_luna_hsm_client_addr': {
        'mib_names': 'SAFENET-HSM-MIB,LM-SENSORS-MIB',
        'object_names': '.1.3.6.1.4.1.23629.1.5.1.7.1.2',
        'index': 'hsm_client_addr'
    },
    '_luna_hsm_info': {
        'mib_names': 'SAFENET-HSM-MIB,LM-SENSORS-MIB,CHRYSALIS-UTSP-MIB',
        'object_names': '.1.3.6.1.4.1.23629.1.5.1.2.1.3,.1.3.6.1.4.1.23629.1.5.1.2.1.1,.1.3.6.1.4.1.23629.1.5.1.2.1.2,.1.3.6.1.4.1.23629.1.5.1.2.1.4,.1.3.6.1.4.1.23629.1.5.1.2.1.5,.1.3.6.1.4.1.23629.1.5.1.2.1.7,.1.3.6.1.4.1.23629.1.5.1.2.1.9,.1.3.6.1.4.1.23629.1.5.1.2.1.10,.1.3.6.1.4.1.23629.1.5.1.2.1.11,.1.3.6.1.4.1.23629.1.5.1.2.1.15,.1.3.6.1.4.1.23629.1.5.1.2.1.12,.1.3.6.1.4.1.23629.1.5.1.2.1.13,.1.3.6.1.4.1.23629.1.5.1.2.1.6,.1.3.6.1.4.1.23629.1.5.1.2.1.16,.1.3.6.1.4.1.23629.1.5.1.2.1.17,.1.3.6.1.4.1.23629.1.5.1.2.1.18,.1.3.6.1.4.1.23629.1.5.1.5.1.4,.1.3.6.1.4.1.23629.1.5.1.2.1.8',
        'index': 'hsm_information'
    },
    '_luna_hsm_partition_info': {
        'mib_names': 'SAFENET-HSM-MIB',
        'object_names': '.1.3.6.1.4.1.23629.1.5.1.4.1.1,.1.3.6.1.4.1.23629.1.5.1.4.1.2,.1.3.6.1.4.1.23629.1.5.1.4.1.3,.1.3.6.1.4.1.23629.1.5.1.4.1.4,.1.3.6.1.4.1.23629.1.5.1.4.1.5,.1.3.6.1.4.1.23629.1.5.1.4.1.6',
        'index': 'hsm_partition_info'
    },
    '_luna_hsm_network_info': {
        'mib_names': 'RFC1213-MIB,SNMPv2-MIB,IF-MIB',
        'object_names': '.1.3.6.1.2.1.2.2.1.8,.1.3.6.1.2.1.4.20.1.1,.1.3.6.1.2.1.1.5',
        'index': 'hsm_network_info'
    }
}


def validate_snmp_input_fields(config):
    """
    """
    # Check all required fields
    invalid_fields = []
    for c in ['activation_key', 'destination', 'v3_securityName', 'v3_authKey', 'v3_authProtocol', 'v3_privKey', 'v3_privProtocol']:
        if c not in config or config[c] == None or config[c].strip() == '':
            invalid_fields.append(c)
    # TODO: Validation of received values?
    if len(invalid_fields) > 0:
        return invalid_fields
    return None


def add_missing_fields(config):
    """
    """
    for field, value in optArgsDefaultValue.items():
        if field not in config or config[field] == None or config[field].strip() == '':
            config[field] = value
    config['do_bulk_get'] = '0'
    config['do_get_subtree'] = '1'
    config['lexicographic_mode'] = '0'
    config['log_level'] = 'ERROR'
    config['max_repetitions'] = '3'
    config['non_repeaters'] = '2'
    config['run_process_checker'] = '1'
    config['snmp_mode'] = 'attributes'
    config['snmp_version'] = '3'
    config['sourcetype'] = 'snmp_ta'
    config['split_bulk_output'] = '1'
    config['use_system_python'] = '1'
    config['trap_rdns'] = '0'
    return config


def check_entity_exists(config_name, entities=None, session_key=None):
    """
    """
    if entities == None and session_key == None:
        return None
    if entities == None:
        search_constraint = ''
        for i in configIndexes:
            search_constraint += 'index=%s or ' % i
        entities = entity.getEntities(['configs', 'inputs'], namespace="snmp_ta", owner='nobody',
                                      sessionKey=session_key, count=100, search=search_constraint[0:len(search_constraint)-3])
    for i, e in entities.items():
        entity_name = i[7:i.rindex("_luna_")]
        if entity_name == config_name:
            return True
    return False


class LunaSnmpConfigEntity(object):
    """
    """

    def __init__(self, configName, configProps):
        super().__init__()
        self.configName = configName
        self.properties = {}
        for o in snmpConfigArgsList:
            self.properties[o] = configProps[o]

    def getName(self):
        return self.configName

    def getProperties(self):
        return self.properties


class LunaHsmConfigHandler(splunk.admin.MConfigHandler):
    """
    """

    def setup(self):
        """
        """
        logger.debug("setup")
        try:
            logger.debug("Incoming Operation ID: %s" % self.callerArgs.id)
            if (self.callerArgs.id not in getOperations.keys()) and (self.callerArgs.id not in postOperations.keys()):
                # If no operation id was specified, just ignore the request and respond with '400: Bad Request' else log error
                if self.callerArgs.id is not None:
                    logger.error("Invalid operation '%s'" %
                                     self.callerArgs.id)
                # a hack to cause '400: Bad Request' for invalid operations
                self.supportedArgs.addReqArg("invalid_operation")
            if self.requestedAction == splunk.admin.ACTION_LIST and self.callerArgs.id in getOperations.keys():
                for arg in getOperations[self.callerArgs.id]:
                    self.supportedArgs.addReqArg(arg)
            if self.requestedAction == splunk.admin.ACTION_EDIT and self.callerArgs.id in postOperations.keys():
                for arg in postOperations[self.callerArgs.id]:
                   self.supportedArgs.addReqArg(arg)
            for arg in allOptArgs:
                self.supportedArgs.addOptArg(arg)
        except Exception as ex:
            e = sys.exc_info()[0]
            logger.error("Error setting up properties : %s" % e)
            logger.exception(ex)
            raise ex

    def handleList(self, confInfo):
        """
        """
        try:
            logger.info("Processing started for '%s' operation..." %
                        self.callerArgs.id)
            configuredAppliances = {}
            logger.debug("Calling entity.getEntities()")
            entities = entity.getEntities(['configs', 'inputs'], namespace="snmp_ta", owner='nobody',
                                          sessionKey=self.getSessionKey(), count=100, search="index=lunasa_appliance")
            logger.debug(
                "Enumerting configured appliances from '%d' entities" % len(entities))
            for i, e in entities.items():
                # pattern : snmp://<config_name>_luna_appliance
                if i.startswith("snmp://") and i.endswith("_luna_appliance"):
                    config_name = i[7:i.rindex("_luna_appliance")]
                    logger.info(
                        "Found appliance configuration '%s'" % config_name)
                    appliance = LunaSnmpConfigEntity(config_name, e)
                    configuredAppliances[config_name] = appliance
                else:
                    logger.debug("Ignoring entity '%s'" % i)
            if len(configuredAppliances) == 0:
                logger.info("No appliance configuration found")
                return
            if self.callerArgs.id == 'checkconfignames':
                if self.callerArgs.data['config_names'][0] in [None, '', '[]']:
                    logger.error(
                        "Required parameter 'config Name' is either invalid or missing")
                    raise Exception(
                        "Required parameter 'config Name' is either invalid or missing")
                config_names = self.callerArgs.data['config_names']
                existing_config_names = []
                for config_name in json.loads(config_names):
                    if check_entity_exists(config_name, entities=entities):
                        existing_config_names.append(config_name)
                if len(existing_config_names) > 0:
                    confInfo['checkconfignames'].append(
                        'existing_config_names', '' + existing_config_names)
                else:
                    confInfo['checkconfignames'].append(
                        'existing_config_names', '[]')
            elif self.callerArgs.id == 'getappliancelist':
                for i, c in configuredAppliances.items():
                    logger.debug("Appending '%s,%s' to list." % (
                        c.getName(), c.getProperties()['destination']))
                    confInfo['getappliancelist'].append(
                        c.getName(), c.getProperties()['destination'])
            logger.info("Processing finished for '%s' operation." %
                        self.callerArgs.id)

        except Exception as ex:
            logger.exception(ex)
            e = sys.exc_info()[0]
            logger.error("Error listing properties : %s" % e)
            raise ex

    def handleEdit(self, confInfo):
        """
        urllib.parse.unquote_plus(str) decodes URI encoded string from js encodeURIComponent(json_str)
        urllib.parse.parse_qs(str) decodes query parameters and return them as dict
        urllib.parse.parse_qsl(str) decodes query parameters and return them as list of tuples
        """
        try:
            logger.info("Processing started for '%s' operation..." %
                        self.callerArgs.id)
            if self.callerArgs.id == 'removeappliances':
                if self.callerArgs.data['appliances_to_delete'][0] in [None, '', '[]']:
                    logger.error(
                        "Required parameter 'appliances_to_delete' is either invalid or missing")
                    raise Exception(
                        "Required parameter 'appliances_to_delete' is either invalid or missing")
                config_data = self.callerArgs.data['appliances_to_delete'][0]
                config_names = json.loads(config_data)
                logger.info(
                    "Appliance configuration list received for removal: " + ','.join(config_names))
                exception = False
                for config_name in config_names:
                    for suffix in configSuffixes:
                        try:
                            entity.deleteEntity(['configs', 'inputs'], "snmp://" + config_name + suffix,
                                                namespace="snmp_ta", owner='nobody', sessionKey=self.getSessionKey())
                        except Exception as ex:
                            exception = True
                            e = sys.exc_info()[0]
                            logger.error("Failed to delete child config: '%s'. Exception: %s" % (
                                config_name + suffix, e))
                    if exception:
                        logger.info(
                            "Appliance configuration '%s' deleted with errors." % config_name)
                        exception = False
                    else:
                        logger.info(
                            "Appliance configuration '%s' successfully deleted." % config_name)
            elif self.callerArgs.id == 'addappliances':
                for k, v in self.callerArgs.data.items():
                    logger.debug(("%s : %s") % (k, v))
                if self.callerArgs.data['appliances_to_add'][0] in [None, '']:
                    logger.error(
                        "Required parameter 'appliances_to_add' is either invalid or missing")
                    raise Exception(
                        "Required parameter 'appliances_to_add' is either invalid or missing")
                appliances_data = self.callerArgs.data['appliances_to_add'][0]
                appliances = json.loads(appliances_data)
                for i, a in appliances.items():
                    c = json.loads(a)
                    logger.info("Configuring appliance configuration: %s" % i)
                    # for k, v in c.items():
                    #     logger.debug("Appliance data [%s]: %s" % (k, v))
                    ret = validate_snmp_input_fields(c)
                    if ret != None:
                        logger.error(
                            "Validation failed for configuration '%s'. Fields failing validation: %s" % (i, ret))
                        del appliances[i]
                    else:
                        logger.info(
                            "Validation succeeded for configuration: %s" % i)
                exception = False
                for i, a in appliances.items():
                    for suffix in configSuffixes:
                        try:
                            c = json.loads(a)
                            c = add_missing_fields(c)
                            c.update(snmpConfigVariableFields[suffix])
                            logger.debug("Adding configuration: %s" % i+suffix)
                            new_entity = entity.Entity(
                                ['configs', 'inputs'], "snmp://" + i + suffix, contents=c, namespace="snmp_ta", owner='nobody')
                            entity.setEntity(
                               new_entity, sessionKey=self.getSessionKey())
                        except Exception as ex:
                            exception = True
                            e = sys.exc_info()[0]
                            logger.error(
                                "Failed to add child config: '%s'. Exception: %s" % (i + suffix, e))
                    if exception:
                        logger.info(
                            "Appliance configuration '%s' created with errors." % i)
                        exception = False
                    else:
                        logger.info(
                            "Appliance configuration '%s' successfully created." % i)
            logger.info("Processing finished for '%s' operation." %
                        self.callerArgs.id)
        except Exception as ex:
            e = sys.exc_info()[0]
            logger.error("Error editing properties : %s" % e)
            logger.exception(ex)
            raise ex


def main():
    logger.debug("main")
    splunk.admin.init(LunaHsmConfigHandler, splunk.admin.CONTEXT_NONE)


if __name__ == '__main__':

    main()
