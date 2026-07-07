##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
import import_declare_test  # noqa: F401 isort: skip
import base64
import json
import sys  # noqa: F401
import traceback

import requests
import splunk.rest as rest  # noqa: F401
from import_declare_test import SETTINGS_CONF, ta_name
from solnlib import conf_manager, utils
from solnlib.modular_input import checkpointer
from splunktaucclib.rest_handler import util
from splunktaucclib.rest_handler.error import RestError

CHECKPOINTER = import_declare_test.CHECKPOINTER
API_TIME_OUT = 120

params = {
    "CONTENT_PARAM": "content",
    "F5_BIGIP_TEMPLATES_CONF_FILE_NAME": "f5_templates_ts",
}


def is_input_exists(callerargs_id, session_key, field):
    """
    This fuction will check for the fields(servers, templates) having inputs configured with it or not.
    :param callerargs_id: parameter containing the name of the raw from the callerArgs.
    :param session_key: parameter containing the session key.
    :param field: parameter containing the field name.
    :return tuple:
    """
    app_name = util.get_base_app_name()
    cfm = conf_manager.ConfManager(session_key, app_name)
    try:
        task_objs_dict = cfm.get_conf("inputs").get_all()
        task_items = list(task_objs_dict.items())
        if task_items:
            for task, task_info in task_items:
                fields = task_info.get(field)
                # If an input uses two or more templates, then it is stored as pipe separated value in 'templates' field.  # noqa E501
                if "|" in str(fields):
                    list_of_fields = str(fields).split("|")
                    if callerargs_id in list_of_fields:
                        return True, callerargs_id
                if fields == callerargs_id:
                    return True, fields
    except Exception:
        # Handle the case when no inputs configuration found. In this case, no need to
        # check delete raw exists in task configuration.
        pass
    return False, callerargs_id


def perform_validation(
    stanza_name, payload, conf_name, endpoint, existing, session_key
):
    """
    Perform the validation on configuration object.
    :param stanza_name: stanza name
    :param payload: payload
    :param conf_name: conf file name
    :param endpoint: endpoint object
    :param existing: boolean flag to identify create/update operation
    :param session_key: session key
    """
    if not existing:
        _check_name_for_create(stanza_name)

    # Check the configuration object is exist or not. set the None value if configuration object not found.
    try:
        cfm = conf_manager.ConfManager(session_key, util.get_base_app_name())
        entity = cfm.get_conf(conf_name).get(stanza_name)
    except Exception:
        entity = None

    if existing and not entity:
        raise RestError(404, '"%s" does not exist' % stanza_name)
    elif not existing and entity:
        raise RestError(409, 'Name "%s" is already in use' % stanza_name)

    endpoint.validate(stanza_name, payload, entity)


def _check_name_for_create(name):
    """
    Check the stanza name should not be default or not start with `_`
    :param name: stanza name
    """
    if name == "default":
        raise RestError(400, '"%s" is not allowed for entity name' % name)
    if name.startswith("_"):
        raise RestError(400, 'Name starting with "_" is not allowed for entity')


def get_ssl_value(session_key, stanza_name, logger):
    try:
        cfm = conf_manager.ConfManager(
            session_key,
            ta_name,
            realm="__REST_CREDENTIAL__#{}#configs/conf-splunk_ta_f5_settings".format(
                ta_name
            ),
        )
        cfm_settings = cfm.get_conf(SETTINGS_CONF)
        settings_conf_stanzas = cfm_settings.get_all()
        settings_conf_items = list(settings_conf_stanzas.items())
        if settings_conf_items:
            for stanza, stanza_info in settings_conf_items:
                if stanza == stanza_name:
                    ssl_value = (
                        True if utils.is_true(stanza_info.get("enable_ssl")) else False
                    )
                    return ssl_value
    except Exception as e:
        logger.error("Error while gettings ssl value: {}".format(e))

    return True


def validate_f5_bigip(session_key, f5_bigip_url, username, password, logger):
    """
    This function is used to create the F5 BigIP object.
    :return: This function returns the F5 object.
    """

    url_values = ("https://", f5_bigip_url, "/mgmt/shared/authn/login")
    url = "".join(url_values)
    data = {
        "username": username,
        "password": password,
        "loginProviderName": "tmos",
    }
    ssl_value = get_ssl_value(session_key, "ssl_verify", logger)
    try:
        r = requests.post(
            url=url, data=json.dumps(data), verify=ssl_value, timeout=API_TIME_OUT
        )
        return r
    except Exception as e:
        raise Exception(e)


def encode(value):
    """
    Encode a string using the URL- and filesystem-safe Base64 alphabet.
    :param value: string to converted into base64
    :return: base64 encoded string
    """
    if value is None:
        return ""
    return base64.urlsafe_b64encode(value.encode("utf-8").strip()).decode()


def decode(value):
    """
    Decode a string using the URL- and filesystem-safe Base64 alphabet.
    :param value: string to be decoded
    :return: decoded string
    """
    if value is None:
        return ""
    return base64.urlsafe_b64decode(value).decode()


def checkpoint_handler(session_key, check_point_key, data, logger):
    """
    Handles checkpoint
    """
    checkpoint_collection = checkpointer.KVStoreCheckpointer(
        CHECKPOINTER, session_key, ta_name
    )
    try:
        logger.info("Updating {} as checkpoint value".format(data))
        checkpoint_collection.update(check_point_key, data)
    except Exception as e:
        logger.error("Updating checkpoint failed. Exception occurred : {}".format(e))


def check_if_checkpoint_exist(session_key, check_point_key, logger):
    try:
        checkpoint_collection = checkpointer.KVStoreCheckpointer(
            CHECKPOINTER, session_key, ta_name
        )
        checkpoint_dict = checkpoint_collection.get(check_point_key)  # noqa: F841
        if checkpoint_dict:
            decode_value = decode(str(checkpoint_dict))
            return decode_value
    except Exception as e:  # noqa: F841
        logger.error("Error in Checkpoint handling : {}".format(traceback.format_exc()))

    return None


def delete_checkpoint(session_key, checkpoint_key, logger):
    try:
        checkpoint_collection = checkpointer.KVStoreCheckpointer(
            CHECKPOINTER, session_key, ta_name
        )
        checkpoint_collection.delete(checkpoint_key)
    except Exception as e:
        logger.error("Error occuered while deleting checkpoint: {}".format(e))


def get_session_key(logger):
    """
    This function is used to get the session key.
    :return: This function returns the session_key value.
    """
    try:
        session_key = sys.stdin.readline().strip()
    except Exception as e:
        logger.error("Exception occured while getting session key: " + str(e))

    return session_key
