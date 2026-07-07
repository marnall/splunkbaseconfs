import datetime
import json
import os, os.path
import splunklib.client as client
import sys
import logging.handlers

from splunklib.modularinput import *
from splunk.clilib import cli_common as cli
from taxii_client_v2 import Taxii2Client
from logger.logger import *

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".", "splunklib"))

file_handler = logging.handlers.RotatingFileHandler(
    os.environ['SPLUNK_HOME'] + '/var/log/splunk/taxii_feed.log',
    maxBytes=25000000, backupCount=5)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
file_handler.setFormatter(formatter)
logger = create_logger(__name__, handler=file_handler)


class TAXIIModularInput(Script):

    MASK = "**************"
    CLEAR_PASSWORD = None

    def get_scheme(self):
        """
        Return the expected XML by Splunk Enterprise when it starts.
        """

        scheme = Scheme("TAXII Feed 2.1")
        scheme.description = "Periodically poll a TAXII feed to retrieve IOCs"

        # If single instance mode is enabled, each stanza defined in the script is run in the same instance.
        # Otherwise, Splunk Enterprise launches a separate instance for each stanza.
        scheme.use_external_validation = True
        scheme.use_single_instance = False

        # Only available data types :
        # data_type_boolean / data_type_boolean / data_type_number
        taxii_host = Argument("taxii_host")
        taxii_host.title = "Taxii Host"
        taxii_host.data_type = Argument.data_type_string
        taxii_host.description = "TAXII feed host url."
        taxii_host.required_on_create = True
        scheme.add_argument(taxii_host)

        taxii_path = Argument("taxii_path")
        taxii_path.title = "Discovery Path"
        taxii_path.data_type = Argument.data_type_string
        taxii_path.description = "TAXII feed discovery path."
        taxii_path.required_on_create = True
        scheme.add_argument(taxii_path)

        taxii_feed_id = Argument("taxii_collection_url")
        taxii_feed_id.title = "Collection URLs"
        taxii_feed_id.data_type = Argument.data_type_string
        taxii_feed_id.description = "collection URLs with comma-delimited. if no collection URL is provided, " \
                                    "IOCs will be fetched from all available collections"
        taxii_feed_id.required_on_create = False
        scheme.add_argument(taxii_feed_id)

        taxii_login = Argument("taxii_user")
        taxii_login.title = "Username"
        taxii_login.data_type = Argument.data_type_string
        taxii_login.description = "Taxii server username."
        taxii_login.required_on_create = True
        scheme.add_argument(taxii_login)

        taxii_password = Argument("taxii_password")
        taxii_password.title = "Password"
        taxii_password.data_type = Argument.data_type_string
        taxii_password.description = "Taxii server password"
        taxii_password.required_on_create = True
        scheme.add_argument(taxii_password)

        taxii_cert_pem = Argument("taxii_cert_pem")
        taxii_cert_pem.title = "cert_pem"
        taxii_cert_pem.data_type = Argument.data_type_string
        taxii_cert_pem.description = "Specify the path after $SPLUNK_HOME of the SSL certificate to use (.pem) for " \
                                     "a dual-factor authentication."
        taxii_cert_pem.required_on_create = False
        scheme.add_argument(taxii_cert_pem)

        taxii_cert_key = Argument("taxii_cert_key")
        taxii_cert_key.title = "cert_key"
        taxii_cert_key.data_type = Argument.data_type_string
        taxii_cert_key.description = "Specify the path after $SPLUNK_HOME of the certificate key file to use (.key) " \
                                     "for a dual-factor authentication."
        taxii_cert_key.required_on_create = False
        scheme.add_argument(taxii_cert_key)

        taxii_use_https = Argument("verify_ssl")
        taxii_use_https.title = "Verify ssl"
        taxii_use_https.data_type = Argument.data_type_boolean
        taxii_use_https.description = "Specify to use HTTPS instead of regular HTTP."
        taxii_use_https.required_on_create = True
        scheme.add_argument(taxii_use_https)
        return scheme

    def validate_input(self, validation_definition):
        """Validates input."""
        collections = []
        taxii_cert_pem = validation_definition.parameters.get("taxii_cert_pem")
        taxii_cert_key = validation_definition.parameters.get("taxii_cert_key")
        taxii_host = validation_definition.parameters.get("taxii_host")
        collection_url = validation_definition.parameters.get("taxii_collection_url")
        if collection_url:
            collections = collection_url.split(',')
        instance_type = self.get_instance_type()
        if taxii_cert_pem and taxii_cert_key:
            taxii_cert_pem = os.environ['SPLUNK_HOME'] + taxii_cert_pem \
                if not taxii_cert_pem.startswith("/") else "/" + taxii_cert_pem  # cert.pem
            taxii_cert_key = os.environ['SPLUNK_HOME'] + taxii_cert_key \
                if not taxii_cert_key.startswith("/") else "/" + taxii_cert_key  # cert.key
            if (not os.path.exists(taxii_cert_pem)) or (not os.path.exists(taxii_cert_key)):
                raise ValueError(" taxii_cert_pem or taxii_cert_key doesn't exists")
        if instance_type and not taxii_host.startswith("https://"):
            raise ValueError("Insecure HTTP call is not allowed in Splunk Cloud.")
        if instance_type and len(collections):
            for collection in collections:
                if not collection.startswith("https://"):
                    raise ValueError("Insecure HTTP call is not allowed in Splunk Cloud.")

    def get_instance_type(self, stanza="general", file_name="server.conf", key_name="instanceType"):
        appdir = os.path.dirname(os.path.dirname(__file__))
        localconfpath = os.path.join(appdir, "local", file_name)
        if os.path.exists(localconfpath):
            localconf = cli.readConfFile(localconfpath)
            instance_type = localconf.get(stanza, {}).get(key_name)
            if instance_type and instance_type == "cloud":
                return instance_type

    def encrypt_password(self, username, password, session_key):
        args = {'token': session_key}
        service = client.connect(**args)
        try:
            # If the credential already exists, delte it.
            for storage_password in service.storage_passwords:
                if storage_password.username == username:
                    service.storage_passwords.delete(username=storage_password.username)
                    break
            # Create the credential.
            service.storage_passwords.create(password, username)
        except Exception as e:
            raise Exception("An error occurred updating credentials. Please ensure your user account has "
                            "admin_all_objects and/or list_storage_passwords capabilities. Details: %s" % str(e))

    def mask_password(self, session_key, username, input_name):
        try:
            args = {'token': session_key}
            service = client.connect(**args)
            kind, input_name = input_name.split("://")
            item = service.inputs.__getitem__((input_name, kind))
            kwargs = {
                "taxii_user": username,
                "taxii_password": self.MASK
            }
            item.update(**kwargs).refresh()
        except Exception as e:
            raise Exception("Error updating inputs.conf: %s" % str(e))

    def get_password(self, session_key, username):
        args = {'token': session_key}
        service = client.connect(**args)
        # Retrieve the password from the storage/passwords endpoint
        for storage_password in service.storage_passwords:
            if storage_password.username == username:
                return storage_password.content.clear_password

    def create_taxii_connection(self, connection_object):
        return connection_object.test_connection()

    def stream_events(self, inputs, ew):
        # Splunk Enterprise calls the modular input,
        # streams XML describing the inputs to stdin,
        # and waits for XML on stdout describing events.
        session_key = self._input_definition.metadata["session_key"]
        for input_name, input_item in inputs.inputs.items():
            try:
                logger.debug(f"input name: {input_name}")
                if "taxii_feed://" in input_name:
                    logger.debug(f"Input name {input_name} matched")
                    taxii_host = input_item["taxii_host"]
                    taxii_path = input_item["taxii_path"]
                    taxii_collection_url = input_item.get("taxii_collection_url")
                    taxii_login = input_item["taxii_user"]
                    taxii_password = input_item["taxii_password"]
                    taxii_cert_pem = input_item.get("taxii_cert_pem")
                    taxii_cert_key = input_item.get("taxii_cert_key")
                    interval = input_item.get("interval", 3600)

                    if not taxii_cert_pem or not taxii_cert_key:
                        taxii_cert_pem = None
                        taxii_cert_key = None
                    else:
                        taxii_cert_pem = os.environ['SPLUNK_HOME'] + taxii_cert_pem \
                            if not taxii_cert_pem.startswith("/") else "/" + taxii_cert_pem # cert.pem
                        taxii_cert_key = os.environ['SPLUNK_HOME'] + taxii_cert_key \
                            if not taxii_cert_key.startswith("/") else "/" + taxii_cert_key # cert.key

                        if (not os.path.exists(taxii_cert_pem)) or (not os.path.exists(taxii_cert_key)):
                            raise ValueError(" taxii_cert_pem or taxii_cert_key doesn't exists")

                    verify_ssl = True
                    if input_item["verify_ssl"] in ["0", "False"]:
                        verify_ssl = False
                    source_confidence = "medium"
                    user_verdict = "malicious"
                    if taxii_host.endswith("/"):
                        taxii_host = taxii_host.rstrip("/")
                    if not taxii_path.startswith("/"):
                        taxii_path = "/" + taxii_path
                    if not taxii_path.endswith("/"):
                        taxii_path = taxii_path + "/"
                    discovery_url = taxii_host + taxii_path
                    try:
                        # If the password is not masked, mask it.
                        if taxii_password != self.MASK:
                            self.encrypt_password(taxii_login, taxii_password, session_key)
                            self.mask_password(session_key, taxii_login, input_name)
                            logger.info("Credentials masking complete, Launching another instance")
                            break
                        self.CLEAR_PASSWORD = self.get_password(session_key, taxii_login)
                        logger.debug(f"input item: {input_item}")
                    except Exception as e:
                        ew.log("ERROR", "Error: %s" % str(e))
                    taxii_client = Taxii2Client(discovery_url, taxii_login, self.CLEAR_PASSWORD, 443,
                                                taxii_collection_url, logger, verify_ssl, source_confidence,
                                                user_verdict, cert=(taxii_cert_pem, taxii_cert_key),
                                                discovery_url_path=taxii_path)
                    self.create_taxii_connection(taxii_client)
                    try:
                        earliest_time = datetime.datetime.utcnow().timestamp() - int(interval)
                        params = {"start_date": earliest_time}
                        status, data = taxii_client.get_objects(params)
                        logger.info(f"status for taxii feed call is {status}")
                        if status and data:
                            event = Event()
                            event.stanza = input_name
                            if isinstance(data, list):
                                logger.info(f"length of data is :{str(len(data))}")
                                for data_entry in data:
                                    event.data = json.dumps(data_entry)
                                    ew.write_event(event)
                            else:
                                event.data = json.dumps(data)
                                ew.write_event(event)
                    except Exception as err:
                        logger.debug(f"Exception occurred in polling from stix server. Error is {str(err)}")
            except Exception as err:
                logger.debug(f"Exception occurred in stream event. Error is {str(err)}")


if __name__ == "__main__":
    sys.exit(TAXIIModularInput().run(sys.argv))
