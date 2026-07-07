"""This module contain utilities related to modular inputs."""
import import_declare_test  # noqa F401
import json
import google.auth
from solnlib import conf_manager
from solnlib.modular_input import checkpointer
import splunk.rest as rest
import traceback
import os.path as op
import httplib2
import sys
from TA_GoogleSCC_consts import constants

APP_NAME = __file__.split(op.sep)[-3]


def get_credentials(session_key, account_name, logger):
    """Provide credentials of the configured account.

    Args:
        session_key: current session session key
        logger: log object

    Returns:
        Dict: A Dictionary having account information.
    """
    try:
        cfm = conf_manager.ConfManager(
            session_key,
            import_declare_test.ta_name,
            realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(
                import_declare_test.ta_name, import_declare_test.ta_accounts_conf
            ),
        )  # noqa: E501

        account_conf_file = cfm.get_conf(import_declare_test.ta_accounts_conf)
        service_account_json = account_conf_file.get(account_name).get('service_account_json')
        service_account_json = json.loads(service_account_json)
        organization_id = account_conf_file.get(account_name).get('organization_id')
        credential_configuration_file = account_conf_file.get(account_name).get("credential_configuration_file")
    except Exception:
        logger.error("message=account_error |"
                     " Failed to fetch Google SCC Account details from configuration.\n"
                     "{}".format(traceback.format_exc()))
        sys.exit(1)
    return {
        "service_account_json": service_account_json,
        "credential_configuration_file": credential_configuration_file,
        "organization_id": organization_id,
    }


def checkpoint_handler(logger, session_key, key, checkpoint_name):
    """
    Handle checkpoint.

    Args:
        logger: log object
        session_key: current session session key
        key: key name in checkpoint
        checkpoint_name: name of checkpoint

    Returns:
        Boolean: True or False according to checkpoint value
    """
    try:
        checkpoint_collection = checkpointer.KVStoreCheckpointer(
            checkpoint_name, session_key, APP_NAME
        )
        checkpoint_dict = checkpoint_collection.get(checkpoint_name) or {}
        if not checkpoint_dict:
            logger.info("message=checkpoint_not_found |"
                        " Checkpoint not found for input '{}', hence setting historical flag to 1".format(key))
            checkpoint_collection.update(checkpoint_name, {key: constants.FLAG})
            return True
        else:
            logger.info("message=checkpoint_found |"
                        " Checkpoint found for input {}".format(key))
            return False

    except Exception:
        logger.error("message=checkpoint_error |"
                     " Error in Checkpoint handling.\n{}".format(traceback.format_exc()))
        return False


def get_proxy_settings(logger, session_key):
    """
    Read proxy settings.

    Args:
        logger: log object
        session_key: current session session_key

    Returns:
        Dict: A dictionary proxy having settings
    """
    try:
        settings_cfm = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            realm="__REST_CREDENTIAL__#{}#configs/conf-ta_googlescc_settings".format(
                APP_NAME
            ),
        )
        ta_googlescc_settings_conf = settings_cfm.get_conf(
            "ta_googlescc_settings"
        ).get_all()

        proxy_settings = None
        proxy_stanza = {}
        for key, value in ta_googlescc_settings_conf["proxy"].items():
            proxy_stanza[key] = value

        if int(proxy_stanza.get("proxy_enabled", 0)) == 0:
            logger.info("message=proxy_disabled | Proxy is disabled. Returning None")
            return proxy_settings
        proxy_port = proxy_stanza.get("proxy_port")
        proxy_url = proxy_stanza.get("proxy_url")
        proxy_type = proxy_stanza.get("proxy_type")  # noqa F481
        proxy_username = proxy_stanza.get("proxy_username", "")
        proxy_password = proxy_stanza.get("proxy_password", "")

        if proxy_type == "socks5":
            proxy_type = httplib2.socks.PROXY_TYPE_SOCKS5
        elif proxy_type == "socks4":
            proxy_type = httplib2.socks.PROXY_TYPE_SOCKS4
        elif proxy_type == "https":
            proxy_type = httplib2.socks.PROXY_TYPE_HTTP

        if proxy_url:
            proxy_settings = httplib2.ProxyInfo(
                proxy_type=proxy_type,
                proxy_host=proxy_url,
                proxy_port=int(proxy_port),
                proxy_user=proxy_username,
                proxy_pass=proxy_password,
            )
        logger.info("message=fetched_proxy_details | Successfully fetched configured proxy details.")
        return httplib2.Http(proxy_info=proxy_settings, timeout=constants.TIMEOUT_TIME)

    except Exception:
        logger.error("message=proxy_error |"
                     " Failed to fetch proxy details from configuration.\n{}".format(traceback.format_exc()))
        sys.exit(1)


