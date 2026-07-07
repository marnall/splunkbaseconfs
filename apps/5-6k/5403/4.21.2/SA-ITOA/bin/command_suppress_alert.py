# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
import csv
import logging

# Core Splunk Imports
import splunk.rest
import splunk.Intersplunk
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path
from ITOA.itoa_config import get_supported_objects
from itsi.suppress_alert import CustomSuppressAlert, ParseArgs
from ITOA.setup_logging import getLogger4SearchCmd
logger, settings, records = getLogger4SearchCmd(level=logging.ERROR, is_console_header=True, return_all=True)


def get_params(args):
    '''
    Parse search arguments and return dict of search params
    :param: dict list of system arguments pass to scripts
    :return: dict of search params and their values
    :rtype: dict
    '''
    params, error_msg = ParseArgs.get_params(args[1:])
    if error_msg is not None:
        splunk.Intersplunk.parseError(error_msg)
    return params


params = get_params(sys.argv)

# Check for required fields
if 'count' not in list(params.keys()):
    splunk.Intersplunk.parseError("Required field `count` is missing.")

if 'is_consecutive' not in list(params.keys()):
    splunk.Intersplunk.parseError("Required field `is_consecutive` is missing.")

# Make sure required param must exist
if not params.get('count'):
    splunk.Intersplunk.parseError("Invalid value for `count` field.")

if params.get('is_consecutive') is None or not isinstance(params.get('is_consecutive'), bool):
    splunk.Intersplunk.parseError("Invalid value for `is_consecutive` field.")

alert_sup = CustomSuppressAlert(params)
# Get data in streaming mode
try:
    for record in records:
        alert_sup.process_result(record)
    results = alert_sup.get_alerts()
except Exception as e:
    if alert_sup is not None:
        alert_sup.logger.exception(e)
    results = splunk.Intersplunk.generateErrorResults(e)
finally:
    # Output results
    splunk.Intersplunk.outputResults(results)
