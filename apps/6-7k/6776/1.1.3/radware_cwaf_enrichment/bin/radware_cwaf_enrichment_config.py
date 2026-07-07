#!/usr/bin/env python
#
# Config handler for Radware Cloud WAF Enrichment App
# HandleEdit is highly customized and handles credential storage in addition to validation
# For reading the settings you can use the default properties/[stanza] endpoint.
#
# Dimiter Todorov - 2023

import copy
import re

import splunk.admin as admin
import splunk.entity as entity

from radware_cwaf_common import CredentialHandler, setup_logger

logger = setup_logger('radware_cwaf_enrichment_config')


class StandardFieldValidator(object):
    """
    This is the base class that should be used to for field validators.
    """

    def to_python(self, name, value):
        """
        Convert the field to a Python object. Should throw a ArgValidationException if the data is invalid.

        Arguments:
        name -- The name of the object, used for error messages
        value -- The value to convert
        """

        if len(str(value).strip()) == 0:
            raise admin.ArgValidationException(
                "The value for the '%s' parameter cannot be empty" % (name))

        return value

    def to_string(self, name, value):
        """
        Convert the field to a string that can be persisted to a conf file. Should throw a ArgValidationException if the data is invalid.

        Arguments:
        name -- The name of the object, used for error messages
        value -- The value to convert
        """

        if value is None:
            return ""
        else:
            return str(value)


class BooleanFieldValidator(StandardFieldValidator):
    """
    Validates and converts fields that represent booleans.
    """

    def to_python(self, name, value):
        if value in [True, False]:
            return value

        elif str(value).strip().lower() in ["true", "1"]:
            return True

        elif str(value).strip().lower() in ["false", "0"]:
            return False

        raise admin.ArgValidationException(
            "The value of '%s' for the '%s' parameter is not a valid boolean" % (str(value), name))

    def to_string(self, name, value):
        if value:
            return "1"

        elif not value:
            return "0"

        return super(BooleanFieldValidator, self).to_string(name, value)


class IntegerFieldValidator(StandardFieldValidator):
    """
    Validates and converts fields that represent integers.
    """

    def __init__(self, min_value=None, max_value=None):
        self.min_value = min_value
        self.max_value = max_value

    def to_python(self, name, value):

        if value is None:
            return None

        int_value = int(str(value).strip())

        # Make sure that the value is at least the minimum
        if self.min_value is not None and int_value < self.min_value:
            raise admin.ArgValidationException(
                "The value of '%s' for the '%s' parameter is not valid, it must be at least %s" % (
                    str(value), name, self.min_value))

        # Make sure that the value is no greater than the maximum
        if self.max_value is not None and int_value > self.max_value:
            raise admin.ArgValidationException(
                "The value of '%s' for the '%s' parameter is not valid, it must be not be greater than %s" % (
                    str(value), name, self.max_value))

        try:
            return int(str(value).strip())
        except ValueError:
            raise admin.ArgValidationException(
                "The value of '%s' for the '%s' parameter is not a valid integer" % (str(value), name))

    def to_string(self, name, value):

        if value is None or len(str(value).strip()) == 0:
            return None

        else:
            return super(IntegerFieldValidator, self).to_string(name, value)


class FieldOptionsValidator(StandardFieldValidator):
    """
    Validates and converts field option selections to conform to a list of valid options.
    e.g. FieldOptionsValidator(["option1", "option2"])
    """

    def __init__(self, valid_options):
        self.valid_options = valid_options

    def to_python(self, name, value):
        if value not in self.valid_options:
            raise admin.ArgValidationException(
                f"The value of {value}  is not in permitted options {self.valid_options}"
            )
        return super().to_python(name, value)


class FieldSetValidator:
    """
    This base class is for validating sets of fields.
    """

    def validate(self, name, values):
        """
        Validate the values. Should throw a ArgValidationException if the data is invalid.

        Arguments:
        name -- The name of the object, used for error messages
        values -- The value to convert (in a dictionary)
        """

        pass


class ListValidator(StandardFieldValidator):
    """
    Validates and converts field that represents a list (comma or colon separated).
    """

    LIST_SPLIT = re.compile("[:,]")

    def to_python(self, name, value):

        # Treat none as an empty list
        if value is None:
            return []
        if re.match(r".*,.*|.*:.*", value):
            return ListValidator.LIST_SPLIT.split(value)
        else:
            return [value]

    def to_string(self, name, value):

        if value is None:
            return ""
        else:
            if type(value) is list:
                return ",".join(value)
            else:
                return value
            # Rebuild the list as comma separated list in order to normalize it