def is_gcp_vm(logger):
    """
    Check whether app environment is on GCP vm or not.

    Args:
        logger: log object

    Returns:
        bool:  True if gcp instance else False

    """
    try:
        credentials, project_id = google.auth.default()
        logger.info("message=instance_details | Splunk is installed on GCP Instance.")
        return True
    except Exception:
        logger.info("message=instance_details | Splunk is installed on non-GCP Instance.")
    return False


def is_aws_vm(logger, session_key):
    """
    Check whether app environment is on AWS vm or not.

    Args:
        logger: log object
        session_key: current session session_key

    Returns:
        bool:  True if aws vm else False

    """
    try:
        scheme = get_scheme(logger, session_key)
        metadata_url = (
            "{}://169.254.169.254/latest/meta-data/".format(scheme)
        )
        http = httplib2.Http(timeout=5)
        response, context = http.request(metadata_url, method="GET")
        if response.status == 200:
            logger.info("message=instance_details | Splunk is installed on AWS VM.")
            return True
    except Exception:
        logger.info("message=instance_details | Splunk is installed on non-AWS VM.")
    return False


def is_azure_vm(logger, session_key):
    """
    Check whether app environment is on Azure vm or not.

    Args:
        logger: log object
        session_key: current session session_key

    Returns:
        bool:  True if azure vm else False

    """
    try:
        scheme = get_scheme(logger, session_key)
        metadata_url = (
            "{}://169.254.169.254/metadata/instance?api-version=2021-02-01".format(scheme)
        )
        headers = {"Metadata": "true"}
        http = httplib2.Http(timeout=5)
        response, context = http.request(metadata_url, method="GET", headers=headers)
        if response.status == 200:
            logger.info("message=instance_details | Splunk is installed on Azure VM.")
            return True
    except Exception:
        logger.info("message=instance_details | Splunk is installed on non-Azure VM.")
    return False


def get_project_id(logger, project_id=None, service_account_json=None):
    """Fetch project id for inputs."""
    try:
        if project_id:
            return project_id
        elif service_account_json and service_account_json.get('project_id') is not None:
            return service_account_json.get('project_id')
        else:
            return get_gcp_project_id(logger)
    except Exception:
        logger.error("message=project_id_error |"
                     " Error while fetching project id.\n{}".format(traceback.format_exc()))
        return ""


def get_gcp_project_id(logger):
    """
    Provide project_id from the metdata data of GCP vm.

    Args:
        logger: log object

    Returns:
        string: project id if gcp instance else empty string

    """
    try:
        credentials, project_id = google.auth.default()
        if project_id:
            return project_id
    except Exception:
        logger.error("message=project_id_error |"
                     " Error while fecthing project id from GCP Instance.\n{}".format(traceback.format_exc()))
    return ""


def get_scheme(logger, session_key):
    """
    Get scheme from the configuration file.

    Args:
        logger: log object
        session_key: current session session_key
    Returns:
        string: scheme from the configuration file

    """
    try:
        _, response_content = rest.simpleRequest(
            "/servicesNS/nobody/{}/configs/conf-{}/additional_parameters".format(
                import_declare_test.ta_name, import_declare_test.ta_settings_conf
            ),
            sessionKey=session_key,
            getargs={"output_mode": "json"},
            raiseAllErrors=True,
        )
        additional_parameters_info = json.loads(response_content)["entry"][0]["content"]
        http_scheme = additional_parameters_info.get('scheme')
        return http_scheme
    except Exception:
        logger.error("message=scheme_error |"
                     " Error occurred while fetching scheme from the configuration file.\n"
                     "{}".format(traceback.format_exc()))
    return "https"


def get_vm_details(logger, session_key):
    """
    Get VM details from checkpoint.

    Args:
        logger: log object
        session_key: current session session_key
    Returns:
        bool: True if GCP VM else False
        bool: True if AWS VM else False
        bool: True if Azure VM else False

    """
    try:
        checkpoint_name = constants.INSTANCE_CHECKPOINT
        checkpoint_collection = checkpointer.KVStoreCheckpointer(
            checkpoint_name, session_key, import_declare_test.ta_name
        )
        checkpoint_dict = checkpoint_collection.get(checkpoint_name) or {}
        is_gcp = checkpoint_dict.get("is_gcp", False)
        is_aws = checkpoint_dict.get("is_aws", False)
        is_azure = checkpoint_dict.get("is_azure", False)
        return is_gcp, is_aws, is_azure
    except Exception:
        logger.error("message=instance_details_error |"
                     " Error occurred while fetching instance details.\n{}".format(traceback.format_exc()))
        return False, False, False
