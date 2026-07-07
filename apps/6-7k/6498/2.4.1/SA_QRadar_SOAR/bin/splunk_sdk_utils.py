# -*- coding: utf-8 -*-
# pragma pylint: disable=unused-argument, no-self-use

# (c) Copyright IBM Corp. 2024. All Rights Reserved.

import os
import sys
import json
import re
from six import u
import splunk
import splunk.admin as admin
from xml.dom.minidom import parseString as parseString

# add ../lib to the system path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Get the SA constants.
from app_constants import SA_ACTION_NAME

# Handle unicode in 2.x and 3.x
try:
    unicode
except NameError:
    unicode = str

DOLLAR_SUBSTITUTE_VALUE = u"dollar_substitute_value"

class SplunkSdkUtils:
    """
    SplunkSdkUtils
    """
    appName = None
    logger = None
    appUrl = None

    def __init__(self, logger, appName=None):
        """Init """
        self.appName = appName
        self.appUrl = "/servicesNS/nobody/" + self.appName
        self.logger = logger

    def getPassword(self, service, password_id):
        """
        Get the specified password ID from password storage.
        If the service object lacks the right permissions or we pass a bad passwordID,
        a splunklib.binding.HTTPError is raised.
        """
        res = service.storage_passwords.get(password_id)
        if res['status'] != 200:
            self.logger.error("Unexpected error '{}' - '{} reading password for password ID '{}'".format(res['status'], res['reason'], password_id))
        xml = b''
        for line in res['body']:
            xml += line.strip()
        dom = parseString(xml)
        keys = dom.getElementsByTagName('s:key')
        for key in keys:
            if key.getAttribute('name') == 'clear_password':
                password = key.childNodes[0].nodeValue
        return password

    def get_saved_search_info(self, service, search_name=None):
        """
        Retrives the supplied saved search from Splunk and returns the xml
        as a dictionary, excluding the junk fields.
        """
        res = service.saved_searches.get(search_name)
        if res.status == 200:
            result_dict = self.xmlToDict(res)
            return result_dict
        # otherwise saved search does not exist
        return {}

    def xmlToDict(self, response):
        """
        Takes a response from the Splunk API, converts the ResponseReader
        object to a dictionary, and returns it.
        The elements of the xml response that contain relevant data are all tagged as 's:key',
        so we take all those elements and cast to a dictionary, taking the name attibute as the
        key and the nodeValue of the first (and only) child as the value.
        """
        xml = b''
        for line in response['body']:
            xml += line.strip()
        dom = parseString(xml)
        keys = dom.getElementsByTagName('s:key')
        result_dict = {}
        for key in keys:
            if key.childNodes:
                k = key.getAttribute('name')
                v = key.childNodes[0].nodeValue
                result_dict[k] = v
        return result_dict


    def getConfig(self, service):
        """
        Gets the sa_resilient configuration from the server and returns the xml
        converted to a dictionary, discarding the junk fields.
        """
        config_url = 'configs/conf-{0}/config'.format(SA_ACTION_NAME)
        res = service.get(config_url)
        result_dict = self.xmlToDict(res)
        return result_dict

    def getAlertParamters(self, service, action_name):
        """
        Gets the paramters associated with the provided alert action name
        """
        return service.confs["alert_actions"][action_name]
    
    def updateAlertParameters(self, stanza, params):
        """
        Updates an alert configuration Stanza object with any parameters that arent in the list
        fetched from Resilient. We can only add fields to this stanza, as Splunk forbids
        DELETE requests to this endpoint. This means that deleted fields in Resilient will
        persist in the Splunk mapping and begin to accumulate (this is ok, Resilient
        will not throw an exception).

        We cannot post a new null field to the endpoint, so we first post a non-empty string
        and thne update the value to null once the field has been created.
        
        .submit() adds the provided key:value pair to the Stanza object
        .update() pushes the data from the Stanza object to Splunk

        Note: it is still possible to delete fields in the mapping manually.
        - Remove the field(s) from local/alert_actions.conf
        - Restart splunkd
        """
        ara_dict = stanza.content

        for param in params:
            if param not in ara_dict.keys():
                self.logger.info("Adding newly discovered field from Resilient: " + param)
                stanza.submit({param: " "})
                stanza.submit({param: ""})
                stanza.update()
        return

    # used in the tests only
    def get_parameters_conf(self, service, action_name):
        res = service.get("configs/conf-alert_actions/" + action_name, **{"output_mode": "json"})
        content = json.loads(res['body'].read())
        # return the params we have defined
        return content['entry'][0]['content'].keys()

    def update_notable_comment(self, sessionKey, event_id, message):
        """Add message as comment to notable event identified by event_id"""

        args = {}
        args["comment"] = message
        args["ruleUIDs"] = [event_id]
        url = "/services/notable_update"
        return splunk.rest.simpleRequest(url,
                                         sessionKey=sessionKey,
                                         postargs=args)

    def get_tokens(self, config):
        """
        Given a dictionary return the list of tokens in the dictionary values.
        A token is a string delimited by 2 dollar sign characters: $token$. 
        For each token, return the string between the two dollar sign.  
        Prior to adding this function, the add-on was computing the tokens from 
        the mapping string that contained key and values together.  If a value 
        contained a $ that was not a token delimiter, errors occurred trying to
        compute tokens over multiple fields which is not correct.
        """
        tokens = []
        if config:
            regex = r"\$(.+?)\$"
            for k, v in config.items():
                tokens_in_value = re.findall(regex, v)
                for token in tokens_in_value:
                    tokens.append(token)
        return tokens

    def map_config_result(self, config, result):
        """
        The config contains basically the template. Here we are going to substitute
        the values in result.
        This is the tough part because we don't have the spec. There could be many
        corner cases. Separate this in its own function so it can be thoroughly
        (as much as possible) tested by unit tests.
        And we are also making assumptions here.
        Note that in resilient_client:create_incident, we will cast the values
        into proper types. So here we map into string, and cast it later

        How many tokens do we need to handle, besides result? Refer to this link
        https://docs.splunk.com/Documentation/Splunk/7.2.5/AdvancedDev/ModAlertsLog#Pass_search_result_values_to_alert_action_tokens

        Also refer to our test file testSplunkSdkUtils.py for summary of tokens
        supported by Splunk.

        Assumptions:
        1. Only one layer of the result dict is allowed to access. Example like
        result.some_dict.some_field is not handled
        2. Splunk handles only a subset of the above tokens. We try our best to follow Splunk

        :param config:
        :param result:
        :return:
        """
        ret_mapping = {}
        #
        #   We only care about the one with none-empty value
        #
        mapping = dict((k, v) for k, v in config.items() if v is not u'')
        self.logger.info("Mapping: " + str(mapping))
        mapping_str = json.dumps(mapping, ensure_ascii=False)

        #
        # find all the tokens: something wrapped by $xxxx$ like $result.user$
        #
        tokens = self.get_tokens(mapping)
        self.logger.info("tokens: " + str(tokens))
        #
        #   Go through each token to do substitution
        #
        for token in tokens:
            fields = token.split('.')
            if len(fields) == 2 and fields[0] == "result" and fields[1] in result:
                value = SplunkSdkUtils.cleanup(result[fields[1]])
                mapping_str = mapping_str.replace("${}$".format(token), value)
            else:
                if len(fields) == 2 and fields[0] == "result":
                    # Don't know how to handle this. Log debug, and continue
                    self.logger.debug(u"Unable to do substitution for token: " + token)

        try:
            if sys.version_info >= (3, 9):
                ret_mapping = json.loads(mapping_str)
            else:
                ret_mapping = json.loads(mapping_str, encoding="utf-8")
        except Exception as e:
            self.logger.error(f"{e}\n Unable to convert string {mapping_str} back to dict in result.")
            ret_mapping = mapping

        return ret_mapping

    def map_modular_action_fields(self, modular_action, config):
        """
        Substitute the following tokens
            $name$      = modular_action.search_name
            $owner$     = modular_action.user
            $app$       = modular_action.app

        :param modular_action:  Modular action handler
        :param config:          config to be substituted
        :return:
        """
        mapping_str = json.dumps(config, ensure_ascii=False)

        #
        # find all the tokens: something wrapped by $xxxx$ like $result.user$
        #
        tokens = self.get_tokens(config)
        self.logger.debug("tokens: " + str(tokens))
        #
        #   Go through each token to do substitution
        #
        for token in tokens:
            if token == "owner" and modular_action.user is not None:
                mapping_str = mapping_str.replace(u"${}$".format(token),
                                                  SplunkSdkUtils.cleanup(modular_action.user))
            elif token == "name" and modular_action.search_name is not None:
                mapping_str = mapping_str.replace(u"${}$".format(token),
                                                  SplunkSdkUtils.cleanup(modular_action.search_name))
            elif token == "app" and modular_action.app is not None:
                mapping_str = mapping_str.replace(u"${}$".format(token),
                                                  SplunkSdkUtils.cleanup(modular_action.app))

        ret_mapping = config
        try:
            if sys.version_info >= (3, 9):
                ret_mapping = json.loads(mapping_str)
            else:
                ret_mapping = json.loads(mapping_str, encoding="utf-8")
        except Exception as e:
            self.logger.error(f"{e}\n Unable to convert string {mapping_str} back to dict in modular action.")
            ret_mapping = config

        return ret_mapping

    def map_search_information(self, search_info, config):
        """
        Substitute tokens related to search_info
        $alert.severity$
        $alert.expires$
        $cron_schedule$
        $description$
        $search$
        :param search_info:
        :param config:
        :return:
        """
        mapping_str = json.dumps(config, ensure_ascii=False)
        #
        # find all the tokens: something wrapped by $xxxx$ like $result.user$
        #
        tokens = self.get_tokens(config)
        self.logger.debug(u"tokens: " + str(tokens))
        #
        #   Go through each token to do substitution
        #
        TOKENS = {
            "alert.severity",
            "alert.expires",
            "cron_schedule",
            "description",
            "search"
        }
        for token in tokens:
            if token in TOKENS:
                value = SplunkSdkUtils.cleanup(search_info.get(token, ""))
                self.logger.debug(u"replacing {} with {}".format(token, value))
                mapping_str = mapping_str.replace(u"${}$".format(token), value)
            else:
                # Whatever token we don't know how to substitute, replace it with
                # empty string
                self.logger.debug(u"replacing {} with empty string".format(token))
                mapping_str = mapping_str.replace(u"${}$".format(token), u"")

        ret_mapping = config
        try:
            if sys.version_info >= (3, 9):
                ret_mapping = json.loads(mapping_str)
            else:
                ret_mapping = json.loads(mapping_str, encoding="utf-8")
        except Exception as e:
            self.logger.error(f"{e}\n Unable to convert string {mapping_str} back to dict in search.")
            # if there is an error, return the original (unmapped) config
            ret_mapping = config

        return ret_mapping

    def map_result(self, sessionKey, actionName, modular_action, result, service):
        """
        Get the alert_actions.config, and then map the result
        :param sessionKey:      sessionKey to use splunk SDK
        :param actionName:      action name to get the alert config
        :param modular_action:  modular action handler
        :param result:          raw result to be mapped
        :return:                mapped return
        """
        #
        #   Get saved_search_info
        #
        url = modular_action.settings["server_uri"] + \
            modular_action.settings["search_uri"]

        search_info = self.get_saved_search_info(service,
                                                 modular_action.settings["search_name"])

        config = SplunkSdkUtils.extract_config_from_search_info(search_info, actionName)

        ret_mapping = {}
        if config:
            #
            #   Map result. All tokens like $result.xxxx$
            #
            ret_mapping = self.map_config_result(config, result)
            #
            #   Map ModularAction fields
            #
            ret_mapping = self.map_modular_action_fields(modular_action,
                                                         ret_mapping)
            #
            #   Map search_info.
            #   including $cron_schedule$, $description$, $alert.severity$, and $alert.expires$
            ret_mapping = self.map_search_information(search_info,
                                                      ret_mapping)
            #
            #   Convert and token values containing $ back to $ after mapping is complete
            #
            ret_mapping = self.map_substitute_dollar(ret_mapping)
        else:
            self.logger.error("Error finding config from for: {}".format(self.appName))

        return ret_mapping


    def map_substitute_dollar(self, config):
        """
        If a value containing a '$' was substituted in the template token, then convert the "substitution value"
        back to a '$' character. Splunk uses the $ character as a delimiter and this creates
        problems if there is a $ in a token value - json fields may be deleted.
        """
        mapping_str = json.dumps(config, ensure_ascii=False)
        mapping_str = mapping_str.replace(DOLLAR_SUBSTITUTE_VALUE, '$')

        ret_mapping = config
        try:
            if sys.version_info >= (3, 9):
                ret_mapping = json.loads(mapping_str)
            else:
                ret_mapping = json.loads(mapping_str, encoding="utf-8")
        except Exception as e:
            self.logger.error(f"{e}\n Unable to convert string {mapping_str} back to dict after '$' substitution.")
            # if there is an error, return the original (unmapped) config
            ret_mapping = config

        return ret_mapping

    @staticmethod
    def extract_config_from_search_info(search_info, action_name):
        """
        Extract the config data from saved search information
        :param search_info:     saved search information
        :param action_name:     action name
        :return:
        """
        prefix = u"action.{}.param.".format(action_name)
        config = dict((k.replace(prefix, ""), v) for k, v in search_info.items() if k.startswith(prefix))
        return config

    @staticmethod
    def cleanup(in_value):
        """
        Cast it to string first if not unicode
        Otherwise, clean up input value by replacing " and ' by \" and \'
        Also replace $ character and substitute it back when template is completely mapped so that the
        $ in the values do not interfere with the $ characters delimiting the tokens.
        :param in_value:
        :return:
        """
        value = in_value
        if not isinstance(in_value, unicode) and not isinstance(in_value, str):
            value = str(in_value)
        else:
            # Escape characters as documented here: https://docs.splunk.com/Documentation/SCS/current/Search/Escapecharacters
            value = value \
                    .replace('\\', '\\\\') \
                    .replace('\b', '\\b') \
                    .replace('\f', '\\f') \
                    .replace('\n', '\\n') \
                    .replace('\t', '\\t') \
                    .replace('"', '\\"') \
                    .replace('$', DOLLAR_SUBSTITUTE_VALUE)
        return value
