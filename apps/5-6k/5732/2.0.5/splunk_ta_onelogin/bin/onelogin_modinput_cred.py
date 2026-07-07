#!/usr/bin/env python

import os
import sys

app_dependencies_path = os.path.join(
    os.environ.get('SPLUNK_HOME'),
    'etc',
    'apps',
    'splunk_ta_onelogin',
    'lib'
)
if app_dependencies_path not in sys.path:
    sys.path.append(app_dependencies_path)

import splunklib.client as client
from splunklib.modularinput import Argument, Scheme, Script


class OneloginModinputCred(Script):
    # Define some global variables
    MASK = '<nothing to see here>'
    APP = __file__.split(os.sep)[-3]

    def __init__(self):
        self.username = None
        self.clean_password = None

    @staticmethod
    def get_scheme():
        scheme = Scheme('Onelogin Modular Input Credentials')
        scheme.description = 'Save encrypted credentials in modular inputs.'
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        username_arg = Argument(
            name='username',
            title='Client ID',
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(username_arg)

        password_arg = Argument(
            name='password',
            title='Client Secret',
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(password_arg)

        return scheme

    def stream_events(self, inputs, event_writer):
        input_name_and_kind, input_items = inputs.inputs.popitem()
        session_key = self._input_definition.metadata['session_key']
        self.username = input_items['username']
        password = input_items['password']

        try:
            # If the password is not masked, mask it.
            if password != self.MASK:
                self._encrypt_password(password, session_key)
                self._mask_password(session_key, input_name_and_kind)

            self.clean_password = self._get_password(session_key)
        except Exception as e:
            event_writer.log('ERROR', 'Error: %s' % str(e))

    def _encrypt_password(self, password, session_key):
        args = {'token': session_key}
        service = client.connect(**args)

        try:
            # If the credential already exists, delete it.
            for storage_password in service.storage_passwords:
                if storage_password.username == self.username:
                    service.storage_passwords.delete(
                        username=self.username, realm=storage_password.realm)
                    break

            # Create the credential.
            service.storage_passwords.create(
                password, self.username, realm=self.APP)

        except Exception as e:
            raise Exception(
                'An error occurred updating credentials. '
                'Please ensure your user account has admin_all_objects and/or '
                'list_storage_passwords capabilities. Details: %s' % str(e)
            )

    def _mask_password(self, session_key, input_name_and_kind):
        try:
            args = {'token': session_key}
            service = client.connect(**args)
            kind, input_name = input_name_and_kind.split('://')
            item = service.inputs.__getitem__((input_name, kind))

            kwargs = {
                'username': self.username,
                'password': self.MASK
            }
            item.update(**kwargs).refresh()

        except Exception as e:
            raise Exception('Error updating inputs.conf: %s' % str(e))

    def _get_password(self, session_key):
        args = {'token': session_key}
        service = client.connect(**args)

        # Retrieve the password from the storage/passwords endpoint
        for storage_password in service.storage_passwords:
            if storage_password.username == self.username:
                return storage_password.content.clear_password


if __name__ == '__main__':
    exitcode = OneloginModinputCred().run(sys.argv)
    sys.exit(exitcode)
