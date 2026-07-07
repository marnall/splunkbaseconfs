from __future__ import unicode_literals
import sys
import six
import splunk.admin as admin
from logger import setup_logger
from util.utils import verify_https_url, deploy_macros, normalise_log_level
from util.splunk_access import SplunkAccess
from ts.settings import default_ui_url
import logging

url = "url"

class ParameterValidationException(Exception):
    pass

class SplunkSetupArg(object):
    """Quick and dirty class for setup arguments"""
    supported_arg_types = [bool, int, url, str]

    def __init__(self, name, param_type, required=False, skip_validation=False):
        self.name = name
        self.type = param_type
        self.required = required
        self.value = None
        self.skip_validation = skip_validation

    def set_value(self, value):
        self.value = value

    def __str__(self):
        return self.name


param_general_log_level = SplunkSetupArg("log_level", str, required=True)
param_dm_es = SplunkSetupArg("es_integrated", bool, required=True)
param_dm_ts = SplunkSetupArg("dm_acceleration_enabled", bool, required=True)
param_ingestion_integrator_ssh = SplunkSetupArg("siem_integrator", str, required=True)
param_ingestion_snapshot = SplunkSetupArg("optic", bool, required=True)
param_ingestion_username = SplunkSetupArg("username", str, required=True)
param_ingestion_apikey = SplunkSetupArg("apikey", str, required=True)
param_proxy_host = SplunkSetupArg("proxy_host", str)
param_proxy_port = SplunkSetupArg("proxy_port", int)
param_proxy_username = SplunkSetupArg("proxy_username", str)
param_proxy_password = SplunkSetupArg("proxy_password", str)
param_ingestion_snapshot_url = SplunkSetupArg("url", url, required=True)
param_threat_model_poll_time = SplunkSetupArg("tm_poll_time", int, required=True)
param_threat_model_retention_time = SplunkSetupArg("tm_retention_period", int, required=True)
param_threat_model_force_sync = SplunkSetupArg("force_sync", bool, required=True)
param_invisible_update_only = SplunkSetupArg("update_only", bool, skip_validation=True)
param_search_custom_command = SplunkSetupArg("custom_search_command_matching", bool, required=True)
param_workflow_onprem = SplunkSetupArg("on_prem_url", url)
param_snapshot_id = SplunkSetupArg("snapshot_id", int)
param_no_proxy = SplunkSetupArg("no_proxy", str)
param_use_proxy_env = SplunkSetupArg("use_proxy_env", bool)
param_tm_max_body_size = SplunkSetupArg("tm_max_body_size", int, required=True)

args = [
    param_general_log_level,
    param_dm_es,
    param_dm_ts,
    param_ingestion_integrator_ssh,
    param_ingestion_snapshot,
    param_ingestion_username,
    param_ingestion_apikey,
    param_use_proxy_env,
    param_no_proxy,
    param_proxy_host,
    param_proxy_port,
    param_proxy_username,
    param_proxy_password,
    param_ingestion_snapshot_url,
    param_threat_model_poll_time,
    param_threat_model_retention_time,
    param_threat_model_force_sync,
    param_invisible_update_only,
    param_search_custom_command,
    param_workflow_onprem,
    param_snapshot_id,
    param_tm_max_body_size
]

supported_args = [x.name for x in args]

supported_bool_true = [1, "1", "enabled"]
supported_bool_false = [0, "0", "disabled"]
supported_bool_types = supported_bool_false + supported_bool_true

onprem_static_workflow_prepend = "ThreatStream Portal"
onprem_static_workflow_key = "link.uri"