def log_function_invocation(fx):
    """
    This decorator will provide a log message for when a function starts and stops.

    Arguments:
    fx -- The function to log the starting and stopping of
    """

    def wrapper(self, *args, **kwargs):
        logger.debug("Entering: " + fx.__name__)
        r = fx(self, *args, **kwargs)
        logger.debug("Exited: " + fx.__name__)

        return r

    return wrapper


class RadwareConfigApp(admin.MConfigHandler):
    """
    The REST handler provides <ADD_DESCRIPTION_HERE>...
    """

    # Below is the name of the conf file
    CONF_FILE = 'radware_cwaf_enrichment'

    # Below are the list of parameters that are accepted
    PARAM_LOGLEVEL = 'log_level'
    PARAM_OBJECT_LIST = 'object_list'
    PARAM_USE_PROXY = 'use_proxy'
    PARAM_PROXY_HOST = 'proxy_host'
    PARAM_PROXY_PORT = 'proxy_port'
    PARAM_PROXY_USER = 'proxy_user'
    PARAM_PROXY_PASSWORD = 'proxy_password'
    PARAM_CREDENTIAL_NAME = 'credential.*.name'
    PARAM_CREDENTIAL_TENANT_ID = 'credential.*.tenant_id'
    PARAM_CREDENTIAL_USERNAME = 'credential.*.username'
    PARAM_CREDENTIAL_PASSWORD = 'credential.*.password'
    PARAM_CREDENTIAL_PASSWORD_SET = 'credential.*.password_set'
    PARAM_CREDENTIAL_ID = 'credential.*.id'
    PARAM_CREDENTIAL_META = 'credential.*.meta'

    PARAM_CREDENTIAL_ACTION = 'credential.*.action'

    # Below are the list of valid and required parameters
    VALID_PARAMS = [PARAM_LOGLEVEL, PARAM_OBJECT_LIST, PARAM_USE_PROXY, PARAM_PROXY_HOST, PARAM_PROXY_PORT,
                    PARAM_PROXY_USER, PARAM_PROXY_PASSWORD,
                    PARAM_CREDENTIAL_NAME, PARAM_CREDENTIAL_TENANT_ID,
                    PARAM_CREDENTIAL_USERNAME,
                    PARAM_CREDENTIAL_PASSWORD, PARAM_CREDENTIAL_PASSWORD_SET, PARAM_CREDENTIAL_ID,
                    PARAM_CREDENTIAL_META, PARAM_CREDENTIAL_ACTION]

    REQUIRED_PARAMS = []

    # These are parameters that are not persisted to the conf files; these are used within the REST handler only
    UNSAVED_PARAMS = []

    # List of fields and how they will be validated
    # Note: if a field does not have a validator, it will be passed through without validation
    FIELD_VALIDATORS = {
        PARAM_OBJECT_LIST: ListValidator(),
        PARAM_LOGLEVEL: FieldOptionsValidator(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
        PARAM_USE_PROXY: BooleanFieldValidator(),
        PARAM_CREDENTIAL_PASSWORD_SET: BooleanFieldValidator(),
        PARAM_CREDENTIAL_ACTION: FieldOptionsValidator(["create", "update", "delete"])
    }

    # This field designates the fields that the REST handler ought to allow fields with similar values using dot syntax (value.1, value.2, etc).
    # For these fields, instances containing what looks like the dot syntax will use the validator based on the item without the dot syntax.
    # Thus, the field "value.1.name" will be validated by whatever item validates "value.name".
    MULTI_FIELDS = [PARAM_CREDENTIAL_NAME, PARAM_CREDENTIAL_TENANT_ID, PARAM_CREDENTIAL_USERNAME,
                    PARAM_CREDENTIAL_PASSWORD, PARAM_CREDENTIAL_PASSWORD_SET, PARAM_CREDENTIAL_ID,
                    PARAM_CREDENTIAL_META, PARAM_CREDENTIAL_ACTION]

    MULTI_FIELD_RE = re.compile(
        "(?P<prefix>.*)\.(?P<idx>[0-9]+|create)\.(?P<suffix>.*)")

    # These are validators that work across several fields and need to occur on the cleaned set of fields
    GENERAL_VALIDATORS = []

    # General variables
    APP_NAME = "radware_cwaf_enrichment"

    # Field Handlers
    FIELD_HANDLERS = {
        PARAM_CREDENTIAL_ACTION: CredentialHandler(),
    }

    def setup(self):
        """
        Setup the required and optional arguments
        """
        if self.requestedAction == admin.ACTION_EDIT or self.requestedAction == admin.ACTION_CREATE:

            # Set the required parameters
            for arg in self.REQUIRED_PARAMS:
                self.supportedArgs.addReqArg(arg)

            # Set up the valid parameters
            for arg in self.VALID_PARAMS:
                if arg not in self.REQUIRED_PARAMS:
                    self.supportedArgs.addOptArg(arg)

            # Set up the unsaved parameters
            for arg in self.UNSAVED_PARAMS:
                if arg not in self.REQUIRED_PARAMS:
                    self.supportedArgs.addOptArg(arg)

        CredentialHandler.init_context(self.getSessionKey())

    @classmethod
    def removeMultiFieldSpecifier(cls, name, replace_with="*"):
        """
        Remove the multi-field specifier if the field is supposed to be support mulitple instances using the dot syntax (value.1, value.2, etc).

        Arguments:
        name -- The name of the field.
        """

        # Stop if we don't have any multi-fields
        if cls.MULTI_FIELDS is None:
            return name

        m = cls.MULTI_FIELD_RE.match(name)

        if m and len(m.groups()) == 3:
            multi_field_name = m['prefix'] + ".*." + m['suffix']
            if multi_field_name in cls.MULTI_FIELDS:
                logger.debug("removeMultiFieldSpecifier: " + name +
                             " to " + m.groups()[0] + m.groups()[1])
                return multi_field_name
        else:
            return name

    @classmethod
    def callHandlers(cls, name, params, existing_settings):
        """
        Call the field handlers to perform any additional processing.

        Arguments:
        name -- The name of the stanza being processed (used for exception messages)
        params -- The dictionary containing the parameter values
        existing_settings -- The existing settings for the stanza
        """

        for key, value in params.items():
            handler = cls.FIELD_HANDLERS.get(
                cls.removeMultiFieldSpecifier(key))
            if handler is not None:
                return handler.handle(key, value, params, existing_settings)
        return params, existing_settings, []

    @classmethod
    def convertParams(cls, name, params, to_string=False):
        """
        Convert so that they can be saved to the conf files and validate the parameters.

        Arguments:
        name -- The name of the stanza being processed (used for exception messages)
        params -- The dictionary containing the parameter values
        to_string -- If true, a dictionary containing strings is returned; otherwise, the objects are converted to the Python equivalents
        """

        new_params = {}
        for key, value in params.items():
            validator = cls.FIELD_VALIDATORS.get(
                cls.removeMultiFieldSpecifier(key))
            m = CredentialHandler.CREDENTIAL_MAP_RE.match(key)
            if m and len(m.groups()) == 3 and m['suffix'] != 'action':
                if not f"credential.{m['idx']}.action" in params.keys():
                    logger.debug(
                        f"missing action for credential param {key}. Please set action to 'new' or 'update' or 'delete'")
                    new_params.pop(key, None)
                    continue
            if validator is not None:
                if to_string:
                    new_params[key] = validator.to_string(key, value)
                else:
                    new_params[key] = validator.to_python(key, value)
            else:
                new_params[key] = value
        return new_params

    @log_function_invocation
    def handleList(self, confInfo):
        """
        Provide the list of configuration options.

        Arguments
        confInfo -- The object containing the information about what is being requested.
        """

        # Read the current settings from the conf file
        confDict = self.readConf(self.CONF_FILE)

        # Set the settings
        if None != confDict:
            for stanza, settings in confDict.items():

                # DEFINE DEFAULT PARAMETERS HERE

                for key, val in settings.items():
                    confInfo[stanza].append(key, val)

                    # ADD CODE HERE to get your parameters

    @log_function_invocation
    def handleReload(self, confInfo):
        """
        Reload the list of configuration options.

        Arguments
        confInfo -- The object containing the information about what is being requested.
        """

        # Refresh the configuration (handles disk based updates)
        entity.refreshEntities(
            'properties/' + self.CONF_FILE, sessionKey=self.getSessionKey())

    def clearValue(self, d, name):
        """
        Set the value of in the dictionary to none

        Arguments:
        d -- The dictionary to modify
        name -- The name of the variable to clear (set to none)
        """

        if name in d:
            d[name] = None

    @log_function_invocation
    def handleEdit(self, confInfo):
        """
        Handles edits to the configuration options

        Arguments
        confInfo -- The object containing the information about what is being requested.
        """

        try:

            name = self.callerArgs.id
            args = self.callerArgs

            # Load the existing configuration
            confDict = self.readConf(self.CONF_FILE)

            # Get the settings for the given stanza
            is_found = False

            if name is not None:
                for stanza, settings in confDict.items():
                    if stanza == name:
                        is_found = True
                        # In case, we need to view the old settings
                        existing_settings = copy.copy(settings)
                        break  # Got the settings object we were looking for

            # Stop if we could not find the name
            if not is_found:
                raise admin.NotFoundException(
                    "A stanza for the given name '%s' could not be found" % (name))

            # Initialize the context for the credential action handler
            CredentialHandler.init_context(self.getSessionKey())

            # Get the settings that are being set
            new_settings = {}

            for key in args.data:
                new_settings[key] = args[key][0]

            # Create the resulting configuration that would be persisted if the settings provided are applied
            settings.update(new_settings)

            # Check the configuration settings
            cleaned_params = self.checkConf(
                settings, name, confInfo, existing_settings=existing_settings)

            # Get the validated parameters
            validated_params = self.convertParams(name, cleaned_params, True)

            # Handle any actions that need to be performed
            validated_params, existing_settings, params_to_clear = self.callHandlers(
                name, validated_params, existing_settings)

            # Clear out the given parameters if blank so that it can be removed if the user wishes
            # (note that values of none are ignored by Splunk)
            clearable_params = []
            for p in clearable_params:
                if p in validated_params and validated_params[p] is None:
                    validated_params[p] = ""

            for p in params_to_clear:
                validated_params[p] = ""

            updated_settings = {**existing_settings, **validated_params}
            for k, v in updated_settings.items():
                confInfo[name].append(k, v)

            self.writeConf(self.CONF_FILE, name, updated_settings)

        except admin.NotFoundException as e:
            raise e
        except Exception as e:
            logger.exception("Exception generated while performing edit")

            raise e

    @classmethod
    def checkConf(cls, settings, stanza=None, confInfo=None, onlyCheckProvidedFields=False, existing_settings=None):
        """
        Checks the settings and raises an exception if the configuration is invalid.

        Arguments:
        settings -- The settings dictionary the represents the configuration to be checked
        stanza -- The name of the stanza being checked
        confInfo -- The confinfo object that was received into the REST handler
        onlyCheckProvidedFields -- Indicates if we ought to assume that this is only part of the fields and thus should not alert if some necessary fields are missing
        existing_settings -- The existing settings before the current changes are applied
        """

        # Add all of the configuration items to the confInfo object so that the REST endpoint lists them (even if they are wrong)
        # We want them all to be listed so that the users can see what the current value is (and hopefully will notice that it is wrong)
        for key, val in settings.items():

            # Add the value to the configuration info
            if stanza is not None and confInfo is not None:

                # Handle the EAI:ACLs differently than the normal values
                if key == 'eai:acl':
                    confInfo[stanza].setMetadata(key, val)
                elif key in cls.VALID_PARAMS and key not in cls.UNSAVED_PARAMS:
                    logger.debug("checking param %s" % key)
                    confInfo[stanza].append(key, val)

        # Below is a list of the required fields. The entries in this list will be removed as they
        # are observed. An empty list at the end of the config check indicates that all necessary
        # fields where provided.
        required_fields = cls.REQUIRED_PARAMS[:]

        # Check each of the settings
        for key, val in settings.items():

            # Remove the field from the list of required fields
            try:
                required_fields.remove(key)
            except ValueError:
                pass  # Field not available, probably because it is not required

        # Stop if not all of the required parameters are not provided
        # stanza != "default" and
        if onlyCheckProvidedFields == False and len(required_fields) > 0:
            raise admin.ArgValidationException(
                "The following fields must be defined in the configuration but were not: " + ",".join(required_fields))

        # Clean up and validate the parameters
        cleaned_params = cls.convertParams(stanza, settings, False)

        # Run the general validators
        for validator in cls.GENERAL_VALIDATORS:
            validator.validate(stanza, cleaned_params, existing_settings)

        # Remove the parameters that are not intended to be saved
        for to_remove in cls.UNSAVED_PARAMS:
            if to_remove in cleaned_params:
                del cleaned_params[to_remove]

        # Return the cleaned parameters
        return cleaned_params

    @staticmethod
    def stringToIntegerOrDefault(str_value, default_value=None):
        """
        Converts the given string to an integer or returns none if it is not a valid integer.

        Arguments:
        str_value -- A string value of the integer to be converted.
        default_value -- The value to be used if the string is not an integer.
        """

        # If the value is none, then don't try to convert it
        if str_value is None:
            return default_value

        # Try to convert the string to an integer
        try:
            return int(str(str_value).strip())
        except ValueError:
            # Return none if the value could not be converted
            return default_value


# initialize the handler
admin.init(RadwareConfigApp, admin.CONTEXT_NONE)
