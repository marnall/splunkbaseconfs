#!/usr/bin/env python

import csv
import os
import re
import sys

import requests
from splunk.clilib import cli_common as cli

__MAC_ADDRESS_IO_SETUP_CONFIG_FILE = "mac_address_io_setup.conf"
__MAC_ADDRESS_IO_API_STANZA = "mac_address_io_config"
__MAC_ADDRESS_RE = re.compile(r'(([0-9A-Fa-f]{1,2}[.:-]?){5,7}([0-9A-Fa-f]{1,2}))', flags=re.IGNORECASE)


def get_application_config(stanza):
    app_dir = os.path.dirname(os.path.dirname(__file__))
    config_path = os.path.join(app_dir, "default", __MAC_ADDRESS_IO_SETUP_CONFIG_FILE)
    config = cli.readConfFile(config_path)
    local_config_path = os.path.join(app_dir, "local", __MAC_ADDRESS_IO_SETUP_CONFIG_FILE)

    if os.path.exists(local_config_path):
        local_config = cli.readConfFile(local_config_path)
        for name, content in local_config.items():
            if name in config:
                config[name].update(content)
            else:
                config[name] = content

    return config[stanza]


def normalize_mac_address(_value):
    _value = re.sub(r'[.:\-]', '', _value)
    _value = _value.upper()
    _value = _value.strip()
    _value = \
        ':'.join([_value[i:i + 2] for i in range(0, len(_value), 2)])

    return _value


def validate_mac_address(_value):
    return __MAC_ADDRESS_RE.search(_value) is not None


def send_api_request(_value, _api_config):
    payload = {
        'output': 'csv',
        'search': _value
    }

    response = requests.get(
        _api_config['api_url'],
        headers={
            'X-Authentication-Token': _api_config['api_key'],

        },
        params=payload
    )

    return response.content


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(1)
    else:
        api_config = get_application_config(__MAC_ADDRESS_IO_API_STANZA)

        mac_address_field = sys.argv[1]

        input_file = sys.stdin
        events_reader = csv.DictReader(input_file)

        output_file = sys.stdout
        events_writer = csv.DictWriter(output_file, fieldnames=events_reader.fieldnames)
        events_writer.writeheader()

        cache = dict()

        for event in events_reader:
            mac_address = event[mac_address_field]
            mac_address = normalize_mac_address(mac_address)
            if not validate_mac_address(mac_address):
                event.update({'isValid': 'False'})
                continue
            elif mac_address in cache:
                event.update(cache[mac_address])
            else:
                try:
                    api_response = send_api_request(mac_address, api_config)

                except requests.exceptions.RequestException:
                    events_writer.writerow(event)
                    continue
                api_response_reader = csv.DictReader(api_response.splitlines())
                result = api_response_reader.next()
                result = {k: v for k, v in result.items() if k in events_reader.fieldnames}
                result['isValid'] = 'True' if result['isValid'] == 1 else 'False'
                result['isPrivate'] = 'True' if result['isPrivate'] == 1 else 'False'
                result['blockFound'] = 'True' if result['blockFound'] == 1 else 'False'
                cache[mac_address] = result
                event.update(result)

            events_writer.writerow(event)
