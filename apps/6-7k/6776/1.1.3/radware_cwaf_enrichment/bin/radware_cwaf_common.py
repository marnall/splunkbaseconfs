# radware_cwaf_common.py
# Contains common code for the Radware CWAF Splunk app.
#
# Author: Dimiter Todorov (dimiter.todorov@ontario.ca)
# Date: 2023-02-10

from __future__ import print_function

import json
import logging
import logging.handlers
import os
import re
import sys
import traceback

import splunk.rest as rest
from splunk import admin
from splunk.clilib import cli_common as cli

from mock_service.radware_cwaf_mock_api_service import MockRadwareService
from radware_cwaf_api_service import RadwareCwafService
from splunklib import client

APP_NAME = 'radware_cwaf_enrichment'


def get_server_apps(uri, session_key, app=None):
    apps = []
    if app is not None:
        apps.append(app)
    else:
        # Enumerate all remote apps
        apps_uri = uri + '/services/apps/local?output_mode=json'
        content = rest.simpleRequest(
            apps_uri, sessionKey=session_key, method='GET')[1]
        content = json.loads(content)
        for entry in content["entry"]:
            if not entry["content"]["disabled"]:
                apps.append(entry["name"])
    return apps


def get_radware_service(credential, settings):
    # Create the service
    try:
        if credential['username'].startswith('mock'):
            service = MockRadwareService(credential, settings)
        else:
            service = RadwareCwafService(credential, settings, logger=logger)
        logger.info("created Radware CWAF service for user %s" %
                    credential['username'])
        return service
    except BaseException as e:
        raise Exception("Failed to create Radware CWAF service for username %s: %s" % (
            credential['username'], repr(e)))


def setup_logger(facility, use_rotating_handler=True):
    """
    Setup and return a common logger.

    Arguments:
        facility {str} -- The name of the facility that is logging.
    """
    file_name = f"{APP_NAME}.log"
    try:
        cfg = cli.getConfStanza(APP_NAME, 'settings')
        log_level = cfg.get('log_level', 'INFO')
    except BaseException as e:
        traceback.print_exc(file=sys.stderr)
        print("Error setting up logger: %s" % e, file=sys.stderr)
        log_level = 'DEBUG'
    _logger = logging.getLogger(facility)
    # Prevent the log messages from being duplicated in the python.log file
    _logger.propagate = False
    _logger.setLevel(log_level)

    log_file_path = os.path.join(
        os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk', file_name)

    if use_rotating_handler:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path, maxBytes=25000000, backupCount=5)
    else:
        file_handler = logging.FileHandler(log_file_path)

    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s ' + facility + ' - %(message)s')
    file_handler.setFormatter(formatter)

    _logger.addHandler(file_handler)

    return _logger


# Setup logger for this module. This is the default logger for common commands.
facility = os.path.basename(__file__)
facility = os.path.splitext(facility)[0]
# Set up the logger
logger = setup_logger(facility)


