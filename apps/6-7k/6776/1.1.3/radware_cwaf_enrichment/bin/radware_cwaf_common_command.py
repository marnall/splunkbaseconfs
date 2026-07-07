#!/usr/bin/env python
#
# Base class for Radware Cloud WAF generating commands.
# Implements common logic for handling connectivity to the Radware Cloud WAF API
#
# Dimiter Todorov - 2023

import json
import sys

import splunk.rest as rest
from splunk.clilib import cli_common as cli

import radware_cwaf_common as rwc
import splunklib.client as client
from splunklib.searchcommands import GeneratingCommand, Option


class CredentialsNotFoundException(Exception):
    """
    Raised when no credentials can be found for the command.
    This can happen if the user has not configured the app, or if the user has not configured the credentials.

    Attributes:
        message (str): The message to display to the user.
        tenant_id (str): The tenant_id for which no credentials were found. [optional]
    """

    def __init__(self, message, tenant_id="*"):
        self.message = f"{message}\nCould not find credentials for tenant_id {tenant_id}. Please configure the app and credentials."
        super().__init__(self.message)


class RadwareCommonCommand(GeneratingCommand):
    tenant_id = Option(
        doc='''
            Syntax: tenant_id=<tenant_id>
            Description: The tenant_id to select apps from''',
        require=False,
        default="*")

    object_type = Option(
        doc='''
                Syntax: object_type
                Description: The object type to import.''',
        require=False,
        default="applications")

    def generate(self):
        raise NotImplementedError

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.splunkd_uri = None
        self.local_session_key = None
        self.app_logger = None
        self.cfg = None
        self.credential_handler = None

    def init_command(self, required_permission):
        try:
            self.cfg = cli.getConfStanza('radware_cwaf_enrichment', 'settings')
        except BaseException as e:
            print("Could not read configuration: " + repr(e))

        # Facility info - prepended to log lines
        command_name = self.__class__.__name__
        self.app_logger = rwc.setup_logger(command_name)
        self.app_logger.info('Command %s started by %s' %
                             (command_name, self._metadata.searchinfo.username))

        self.local_session_key = self._metadata.searchinfo.session_key
        self.splunkd_uri = self._metadata.searchinfo.splunkd_uri

        self.credential_handler = rwc.CredentialHandler()
        # Check for permissions to run the command
        content = rest.simpleRequest(
            '/services/authentication/current-context?output_mode=json', sessionKey=self.local_session_key,
            method='GET')[1]
        content = json.loads(content)
        current_user = self._metadata.searchinfo.username
        current_user_capabilities = content['entry'][0]['content']['capabilities']
        if required_permission in current_user_capabilities or 'run_radware_cwaf_enrichment_all' in current_user_capabilities or current_user == 'splunk-system-user':
            self.app_logger.debug("user %s is authorized for action: %s" % (current_user, required_permission))
            self.credential_handler.init_context(self.local_session_key)
        else:
            self.app_logger.error(self._metadata.searchinfo)
            self.app_logger.error(required_permission)
            self.app_logger.error(current_user_capabilities)
            self.app_logger.error(
                "User %s is unauthorized. Has the %s capability been granted?" % (current_user, required_permission))
            sys.exit(3)

        # Sanitize inputs
        if self.tenant_id:
            self.app_logger.debug('Tenant ID Context: %s' % self.tenant_id)
        else:
            self.tenant_id = None

    def get_object_store(self):
        # Ensure we have a collection set up.
        # if not, then create the object collection
        opts = {"owner": "nobody", "token": self._metadata.searchinfo.session_key, "app": "radware_cwaf_enrichment"}
        service_client = client.connect(**opts)
        collection_name = f"radware_cwaf_{self.object_type}"
        collections = service_client.kvstore
        if collection_name in collections:
            object_store = collections[collection_name]
        else:
            service_client.kvstore.create(
                collection_name, app=opts["app"], sharing="global")
            object_store = service_client.kvstore[collection_name]
        return object_store

    def get_radware_objects(self):
        # Get objects from the API
        self.app_logger.debug('Getting %s from tenant %s' % (self.object_type, self.tenant_id))
        try:
            if self.tenant_id and self.tenant_id != "*":
                credentials = self.credential_handler.get_credentials(tenant_id=self.tenant_id)
            else:
                credentials = self.credential_handler.get_credentials()
        except Exception as e:
            self.app_logger.error('Error getting credentials for tenant %s: %s' % (self.tenant_id, e))
            raise CredentialsNotFoundException(e, self.tenant_id)

        if len(credentials) == 0:
            self.app_logger.error('No credentials found for tenant %s' % self.tenant_id)
            raise CredentialsNotFoundException("No credentials found", self.tenant_id)

        object_dict = {}
        # Get apps from the API
        for k in credentials.keys():
            self.app_logger.debug(f"Loading {self.object_type} for tenant {credentials[k]['tenant_id']}")
            svc = rwc.get_radware_service(credentials[k], self.cfg)
            svc.login()
            object_functions = {
                'applications': svc.get_applications,
            }
            get_method = object_functions.get(self.object_type, None)
            if get_method:
                object_dict[svc.radware_tenant_id] = get_method()
            else:
                raise NotImplementedError("Object type %s is not implemented for enrichment (yet)" % self.object_type)

        return object_dict
