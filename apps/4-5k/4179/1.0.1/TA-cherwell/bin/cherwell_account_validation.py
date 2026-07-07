import os
import io
import sys
import json
import requests
import ConfigParser

import splunk.admin as admin
import splunk.entity as entity
from splunk.clilib.bundle_paths import make_splunkhome_path
from splunktaucclib.rest_handler.endpoint.validator import Validator


class GetSessionKey(admin.MConfigHandler):
    def __init__(self):
        self.session_key = self.getSessionKey()

class Address(Validator):
    def __init__(self, *args, **kwargs):
        """

        :param validator: user-defined validating function
        """
        super(Address, self).__init__()
        self._args = args
        self._kwargs = kwargs

    def validate(self, value, data):
        value.strip('/')
        try:
            if "://" in value:
                msg = "Protocols are not allowed in IP Address/Hostname field."
                raise Exception(msg)
            if '?' in value or '#' in value or '@' in value:
                msg = "Please enter valid IP Address/Hostname."
                raise Exception(msg)
        except Exception as exc:
            self.put_msg(msg)
            return False
        else:
            data["ipaddress"] = value.strip('/')
            return True