class CredentialHandler:
    CREDENTIAL_MAP_RE = re.compile(
        "(?P<prefix>.*)\.(?P<idx>[0-9]+|create)\.(?P<suffix>.*)")
    session_key = None
    connect_opts = {}

    @classmethod
    def get_credentials(cls, **kwargs):
        try:
            cfg = cli.getConfStanza('radware_cwaf_enrichment', 'settings')
            credentials, _ = cls.parse_credential_params(cfg)
            response_credentials = {}
            if kwargs.get('tenant_id') is not None:
                credentials = list(filter(lambda x: x['tenant_id'] == kwargs.get('tenant_id'), credentials.values()))
            service = cls.get_service_client()
            storage_passwords = service.storage_passwords.list(search="credential-")
            for idx, cred in credentials.items():
                if not cred['password'] or not cred['username']:
                    logger.debug("Password or Username not found for cred id %s " % idx)
                    continue
                password = next(filter(lambda p: p.name == cred['password'], storage_passwords), None)
                if password:
                    cred['password'] = password.clear_password
                    response_credentials[idx] = cred
                else:
                    logger.critical("Password not found for cred id %s" % cred['password'])
            return response_credentials
        except Exception as e:
            logger.error("error getting credentials - cannot load configuration: %s" % e)
            raise e

    @classmethod
    def init_context(cls, session_key, owner="nobody", app="radware_cwaf_enrichment", sharing="app"):
        """
        Initializes the class context.

        Arguments:
        session_key -- The session key to use for connecting to splunkd
        owner -- The owner context to use for connecting to splunkd
        app -- The app context to use for connecting to splunkd
        sharing -- The sharing context to use for connecting to splunkd
        """
        cls.session_key = session_key
        opts = {"owner": owner, "token": session_key, "app": app, "sharing": sharing}
        cls.connect_opts = opts

    @classmethod
    def get_service_client(cls):
        return client.connect(**cls.connect_opts)

    @classmethod
    def parse_credential_params(cls, new_params, existing_params={}):
        """
        Gets the credential values from the given parameters. This method will
        look for the credential fields in the given parameters and return a
        dictionary of the credential values.

        Arguments:
        new_params -- The parameters to look for credential values in
        existing_params -- The existing parameters to look for credential values in

        Returns:
        A tuple of the credential values and the next key to use for a new credential
        """
        credential_fields = ['name', 'username', 'password',
                             'meta', 'tenant_id', 'password_set', 'id']
        credential_values = {}
        next_key = -1
        for params in [existing_params, new_params]:
            for key in params.keys():
                match = cls.CREDENTIAL_MAP_RE.match(key)
                if match:
                    if match.group('idx') == 'create':
                        index_key = -1
                    else:
                        index_key = match.group('idx')
                    if not index_key in credential_values.keys():
                        credential_values[index_key] = {}
                    credential_values[index_key][match.group(
                        'suffix')] = params[key]

        # If there are no credential values, return the dictionary and start with 1
        if (len(credential_values.keys()) == 1 and -1 in credential_values.keys()):
            return credential_values, 1

        # Try to find the next key to use. If a certain credential set is empty, we can reuse that key.
        # This is to avoid bloat in the config file
        sorted_keys = sorted(credential_values.keys(), key=lambda x: int(x))
        for key in sorted_keys:
            if key == -1:
                continue
            fields_clear = 0
            for credential_field in credential_fields:
                if credential_field not in credential_values[key].keys():
                    fields_clear += 1
                elif credential_values[key][credential_field] == '':
                    fields_clear += 1
            if fields_clear == len(credential_fields):
                next_key = int(key)
                break
            else:
                next_key = int(key) + 1
        return credential_values, next_key

    """
    Handles the credential actions and parameters.
    Supports new, update, and delete actions.
    Validates field

    Parameters:
    key -- The key of the parameter initiating the handler
    name -- The name of the credential
    params -- The parameters to use
    existing_settings -- The existing settings

    """

    @classmethod
    def handle(cls, key, value, params, existing_settings):
        m = CredentialHandler.CREDENTIAL_MAP_RE.match(key)
        # Check if the key matches the credential pattern
        if m and len(m.groups()) == 3:
            # Get rid of the action parameter as we don't need it anymore
            params.pop(key, None)
            existing_settings.pop(key, None)

            # Get an index of the credentials
            idx = m['idx']

            # Password formatting - used for unique secret id generation
            password_name = f"credential-{idx}-password"
            credentials_dict, next_key = cls.parse_credential_params(
                params, existing_settings)
            # Delete Actions
            if value == "delete":
                params_to_clear = []
                matching_idx_re = re.compile(
                    f"(?P<prefix>.*)\.{idx}\.(?P<suffix>.*)")

                # Check existing params and clear any keys for the credential with index idx
                for d in [params, existing_settings]:
                    for k in d.keys():
                        if matching_idx_re.match(k):
                            params_to_clear.append(k)
                params_to_clear = list(dict.fromkeys(params_to_clear))

                # Clear the password from secret storage
                cls.clear_passwords(password_name)
                return params, existing_settings, params_to_clear

            # Update Actions
            elif value == "update":
                if params[f"credential.{idx}.username"] != existing_settings[f"credential.{idx}.username"]:
                    logger.debug(
                        f"Updating username for credential {idx} to {params[f'credential.{idx}.username']}")

                    if not params[f"credential.{idx}.password"]:
                        raise admin.ArgValidationException(
                            f"Password must be set when updating username")
                    params[f"credential.{idx}.tenant_id"] = cls.validate_credentials(
                        params[f"credential.{idx}.username"], params[f"credential.{idx}.password"], params)
                    password = cls.create_or_update_password(
                        password_name, credentials_dict[idx]['username'], params[f"credential.{idx}.password"])
                    params[f"credential.{idx}.password"] = password.name
                elif params[f"credential.{idx}.password"] != existing_settings[f"credential.{idx}.password"]:
                    params[f"credential.{idx}.tenant_id"] = cls.validate_credentials(
                        params[f"credential.{idx}.username"], params[f"credential.{idx}.password"], params)
                    password = cls.create_or_update_password(
                        password_name, credentials_dict[idx]['username'], params[f"credential.{idx}.password"])
                    params[f"credential.{idx}.password"] = password.name
                if not params[f'credential.{idx}.tenant_id']:
                    logger.debug(
                        f"No Tenant ID found for {params[f'credential.{idx}.name']}")
                    credential = cls.get_credentials()[idx]
                    params[f"credential.{idx}.tenant_id"] = cls.validate_credentials(
                        credential['username'], credential['password'], params)
                return params, existing_settings, []

            # Create Actions
            elif value == "create":
                # Use the next key to index the new credential into the next available index
                credentials_dict[next_key] = credentials_dict[-1]

                # Basic
                required_params = ['name', 'username', 'password']
                for param in required_params:
                    if not param in credentials_dict[next_key].keys():
                        raise admin.ArgValidationException(
                            f"Missing required parameter {param} for new credential")

                # Check connectivity before making any further modifications to the config.
                credentials_dict[next_key]['tenant_id'] = cls.validate_credentials(
                    credentials_dict[next_key]['username'], credentials_dict[next_key]['password'], params)
                # Clear out credential.create.* parameters, so they don't get persisted
                for k, v in credentials_dict[next_key].items():
                    if k == "action":
                        existing_settings.pop(f"credential.create.{k}", None)
                        params.pop(f"credential.create.{k}", None)
                    else:
                        params[f"credential.{next_key}.{k}"] = v
                        existing_settings.pop(f"credential.create.{k}", None)
                        params.pop(f"credential.create.{k}", None)
                    if k == "password":
                        password_name = f"credential-{next_key}-password"
                        password = cls.create_or_update_password(
                            password_name, credentials_dict[next_key]['username'], v)
                        params[f"credential.{next_key}.password"] = password.name
                        params[f"credential.{next_key}.password_set"] = 1

        return params, existing_settings, []

    @classmethod
    def validate_credentials(cls, username, password, settings):
        logger.debug(
            "new or updated credentials detected - check connectivity")
        cred = {
            'username': username,
            'password': password
        }
        try:
            svc = get_radware_service(cred, settings)
            svc.login()
            logger.info(f"Validated Credentials for Radware Tenant {svc.get_tenant_id()}")
        except BaseException as e:
            logger.exception(e)
            raise admin.ArgValidationException(
                "Validating Radware Credentials failed. Please check your credentials and try again. %s" % e)
        return svc.radware_tenant_id

    @classmethod
    def clear_passwords(cls, password_name):
        """
        Clear all passwords in the Splunk secret store that match the given name.
        """
        service = cls.get_service_client()
        passwords = service.storage_passwords.list()
        for p in passwords:
            if password_name in p.name:
                p.delete()

    @classmethod
    def create_or_update_password(cls, password_name, password_username, password_value):
        """
        Create or update a password in the Splunk secret store.
        Updating an existing credential's username will delete the old object completely and create a new one.
        This is done since changing the username changes the internal key used to store the password.

        Args:
            password_name (str): The name of the password to create or update
            password_username (str): The username to associate with the password
            password_value (str): The password value to store
        Returns:
            The password object created or updated
        """
        service = cls.get_service_client()
        password = None
        try:
            passwords = service.storage_passwords.list(
                search=f"{password_name}")
            if len(passwords) > 0:
                for p in passwords:
                    if password_username == p.username:
                        password = p
                    else:
                        # Delete any passwords that don't match the username
                        # Retain the password value so we can create a new password with the correct username
                        password_value = p.clear_password
                        p.delete()
                        password = None
            else:
                password = None
        except Exception as e:
            logger.debug("password not found: %s" % e)
            password = None
        if password is None:
            password = service.storage_passwords.create(
                password_value, password_username, password_name)
        else:
            logger.debug("Password found: %s" % password_name)
            password.update(**{'password': password_value})

        logger.debug("Password updated: %s" % password.name)
        return password
