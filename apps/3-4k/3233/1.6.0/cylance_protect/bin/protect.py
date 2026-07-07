"""
Description:
    Assortment of protect related utility functions to support the input scripts.

Authors:
    Peter Uys, Cylance Inc.
    Matt Maisel, Cylance Inc.
"""


import os
import hashlib
import json
import logging


from config import Configurator, get_logger
from spreadsheet import read_csv_file, write_csv_file


g_cylogger = get_logger('cylance')


def get_previous_shas_absolute_filename(path, tenant, input_type):
    previous_shas_absolute_filename = os.path.join(path, 'local', tenant['TenantName'] + '-' +  input_type + '.sha')
    return previous_shas_absolute_filename


def get_previous_shas(previous_shas_absolute_filename):
    previous_shas_list = []
    try:
        with open(previous_shas_absolute_filename) as sha_file:
            previous_shas_list = sha_file.read().splitlines()
        return set(previous_shas_list)
    except:
        msg = 'Error - could not access file {}.' +\
        g_cylogger.error(msg.format(previous_shas_absolute_filename, previous_shas_absolute_filename))
        return set([])


def create_local_dir(app_path):
    """ Creates local dir if it does not yet exist. """
    local_dir = os.path.join(app_path, 'local')
    if not os.path.exists(local_dir):
        try:
            os.makedirs(local_dir)
        except:
            g_cylogger.error('Error - could not create dir {}.'.format(local_dir))


def format_data(data, input_type):
    if input_type == 'indicators':
        # indicators of compromise
        ioc = {'Tenant': data['Tenant']}
        ioc['SHA256'] = data['SHA256']
        ioc['indicators'] = []
        for k, v in data.items():
            if v == '1':
                ioc['indicators'].append(k)
        ioc['indicators'].sort()
        return json.dumps(ioc, sort_keys=True)
    else:
        return json.dumps(data, sort_keys=True)


def get_data(session_key, input_type, tracking=True):
    """
    Function:
      - downloads the 'input_type' CSV file (e.g. threats CSV) from the tenant.
      - creates a digest of each record (this is an ad hoc tracking mechanism - do not confuse this with a threat SHA)
      - if a digest has not been seen before the jsonified row is written to Splunk
    """

    cfg = Configurator(session_key)
    g_cylogger.debug('get_data() with ' + input_type)

    if not cfg.tenants:
        g_cylogger.warning('There are no correctly configured tenants.')

    for tenant in cfg.tenants:
        g_cylogger.debug('{}'.format(tenant['TenantName']))

        create_local_dir(cfg.app_path)

        csv_absolute_filename = os.path.join(cfg.app_path, 'local', tenant['TenantName'] + '-' +  input_type + '.csv')

        if write_csv_file(csv_absolute_filename, tenant['ThreatDataReportURL'], input_type, tenant['ThreatDataReportToken']):
            rows = read_csv_file(csv_absolute_filename, input_type)
            if not rows:
                return

            if tracking:
                previous_shas_absolute_filename = get_previous_shas_absolute_filename(cfg.app_path, tenant, input_type)
                previous_shas = []
                if os.access(previous_shas_absolute_filename, os.R_OK | os.W_OK):
                    previous_shas = get_previous_shas(previous_shas_absolute_filename)

                with open(previous_shas_absolute_filename, 'w') as previous_shas_file:
                    for row in rows:
                        row['Tenant'] = tenant['TenantName']
                        formatted_data = format_data(row, input_type)
                        current_sha = hashlib.sha256(str(formatted_data).encode('utf8')).hexdigest()
                        previous_shas_file.write(current_sha + os.linesep)
                        if current_sha not in previous_shas:
                            print(formatted_data)
            else:
                for row in rows:
                    row['Tenant'] = tenant['TenantName']
                    formatted_data = format_data(row, input_type)
                    print(formatted_data)
        else:
            msg = 'Error - could not write csv file {} data url for {}.'
            g_cylogger.error(msg.format(csv_absolute_filename, tenant['TenantName']))
