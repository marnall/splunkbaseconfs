#
# SPDX-FileCopyrightText: 2026 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#

import base64
import os
import urllib.parse
from traceback import format_exc

import splunk_ta_jmx_logger_helper as log_helper
import splunk_ta_jmx_rest as rest
from java_const import LOG_FILE_NAMES
from lxml import etree
from solnlib import conf_manager, splunkenv, utils
from splunk import admin
from splunktaucclib.rest_handler import util
from splunktaucclib.rest_handler.error import RestError

APPNAME = util.get_base_app_name()

params = {
    "DESTINATION_APP_PARAM": "destinationapp",
    "ACCOUNT_NAME_PARAM": "account_name",
    "ACCOUNT_PASSWORD_PARAM": "account_password",
    "CONTENT_PARAM": "content",
    "JMX_SERVERS_CONF_FILE_NAME": "jmx_servers",
    "JMX_TASKS_CONF_FILE_NAME": "jmx_tasks",
    "JMX_TEMPLATES_CONF_FILE_NAME": "jmx_templates",
    "CRED_REALM": "__REST_CREDENTIAL__#_{app_name}_account_#{destinationapp}#{stanza_name}",
    "EAI:APPNAME": "eai:appName",
    "DISABLED_PARAM": "disabled",
}


def is_input_exists(callerargs_id, session_key, field):
    """
    This method has checked the deletion of raw is used in tasks or not. If the value is used in task then return the
    tuple with True and field name otherwise return the tuple with False and field name.
    :param callerargs_id: parameter containing the name of the raw from the callerArgs.
    :param session_key: parameter containing the session key.
    :param field: parameter containing the field name.
    :return tuple:
    """
    app_name = util.get_base_app_name()
    field_name = app_name + ":" + callerargs_id
    cfm = conf_manager.ConfManager(session_key, app_name)
    try:
        task_objs_dict = cfm.get_conf("jmx_tasks").get_all()
        task_items = list(task_objs_dict.items())
        if task_items:
            for task, task_info in list(task_objs_dict.items()):
                fields = task_info[field]
                if field_name in fields.replace(" ", "").split("|"):
                    return True, field_name
    except Exception:
        # Handle the case when no jmx_tasks configuration found. In this case, no need to
        # check delete raw exists in task configuration.
        pass
    return False, field_name


def check_data_duplication(
    servers_list, templates_list, tasks_stanza, input_name, logger
):
    """
    This method validates the possibility of data duplication, warning log message and returns bool value accordingly

    :param servers_list: list of server names
    :param templates_list: list of template names
    :param tasks_stanza: dict of task stanza
    :param input_name: String containing name of input name
    :param logger: Logger object
    :return: bool
    """

    servers_list = set(servers_list)
    templates_list = set(templates_list)
    for stanza_name, content in list(tasks_stanza.items()):
        if input_name == stanza_name:
            continue
        is_disabled = content.get("disabled", "0")
        stanza_templates = set(content.get("templates", "").replace(" ", "").split("|"))
        stanza_servers = set(content.get("servers", "").replace(" ", "").split("|"))
        stanza_status = "disabled" if utils.is_true(is_disabled) else "enabled"

        # a & b returns set() containing intersection of set a and set b if there is intersection else empty set()
        if templates_list & stanza_templates and servers_list & stanza_servers:
            if stanza_status == "enabled":
                logger.warning(
                    "Selected templates: {} and servers: {} are already present in {} stanza: {}. "
                    "This may cause data duplication".format(
                        list(templates_list),
                        list(servers_list),
                        stanza_status,
                        stanza_name,
                    )
                )
            return True

    return False


def update_conf_metadata(field_object, app_name):
    """
    This method has updated the appName metadata in the configuration object.
    :param field_object: configuration object.
    :param app_name: current addon name
    """
    field_object["eai:appName"] = app_name
    field_object.setMetadata(
        admin.EAI_ENTRY_ACL,
        {"app": app_name, "owner": "nobody"},
    )