class ConfigApp(admin.MConfigHandler):
    """Set up supported arguments"""

    STANZA = 'ts_app'
    CRED_NAME = 'ts_optic_cred'
    PROXY_NAME = 'ts_proxy_cred'

    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in supported_args:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        """List the setup values within the App"""
        conf_dict = self.readConf("ts_setup")
        logger = setup_logger('ts_install', static_msg_part="setup-list")


        if conf_dict is not None:
            for stanza, settings in conf_dict.items():
                for key, val in settings.items():
                    # Old options can be included if we do ensure the keys are in our supported args
                    if key in supported_args:
                        confInfo[stanza].append(key, val)

            logger.setLevel(normalise_log_level(conf_dict["ts_app"][param_general_log_level.name]))
            logger.debug("Listing Setup Values")
            logger.info("Printing conf_dict %s" % conf_dict)
            splunkd = SplunkAccess(session_key=self.getSessionKey(), logger=logger)
            config_manager = splunkd.get_config_manager()
            credential_manager = splunkd.get_cred_store()

            acceleration_enabled, earliest_time = config_manager.get_dm_acceleration()
            if acceleration_enabled or acceleration_enabled in [1, '1']:
                acceleration_enabled = 1
            else:
                acceleration_enabled = 0
            confInfo[self.STANZA].append(param_dm_ts.name, acceleration_enabled)

            # Display Credentials
            try:
                username, apikey = credential_manager.get(self.CRED_NAME)
                confInfo[self.STANZA].append(param_ingestion_username.name, username)
                confInfo[self.STANZA].append(param_ingestion_apikey.name, apikey)
            except Exception:
                logger.error("Unable to decrypt optic credentials")
                raise AttributeError("Unable to get %s from Splunk Cred Store" % self.CRED_NAME)

            try:
                proxy_username, proxy_password = credential_manager.get(self.PROXY_NAME)
                confInfo[self.STANZA].append(param_proxy_username.name, proxy_username)
                confInfo[self.STANZA].append(param_proxy_password.name, proxy_password)
            except Exception:
                logger.error("Unable to decrypt proxy credentials ")
                raise AttributeError("Unable to get %s from Splunk Cred Store" % self.PROXY_NAME)

    '''
    After user clicks Save on setup screen, take updated parameters,
    normalize them, and save them somewhere
    '''
    def handleEdit(self, confInfo):
        name = self.callerArgs.id
        data = self.callerArgs.data
        data_to_log = dict(data)
        try:
            data_to_log.pop(param_ingestion_apikey.name)
            data_to_log.pop(param_proxy_password.name)
        except KeyError:
            pass

        logger = setup_logger('ts_install', static_msg_part="setup-edit")

        python_version = "python2" if six.PY2 else "python3"
        logger.info("Running under a %s environment" % python_version)

        # Get splunk config
        splunkd = SplunkAccess(session_key=self.getSessionKey(), logger=logger)
        splunk_config = splunkd.get_config_manager()
        cred_store = splunkd.get_cred_store()


        # Do update stuff - only supported for flipping the force_sync flag
        if data.get(param_invisible_update_only.name):
            data.pop(param_invisible_update_only.name)
            self.writeConf('ts_setup', self.STANZA, data)
            return

        logger.debug("Starting Parameter Validation")
        validate_params(splunkd, data, logger)

        for key in data:
            if isinstance(data[key][0], six.binary_type) and six.PY3:
                data[key][0] = data[key][0].decode()
            if data[key][0] is None:
                data[key][0] = ''
            elif isinstance(data[key][0], six.string_types):
                data[key][0] = data[key][0].strip()

        logger.info("Setup Values: %s=%s" % (name, data_to_log))

        try:
            # Change the macros for both the ES DM and Custom Search Command if applicable
            deploy_macros(data[param_dm_es.name][0], data[param_search_custom_command.name][0], splunkd, logger)
        except Exception as e:
            logger.error("Failed to deploy macros")
            logger.exception(e)

        # enable data model acceleration for the TS Optic datamodel
        if data.get(param_dm_ts.name)[0] in supported_bool_true:
            try:
                acceleration_enabled, earliest_time = splunk_config.get_dm_acceleration()
                splunk_config.enable_acceleration(data[param_dm_ts.name][0], earliest_time)
                data.pop(param_dm_ts.name)
                logger.info("Accelerated TS_Optic datamodel")
            except Exception as e:
                logger.error("Failed to enable TS Optic data model acceleration. Error: %s" % str(e))
                logger.exception(e)
        else:
            logger.debug("Not accelerating Optic Datamodel")
        # enable/disable Optic dependent IOC tasks
        send_myattacks_task_name = "Daily Outbound Indicator Matches (ThreatStream MyAttacks)"
        try:
            optic = data[param_ingestion_snapshot.name][0]
            if optic in supported_bool_true:
                splunk_config.enable_saved_search(saved_search_name=send_myattacks_task_name, flag=1)
                logger.info("Enabled Search %s" % send_myattacks_task_name)
            else:
                logger.info("Not enabling %s search as Integrator SSH method does not provide endpoint" % send_myattacks_task_name)
        except Exception as e:
            logger.exception(e)

        # store optic credential - this can be used either for optic or for the Integrator Snapshot
        try:
            optic_username = data[param_ingestion_username.name][0]
            optic_apikey = data[param_ingestion_apikey.name][0]
            if optic_username and optic_apikey:
                cred_store.set(self.CRED_NAME, optic_username, optic_apikey)
                logger.info("ThreatStream Optic credential is successfully updated")
        except Exception as e:
            logger.error("Failed to update ThreatStream Optic credential")
            logger.exception(e)

        try:
            data.pop(param_ingestion_username.name)
            data.pop(param_ingestion_apikey.name)
        except KeyError:
            pass

        # store proxy credential
        if data.get(param_proxy_username.name, [""])[0] != "" and data.get(param_proxy_password.name, [""])[0] != "":
            try:
                proxy_username = data[param_proxy_username.name][0]
                proxy_password = data[param_proxy_password.name][0]
                if proxy_username and proxy_password:
                    cred_store.set(self.PROXY_NAME, proxy_username, proxy_password)
                    logger.info("Proxy credential is successfully updated")

            except Exception as e:
                logger.error("Failed to update Proxy credential")
                logger.exception(e)

            data.pop(param_proxy_username.name)
            data.pop(param_proxy_password.name)

        else:
            # Delete the proxy credential if it already exists - null proxy details
            logger.info("Deleting previous proxy credentials")
            cred_store.delete(self.PROXY_NAME)

        # Change workflow actions
        if param_workflow_onprem.name in data:
            on_prem_changes(splunkd, logger, data[param_workflow_onprem.name][0])
        else:
            revert_on_prem_changes(splunkd, logger)
            data[param_workflow_onprem.name] = [""]

        # add the threatstream_summary_index
        try:
            self._create_ts_index_if_needed(logger)
        except Exception as e:
            logger.exception(e)

        # attempt to add threatstream to the es apps_import_update modular input
        try:
            if splunkd.es is not None and splunkd.es:
                splunkd.es.set_app_import_update()
                logger.info("Added threatstream app to ES importer")
            else:
                logger.info("ES is not installed, not adding threatstream to ES importer")
        except Exception as e:
            logger.error("Unable to add threatstream app to ES import, reason=%s" % e)

        self.writeConf('ts_setup', self.STANZA, data)
        logger.info("Wrote new configuration values into ts_setup.conf")
        logger.info("Attempting to bounce the default modular input ts_ioc_ingest://threatstream_app")
        splunk_config.bounce_mod_input()
        logger.info('Finished executing ts_setup_handler.py')

    def _create_ts_index_if_needed(self, logger):
        base_url = 'admin/indexes'
        index_name = 'threatstream_summary'
        index_url = base_url + '/%s' % index_name

        splunkd = SplunkAccess(logger=logger, session_key=self.getSessionKey())
        ts_index_exists = True if splunkd.get_config_object(index_url, log404Error=False) else False
        logger.info(index_name + ' exists: %s' % ts_index_exists)
        if not ts_index_exists:
            response = splunkd.post(base_url, name=index_name)
            logger.info(
                index_name + ' %s' % 'is created successfully' if response else 'failed to be created')

