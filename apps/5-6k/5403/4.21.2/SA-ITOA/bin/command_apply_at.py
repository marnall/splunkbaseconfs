# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import logging
import random
import re
import sys
import time

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
from ITOA.itoa_common import is_feature_enabled
from ITOA.setup_logging import setup_logging
from at_utils.chunked_util import read_chunk, write_chunk
from at_utils.utils import log_and_warn, log_and_die, chunker, gather_input_data

# Set this constant if you want to enable file-based KPI specification
# (useful for debugging without accessing the KV store).
# **** DO NOT SET THIS IN PRODUCTION (ITOA-3809) ****
# ENABLE_FILE_ARGUMENT = 1

##################
# applyat
##################
# Command logs to $SPLUNK_HOME/var/log/splunk/itsi_apply_at.log

# contents of searchbnf.conf:
# [applyat-command]
# syntax = applyat (nokv) (file=<filename containing kpi json object>) (usetempcollection) (collection=<string: name of the collection>) (key=<string: object key>)
# description = Computes thresholds based on the input data and according to the schedules and policies specified in settings (in nokv mode) or found in the kv store (default).
#   The data is partitioned according to which block of the schedule it corresponds to, then thresholds are computed for each block according to the rules in the associated policy.
#   If any policies of any KPIs lack sufficient data to compute the thresholds as specified, the command will return no thresholds for that policy and will not update the corresponding thresholds.
#   The _time field should be in UTC epoch time with the timezone specified in the KPI and that timezone should correspond with the timezone in which the time blocks are specified.
#   No thresholds will be returned (or written to the KV store) for any KPIs for which an error was encountered; otherwise, the computed thresholds will be output even if multiple thresholds have the same value.
#   The command returns thresholds via stdout, and may additionally write them to the KV store if the appropriate arguments are passed. The empty string '' is an invalid value for all fields.
# shortdesc = Computes adaptive thresholds for the given data and kpi information (which it uses to acquire schedules and policies from the kv store).
# comment1 = An example using the command with the KV store (the 'table' command is optional):
# example1 = | table _time alert_value itsi_service_id itsi_kpi_id | applyat
# comment2 = You can also pass a filename containing the kpi json directly to the command and receive the results as events (replace $SPLUNK_HOME with the correct path):
# example2 = | table _time alert_value itsi_service_id itsi_kpi_id | applyat nokv file=$SPLUNK_HOME/etc/apps/SA-ITSI-ATAD/bin/test/SHKPI.json
# comment3 = You can use the command with a temporary collection in the KV store like this:
# example3 = | table _time alert_value itsi_service_id itsi_kpi_id | applyat usetempcollection collection=temp_kpi_collection key=857d4397893137141fb6c427
# usage = public
# tags = kpi adaptive thresholding dynamic thresholds schedule blocks policy

# [applyat-nokv-option]
# syntax = nokv
# description = When present, this flag makes the command use a file (specified in the settings argument) instead of the KV store to acquire the policies and schedules. The computed thresholds are returned as events.

# [applyat-file-option]
# syntax = file=<filename containing KPI JSON object>
# description = In interactive mode (pass the "nokv" flag), the "file" parameter takes a filename containing the plaintext JSON of a KPI object. This has the Time Block and Threshold Policy data structures under the 'time_variate_thresholds_specification' key, which, in KV mode, the command retrieves from the KV store. If the nokv flag is not present, this argument is ignored.

# [applyat-usetempcollection-option]
# syntax = usetempcollection
# description = When present, this flag makes the command use temporary collection in the KV store. The collection name and object key must both be provided. If the nokv flag is also present, the command throws an error.

# [applyat-collection-option]
# syntax = collection=<string: temp collection name>
# description = The name of the temporary collection to use.

# [applyat-key-option]
# syntax = key=<string: temp object key>
# description = The key to use for the object in the temporary collection.

# Windows will mangle our line-endings unless we do this.
if sys.platform == "win32":
    import os
    import msvcrt

    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)

logger = setup_logging("itsi_apply_at_command.log", "itsi.apply_at.command", level=logging.INFO)


