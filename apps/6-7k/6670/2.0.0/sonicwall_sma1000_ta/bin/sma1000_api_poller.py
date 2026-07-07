#!/usr/bin/env python

import datetime
import decimal
import os
import requests
import sys
import warnings
import urllib3.exceptions

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
import splunklib.client as client
from splunklib.modularinput import *


class SmaApiPoller(Script):
    APP = 'sonicwall_sma1000_ta'

    TRANSFORMS = {
        'committed_hotfixes': {
            'calc': lambda d: ','.join(d['committedHotfixes']) if d['committedHotfixes'] is not None else None
        },
        'cpu_load_percent': {
            'source': 'cpuUsagePercent'
        },
        'hotfixes': {
            'calc': lambda d: ','.join(d['hotfixes']) if d['hotfixes'] is not None else None
        },
        'mem': {
            'calc': lambda d: decimal.Decimal(d['memoryTotalMB'])
        },
        'mem_free': {
            'calc': lambda d: decimal.Decimal(d['memoryTotalMB']) -
                              (
                                      decimal.Decimal(d['memoryTotalMB']) * decimal.Decimal(d['memoryUsagePercent'] / 100)
                              )
        },
        'mem_used': {
            'calc': lambda d: decimal.Decimal(d['memoryTotalMB']) * decimal.Decimal(d['memoryUsagePercent'] / 100)
        },
        'storage': {
            'calc': lambda d: decimal.Decimal(d['diskTotalGB']) * 1024
        },
        'storage_free': {
            'calc': lambda d: (
                                      decimal.Decimal(d['diskTotalGB']) -
                                      decimal.Decimal(d['diskTotalGB']) * decimal.Decimal(d['diskUsagePercent'] / 100)
                              ) * 1024
        },
        'storage_used': {
            'calc': lambda d: decimal.Decimal(d['diskTotalGB']) * decimal.Decimal(d['diskUsagePercent']) * decimal.Decimal(10.24)
        },
        'swap': {
            'calc': lambda d: decimal.Decimal(d['swapSpaceTotalMB'])
        },
        'swap_free': {
            'calc': lambda d: decimal.Decimal(d['swapSpaceTotalMB']) -
                              (
                                      decimal.Decimal(d['swapSpaceTotalMB']) * decimal.Decimal(d['swapSpaceUsagePercent'] / 100)
                              )
        },
        'swap_used': {
            'calc': lambda d: decimal.Decimal(d['swapSpaceTotalMB']) * decimal.Decimal(d['swapSpaceUsagePercent'] / 100)
        },
        'thruput': {
            'calc': lambda d: (
                                      decimal.Decimal(d['internalInterfaceMbps']) +
                                      decimal.Decimal(d['externalInterfaceMbps'] if d['maxExternalInterfaceMbps'] is not None else 0)
                              ) / 8
        },
        'thruput_external': {
            'calc': lambda d: decimal.Decimal(d['externalInterfaceMbps']) / 8 if d['maxExternalInterfaceMbps'] is not None else None
        },
        'thruput_external_max': {
            'calc': lambda d: decimal.Decimal(d['maxExternalInterfaceMbps']) / 8 if d['maxExternalInterfaceMbps'] is not None else None
        },
        'thruput_internal': {
            'calc': lambda d: decimal.Decimal(d['internalInterfaceMbps']) / 8
        },
        'thruput_internal_max': {
            'calc': lambda d: decimal.Decimal(d['maxInternalInterfaceMbps']) / 8 if d['maxInternalInterfaceMbps'] is not None else None
        },
        'thruput_max': {
            'calc': lambda d: (
                                      decimal.Decimal(d['maxInternalInterfaceMbps']) +
                                      decimal.Decimal(d['maxExternalInterfaceMbps'] if d['maxExternalInterfaceMbps'] is not None else 0)
                              ) / 8
        },
        'uptime': {
            'calc': lambda d: d['upTime']['days'] * 86400 + d['upTime']['hours'] * 3600 +
                              d['upTime']['minutes'] * 60 + d['upTime']['seconds']
        }
    }

    PASSTHRU_FIELDS = [
        'timeZone',
        'serialNumber',
        'productName',
        'hasPendingChanges',
        'activeUserCount',
        'activeFullUserCount',
        'activeEmailUserCount',
        'licenseMaxUsers',
        'licenseMaxEmailUsers',
        'tcpConnectionCount',
        'webConnectionCount',
        'certificateExpiration',
        'licenseStatus',
        'fipsActive',
        'inStandbyMode',
        'applianceIntercommunicationOk',
        'loadScorePercent',
        'captureDiskUsagePercent',
        'hypervisor',
        'cpuCount',
        'version'
    ]

    def get_scheme(self):
        _scheme = Scheme(title='SonicWall SMA1000 API Poller')
        _scheme.description = 'Configure periodic polling of an SonicWall SMA1000 device for utilization data.'
        _scheme.streaming_mode_xml = True
        _scheme.use_external_validation = True
        _scheme.use_single_instance = False

        address_arg = Argument(
            name='address',
            title='Address',
            description='DNS name or IP address of SMA1000 device to poll.',
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        _scheme.add_argument(address_arg)

        username_arg = Argument(
            name='username',
            title='Username',
            description='SMA1000 username for API request authentication. User must have an administrator role with '
                        'System monitoring > View privileges.',
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        _scheme.add_argument(username_arg)

        ssl_arg = Argument(
            name='validate_ssl',
            title='Validate SSL',
            description='Validate SSL certificate presented by SMA1000 device?',
            data_type=Argument.data_type_boolean,
            required_on_create=True,
            required_on_edit=True
        )
        _scheme.add_argument(ssl_arg)

        port_arg = Argument(
            name='port',
            title='Management Port',
            description='TCP port used for management traffic to SMA1000 devices.',
            data_type=Argument.data_type_number,
            required_on_create=True,
            required_on_edit=True
        )
        _scheme.add_argument(port_arg)

        credential_uuid_arg = Argument(
            name='credential_uuid',
            title='Credential UUID',
            description='UUID of password credential in Splunk StoragePasswords service.',
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        _scheme.add_argument(credential_uuid_arg)

        return _scheme

    def get_system_status(self, address, port, username, password, validate_ssl):
        with warnings.catch_warnings():
            if validate_ssl == '0':
                warnings.filterwarnings('ignore', category=urllib3.exceptions.InsecureRequestWarning)

            return requests.get(
                url='https://{0}:{1}/Console/SystemStatus'.format(address, port),
                auth=(username, password),
                verify=validate_ssl == '1',
                timeout=15.0
            )

    def validate_input(self, definition):
        # Configuration via Admin manager is not supported
        raise Exception('SMA1000 API Poller inputs must be configured via the app setup page.')

    def get_client(self, session_key):
        return client.connect(token=session_key, app=self.APP, sharing='app', owner='splunk-system-user')

    def get_password(self, session_key, credential_uuid):
        service = self.get_client(session_key)

        # Retrieve the password from the storage/passwords endpoint
        for storage_password in service.storage_passwords:
            if storage_password._state.access.app == self.APP and storage_password.username == credential_uuid:
                return storage_password.content.clear_password

        raise Exception('StoragePassword credential with UUID {0} not found'.format(credential_uuid))

    def stream_events(self, inputs, ew):
        input_name, input_items = inputs.inputs.popitem()

        try:
            clear_password = self.get_password(
                session_key=self._input_definition.metadata['session_key'],
                credential_uuid=input_items['credential_uuid']
            )
        except Exception as e:
            ew.log('ERROR', 'Error: {0}'.format(e))
            return

        _event = Event(
            stanza=input_name,
            sourcetype='sonicwall:sma1000:system_status',
            time=datetime.datetime.now().timestamp(),
            done=True,
            unbroken=True
        )

        try:
            response = self.get_system_status(
                address=input_items['address'],
                port=input_items['port'],
                username=input_items['username'],
                password=clear_password,
                validate_ssl=input_items['validate_ssl']
            )

            response.raise_for_status()
            _event.data = self.parse_response(response.json())
        except Exception as e:
            _event.data = 'unreachable="true", error="{0}"'.format(e)

        ew.write_event(_event)

    def parse_response(self, response):
        result = []

        # Apply transforms - calculations and custom field renaming
        for field, transform in self.TRANSFORMS.items():
            result = self.append_to_result(
                result=result,
                key=field,
                value=transform['calc'](response) if 'calc' in transform else response[transform['source']]
            )

        # Other fields we will just convert to snake case
        for field in self.PASSTHRU_FIELDS:
            result = self.append_to_result(
                result=result,
                key=self.camel_to_snake(field),
                value=response[field]
            )

        return ', '.join(result)

    # Omit null values, perform data type conversions, flatten to key/value pair string
    def append_to_result(self, result, key, value):
        if value is None:
            return result

        if type(value) is bool:
            value = str(value).lower()

        if type(value) is decimal.Decimal:
            value = '{:.2f}'.format(value)

        result.append('{0}="{1}"'.format(key, value))

        return result

    def camel_to_snake(self, s):
        return ''.join(['_' + c.lower() if c.isupper() else c for c in s]).lstrip('_')


if __name__ == '__main__':
    sys.exit(SmaApiPoller().run(sys.argv))