def getConfigurationObject(session_key, destinationapp, conf_filename):
    """
    This method has checked the configuration file is exists or not. If the configuration file is available then it
    calls ConfManager get_conf event to returns the Conf file object otherwise it calls the ConfManager
    create_conf event to return the Conf file object.
    :param session_key: parameter containing the session key.
    :param destinationapp: destination app/addon name.
    :param conf_filename: configuration filename.
    :return Conf file object:
    """
    cfm = conf_manager.ConfManager(session_key, destinationapp)
    try:
        objs_dict = cfm.get_conf(conf_filename)
    except Exception:
        objs_dict = cfm.create_conf(conf_filename)

    return objs_dict


def getNamespaceForObject(session_key, conf_filename):
    """
    This method populate destination app name if not exist in configuration
    :param session_key: parameter containing the session key.
    :param conf_filename: configuration filename.
    :return dictionary of key value pair of stanza name and destination app:
    """
    cfm = conf_manager.ConfManager(session_key, util.get_base_app_name())
    entity_namespace_mapping = dict()
    try:
        stanzas = cfm.get_conf(conf_filename).get_all()
        if stanzas:
            for stanza, stanza_info in list(stanzas.items()):
                entity_namespace_mapping[stanza] = stanza_info[
                    params.get("EAI:APPNAME")
                ]
    except Exception:
        pass
    return entity_namespace_mapping


def encode(value):
    """
    Encode a string using the URL- and filesystem-safe Base64 alphabet.
    :param value: string to converted into base64
    :return: base64 encoded string
    """
    if value is None:
        return ""
    return base64.urlsafe_b64encode(value.encode("utf-8").strip())


def decode(value):
    """
    Decode a string using the URL- and filesystem-safe Base64 alphabet.
    :param value: string to be decoded
    :return: decoded string
    """
    if value is None:
        return ""

    return base64.urlsafe_b64decode(str(value)).decode()


def get_not_configure_server_list():
    """
    Fetch the server list and make a missing configured server list
    :return: not configured server list
    """
    server_list = []

    # This method is return the server configuration list.
    servers = splunkenv.get_conf_stanzas(params.get("JMX_SERVERS_CONF_FILE_NAME"))

    for key, value in list(servers.items()):
        # Check the account configuration is missing or not
        if value.get("has_account") == "1" and value.get("account_name") is None:
            server_list.append(key)
    return server_list


def _check_name_for_create(name):
    """
    Check the stanza name should not be default or not start with `_`
    :param name: stanza name
    """
    if name == "default":
        raise RestError(400, '"%s" is not allowed for entity name' % name)
    if name.startswith("_"):
        raise RestError(400, 'Name starting with "_" is not allowed for entity')


def perform_validation(
    stanza_name, payload, conf_name, endpoint, existing, session_key
):
    """
    perform the validation on configuration object.
    :param stanza_name: stanza name
    :param payload: payload
    :param conf_name: conf file name
    :param endpoint: endpoint object
    :param existing: boolean flag to identify create/update operation
    :param session_key: session key
    """
    if not existing:
        # Check the stanza name during create time event
        _check_name_for_create(stanza_name)

    # Check the configuration object is exist or not. set the None value if configuration object not found.
    try:
        cfm = conf_manager.ConfManager(session_key, util.get_base_app_name())
        entity = cfm.get_conf(conf_name).get(stanza_name)
        destination_app_param = params.get("DESTINATION_APP_PARAM")
        target_app = payload.get(destination_app_param)
        disabled_param = payload.get(params.get("DISABLED_PARAM"))

        # EAI Name used to update destinationapp field with addon name in which configuration is saved
        # This code block will handle the scenario in which destination field is not configured in stanza
        # destinationapp field will be populted with eai:appName value which is addon name on which conf is stored
        eai_appname = entity.get(params.get("EAI:APPNAME"))
        if target_app is None:
            if entity.get(destination_app_param) is not None:
                target_app = entity.get(destination_app_param)
            elif eai_appname is not None:
                target_app = eai_appname
            else:
                target_app = util.get_base_app_name
        elif target_app != eai_appname:
            target_app = eai_appname
        payload[destination_app_param] = target_app

        # Set the disabled key value from configuration dictionary if it's not available in the payload
        if disabled_param is None:
            payload[params.get("DISABLED_PARAM")] = entity.get(
                params.get("DISABLED_PARAM")
            )
    except Exception:
        entity = None

    if existing and not entity:
        raise RestError(404, '"%s" does not exist' % stanza_name)
    elif not existing and entity:
        raise RestError(409, 'Name "%s" is already in use' % stanza_name)

    endpoint.validate(
        stanza_name,
        payload,
        entity,
    )


