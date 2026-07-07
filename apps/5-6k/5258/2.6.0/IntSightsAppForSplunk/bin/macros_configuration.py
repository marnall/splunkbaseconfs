import ta_intsights_declare  # noqa F401
import os
import traceback

from splunktaucclib.rest_handler.endpoint.validator import Validator

import splunk.admin as admin
from solnlib import conf_manager

from log_manager import setup_logging
from intsights_utils import create_service
import macros_ui_constants as consts
import constants as const
logger_name = os.path.splitext(os.path.basename(__file__))[0]
logger = setup_logging(logger_name)


class GetSessionKey(admin.MConfigHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()


def get_conf_manager(file, app, realm="__REST_CREDENTIAL__#{}#configs/conf-{}"):
    """Returns the  conf file manager."""
    session_key = GetSessionKey().session_key
    return conf_manager.ConfManager(session_key, app, realm=realm.format(app, file))

def get_conf_file(file, app): # noqa E502
    """Returns the content of conf file."""
    cfm = get_conf_manager(file, app).get_conf(file)
    return cfm

def set_upgraded(file, app, stanza):# noqa E502
    """Updates the content of conf file."""
    try:
        logger.info("Setting upgraded value to 1 (True)")
        cfm = get_conf_manager(file, app).get_conf(file)
        conf_stanza = cfm.get(stanza, {})
        updated_stanza = {key: value for key, value in conf_stanza.items() if not key.startswith("eai:")}
        updated_stanza["upgraded"] = 1
        cfm.update(stanza_name=stanza, stanza=updated_stanza)
        logger.info("Sucessfully set upgraded value to 1")
    except Exception as err:
        raise Exception(
            "Error occured while updating upgraded property value in additional_parameters."
            " Error :{}".format(err)
        )


def get_pure_field(value):
    """Returns parsed field name."""
    return value.replace("\"", "").strip()


def update_macros(service, macro_id, macro_name, macro_string):
    """Updates the macros.conf file."""
    try:
        logger.info("Updating macro: {}.".format(macro_name))
        service.post("properties/macros/{}".format(macro_name), definition=macro_string)
        macro_id = "{}_calc".format(macro_id)
        if macro_id in consts.IOC_ADDITIONAL_MACRO_DICT.keys():
            parent_macro_value_list = macro_string.split(",")
            if len(parent_macro_value_list) == 1:
                macro_value = macro_string.replace("\"", "")
            elif len(parent_macro_value_list) > 1 and parent_macro_value_list[0].strip() == "":
                macro_value = '"-"'
            elif macro_name.endswith("target_indicator_fields"):
                base_query = 'mvappend({}, {}, ",")'
                macro_query = base_query.format(get_pure_field(parent_macro_value_list[0]),
                                                get_pure_field(parent_macro_value_list[1]))
                for i in range(2, len(parent_macro_value_list)):
                    macro_query = 'mvappend({}, {}, ",")'.format(macro_query,
                                                                 get_pure_field(parent_macro_value_list[i]))
                macro_value = macro_query

            else:
                base_query = 'mvzip({}, {}, ",")'
                macro_query = base_query.format(get_pure_field(parent_macro_value_list[0]),
                                                get_pure_field(parent_macro_value_list[1]))
                for i in range(2, len(parent_macro_value_list)):
                    macro_query = 'mvzip({}, {}, ",")'.format(macro_query, get_pure_field(parent_macro_value_list[i]))
                macro_value = macro_query
            update_macros(service, macro_id, consts.IOC_ADDITIONAL_MACRO_DICT.get(macro_id), macro_value)
        logger.info("Macro: {} is updated successfully with definition = {}.".format(macro_name, macro_string))
    except Exception as err:
        raise Exception("Error occured while updating macro {}. Error :{}".format(macro_name, err))


def update_last_7day_corr_savedsearches(saved_search, saved_search_name, enable):
    """Enable/disable the specified savedsearches."""
    try:
        action = "enable" if enable == 1 else "disabl"
        logger.info("""{}ing savedsearch {}""".format(action, saved_search_name))
        if enable == 1:
            saved_search.enable()
        else:
            saved_search.disable()
        logger.info("Savedsearch {} is {}ed successfully.".format(saved_search_name, action))
    except Exception as err:
        raise Exception("Error occured while {}ing savedsearch {}. Error :{}.".format(action, saved_search_name, err))


class CorrelationValidator(Validator):
    """Class to Handle macros UI page."""

    def __init__(self):
        """Initialize."""
        super(CorrelationValidator, self).__init__()

    def validate(self, value, data):
        """Validate method of Splunk."""
        try:
            input_type = data.get("selected_input_type")
            conf = get_conf_file(file="ta_intsights_settings", app=const.TA_NAME)
            parameters = conf.get(consts.ADDITIONAL_SETTINGS_STANZA, {})

            if input_type == "alert":
                LABEL_DICT = consts.ALERT_FIELDS_LABEL_DICT
                MACRO_DICT = consts.ALERT_MACRO_DICT
            elif input_type == "vulnerability":
                LABEL_DICT = consts.VULNERABILITY_FIELDS_LABEL_DICT
                MACRO_DICT = consts.VULNERABILITY_MACRO_DICT
            elif input_type == "ioc":
                LABEL_DICT = consts.IOC_FIELDS_LABEL_DICT
                MACRO_DICT = consts.IOC_MACRO_DICT

            for key, value1 in LABEL_DICT.items():
                if data.get(key).strip() == '':
                    msg = "Field '{}' is required".format(value1)
                    self.put_msg(msg)
                    return False

            service = create_service(GetSessionKey().session_key)
            for key, value2 in MACRO_DICT.items():
                if ((parameters.get(key) != data.get(key) and (parameters.get(key) or data.get(key))) or # noqa W504
                        (parameters.get("upgraded", "0") == "0" and input_type == "ioc")):
                    final_data = data.get(key)
                    if key == "enable_tags_comments_api_calls":
                        final_data = "True" if data.get(key) in [True, "True", "true", 1, "1"] else "False"
                    if key == "enable_maintain_corr_indexes_actions":
                        final_data = 1 if data.get(key) in [True, "True", "true", 1, "1"] else 0
                        saved_searches = service.saved_searches
                        for corr_saved_search in consts.IOC_LAST_7_DAY_SEARCHES:
                            update_last_7day_corr_savedsearches(saved_searches[corr_saved_search],
                                                                corr_saved_search, final_data)
                    update_macros(service, key, value2, final_data)
            if (parameters.get("upgraded", "0") == "0" and input_type == "ioc"):
                set_upgraded(file="ta_intsights_settings", app=const.TA_NAME, stanza=consts.ADDITIONAL_SETTINGS_STANZA)
            return True
        except Exception as err:
            logger.error("Error: {}".format(err))
            logger.error("Traceback : {}".format(traceback.format_exc()))
            self.put_msg("Error occured when updating the macro settings. Please check the logs for more details.")
            return False
