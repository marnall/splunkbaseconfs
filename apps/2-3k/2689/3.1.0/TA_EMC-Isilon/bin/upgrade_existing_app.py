import ta_emc_isilon_declare  # noqa: F401
import sys
import traceback
from ta_emc_isilon_declare import ta_name
import isilon_utilities as utility
import isilon_logger_manager as log
import const

logger = log.setup_logging("ta_emc_isilon_upgrade")


class DeleteExistingData():
    """Class to delete the existing inputs and accounts conf file."""

    @staticmethod
    def delete_existing_inputs_and_account():
        """Method to delete old inputs and account details on upgrading the app."""
        try:
            logger.info("message=upgrading_add_on | Deleting old inputs and account details.")
            session_key = sys.stdin.readline().strip()

            input_conf_file_exists = utility.file_exist(const.INPUTS_CONF_FILE, ta_name)
            if input_conf_file_exists:
                inputs_conf_file = utility.get_conf_file(session_key, ta_name, const.INPUTS_CONF_FILE)
                created_inputs = list(inputs_conf_file.keys())
                for each in created_inputs:
                    if each.startswith("isilon://"):
                        utility.splunk_rest_call("DELETE", const.INPUTS_CONF_FILE, each, session_key)
                logger.info("message=deleted_old_inputs | Successfully deleted old inputs.")
                utility.reload_stanza(session_key, logger)

            old_acc_conf_file = "isilonappsetup"
            account_conf_file_exists = utility.file_exist(old_acc_conf_file, ta_name)
            if account_conf_file_exists:
                accounts_conf_file = utility.get_conf_file(session_key, ta_name, old_acc_conf_file)
                created_accounts = list(accounts_conf_file.keys())
                for each in created_accounts:
                    utility.splunk_rest_call("DELETE", old_acc_conf_file, each, session_key)
                logger.info("message=deleted_old_account | Successfully deleted old account.")

            # disable the script
            postargs = {"disabled": "1", }
            utility.splunk_rest_call(
                "POST", const.INPUTS_CONF_FILE, const.UPGRADE_SCRIPT_STANZA, session_key, postargs=postargs)
            logger.info("message=updated_the_add_on | Upgrade script ran successfully.")
        except Exception:
            logger.error("message=upgrade_add_on_script_error | An error occured while deleting the inputs and account"
                         " details of existing app.\n{}".format(traceback.format_exc()))


if __name__ == "__main__":
    DeleteExistingData.delete_existing_inputs_and_account()
