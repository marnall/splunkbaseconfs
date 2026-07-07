import ta_cloudknox_declare  # noqa: F401
from splunklib import binding
from solnlib import conf_manager
from log_manager import setup_logging
from cloudknox_consts import inputs_conf_file, inputs_upgradation_stanza
from ta_cloudknox_declare import ta_name
import cloudknox_upgrade_utility as utility
from cloudknox_collect import CloudKnoxCollect


logger = setup_logging("upgrade_existing_inputs")


class UpgradeExistingInputs():
    """Class to upgrade the existing inputs.conf file."""

    @staticmethod
    def upgrade_each_existing_input_stanzas(session_key):
        """
        Update the stanzas in inputs.conf file.

        :param session_key: The session key value.
        :param cfm: Object of the ConfManager to perform operations on the conf files.
        """
        collect_obj = CloudKnoxCollect(session_key, ta_name)
        response = collect_obj.cloudknox_get_all_auth_systems()
        logger.info("Fetching CloudKnox auth systems.")
        # try to load the response as json
        AUTH_SYS = response.json().get("data")

        cfm = conf_manager.ConfManager(
            session_key, ta_name, realm='__REST_CREDENTIAL__#TA-CloudKnox#configs/conf-ta_cloudknox_settings')
        cfm_input_conf_file = cfm.get_conf(inputs_conf_file)
        inputs_dict_obj = cfm_input_conf_file.get_all()
        input_items = list(inputs_dict_obj.items())
        if input_items:
            for input_stanza, input_info in input_items:
                # Add alert_type = activity to existing alert inputs
                # Modifying auth_systems in PAR inputs to include the ids in ()
                if input_stanza.startswith("cloudknox_alerts://") and "alert_type" not in input_info:
                    input_info['alert_type'] = "activity"
                    del input_info["eai:access"]
                    cfm_input_conf_file.update(input_stanza, input_info)
                elif input_stanza.startswith("cloudknox://") and "auth_systems" in input_info:
                    auth_system_names_list = []
                    auth_system_type = input_info["auth_system_type"]
                    auth_systems = input_info["auth_systems"]
                    auth_systems_list = auth_systems.split(",")
                    if "All" in auth_systems_list:
                        auth_system_names_list.append("All")
                        auth_systems_list.remove("All")
                    for each in AUTH_SYS:
                        if each.get("name") in auth_systems_list and each["type"].upper() == auth_system_type:
                            offline_status = "[OFFLINE] " if each.get("status", "invalid").upper() == "OFFLINE" else ""
                            auth_system_names_list.append(
                                offline_status + each.get("name") + " (" + each.get("id") + ")")
                    new_auth_system_names_list = ",".join(auth_system_names_list)
                    input_info["auth_systems"] = new_auth_system_names_list
                    del input_info["eai:access"]
                    cfm_input_conf_file.update(input_stanza, input_info)

    @staticmethod
    def upgrade_existing_inputs():
        """Perform the operations required to upgrade existing inputs.conf file."""
        has_upgraded = "0"
        session_key = utility.get_session_key()
        cfm = conf_manager.ConfManager(
            session_key, ta_name, realm='__REST_CREDENTIAL__#TA-CloudKnox#configs/conf-ta_cloudknox_settings')
        has_upgraded = utility.check_has_upgraded_value(
            cfm, inputs_upgradation_stanza)
        if has_upgraded == "0":
            input_exists = utility.file_exist(inputs_conf_file, ta_name)
            try:
                if input_exists:
                    logger.info("Upgrading configured inputs.")
                    UpgradeExistingInputs.upgrade_each_existing_input_stanzas(session_key)
                    logger.info("Upgrading configured inputs completed.")
                else:
                    logger.info("No inputs configured to upgrade.")
                utility.update_settings_conf(session_key, inputs_upgradation_stanza)
            except binding.HTTPError as e:
                logger.error("HTTPError: " + str(e))
            except KeyError as e:
                logger.error("Keyerror exception: " + str(e))
            except Exception as e:
                logger.error("Unexpected error occurred: " + str(e))


if __name__ == "__main__":
    UpgradeExistingInputs.upgrade_existing_inputs()
