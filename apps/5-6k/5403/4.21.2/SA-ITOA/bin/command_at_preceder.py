# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import logging
import re
import sys
import ast

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path
from ITOA.setup_logging import setup_logging
from at_utils.chunked_util import read_chunk, write_chunk
from at_utils.utils import log_and_die, chunker, gather_input_data

##################
# itsiatpreceder
##################
# Command logs to $SPLUNK_HOME/var/log/splunk/itsi_at_preceder.log


# Windows will mangle our line-endings unless we do this.
if sys.platform == "win32":
    import os
    import msvcrt

    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)

logger = setup_logging("itsi_at_preceder_command.log", "itsi.apply_at.preceder", level=logging.DEBUG)


def parse_args(args, in_metadata, out_metadata, logger):
    params = {}
    params['use_kv_store'] = True
    params['use_temp_collection'] = False
    params['entity_level_thresholds'] = False
    params['use_incremental_method'] = False
    params['incremental_learning_enabled'] = False
    params['threshold_key'] = 'aggregate_thresholds'

    if isinstance(args, list):
        arg_list = args
    elif isinstance(args, str):
        try:
            arg_list = ast.literal_eval(args)
            if not isinstance(arg_list, list):
                raise ValueError()
        except (ValueError, SyntaxError):
            log_and_die(metadata=out_metadata, logger=logger, msg=f'Failed to parse arguments string: {args}')

    else:
        log_and_die(metadata=out_metadata, logger=logger, msg=f'Unexpected argument type: {type(args)}')

    logger.debug(f"Arg list: {arg_list}")

    arg_dict = {}
    for arg in arg_list:
        if '=' in arg:
            key, value = arg.split('=', 1)
            arg_dict[key.strip()] = value.strip()
        else:
            arg_dict[arg.strip()] = True

    if 'nokv' in arg_dict:
        params['use_kv_store'] = False

    if 'entitylevelthreshold' in arg_dict:
        params['entity_level_thresholds'] = True
        params['pseudo_entities'] = dict()
        params['threshold_key'] = 'entity_thresholds'

    if 'usetempcollection' in arg_dict:
        params['use_temp_collection'] = True

        if 'collection' in arg_dict:
            params['temp_collection'] = arg_dict['collection']
            logger.debug("Temporary collection name: %s", params['temp_collection'])
        else:
            log_and_die(metadata=out_metadata, logger=logger,
                        msg='Must provide a temporary collection name.')

        if 'key' in arg_dict:
            params['temp_key'] = arg_dict['key']
            logger.debug("Temporary object key: %s", params['temp_key'])
        else:
            log_and_die(metadata=out_metadata, logger=logger,
                        msg='Must provide a temporary object key.')

        if params.get('entity_level_thresholds'):
            if 'entity_title' in arg_dict:
                params['temp_entity_title'] = arg_dict['entity_title']
                logger.debug("Temporary entity title: %s", params['temp_entity_title'])
            else:
                log_and_die(metadata=out_metadata, logger=logger,
                            msg='Must provide a temporary entity title.')

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

    return params


def main():
    logger.debug(
        "Starting ITSI AT preceder.")
    out_metadata = {}
    out_metadata['inspector'] = {'messages': []}

    # Phase 0: getinfo exchange
    metadata, body = read_chunk(sys.stdin, logger)
    # Don't run in preview.
    if metadata.get('preview', False):
        write_chunk(sys.stdout, {'finished': True}, '')
        sys.exit(0)

    args = metadata['searchinfo']['args']

    params = parse_args(
        args=args, in_metadata=metadata, out_metadata=out_metadata, logger=logger)
    params['logger'] = logger
    params['out_metadata'] = out_metadata

    params['out_metadata']['finished'] = False
    fields_list = ['_time', 'itsi_service_id', 'itsi_kpi_id', 'alert_value']
    if params['entity_level_thresholds']:
        fields_list = fields_list + ['entity_key', 'entity_title']
    params['out_metadata']['required_fields'] = fields_list
    params['out_metadata']['type'] = 'reporting'
    write_chunk(sys.stdout, params['out_metadata'], '')
    params['out_metadata'].pop('type', None)
    params['out_metadata'].pop('required_fields', None)
    # Phase 1:
    gather_input_data(params, logger, fields_list)
    # Calling the chunker
    chunker(params)
    ret = read_chunk(sys.stdin, logger)
    if ret:
        write_chunk(sys.stdout, {"finished": True}, '')

    logger.debug(
        "Finished ITSI AT preceder.")


if __name__ == "__main__":
    main()
