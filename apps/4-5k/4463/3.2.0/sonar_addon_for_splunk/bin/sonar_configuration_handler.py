import os
import sys
import json

import splunk.admin as admin

from constants import (ADDRESS_FIELD, PORT_FIELD, LIMIT_FIELD, LICENSE_FIELD, INSTANCE_FIELD, INSTANCES_FIELD,
                       DESCRIPTION_FIELD, IS_DEFAULT_FIELD, CONFIGURATION_NAME, CONFIGURATION_STANZA, REALM,
                       PREV_INSTANCE_FIELD)
from utils import string, logger

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "lib"))
import splunklib.client as client


class SonarConfigurationHandler(admin.MConfigHandler):
    handledActions = [admin.ACTION_LIST, admin.ACTION_EDIT, admin.ACTION_REMOVE]
    conf_fields = [ADDRESS_FIELD, PORT_FIELD, LIMIT_FIELD, DESCRIPTION_FIELD, IS_DEFAULT_FIELD]
    secret_fields = [LICENSE_FIELD]

    def setup(self):
        if self.requestedAction not in self.handledActions:
            exception = admin.BadActionException(
                "This handler does not support this action (%d)." % self.requestedAction)
            logger.error("Action='Setup', Message='%s'", exception)
            raise exception

        self.supportedArgs.addOptArg(ADDRESS_FIELD)
        self.supportedArgs.addOptArg(PORT_FIELD)
        self.supportedArgs.addOptArg(LIMIT_FIELD)
        self.supportedArgs.addOptArg(LICENSE_FIELD)
        self.supportedArgs.addOptArg(INSTANCE_FIELD)
        self.supportedArgs.addOptArg(DESCRIPTION_FIELD)
        self.supportedArgs.addOptArg(IS_DEFAULT_FIELD)
        self.supportedArgs.addOptArg(PREV_INSTANCE_FIELD) # Used for renaming a configuration so Splunk knows which one to disable

    def handleList(self, confInfo: admin.ConfigInfo):
        logger.debug("Listing configurations. Initial confInfo: %s", self.get_conf())
        logger.info("Action='List'")

        # Rearranging the conf data
        settings = {}
        for key, value in self.get_conf().items():
            logger.debug(f"Action='List', Step='Fetching license for {key}'")

            if key == CONFIGURATION_STANZA:
                sonar_license = self.get_secret_field(LICENSE_FIELD)
                confInfo[CONFIGURATION_STANZA].append(LICENSE_FIELD, sonar_license if sonar_license else '')
                logger.debug("Action='List', Step='Fetching license for %s', IsConfigured='%s'" %(key, 'True' if sonar_license else 'False'))

                settings.update(value)

            else:
                sonar_license = self.get_secret_field(f"{LICENSE_FIELD}-{key}")
                confInfo[key].append(LICENSE_FIELD, sonar_license if sonar_license else '')
                logger.debug("Action='List', Step='Fetching license for %s', IsConfigured='%s'" %(key, 'True' if sonar_license else 'False'))

                obj = {INSTANCE_FIELD: key}
                license_obj = {LICENSE_FIELD: sonar_license}
                if INSTANCES_FIELD not in settings:
                    settings[INSTANCES_FIELD] = [{**obj, **value, **license_obj}]
                else:
                    settings[INSTANCES_FIELD].append({**obj, **value, **license_obj})

        if not settings:
            logger.warn(
                "Action='List', Step='Fetching sonar configuration', Message='No configuration found for stanza %s'",
                CONFIGURATION_STANZA)
            return

        logger.info(f"Action='List', Step='Retrieved all conf settings'")
        logger.debug(f"Action='List', Step='Retrieved all conf settings' Details='{settings}'")
        use_fallback_configuration = settings.get(INSTANCES_FIELD) is None

        # Do not break upgrades
        for field in self.conf_fields:

            if field == IS_DEFAULT_FIELD:
                confInfo[CONFIGURATION_STANZA].append(field, "true")
            else:
                value = settings[field] if field in settings and settings[field] else ''
                confInfo[CONFIGURATION_STANZA].append(field, value)
                logger.debug("Action='List', Step='Fetching sonar configuration', Field='%s', IsConfigured='%s'", field,
                             'True' if value else 'False')

        if not use_fallback_configuration:
            confInfo[CONFIGURATION_STANZA].append(INSTANCES_FIELD, json.dumps(settings[INSTANCES_FIELD]))

    def get_conf(self):
        return self.readConf(CONFIGURATION_NAME)

    def get_conf_stanza_settings(self, stanza_name):
        conf_dict = self.get_conf()
        if not conf_dict:
            return

        return conf_dict[stanza_name]

    def handleEdit(self, confInfo):
        logger.info("Action='Edit', Step='Updating sonar configuration file'")
        instance_data = self.callerArgs.data[INSTANCE_FIELD]
        prev_instance_data = self.callerArgs.data[PREV_INSTANCE_FIELD]

        selected_instance = instance_data[0] if instance_data else ""  # UI validates that instance cannot be empty
        prev_instance = prev_instance_data[0] if prev_instance_data else ""

        # If instance is being renamed
        if selected_instance and prev_instance and selected_instance != prev_instance and prev_instance != "undefined":
            logger.info(f"Action='Edit', Step='Replacing [{prev_instance}] with [{selected_instance}]'")
            self.disable_configuration(prev_instance)

        is_default_arg = self.callerArgs.data.get(IS_DEFAULT_FIELD)
        is_default = is_default_arg[0] == "true" if is_default_arg else False

        # Adding token to Splunk secret storage
        for field in self.secret_fields:
            value = self.callerArgs.data[field][0] if self.callerArgs.data[field][0] is not None else ''
            self.save_secret_field(field, value, selected_instance)

        stanza_settings = {"is_disabled": "false"}
        for field in self.conf_fields:
            value = self.callerArgs.data[field][0] if self.callerArgs.data[field][0] is not None else ''
            stanza_settings[field] = value

        # If this is the first time generating the file, or upgrading 'sonar_addon_for_splunk' to 3.2.0+, then write to [sonar_service] as well
        if len(self.get_conf()) == 1 and CONFIGURATION_STANZA in self.get_conf().keys():
            subset = {key: value for key, value in stanza_settings.items() if key not in {'is_default'}}
            self.writeConf(CONFIGURATION_NAME, CONFIGURATION_STANZA, subset)
            stanza_settings.update({"is_default": "true"})

        self.writeConf(CONFIGURATION_NAME, selected_instance, stanza_settings)

        # If selected_instance is being set to is_default=true, then update all other stanzas to is_default=false ([sonar_service] remains unaffected)
        if is_default:
            for stanza, value in self.get_conf().items():
                if stanza != selected_instance and stanza != CONFIGURATION_STANZA:
                    value.update({"is_default": "false"})
                    self.writeConf(CONFIGURATION_NAME, stanza, value)

    def handleRemove(self, confInfo):
        """
        Handles the removal of a configuration stanza by disabling it
        """
        logger.info("Action='Delete', Step='Disabling config from sonar configuration file'")
        instance = self.callerArgs.data.get(INSTANCE_FIELD)
        selected_instance = None

        # Handling odd behaviour where this endpoint is being called twice, once with callerArgs.data provided like {'instance': ['splunk_test']}
        # and another time where data is empty, but callerArgs.id has the selected instance name instead
        if instance:
            selected_instance = instance[0]
        else:
            args_id = self.callerArgs.id
            selected_instance = args_id if args_id != CONFIGURATION_STANZA else None

        self.disable_configuration(selected_instance)

    def get_secret_field(self, field):
        if SonarConfigurationHandler.is_blank_string(field):
            return ''

        splunk_service = client.connect(token=self.getSessionKey(), app=self.appName)
        password_storage = splunk_service.storage_passwords

        for credential in password_storage:
            if credential.username == field and credential.realm == REALM:
                return credential.clear_password

        return ''

    def save_secret_field(self, field, value, selected_instance):
        splunk_service = client.connect(token=self.getSessionKey(), app=self.appName)
        storage_list = splunk_service.storage_passwords
        storage = None
        instance_username = f"{field}-{selected_instance}"

        # If StoragePasswords does not exist, create one for the first time with two records:
        # 1. Fallback username: "license"
        # 2. New format "license-<selected_instance>"
        if not storage_list or len(storage_list) == 0:
            storage_list.create(value, field, REALM)
            storage_list.create(value, instance_username, REALM)

        for credential in storage_list:
            # Singular sonar config
            if not selected_instance and credential.username == field and credential.realm == REALM:
                storage = credential
                break
            # Multi sonar configs
            elif selected_instance and credential.username == instance_username and credential.realm == REALM:
                storage = credential
                break

        # Add new StoragePassword if none were found matching the instance name
        if storage is None:
            if SonarConfigurationHandler.is_blank_string(value):
                return

            storage = storage_list.create(value, instance_username, REALM)
        else:
            if SonarConfigurationHandler.is_blank_string(value):
                storage.delete()
                return

            storage = storage.update(password=value).refresh()

        storage.post('acl', **{'body': "owner=nobody;sharing=global;perms.read=*"})
        return

    def delete_secret_storage(self, field, selected_instance):
        """
        Delete secret storage based on the username format of <field>-<selected_instance> (e.g. license-splunk_test)
        The StoragePassword object where username: "license" (legacy format) will never be deleted by this method
        """
        splunk_service = client.connect(token=self.getSessionKey(), app=self.appName)
        storage_list = splunk_service.storage_passwords
        storage = None
        instance_username = f"{field}-{selected_instance}"

        for credential in storage_list:
            if selected_instance and credential.username == instance_username:
                storage = credential
                break

        storage.delete()

    def disable_configuration(self, stanza_name):
        """
        "Removes" a Sonar configuration by setting the flag is_disabled=true. The UI will not display these instances
        and the license/token is also removed from Splunk's secret storage
        """
        # Note: existing_stanzas would include any stanzas that are already disabled, but UI will have already filtered out any confs that are is_disabled=true so they would not be selected
        existing_stanzas = list(self.get_conf().keys())

        selected_conf = self.get_conf_stanza_settings(stanza_name)
        if stanza_name in existing_stanzas and stanza_name != CONFIGURATION_STANZA:
            selected_conf.update({"is_disabled": "true"})

            self.writeConf(CONFIGURATION_NAME, stanza_name, selected_conf)
            self.delete_secret_storage(LICENSE_FIELD, stanza_name)

    @staticmethod
    def is_blank_string(value):
        return not (value and isinstance(value, string) and value.strip())


# initialize the handler
admin.init(SonarConfigurationHandler, admin.CONTEXT_NONE)