def parse_args(args, in_metadata, out_metadata, logger):
    params = {}
    params['use_kv_store'] = True
    params['use_temp_collection'] = False
    params['entity_level_thresholds'] = False
    params['use_incremental_method'] = False
    params['threshold_key'] = 'aggregate_thresholds'

    if 'log_level' in args:
        r = re.search(r'\s*log_level\s*=\s*(?P<log_level>\S+)\'', str(args))
        if r is not None:
            try:
                log_level = r.group('log_level')
                logger.info(f"Setting up log level to {log_level}")
                logger.setLevel(log_level)
            except Exception:
                logger.exception("Cannot set log level passed as command parameters")

    if 'nokv' in args:
        params['use_kv_store'] = False

    if 'entitylevelthreshold' in args:
        params['entity_level_thresholds'] = True
        params['pseudo_entities'] = dict()
        params['threshold_key'] = 'entity_thresholds'

    if 'usetempcollection' in args:
        params['use_temp_collection'] = True

        r = re.search(r'\s*collection\s*=\s*(?P<coll>\S+)\'', str(args))
        if r is not None:
            try:
                params['temp_collection'] = r.group('coll')
                logger.debug("Temporary collection name: %s" %
                             str(params['temp_collection']))
            except Exception:
                log_and_die(metadata=out_metadata, logger=logger,
                            msg='Failed to parse temporary collection name in parameters.')
        else:
            log_and_die(metadata=out_metadata, logger=logger,
                        msg='Must provide a temporary collection name.')

        r = re.search(r'\s*key\s*=\s*(?P<key>\S+)\'', str(args))
        if r is not None:
            try:
                params['temp_key'] = r.group('key')
                logger.debug("Temporary object key: %s" %
                             str(params['temp_key']))
            except Exception:
                log_and_die(metadata=out_metadata, logger=logger,
                            msg='Failed to parse temporary object key in parameters.')
        else:
            log_and_die(metadata=out_metadata, logger=logger,
                        msg='Must provide a temporary object key.')
        if 'entitylevelthreshold' in args:
            r = re.search(r'\s*entity_title\s*=\s*(?P<entity_title>\S+)\'', str(args))
            if r is not None:
                try:
                    params['temp_entity_title'] = r.group('entity_title')
                    logger.debug("Temporary entity title: %s" %
                                 str(params['temp_entity_title']))
                except Exception:
                    log_and_die(metadata=out_metadata, logger=logger,
                                msg='Failed to parse temporary entity title in parameters.')

    if 'useincrementalmethod' in args:
        params['use_incremental_method'] = True

    params['session_key'] = str(in_metadata['searchinfo']['session_key'])

    if globals().get('ENABLE_FILE_ARGUMENT', False):
        r = re.search(r'\s*file\s*=\s*(?P<fname>\S+)\'', str(args))
    else:
        r = None

    if r is not None and not params['use_kv_store']:
        try:
            params['settings_file'] = r.group('fname')
            logger.debug("Settings file: %s" % str(params['settings_file']))
        except Exception:
            log_and_die(
                metadata=out_metadata, logger=logger, msg='Failed to parse settings file in parameters.')
    elif not params['use_kv_store']:
        log_and_die(
            metadata=out_metadata, logger=logger, msg='No settings file specified.')

    if not params['use_kv_store'] and params['use_temp_collection']:
        log_and_die(
            metadata=out_metadata, logger=logger, msg="Incompatible arguments passed: nokv and usetempcollection.")

    if params['use_temp_collection'] and params['use_incremental_method']:
        log_and_die(
            metadata=out_metadata, logger=logger, msg="Incompatible arguments passed: usetempcollection and useincrementalmethod.")

    return params


def main():
    logger.info(
        "Starting ITSI adaptive thresholding - applyat")
    out_metadata = {}
    out_metadata['inspector'] = {'messages': []}

    # Phase 0: getinfo exchange
    metadata, body = read_chunk(sys.stdin, logger)
    # Don't run in preview.
    if metadata.get('preview', False):
        write_chunk(sys.stdout, {'finished': True}, '')
        sys.exit(0)

    args = str(metadata['searchinfo']['args'])

    params = parse_args(args=args, in_metadata=metadata, out_metadata=out_metadata, logger=logger)
    params['logger'] = logger
    params['out_metadata'] = out_metadata
    is_high_scale_at_enabled = is_feature_enabled('itsi-high-scale-at', params['session_key'])
    is_incremental_learning_enabled = is_feature_enabled('itsi-at-incremental-learning', params['session_key'])
    params['incremental_learning_enabled'] = is_incremental_learning_enabled and is_high_scale_at_enabled
    if not params['incremental_learning_enabled']:
        params['use_incremental_method'] = False

    params['out_metadata']['finished'] = False
    fields_list = ['_time', 'itsi_service_id', 'itsi_kpi_id', 'alert_value']
    if params["entity_level_thresholds"]:
        fields_list = fields_list + ['entity_key', 'entity_title']
    params['out_metadata']['required_fields'] = fields_list
    params['out_metadata']['type'] = 'reporting'
    write_chunk(sys.stdout, params['out_metadata'], '')
    params['out_metadata'].pop('type', None)
    params['out_metadata'].pop('required_fields', None)
    try:
        # Phase 1:
        gather_input_data(params, logger, fields_list)
        at_run_epoch = str(int(time.time() * 1000))
        params['at_run_epoch'] = at_run_epoch
        # Phase 2
        chunker(params, at_command=True)
        # After updating thresholds to all services, do single rest to batch update the services
        if params['service_object'] and not params['entity_level_thresholds']:
            params['service_object'].batch_update_services()
        elif params['entity_level_thresholds'] and not params['use_temp_collection']:
            params['entity_threshold_object'].batch_update_entity_thresholds()
        # we're done, so send dummy response to finish the session
        ret = read_chunk(sys.stdin, logger)
        if ret:
            write_chunk(sys.stdout, {"finished": True}, '')
    except Exception as e:
        logger.error(f"Failed ITSI adaptive thresholding - applyat with error: {e}")
        raise Exception(e)

    logger.info("Finished ITSI adaptive thresholding - applyat")


if __name__ == "__main__":
    main()
