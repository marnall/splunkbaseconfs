""" FTP Modular Input for Splunk """

import sys
import splunklib.client as client #pylint: disable=consider-using-from-import
from splunklib.modularinput import Argument
from splunklib.modularinput import Script
from splunklib.modularinput import Event
from splunklib.modularinput import Scheme
from ftp_client import FTPClient

""" Based off of TA_modinput_cred-example
https://www.splunk.com/blog/2016/10/10/encrypt-a-modular-input-field-without-using-setup-xml.html""" # pylint: disable=pointless-string-statement


class FTPInput(Script):
    """ FTP modular input """

    # Define some global variables
    MASK = "<nothing to see here>"
    APP = 'TA-ftppull'
    USERNAME = None
    CLEAR_PASSWORD = None

    def get_scheme(self):

        scheme = Scheme("FTP Input")
        scheme.description = "Connects to host over FTP and downloads specified file(s)"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        hostname_arg = Argument(
            name="hostname",
            title="Hostname",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(hostname_arg)

        username_arg = Argument(
            name="username",
            title="User name",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(username_arg)

        password_arg = Argument(
            name="password",
            title="Password",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(password_arg)

        path_arg = Argument(
            name="path",
            title="File path",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(path_arg)

        filename_arg = Argument(
            name="filename",
            title="File name (supports wildcards)",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(filename_arg)

        override_arg = Argument(
            name="override",
            title="Override host field with FTP hostname",
            data_type=Argument.data_type_boolean,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(override_arg)

        disable_wildcards_arg = Argument(
            name="disable_wildcards",
            title="Disable wildcards. Filename will be interpreted literally",
            data_type=Argument.data_type_boolean,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(disable_wildcards_arg)

        force_tls_arg = Argument(
            name="force_tls",
            title="Force TLS on FTP connection (FTPS)",
            data_type=Argument.data_type_boolean,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(force_tls_arg)
        return scheme

    def validate_input(self, definition):
        """ Input validation. Stubbed out for now """
        return

    def get_password(self, session_key, username):
        """ Retrieves the password from the storage/passwords endpoint """
        args = {'token':session_key}
        service = client.connect(**args)

        for storage_password in service.storage_passwords:
            if storage_password.username == username:
                return storage_password.content.clear_password
        return None

    def encrypt_password(self, username, password, session_key):
        """ Encrypts password using the password storage endpoint """
        args = {'token':session_key}
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
            raise Exception('An error occurred updating credentials. ' # pylint: disable=consider-using-f-string,broad-exception-raised
                            'Please ensure your user account has admin_all_objects '
                            'and/or list_storage_passwords capabilities. '
                            'Details: %s' % str(e)) from e

    def mask_password(self, session_key, input_name):
        """ Mask password so it's not stored in inputs.conf """
        try:
            args = {'token':session_key}
            service = client.connect(**args)
            kind, input_name = input_name.split("://")
            item = service.inputs.__getitem__((input_name, kind)) # pylint: disable=unnecessary-dunder-call

            kwargs = {
                "username": item.content['username'],
                "password": self.MASK,
                "hostname": item.content['hostname'],
                "path": item.content['path'],
                "filename": item.content['filename'],
                "override": item.content['override'],
                "disable_wildcards": item.content['disable_wildcards'],
                "force_tls": item.content['force_tls']
            }
            item.update(**kwargs).refresh()

        except Exception as e:
            raise Exception("Error updating inputs.conf: %s" % str(e)) from e # pylint: disable=consider-using-f-string,broad-exception-raised


    def stream_events(self, inputs, ew):
        for input_name, input_item in inputs.inputs.items():
            session_key = self._input_definition.metadata["session_key"]
            self.USERNAME = input_item["username"]
            password = input_item['password']
            hostname = input_item["hostname"]
            path = input_item["path"]
            filename = input_item["filename"]
            override = input_item["override"]

            try:
                # If the password is not masked, mask it.
                if password != self.MASK:
                    self.encrypt_password(self.USERNAME, password, session_key)
                    self.mask_password(session_key, input_name)

                self.CLEAR_PASSWORD = self.get_password(session_key, self.USERNAME)
            except Exception as e: # pylint: disable=broad-exception-caught
                ew.log("ERROR", "Error: %s" % str(e)) # pylint: disable=consider-using-f-string
            ftpclient = FTPClient(hostname, self.USERNAME, self.CLEAR_PASSWORD,
                                  disable_wildcards=input_item["disable_wildcards"],
                                  force_tls=input_item["force_tls"])
            for file_contents in ftpclient.download(path, filename):
                event = Event()
                event.stanza = input_name
                if str(override).lower() in ['0', 'false', 'False']:
                    event.host = input_item['host']
                else:
                    event.host = hostname
                event.source = file_contents['filename']
                event.data = file_contents['contents']
                ew.write_event(event)

if __name__ == "__main__":
    exitcode = FTPInput().run(sys.argv)
    sys.exit(exitcode)
