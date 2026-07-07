import datetime
import os
import sys
import traceback

import const
import log
import netskope_utils
from solnlib import conf_manager
from splunk import rest
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunktalib.conf_manager import data_input_endpoints

logger = log.get_logger("ta_netskope_scripted_input")


class CreateModularInput:
    def __init__(self):
        pass

    def run(self):
        session_key = self._get_session_key()
        cfm = conf_manager.ConfManager(session_key, const.APP_NAME)
        inputs_cfm = conf_manager.ConfManager(
            session_key,
            const.APP_NAME,
            realm="__REST_CREDENTIAL__#{}#configs/conf-inputs".format(const.APP_NAME),
        )
        additional_parameters = self._get_additional_parameters(
            cfm, const.SCRIPTED_INPUT_PARAMETERS_STANZA_NAME
        )
        _are_mandatory_fields_present = self._validate_mandatory_fields(session_key, additional_parameters)
        if not _are_mandatory_fields_present:
            return

        self._delete_is_safe_to_delete_inputs(inputs_cfm)

        is_future_time = self._calculate_is_future_time(additional_parameters, session_key)
        if is_future_time:
            message = "Automated Scripted Input has reached the provided End DateTime. Please disable this scipted input from 'Data Inputs' once all automated inputs are deleted."
            logger.warn(message)
            netskope_utils.send_notification(
                message=message,
                input_name="scripted_input_for_automation",
                session_key=session_key,
                severity="warn",
                logger=logger
            )
            return

        inputs_creation_count = self._calculate_inputs_creation_count(inputs_cfm, additional_parameters)

        if inputs_creation_count <= 0:
            logger.info("No new inputs can be created due to maximum active inputs.")
            return

        self._create_inputs(session_key, additional_parameters, inputs_creation_count)
        self._reload_input_conf(session_key)

    def _validate_mandatory_fields(self, session_key, additional_parameters):
        """Validate if the mandatory fields for inputs creation are provided or not.

        :param additional_parameters: The parameters provided by the user for the scripted input.
        :return: Bool value signifying if the mandatory fields are provided or not for inputs creation.
        """
        _all_values_provided = all(value for value in additional_parameters.values())
        if not _all_values_provided:
            logger.info("Please provide all the required fields for inputs creation in Scripted Inputs Settings tab.")
            return False
        _check_if_account_exist = self._check_if_account_exist(
            session_key,
            additional_parameters.get(const.ACCOUNT_NAME)
        )
        if not _check_if_account_exist:
            logger.info("The account name %s provided does not exist. "
                        "Please provide the correct account name for inputs creation.", additional_parameters.get(const.ACCOUNT_NAME))
            return False

        return True

    def _check_if_account_exist(self, session_key, account_name):
        """Validate if the account_name provided by the user exists or not.

        :param session_key: Splunk session key.
        :param account_name: Account name provided by the user.
        :return: Bool value signifying if the account name exists or not.
        """
        accounts_cfm = conf_manager.ConfManager(
            session_key,
            const.APP_NAME,
            realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(const.APP_NAME, const.ACCOUNTS_CONF_FILE_NAME),
        )
        accounts_conf_file_exist = self._file_exist(
            const.ACCOUNTS_CONF_FILE_NAME, const.APP_NAME
        )
        if not accounts_conf_file_exist:
            logger.info(
                "Account conf file not present. Please configure the account in order to create automated inputs."
            )
            return False

        account_conf_object = accounts_cfm.get_conf(const.ACCOUNTS_CONF_FILE_NAME)
        conf_file_stanzas = account_conf_object.get_all()
        for stanza in conf_file_stanzas:
            if account_name in stanza:
                return True

        return False

    def _delete_is_safe_to_delete_inputs(self, inputs_cfm):
        """Delete the inputs which contains the is_safe_to_delet flag as True.

        :param inputs_cfm: The ConfManager object to delete the stanza.
        """
        inputs_deleted = 0
        conf_file_object = inputs_cfm.get_conf(const.INPUTS_CONF_FILE_NAME)
        conf_file_stanzas = conf_file_object.get_all()
        for stanza in conf_file_stanzas:
            if const.MODINPUT_NAME in stanza and const.IS_SAFE_TO_DELETE_FLAG in conf_file_stanzas[stanza]:
                stanza_deleted = self._delete_stanza(conf_file_object, stanza)
                if stanza_deleted:
                    inputs_deleted += 1

        logger.info("Deleted a total of %s inputs.", inputs_deleted)

    def _calculate_is_future_time(self, additional_parameters, session_key):
        """Check if the time is valid or not.

        :param additional_parameters: Additional parameters provided by the user or obtained from the checkpoint.
        :param session_key: Splunk session key.
        :return: Bool value signifying if the next input should be created or not.
        """
        start_time = self._get_start_date(additional_parameters, session_key)
        datetime_object_start_time = datetime.datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ")
        user_end_datetime = additional_parameters.get(const.USER_END_DATETIME)
        datetime_object_end_datetime = datetime.datetime.strptime(user_end_datetime, "%Y-%m-%dT%H:%M:%SZ")
        if datetime_object_start_time > datetime_object_end_datetime:
            return True

        return False

    def _calculate_inputs_creation_count(self, cfm, additional_parameters):
        """Calculate the count of inputs to be created.

        :param cfm: The ConfManager object.
        :param additional_parameters: The additional parameters provided by the user.
        :return: Returns the number of inputs count to be created.
        """
        inputs_creation_count = int(additional_parameters.get(const.MAX_ACTIVE_INPUTS))

        conf_file_object = cfm.get_conf(const.INPUTS_CONF_FILE_NAME)
        conf_file_stanzas = conf_file_object.get_all()
        for stanza in conf_file_stanzas:
            if f"{const.MODINPUT_NAME}://" in stanza and conf_file_stanzas[stanza].get("disabled") == '0':
                inputs_creation_count -= 1

        return inputs_creation_count

    def _delete_stanza(self, conf_file_object, stanza):
        """Delete the conf file stanza.

        :param conf_file_object: The ConfManager object.
        :param stanza: The conf file stanza name to be deleted.
        :return: Bool value signifying if the input is deleted or not.
        """
        try:
            logger.info("Deleting the stanza %s.", stanza)
            conf_file_object.delete(stanza)
            logger.info("Deleted the stanza %s successfully.", stanza)
        except Exception as ex:
            logger.error("Error occurred while deleting the stanza. Error: %s.", ex)
            return False

        return True

    def _create_inputs(self, session_key, additional_parameters, inputs_creation_count):
        """Create the inputs.

        :param session_key: Splunk session key.
        :param additional_parameters: The additional parameters provided by the user.
        :param inputs_creation_count: Count of inputs to be created.
        """
        logger.info("Starting to create %s new inputs.", inputs_creation_count)
        for _ in range(inputs_creation_count):
            start_time = self._get_start_date(additional_parameters, session_key)
            user_end_datetime = additional_parameters.get(const.USER_END_DATETIME)
            is_future_time = self._is_future_time(start_time)
            if is_future_time:
                logger.info("Next input time is in future time. Hence, skipping the input creation.")
                return
            _is_strat_time_valid = self._is_strat_time_valid(start_time, user_end_datetime)
            if not _is_strat_time_valid:
                logger.info("Next input time is greater than provided End DateTime. Hence, skipping the input creation.")
                return
            input_stanza = self._create_input_stanza(start_time, additional_parameters)
            logger.info("Input will be created with the following values. %s.", input_stanza)
            self._create_modular_input(session_key, input_stanza)
            self._create_checkpoint(input_stanza, session_key, additional_parameters)

    def _is_future_time(self, start_time):
        """Check if the start time is in future or not.

        :param start_time: The start time provided by the user or obtained from the checkpoint.
        :return: Bool value signifying if the next input start time is in future or not.
        """
        current_time = datetime.datetime.utcnow()
        datetime_object_start_time = datetime.datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ")
        if datetime_object_start_time > current_time:
            return True

        return False

    def _is_strat_time_valid(self, start_time, user_end_datetime):
        """Check if the start time is in future or not.

        :param start_time: The start time provided by the user or obtained from the checkpoint.
        :return: Bool value signifying if the next input start time is in future or not.
        """
        datetime_object_start_time = datetime.datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ")
        datetime_object_end_datetime = datetime.datetime.strptime(user_end_datetime, "%Y-%m-%dT%H:%M:%SZ")

        if datetime_object_start_time > datetime_object_end_datetime:
            return False

        return True

    def _reload_input_conf(self, session_key):
        """Reload inputs conf file.

        :param session_key: Splunk Session Key.
        """
        try:
            data_input_endpoints.reload_data_input(
                const.SPLUNKD_URI, session_key,
                "-",
                const.APP_NAME, const.MODINPUT_NAME
            )
            logger.info("Successfully reloaded the conf file.")
        except Exception as ex:
            logger.error("Error while reloading the conf file: %s.", ex)
            raise ex

    def _create_checkpoint(self, input_stanza, session_key, additional_parameters):
        """Create a checkpoint to store the next start time.

        :param input_stanza: The input stanza parameters.
        :param session_key: Splunk session key.
        :param additional_parameters: Parameters provided in the UI.
        """
        checkpoint_end_time = self._calculate_end_time(input_stanza.get(const.END_DATETIME))
        logger.info("Updating the checkpoint with the value: %s.", checkpoint_end_time)
        checkpoint_updated = netskope_utils.set_check_point(
            collection=const.CHECKPOINT_COLLECTION_NAME,
            key=const.NEXT_START_TIME.format(START_TIME=additional_parameters.get(const.START_DATETIME)),
            state=self._format_end_time(checkpoint_end_time),
            session_key=session_key,
        )
        logger.info("Checkpoint update status: %s.", checkpoint_updated)

    def _calculate_input_end_time(self, start_datetime, data_collection_window, user_end_datetime):
        """Calculate input end time.

        :param start_datetime: The start_time provided by the user or obtained from the checkpoint.
        :param data_collection_window: The data collection window for the new input to be created from the start_time.
        :param user_end_datetime: The end time provided by the user.
        :return: The end time obtained from adding data collection window hours to start time.
        """
        new_end_time = datetime.datetime.strptime(start_datetime, const.UTC_FORMAT)
        new_end_time += datetime.timedelta(minutes=int(data_collection_window))
        user_end_datetime = datetime.datetime.strptime(user_end_datetime, const.UTC_FORMAT)
        if new_end_time > user_end_datetime:
            return user_end_datetime
        return new_end_time

    def _calculate_end_time(self, end_datetime):
        """Calculate the end time by adding 1 second to the end time.

        :param end_datetime: The end time to be stored for the new input.
        :return: Updated time by adding 1 second to the end time to be stored in the checkpoint.
        """
        new_end_time = datetime.datetime.strptime(end_datetime, const.UTC_FORMAT)

        return new_end_time + datetime.timedelta(seconds=1)

    def _format_end_time(self, end_datetime):
        """Typecase datetime object to string.

        :param end_datetime: End time for the new input.
        :return: String value to be updated in the checkpoint.
        """
        return end_datetime.strftime(const.UTC_FORMAT)

    def _get_start_date(self, additional_parameters, session_key):
        """Get the start_date for the new input.

        :param additional_parameters: Additional parameters value provided in the settings.conf file.
        :param session_key: Splunk session key.
        :return: Return the start_time if present in the checkpoint or the value provided by the user.
        """
        logger.info("Getting the start time from checkpoint.")
        checkpoint_start_time = netskope_utils.get_check_point(
            collection=const.CHECKPOINT_COLLECTION_NAME,
            key=const.NEXT_START_TIME.format(START_TIME=additional_parameters.get(const.START_DATETIME)),
            session_key=session_key,
        )
        if checkpoint_start_time:
            logger.info("Checkpoint value is: %s.", checkpoint_start_time)
        else:
            logger.info("No checkpoint value obtained. Hence, defaulting the start_time to the user provided value.")
        return (checkpoint_start_time) if checkpoint_start_time else additional_parameters.get(const.START_DATETIME)

    def _create_modular_input(self, session_key, input_stanza):
        """Create the modular input in Splunk.

        :param session_key: Splunk session key.
        :param input_stanza: The input stanza details for the new input.
        """
        logger.info("Creating a modular input with the stanza: %s.", input_stanza)
        try:
            rest.simpleRequest(
                "/servicesNS/nobody/{}/configs/conf-inputs".format(const.APP_NAME),
                session_key,
                postargs=input_stanza,
                method="POST",
                raiseAllErrors=True,
            )
            logger.info("Successfully created an input %s.", input_stanza.get("name"))
        except Exception as ex:
            logger.error("Error occurred while creating the input. Traceback: %s.", traceback.format_exc())
            raise ex

    def _create_input_stanza(self, start_time, additional_parameters):
        """Create an input stanza.

        :param start_time: Start time value for the input.
        :param additional_parameters: Additional Parameters containing the account and the index values.
        :return: Returns the dictionary containing the input stanza.
        """
        end_time = self._calculate_input_end_time(start_time, additional_parameters.get(const.DATA_COLLECTION_WINDOW), additional_parameters.get(const.USER_END_DATETIME))
        input_stanza = {
            "event_type": additional_parameters.get(const.TYPE),
            "name": const.INPUT_NAME.format(INPUT_NAME=start_time),
            "global_account": additional_parameters.get(const.ACCOUNT_NAME),
            "interval": const.INPUT_INTERVAL,
            "start_datetime": start_time,
            "end_datetime": self._format_end_time(end_time),
            "disabled": 0,
            "index": additional_parameters.get(const.INDEX),
        }
        return input_stanza

    def _get_session_key(self):
        """Get the session key.

        :return: This function returns the session_key value.
        """
        session_key = sys.stdin.readline().strip()
        return session_key

    def _file_exist(self, file_name, ta_name):
        """Check if the file exists or not.

        :param file_name: Name of the file which is to be checked if it exists or not.
        :param ta_name: Name of the app.
        :return boolean value after checking if the file exists or not.
        """
        file_path = make_splunkhome_path(["etc", "apps", ta_name, "local", file_name])
        file_name = "".join([file_path, ".conf"])
        return os.path.exists(file_name)

    def _get_additional_parameters(self, cfm, stanza):
        """Get the value of the parameters in the ta_netskopeappforsplunk_settings.conf file.

        :param cfm: Object of the ConfManager to perform operations on the conf files.
        :param stanza: Name of the stanza to check the value of additional_parameters.
        :return additional params value from the ta_netskopeappforsplunk_settings.conf file.
        """
        additional_params_dict = {}
        try:
            cfm_settings_conf = cfm.get_conf(const.SETTINGS_CONF_FILE_NAME, refresh=True)
            additional_parameters = cfm_settings_conf.stanza_exist(stanza)
            stanza_values = cfm_settings_conf.get(stanza, {})
            if additional_parameters:
                additional_params_dict[const.ACCOUNT_NAME] = stanza_values.get(const.ACCOUNT_NAME).strip() if stanza_values.get(const.ACCOUNT_NAME) else None
                additional_params_dict[const.TYPE] = stanza_values.get(const.TYPE).strip() if stanza_values.get(const.TYPE) else None
                additional_params_dict[const.START_DATETIME] = stanza_values.get(const.START_DATETIME) if stanza_values.get(const.START_DATETIME) else None
                additional_params_dict[const.USER_END_DATETIME] = stanza_values.get(const.USER_END_DATETIME) if stanza_values.get(const.USER_END_DATETIME) else None
                additional_params_dict[const.DATA_COLLECTION_WINDOW] = stanza_values.get(const.DATA_COLLECTION_WINDOW) if stanza_values.get(const.DATA_COLLECTION_WINDOW) else None
                additional_params_dict[const.INDEX] = stanza_values.get(const.INDEX) if stanza_values.get(const.INDEX) else None
                additional_params_dict[const.MAX_ACTIVE_INPUTS] = stanza_values.get(const.MAX_ACTIVE_INPUTS) if stanza_values.get(const.MAX_ACTIVE_INPUTS) else None

                logger.info("Additional parameters received are: %s.", additional_params_dict)
        except Exception as ex:
            logger.error(
                "Error reading 'additional_parameters' value under '%s' stanza: %s.", stanza, traceback.format_exc()
            )
            raise ex

        return additional_params_dict


if __name__ == "__main__":
    create_modular_input_object = CreateModularInput()
    try:
        create_modular_input_object.run()
    except Exception:
        logger.error("Error occurred in creating a modular input. Traceback: %s.", traceback.format_exc())
