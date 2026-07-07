"""
This module defines the functionality necessary to run the web-server for accepting data from OSQuery clients.
"""

import splunk
import os
import sys
import json
import logging
import urllib

from splunk.clilib.bundle_paths import make_splunkhome_path

# Import the SolnCommon libraries
from SolnCommon.log import setup_logger
from SolnCommon.modinput import ModularInput
from SolnCommon.modinput.fields import IntegerField, Field, BooleanField
from SolnCommon.pooling import should_execute

# Import local app libraries
from ta_osquery_app.osquery_server import OSQueryServer
from ta_osquery_app.event_writer import StashNewWriter

logger = setup_logger('osquery_modular_input', level=logging.DEBUG)

class FileField(Field):
    '''
    Represents a file path field.
    '''

    def to_python(self, value):

        Field.to_python(self, value)

        if value is not None:
            if os.path.isabs(value):
                return value
            else:
                path = os.path.join(make_splunkhome_path([value]))
                return path
        else:
            return None

    def to_string(self, value):
        return value

class OSQueryModularInput(ModularInput):
    """
    Modular input class that runs a web-server for accepting connections from OSQuery clients.
    """

    def __init__(self):
        scheme_args = {'title': 'osquery Fleet',
                       'description': 'Retrieve endpoint data from osquery clients',
                       'use_external_validation': "true",
                       'streaming_mode': "xml",
                       'use_single_instance': "false"}

        args = [
            IntegerField("port", "Server Port", 'The port to run the server for accepting connections from osquery clients', required_on_create=True, required_on_edit=True),
            Field("address", "Server Address", 'The address to run the server on', required_on_create=True, required_on_edit=True),
            Field("enroll_secret", "Enrollment Secret", 'The enrollment secret that clients must know to connect', required_on_create=False, required_on_edit=False),
    
            BooleanField("use_tls", "Use TLS", 'Use TLS encryption', required_on_create=True, required_on_edit=True),
            FileField("key_file", "Certificate Key file", 'The path to the key file for the certificate', required_on_create=True, required_on_edit=True),
            FileField("cert_file", "Certificate File", 'The path to the certificate file', required_on_create=True, required_on_edit=True),
            FileField("ca_file", "Certificate Authority File", 'The path to the certificate authority file', required_on_create=False, required_on_edit=False)
        ]

        super(OSQueryModularInput, self).__init__(scheme_args, args)

        self.server = None

    def escape_colons(self, string_to_escape):
        """
        Escape the colons. This is necessary for secure password stanzas.
        """
        return string_to_escape.replace(":", "\\:")

    def get_secure_password_stanza(self, username, realm=""):
        """
        Make the stanza name for a entry in the storage/passwords endpoint from the username and
        realm.
        """
        return self.escape_colons(realm) + ":" + self.escape_colons(username) + ":"

    def get_secure_password_by_realm(self, realm, session_key):
        """
        Get the secure password that matches the given realm.
        """

        # Get secure passwords
        server_response, server_content = splunk.rest.simpleRequest('/services/storage/passwords?output_mode=json', sessionKey=session_key)

        if server_response['status'] != '200':
            raise Exception("Could not get the secure passwords")

        passwords_content = json.loads(server_content)
        passwords = passwords_content['entry']

        # Filter down output to the ones matching the realm
        matching_passwords = filter(lambda x: x['content']['realm'] == realm, passwords)

        if len(matching_passwords) > 0:
            return matching_passwords[0]
        else:
            logger.error("Unable to find password entry (none matched the realm), realm=%s", realm)
            return None

    def get_secure_password(self, realm, username=None, session_key=None):
        """
        Get the secure password that matches the given realm and username. If no username is
        provided, the first entry with the given realm will be returned.
        """

        # Look up the entry by realm only if no username is provided.
        if username is None or len(username) == 0:
            return self.get_secure_password_by_realm(realm, session_key)

        # Get secure password
        stanza = self.get_secure_password_stanza(username, realm)
        try:
            server_response, server_content = splunk.rest.simpleRequest('/services/storage/passwords/' + urllib.quote_plus(stanza) + '?output_mode=json', sessionKey=session_key)
        except splunk.ResourceNotFound:
            logger.error("Unable to find password entry, stanza=%s", stanza)
            return None

        if server_response['status'] == '404':
            logger.error("Unable to find password entry (404), stanza=%s", stanza)
            return None
        elif server_response['status'] != '200':
            raise Exception("Could not get the secure passwords")

        passwords_content = json.loads(server_content)
        password = passwords_content['entry']

        return password[0]['content']['clear_password']

    def run(self, cleaned_params):
        logger.info("Running...")

        port = cleaned_params.get('port', 8080)
        address = cleaned_params.get('address', '')

        use_tls = cleaned_params.get('use_tls', False)
        key_file = cleaned_params.get('key_file', None)
        cert_file = cleaned_params.get('cert_file', None)
        ca_file = cleaned_params.get('ca_file', None)

        enroll_secret = cleaned_params.get('enroll_secret', None)

        index = cleaned_params.get('index', 'default')
        sourcetype = cleaned_params.get('sourcetype', 'osquery')
        source = cleaned_params.get('source', 'undefined')
        name = cleaned_params.get('name', 'undefined')

        logger.info("Starting server, stanza=%s", name)

        # Get the enrollment secret from secure storage if it exists
        try:
            enroll_secret = self.get_secure_password(name,
                                                    username="IN_CONF_FILE",
                                                    session_key=self._input_config.session_key)

            if enroll_secret is None:
                logger.info("No password found in secure storage for the shared secret, stanza=%s", name)
            else:
                logger.info("Successfully loaded password from secure storage for the shared secret, stanza=%s", name)
        except:
            logger.exception("Failed to load the password from secure storage for the shared secret, stanza=%s", name)

        # Make a writer for outputting results to Splunk
        writer = StashNewWriter(index=index,
                                source_name=source,
                                sourcetype=sourcetype,
                                file_extension=".stash_osquery")

        def output_results(results):
            for result in results:
                writer.write_event(json.dumps(result), is_raw_string=True)

        # Start the server
        self.server = OSQueryServer.start_server(logger=logger,
                                                 port=port,
                                                 address=address,
                                                 use_tls=use_tls,
                                                 key_file=key_file,
                                                 cert_file=cert_file,
                                                 ca_file=ca_file,
                                                 enroll_secret=enroll_secret,
                                                 output_results=output_results,
                                                 session_key=self._input_config.session_key
                                                )

        logger.info("Server successfully started, stanza=%s", source)

if __name__ == '__main__':
    try:
        logger.info('status="Executing modular input"')
        mod_input = OSQueryModularInput()
        mod_input.execute()
    except:
        logger.exception("Error when attempting to run the input")