def validate_params(splunkd, data, logger):
    """Function used to validate inputted parameters"""

    # Validate log_level
    try:
        validate_log_level(data.get("log_level", ["INFO"])[0])
    except ValueError as e:
        logger.error(e)
        sys.exit(1)

    logger.setLevel(normalise_log_level(data.get("log_level", ["INFO"])[0]))

    logger.debug("Starting Parameter Validation")

    # Type validation and required validation
    for param in args:
        if param.skip_validation:
            logger.debug("Skipping validation for parameter %s" % param.name)
            continue
        logger.debug("Parameter %s being validated" % param.name)
        err_msg = None
        short_err_msg = None
        try:
            param_value = data[param.name][0]
        except KeyError:
            # This is for when items are not populated by the setup view
            logger.debug("Unable to get parameter %s from request" % param.name)
            param_value = None

        if param.type == bool and param_value is not None:
            if param_value not in supported_bool_types:
                err_msg = "Expecting parameter %s with rejected value %s to have a value in %s, " % (
                    param, param_value, supported_bool_types)
                short_err_msg = "Setup: Bad setup parameter %s is not of type bool" % param

        elif param.type == url and param_value is not None:
            if "https://" not in param_value:
                err_msg = "Expecting parameter %s with rejected value %s to be a HTTPS URL" % (param, param_value)
                short_err_msg = "Setup: Bad parameter %s is not a https url" % param

            try:
                # Used to coerce correct URL types ( e.g. host with no path/query)
                data[param.name][0] = verify_https_url(param_value)
            except ValueError:
                raise ParameterValidationException("Invalid URL has been specified for parameter %s" % param)

        # Try to cast value as an integer
        elif param.type == int and param_value is not None:
            try:
                int(param_value)
            except ValueError:
                err_msg = "Expecting parameter %s with rejected value %s to be an integer" % (param, param_value)
                short_err_msg = "Setup: Bad parameter %s is not a integer"

        # If the parameter is required, make sure it isn't None
        if param.required:
            if param_value is None or '':
                err_msg = "Required parameter %s was not found in the request," \
                    "please ensure that this parameter is filled in" % param
                short_err_msg = "Setup: Parameter %s is required, but not filled in " % param

        if err_msg:
            logger.error(err_msg)
            splunkd.post_ui_message(short_err_msg, "error")
            raise ParameterValidationException(err_msg)

    # Validate either optic box is selected or integrator box is selected
    if data[param_ingestion_snapshot.name][0] in supported_bool_false and \
            data[param_ingestion_integrator_ssh.name][0] in supported_bool_false:

        err_msg = "Either Through Threatstream Integrator or Get Snapshot from Threatstream " \
                  "option must be selected for Threat Information Source"

        short_err_msg = "Setup: Must select a Threat Information Source"
        splunkd.post_ui_message(short_err_msg, "error")

        logger.error(err_msg)
        raise ParameterValidationException(err_msg)

    # Validate either CIM Datamodel is selected or Optic Datamodel is selected
    if data.get(param_dm_es.name, [0])[0] in supported_bool_false and \
            data.get(param_dm_ts.name, [0])[0] in supported_bool_false:
        err_msg = "Either ThreatStream or Splunk CIM datamodels must be selected from the datamodels section "

        short_err_msg = "Setup: ThreatStream or Splunk CIM must be selected for datamodel inspection"
        splunkd.post_ui_message(short_err_msg, "error")

        logger.error(err_msg)
        raise ParameterValidationException(err_msg)

    # if the es_integrated option is selected, check that the CIM app is installed
    if data.get("es_integrated", 0)[0] in supported_bool_true:
        # Skip the check if on Splunk Search Head Deployer
        if not splunkd.is_shc_deployer():
            if splunkd.cim is False:
                err_msg = "CIM App is not installed, this app required to use the CIM datamodels options"

                short_err_msg = "Setup: CIM App is required to be installed"
                splunkd.post_ui_message(short_err_msg, "error")

                logger.exception(err_msg)
                raise Exception(err_msg)
        else:
            logger.info("Skipping CIM App Install Check")

    logger.debug("Parameter Validation Finished")


