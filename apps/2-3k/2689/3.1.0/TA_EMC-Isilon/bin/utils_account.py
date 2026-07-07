import os
import traceback
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from splunk import rest
import isilon_logger_manager as log
import const
import isilon_utilities as utility

APP_NAME = os.path.abspath(__file__).split(os.sep)[-3]
SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
logger = log.setup_logging("ta_emc_isilon_account")


class AccountHandler(ConfigMigrationHandler):
    """Account Handler."""

    def handleCreate(self, confInfo):
        """Handle creation of account in config file."""
        super(AccountHandler, self).handleCreate(confInfo)
        self.create_inputs()
        utility.reload_stanza(self.getSessionKey(), logger)

    def create_inputs(self):
        """Create given types of inputs into inputs.conf file."""
        try:
            logger.debug("message=creating_inputs | Creating inputs for cluster node - '{}'"
                         .format(self.callerArgs.id))
            bin_path = os.path.join(SPLUNK_HOME, "etc", "apps", APP_NAME, "bin")
            input_calls_file = open(os.path.join(bin_path, "inputs_v8_above.txt"), "r")
            pathList = input_calls_file.readlines()
            self.appName = APP_NAME
            acc_name = self.callerArgs.id
            index = self.callerArgs.data.get("index")[0]
            count = 0
            for entity_path in pathList:
                entity_path_list = entity_path.strip().split("::")
                endpt = entity_path_list[0]
                input_stanza = {}
                input_stanza.update(
                    {
                        "name": "isilon://{}_{}".format(
                            acc_name, const.MAPPING_DICT[endpt]
                        ),
                        "global_account": acc_name,
                        "sourcetype": const.SOURCETYPE,
                        "index": index,
                        "endpoint": "{}".format(entity_path_list[0]),
                        "interval": int(entity_path_list[1]),
                        "disabled": "1",
                    }
                )

                # Using Splunk internal API to create default input
                try:
                    rest.simpleRequest(
                        "/servicesNS/nobody/{}/configs/conf-inputs".format(APP_NAME),
                        self.getSessionKey(),
                        postargs=input_stanza,
                        rawResult=True,
                        method="POST",
                        raiseAllErrors=True,
                    )
                    count = count + 1
                except Exception as e:
                    logger.error("message=error_creating_input | Error occured while creating input "
                                 "for endpoint - '{}'.\n{}".format(entity_path_list[0], traceback.format_exc()))
                    if "409" in str(e):
                        e = ("Account is created but Inputs are not created for it because inputs are still present for"
                             " same account name. Please close this dialog box and remove the previously created inputs"
                             " and create new.")
                    raise Exception(e)
            logger.info("message=inputs_created | Successfully created {} inputs for cluster node - '{}'"
                        .format(count, acc_name))
        except KeyError:
            logger.error("message=error_creating_inputs | Error occured while creating inputs for node - '{}'.\n{}"
                         .format(acc_name, traceback.format_exc()))
            self.remove_inputs()
            utility.reload_stanza(self.getSessionKey(), logger)
            try:
                acc_name = self.callerArgs.id
                session_key = self.getSessionKey()
                conf_file = const.ACCOUNTS_CONF_FILE
                account_file = utility.get_conf_file(session_key, APP_NAME, conf_file)
                created_accounts = list(account_file.keys())

                for each in created_accounts:
                    if each == acc_name:
                        utility.splunk_rest_call("DELETE", const.ACCOUNTS_CONF_FILE, each, session_key)

            except Exception as err:
                raise Exception(err)
            raise KeyError("Invalid endpoint - '{}'".format(entity_path_list[0]))
        except Exception as e:
            logger.error("message=error_creating_inputs | An error occured while creating inputs.\n{}"
                         .format(traceback.format_exc()))
            raise Exception(e)

    def handleRemove(self, confInfo):
        """Handle the delete operation."""
        self.remove_inputs()
        utility.reload_stanza(self.getSessionKey(), logger)
        super(ConfigMigrationHandler, self).handleRemove(confInfo)

    def remove_inputs(self):
        """Remove given types of inputs from inputs.conf file."""
        try:
            acc_name = self.callerArgs.id
            logger.debug("message=deleting_inputs | Deleting all the inputs linked with cluster node - '{}'"
                         .format(acc_name))
            session_key = self.getSessionKey()
            conf_file = const.INPUTS_CONF_FILE
            inputs_file = utility.get_conf_file(session_key, APP_NAME, conf_file)
            created_inputs = list(inputs_file.keys())

            for each in created_inputs:
                if each.startswith("isilon://"):
                    configured_account = inputs_file.get(each).get('global_account')
                    if configured_account == acc_name:
                        utility.splunk_rest_call("DELETE", const.INPUTS_CONF_FILE, each, session_key)
            logger.info("message=deleted_the_inputs | Successfully deleted all the inputs linked with cluster "
                        "node - '{}'".format(acc_name))
        except Exception:
            logger.error("message=error_deleting_inputs | Error occured while deleting inputs "
                         "linked with cluster node - '{}'.\n{}".format(acc_name, traceback.format_exc()))

    def handleEdit(self, confInfo):
        """Handles the edit operation."""
        super(AccountHandler, self).handleEdit(confInfo)
        self.edit_inputs()
        utility.reload_stanza(self.getSessionKey(), logger)

    def edit_inputs(self):
        """Edit given types of inputs into inputs.conf file."""
        try:
            acc_name = self.callerArgs.id
            logger.debug("message=editing_inputs | Editing the inputs linked with cluster node - '{}'".format(acc_name))
            session_key = self.getSessionKey()
            conf_file = const.INPUTS_CONF_FILE
            inputs_file = utility.get_conf_file(session_key, APP_NAME, conf_file)
            created_inputs = list(inputs_file.keys())

            postargs = {
                "index": self.payload.get("index", "main"),
            }
            for each in created_inputs:
                if each.startswith("isilon://"):
                    configured_account = inputs_file.get(each).get('global_account')
                    if configured_account == acc_name:
                        utility.splunk_rest_call("POST", const.INPUTS_CONF_FILE, each, session_key, postargs=postargs)
            logger.info("message=edited_the_inputs | Successfully edited the inputs linked with cluster "
                        "node - '{}'".format(acc_name))
        except Exception:
            logger.error("message=error_editing_inputs | Error occured while updating inputs linked with "
                         "node - '{}'.\n{}".format(acc_name, traceback.format_exc()))