def make_hash(obj):
    """
    Makes a hash out of anything that contains only list, dict and hashable types including string and numeric types
    :param `obj` : the object that is to be hashed
    :return: hash of the object
    """

    def freeze(obj):
        if isinstance(obj, dict):
            return frozenset({k: freeze(v) for k, v in obj.items()}.items())

        if isinstance(obj, list):
            return tuple(freeze(v) for v in obj)

        return obj

    return hash(freeze(obj))


def conf_reloader(
    session_key,
    logger,
    input_name,
    disabled="1",
    method="GET",
    splunkd_uri="https://127.0.0.1:8089",
    mod_input="ibm_was_jmx",
):

    """
    Reloads the <mod_input>'s inputs.conf end-point
    :param `session_key` : parameter containing the session key
    :param `logger` : Logger object to write logs
    :param `input_name` : string of the input from inputs.conf
    :param `disabled` : string of the status of the input
    :param `method` : string of the method of http request
    :param `splunkd_uri` : string of Splunkd URI
    :param `mod_input` : string of the modular input
    """

    input_name = urllib.parse.quote(input_name)

    enable_template = "{0}/servicesNS/nobody/{1}/data/inputs/{2}/{3}/enable"
    disable_template = "{0}/servicesNS/nobody/{1}/data/inputs/{2}/{3}/disable"
    delete_template = "{0}/servicesNS/nobody/{1}/data/inputs/{2}/{3}"
    # https://<management_splunkd_uri>/servicesNS/nobody/Splunk_TA_jmx/data/inputs/\
    # ibm_was_jmx/<input_name>/[enable|disable|]

    def reload_endpoint(template):
        endpoint = template.format(splunkd_uri, APPNAME, mod_input, input_name)
        logger.debug("Reloading the splunkd uri %s", endpoint)
        resp, _ = rest.splunkd_request(
            splunkd_uri=endpoint, session_key=session_key, _LOGGER=logger, method=method
        )
        if not resp or resp.status not in (200, 201):
            logger.error(
                "Failed to refresh %s, reason=%s", endpoint, resp.reason if resp else ""
            )

    input_disabled = True if utils.is_true(disabled) else False

    reload_endpoint(delete_template) if method == "DELETE" else (
        reload_endpoint(disable_template)
        if input_disabled
        else reload_endpoint(enable_template)
    )


def ibm_java_args_generator(ibm_was_args, server_name, logger):
    """
    Forms the Java arguments with required SSL and Soap file paths and configurations
    and returns the updated Java argument list.

    :param `ibm_was_args` : list of Java args used to invoke the Java class.
    :param `server_name` : str of the server stanza name
    :param `logger` : Logger object to write logs
    :return: list of Java properties
    """

    os_path = os.path
    os_sep = os_path.sep

    def file_presence_checker(filename):
        return os_path.isfile(
            os_sep.join(
                [
                    os_path.dirname(os_path.realpath(os_path.dirname(__file__))),
                    "local",
                    "config",
                    server_name,
                    filename,
                ]
            )
        )

    if file_presence_checker("ssl.client.props"):
        ssl_file_path = os_sep.join(
            [
                os_path.dirname(os_path.realpath(os_path.dirname(__file__))),
                "local",
                "config",
                server_name,
                "ssl.client.props",
            ]
        )
    else:
        logger.warning(
            "File ssl.client.props not found. Make sure the "
            "file exists at $SPLUNK_HOME/etc/apps/Splunk_TA_jmx/local/config"
            "/{}/".format(server_name)
        )
        ssl_file_path = ""

    if file_presence_checker("soap.client.props"):
        soap_file_path = os_sep.join(
            [
                os_path.dirname(os_path.realpath(os_path.dirname(__file__))),
                "local",
                "config",
                server_name,
                "soap.client.props",
            ]
        )
    else:
        logger.warning(
            "File soap.client.props not found. Make sure the "
            "file exists at $SPLUNK_HOME/etc/apps/Splunk_TA_jmx/local/config"
            "/{}/".format(server_name)
        )
        soap_file_path = ""

    if ssl_file_path and soap_file_path:
        ibm_was_args.insert(-1, "-Dcom.ibm.SSL.ConfigURL=file:" + ssl_file_path)
        ibm_was_args.insert(-2, "-Dcom.ibm.SOAP.ConfigURL=file:" + soap_file_path)
        return ibm_was_args

    return []