def validate_log_level(log_level):
    """Validate the log level is suitable"""
    accepted_values = [logging.WARNING, logging.ERROR, logging.INFO, logging.DEBUG]

    if normalise_log_level(log_level) not in accepted_values:
        raise ValueError("Log level: %s is not an valid value. %s are valid values " % (
            log_level, ",".join(accepted_values)))


def on_prem_changes(splunkd, logger, on_prem_url):
    """Container function for OnPrem changes"""
    logger.info("Starting changes to configure the App to use OnPrem")

    on_prem_change_workflow_action(splunkd, logger, on_prem_url)


def on_prem_change_workflow_action(splunkd, logger, onprem_url):
    """Change the workflow actions within the app to point to an OnPrem instance"""
    workflow_actions = splunkd.get_workflow_action()

    logger.info("Found %s workflow actions within scope of the App" % len(workflow_actions))

    for workflow_action in workflow_actions:
        logger.debug("Inspecting workflow action: %s" % workflow_action)
        workflow_action_name = workflow_action
        if onprem_static_workflow_prepend not in workflow_action:
            logger.debug("Workflow action: %s does not depend on OnPrem, skipping update" %
                         workflow_action_name)
            continue
        logger.info("Updating workflow action %s with the ThreatStream On Prem_url: %s" %
                    (workflow_action_name, onprem_url))

        # Get the existing workflow config and change it
        workflow_config = splunkd.get_workflow_action(name=workflow_action_name)
        workflow_uri = None
        for key_entry in workflow_config:
            if onprem_static_workflow_key in key_entry["name"]:
                workflow_uri = splunkd.get_workflow_action(name=workflow_action_name, key="link.uri")

        if workflow_uri:
            if onprem_url and onprem_url not in workflow_uri:

                # Revert the workflow URL to default if its's currently different to the inputted onprem_url
                if default_ui_url not in workflow_uri:
                    revert_on_prem_changes(splunkd, logger)

                on_prem_workflow_uri = workflow_uri.replace(default_ui_url, onprem_url)
                splunkd.set_workflow_action(workflow_action_name, onprem_static_workflow_key, on_prem_workflow_uri)
            else:
                logger.info("No need to change workflow action: %s as it has the correct definition" % workflow_action_name)
        else:
            err_msg = "Unable to change workflow action %s as it does not have link.uri method" % workflow_action
            logger.error(err_msg)

def revert_on_prem_changes(splunkd, logger):
    workflow_actions = splunkd.get_workflow_action()

    logger.info("Found %s workflow actions within scope of the App: %s" %
                (len(workflow_actions), ','.join(workflow_actions)))

    for workflow_action in workflow_actions:
        workflow_action_name = workflow_action
        if onprem_static_workflow_prepend not in workflow_action:
            continue

        # Get the existing workflow config and change it
        workflow_config = splunkd.get_workflow_action(name=workflow_action_name)
        workflow_uri = None
        for key_entry in workflow_config:
            if onprem_static_workflow_key in key_entry["name"]:
                workflow_uri = splunkd.get_workflow_action(name=workflow_action_name, key="link.uri")

            if workflow_uri:
                if default_ui_url not in workflow_uri:
                    default_workflow_uri = default_ui_url + "/" + workflow_uri.split("/", 3)[-1]
                    logger.info("Reverting workflow action %s to default definition %s" % (workflow_action_name, default_workflow_uri))
                    splunkd.set_workflow_action(workflow_action_name, onprem_static_workflow_key, default_workflow_uri)

                else:
                    logger.info("No need to change workflow action: %s as it has the correct definition" % workflow_action_name)


# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
