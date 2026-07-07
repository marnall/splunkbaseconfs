import splunk.admin as admin
import json
import dome9_utils


COL_OPEN_ALERT_IN_DOME9 = "Open Alert in Dome9"
COL_EXCLUDE = "Exclude"
COL_CREATED_TIME = "Created Time"
COL_FINDING_KEY = "Finding Key"
COL_CLOUD_ACCOUNT_ID = "cloud_account_id"
COL_CLOUD_ACCOUNT_TYPE = "cloud_vendor"
COL_CLOUD_ACCOUNT_NAME = "Cloud Account"
COL_RULE_NAME = "Rule"
COL_RULESET_NAME = "Ruleset Name"
COL_RULE_LOGIC_HASH = "rule_logic_hash"
COL_RULE_ID = "rule_id"
COL_BUNDLE_ID = "bundle_id"
COL_ENTITY_ID = "Entity ID"
COL_ENTITY_NAME = "Entity"
COL_ENTITY_TYPE = "Entity Type"
COL_EXCLUDE_BY_RULE = "exclude_by_rule"
COL_EXCLUDE_BY_CLOUD = "exclude_by_cloud"
COL_EXCLUDE_BY_ENTITY = "exclude_by_entity"
COL_COMMENT = "comment"


import logging
from logger_manager import setup_logging
LOGGER = setup_logging("checkpoint_dome9_actions", logging.INFO)


class ActionRestcall(admin.MConfigHandler):
    '''
    Set up supported arguments
    '''
    def setup(self):
        """
        Sets the input arguments
        :return: None
        """
        # Set up the required parameters
        for arg in ['action', 'data']:
            self.supportedArgs.addReqArg(arg)

        # Set up the valid parameters
        for arg in []:
            self.supportedArgs.addOptArg(arg)
    

    def handle_exclude(self, data):
        """
        Send API request for exclude and return response (success, warning, error)
        """
        if COL_FINDING_KEY not in data or not data[COL_FINDING_KEY]:
            return (None, None, "Finding Key is required to make note about the created exclusion from Splunk in lookup.")

        if COL_COMMENT not in data or not data[COL_COMMENT]:
            return (None, None, "Valid comment is required.")

        if len(data[COL_COMMENT]) > 200:
            return (None, None, "Comment cannot be of more than 200 characters.")

        if COL_EXCLUDE_BY_RULE not in data or not data[COL_EXCLUDE_BY_RULE] or COL_EXCLUDE_BY_CLOUD not in data or not data[COL_EXCLUDE_BY_CLOUD] or COL_EXCLUDE_BY_ENTITY not in data \
             or not data[COL_EXCLUDE_BY_ENTITY] or COL_RULE_LOGIC_HASH not in data or COL_ENTITY_ID not in data or COL_BUNDLE_ID not in data or not data[COL_BUNDLE_ID] \
             or COL_CLOUD_ACCOUNT_ID not in data or COL_CLOUD_ACCOUNT_TYPE not in data or not data[COL_CLOUD_ACCOUNT_TYPE]:
            return (None, None, "Following values are compulsory in the data to make the API call: {}, {}, {}, {}, {}, {}, {}, {}, {}, {}.".format(COL_EXCLUDE_BY_RULE, 
                                 COL_EXCLUDE_BY_CLOUD, COL_EXCLUDE_BY_ENTITY, COL_RULE_LOGIC_HASH, COL_RULE_NAME, COL_RULE_ID, COL_ENTITY_ID, COL_BUNDLE_ID, 
                                 COL_CLOUD_ACCOUNT_ID, COL_CLOUD_ACCOUNT_TYPE))

        exclude_by_rule = dome9_utils.convert_to_bool(data[COL_EXCLUDE_BY_RULE])
        exclude_by_cloud = dome9_utils.convert_to_bool(data[COL_EXCLUDE_BY_CLOUD])
        exclude_by_entity = dome9_utils.convert_to_bool(data[COL_EXCLUDE_BY_ENTITY])

        if not exclude_by_rule and not exclude_by_entity:
            return (None, None, "One of Exclude-By-Rule or Exclude-By-Entity-ID is compulsory.")
        
        finding_key = str(data[COL_FINDING_KEY]).strip()
        comment = str(data[COL_COMMENT]).strip()

        rule_logic_hash = None
        if exclude_by_rule:
            rule_logic_hash = str(data[COL_RULE_LOGIC_HASH]).strip()
            if not rule_logic_hash:
                return (None, None, "Rule Logic Hash is compulsory if the exclusion is being created on the basis of Rule.")
        
        cloud_account_id = None
        if exclude_by_cloud:
            cloud_account_id = str(data[COL_CLOUD_ACCOUNT_ID]).strip()
            if not cloud_account_id:
                return (None, None, "Cloud Account ID is compulsory if the exclusion is being created on the basis of Cloud Account.")

        entity_id = None
        if exclude_by_entity:
            entity_id = str(data[COL_ENTITY_ID]).strip()
            if not entity_id:
                return (None, None, "Entity ID is compulsory if the exclusion is being created on the basis of Entity ID.")

        bundle_id = str(data[COL_BUNDLE_ID]).strip()
        cloud_account_type = str(data[COL_CLOUD_ACCOUNT_TYPE]).strip()

        try:
            credentials = dome9_utils.get_credentials(LOGGER, self.getSessionKey(), self.readConf(dome9_utils.CONF_FILE_NAME))
            connection_params = dome9_utils.get_connection_params(LOGGER,self.readConf(dome9_utils.CONF_FILE_NAME))
            proxies = dome9_utils.get_proxy_details(LOGGER, self.getSessionKey(), self.readConf(dome9_utils.CONF_FILE_NAME))
            exclude = dome9_utils.Exclude(LOGGER, credentials, connection_params, proxies, self.getSessionKey())
            return exclude.exclude(rule_logic_hash, entity_id, bundle_id, cloud_account_id, cloud_account_type, comment, finding_key)
        except Exception as e:
            msg = "Unexpected exception occurred while requesting for exclude."
            LOGGER.exception("{} - {}".format(msg, str(e)))
            return (None, None, msg)
        

    def handleEdit(self, conf_info):
        """
        handles POST method request
        """
        LOGGER.debug("Action request received.")
        try:
            action = str(self.callerArgs['action'][0])
            data = json.loads(self.callerArgs['data'][0])

            success = None
            error = None
            if action == COL_EXCLUDE:
                (success, warning, error) = self.handle_exclude(data)
            else:
                error = 'No action {} defined.'.format(action)
        except Exception as e:
            LOGGER.exception("Error while performing action: " + str(e))
            conf_info['action']['error'] = 'Error while performing action. Please check Checkpoint Dome9 Splunk logs for more details.'
            return

        conf_info['action']['success'] = str(success)
        conf_info['action']['warning'] = str(warning)
        conf_info['action']['error'] = str(error)
        LOGGER.debug("Action request served successfully.")



if __name__ == "__main__":
    admin.init(ActionRestcall, admin.CONTEXT_APP_AND_USER)