def server_extractor_from_xml(xml_str, logger):
    """
    Finds the server stanza name from xml_str and returns the server stanza name.
    :param `xml_str` : str(=bytes) of XML of the input that is invoked
    :param `logger` : Logger object to write logs
    :return: str of server_name
    """

    try:
        root = etree.fromstring(  # nosemgrep false-positive : The 'xml_str' is the arg which is fetched from the stdin while invoking the modular input. It doesn't take any user/external inputs. # noqa: E501
            xml_str
        )
        config_file = root.find(".//*[@name='config_file']").text
        config_file_dir = root.find(".//*[@name='config_file_dir']").text
        config_file_path = "".join(
            [
                os.environ["SPLUNK_HOME"],
                os.path.sep,
                config_file_dir,
                os.path.sep,
                config_file,
            ]
        )

        if os.path.isfile(config_file_path):
            try:
                server_name = (
                    etree.parse(  # nosemgrep false-positive : The 'config_file_path' passed in parse() is the arg which is fetched from the stdin while invoking the modular input. It doesn't take any user/external inputs. # noqa: E501
                        config_file_path
                    )
                    .find(".//jmxserver")
                    .get("jmxaccount", "")
                )
            except etree.XMLSyntaxError:
                # Fallback handling when XML config file cannot be directly parsed using `etree.parse`
                with open(config_file_path) as fr:
                    root = etree.fromstring(  # nosemgrep false-positive : We are reading a config XML maintained by the TA. It doesn't take any user/external inputs. # noqa: E501
                        fr.read()
                    )
                    server_name = root.find(".//jmxserver").get("jmxaccount", "")
            return server_name.split("#")[-1] if server_name else ""
        else:
            logger.warning(
                "File not found at the location {}. Please check the "
                "existence of the file.".format(config_file_path)
            )
            return ""
    except Exception:
        logger.error("Failed to extract server_name: {}".format(format_exc()))
        return ""


def input_extractor_from_xml(xml_str, logger):
    """
    Finds the input stanza name from xml_str and returns the input stanza name.
    :param `xml_str` : str(=bytes) of XML of the input that is invoked
    :param `logger` : Logger object to write logs
    :return: str of input stanza name
    """

    try:
        root = etree.fromstring(  # nosemgrep false-positive : The 'xml_str' is the arg which is fetched from the stdin while invoking the modular input. It doesn't take any user/external inputs. # noqa: E501
            xml_str
        )
        config = root.find("configuration")
        stanza = config.find("stanza")
        return stanza.get("name")
    except Exception:
        logger.error("Failed to extract input_name: {}".format(format_exc()))
        return ""


def set_logger_level(token):
    """
    Sets the logging level for all the add-on log files
    :param `token` : splunk session key
    """
    config_manager_obj = conf_manager.ConfManager(token, APPNAME)

    log_level = (
        config_manager_obj.get_conf("splunk_ta_jmx_settings")
        .get("logging", {})
        .get("loglevel", "INFO")
    )

    for logger_name in LOG_FILE_NAMES:
        log_helper.setup_logging(log_name=logger_name, level_name=log_level)
