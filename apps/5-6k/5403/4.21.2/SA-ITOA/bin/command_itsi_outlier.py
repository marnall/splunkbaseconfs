# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.
import collections
import csv
import logging
import re
import sys

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path
from ITOA.setup_logging import setup_logging
from ITOA.itoa_common import is_feature_enabled
from at_utils.chunked_util import read_chunk, write_chunk, add_message
from at_utils.utils import log_and_die, log_and_warn, gather_input_data, detect_outliers, MIN_DATASET_LEN

##################
# itsi_outlier
##################
# Command logs to $SPLUNK_HOME/var/log/splunk/itsi_outlier_command.log


# Windows will mangle our line-endings unless we do this.
if sys.platform == "win32":
    import os
    import msvcrt

    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)

logger = setup_logging("itsi_outlier_command.log", "itsi.apply_at.outlier", level=logging.DEBUG)


def parse_args(args, in_metadata, out_metadata, logger):
    params = {
        'use_kv_store': True,
        'entity_level_thresholds': False,
        'threshold_key': 'aggregate_thresholds',
    }

    if 'nokv' in args:
        params['use_kv_store'] = False

    if 'entitylevelthreshold' in args:
        params['entity_level_thresholds'] = True
        params['pseudo_entities'] = dict()
        params['threshold_key'] = 'entity_thresholds'

    if 'remove' in args:
        # Detects and remove outliers, default behavior is to
        # display is_outlier field set to true per policy block
        params['remove'] = True
    else:
        params['remove'] = False

    if 'show_outliers_only' in args:
        params['show_outliers_only'] = True
    else:
        params['show_outliers_only'] = False

    r = re.search(r'\s*method\s*=\s*(?P<method>\S+)\'', str(args))
    if r is not None:
        try:
            params['method'] = r.group('method')
            logger.debug(
                "Outlier detection method passed: %s" % str(params['method']))
        except Exception:
            log_and_die(metadata=out_metadata, logger=logger,
                        msg='Failed to parse outlier detection method in parameters.')
    else:
        log_and_die(metadata=out_metadata, logger=logger,
                    msg='Must provide a outlier detection method.')

    r = re.search(r'\s*sensitivity\s*=\s*(?P<sensitivity>\S+)\'', str(args))
    if r is not None:
        try:
            params['multiplier'] = r.group('sensitivity')
            logger.debug(
                "Outlier detection multiplier passed: %s" %
                str(params['multiplier'])
            )
        except Exception:
            log_and_die(
                metadata=out_metadata, logger=logger,
                msg='Failed to parse outlier detection multiplier in parameters.')
    else:
        log_and_die(metadata=out_metadata, logger=logger,
                    msg='Must provide a outlier detection multiplier.')

    params['session_key'] = str(in_metadata['searchinfo']['session_key'])
    return params


def main():
    logger.debug("Starting ITSI Outlier detection.")

    out_metadata = {}
    out_metadata['inspector'] = {'messages': []}

    # Phase 0: getinfo exchange
    metadata, body = read_chunk(sys.stdin, logger)
    # Don't run in preview.
    if metadata.get('preview', False):
        write_chunk(sys.stdout, {'finished': True}, '')
        sys.exit(0)

    args = str(metadata['searchinfo']['args'])

    params = parse_args(
        args=args, in_metadata=metadata, out_metadata=out_metadata, logger=logger)
    params['logger'] = logger  # Using logger from the module to be passed along to utils.
    params['out_metadata'] = out_metadata

    if not is_feature_enabled('itsi-at-outlier-removal', params['session_key']):
        logger.error("itsioutlier command is not enabled.")
        sys.exit(1)

    params['out_metadata']['finished'] = False
    fields_list = ['policy_key', 'itsi_service_id', 'itsi_kpi_id', 'alert_value', '_time']
    if params['entity_level_thresholds']:
        fields_list = fields_list + ['entity_key', 'entity_title']
    params['out_metadata']['required_fields'] = fields_list
    params['out_metadata']['type'] = 'reporting'
    write_chunk(sys.stdout, params['out_metadata'], '')
    params['out_metadata'].pop('type', None)
    params['out_metadata'].pop('required_fields', None)
    gather_input_data(params, logger, fields_list)
    kpidict = params['kpidict']

    for itsi_service_id in kpidict:
        params['kpi'] = {
            'service_id': itsi_service_id,
            'service_data': {}
        }
        # kpidict: {'service-id': {'kpi-id': {'_time': [0....N], 'alert_value': [0....N], 'itsi_kpi_id': [0....N],
        # 'itsi_service_id':[0...N], 'policy_key': [0.....N]}}}
        for itsi_kpi_id in kpidict[itsi_service_id]:
            params['kpi']['kpi_id'] = itsi_kpi_id
            if not read_chunk(sys.stdin, logger):
                break
            data = {}
            if params['entity_level_thresholds']:
                list_entity_keys = kpidict[itsi_service_id][itsi_kpi_id].keys()
                entity_key = ""
                for key_from_list in list_entity_keys:
                    entity_key = key_from_list
                data = kpidict[itsi_service_id][itsi_kpi_id][entity_key]

            else:
                data = kpidict[itsi_service_id][itsi_kpi_id]
            # data is a dictionary of field - list pairs
            policy_keys = data['policy_key']
            alert_values = data['alert_value']
            time_stamps = data['_time']
            # Create policy_chunks as array of tuples:
            # example:
            #     [('178.64064691379593', '1664820000.0', False), ('179.75162587638422', '1664820060.0', False),...]
            policy_chunks = collections.OrderedDict()
            # Build policy chunks for outlier detection
            for x in range(len(policy_keys)):
                key = policy_keys[x]
                # Create a tuple entry as (alert_value, _time, is_outler, upper_bound, lower_bound)
                entry = (alert_values[x], time_stamps[x], False, 0, 0)
                if key in policy_chunks:
                    policy_chunks[key].append(entry)
                else:
                    policy_chunks[key] = []
                    policy_chunks[key].append(entry)

            # Perform the min dataset check
            valid_policy_chunks = {}
            for policy in policy_chunks.keys():
                if len(policy_chunks[policy]) < MIN_DATASET_LEN:
                    log_and_warn(
                        metadata=out_metadata, logger=logger,
                        msg='Not enough data to detect outliers for policy block %s of %s, %s ' %
                            (key, itsi_service_id, itsi_kpi_id))
                else:
                    valid_policy_chunks[policy] = policy_chunks[policy]
            # Detect outliers only on valid policy chunks
            policy_outlier_map = detect_outliers(params, valid_policy_chunks)

            # prepare for generating output
            params['out_metadata']['finished'] = False
            fields_list = ['policy_key']
            fields_list = fields_list + ['itsi_service_id', 'itsi_kpi_id', 'alert_value', '_time', 'is_outlier', 'lower_bound', 'upper_bound']
            params['kpi']['writer'] = csv.DictWriter(
                params['outbuf'], fieldnames=fields_list, dialect='excel', extrasaction='ignore')
            params['kpi']['writer'].writeheader()
            # write output to buffer
            # If show outliers only is set, policy_outlier_map has outliers for valid chunks
            # else, policy chunks has both valid and invalid chunks, with invalid chunks default is_outlier set to False.
            data = policy_outlier_map if params['show_outliers_only'] else policy_chunks
            lines = []
            for policy_key, val_tuples in data.items():
                if policy_key in valid_policy_chunks:
                    # Use val_tuples from valid policy chunks if available
                    # else use val_tuples from policy_chunks
                    val_tuples = valid_policy_chunks[policy_key]
                for entry in val_tuples:
                    if params['remove'] and entry[2]:
                        # Remove outliers from the output
                        continue
                    line = {
                        'policy_key': policy_key,
                        'itsi_service_id': params['kpi']['service_id'],
                        'itsi_kpi_id': params['kpi']['kpi_id'],
                        'alert_value': entry[0],
                        '_time': entry[1],
                        'is_outlier': entry[2],
                        'lower_bound': entry[3],
                        'upper_bound': entry[4],
                    }
                    lines.append(line)
            # output the results
            time_sorted_lines = sorted(lines, key=lambda ll: ll['_time'])
            params['kpi']['writer'].writerows(time_sorted_lines)
            write_chunk(
                sys.stdout, params['out_metadata'], params['outbuf'].getvalue())

    ret = read_chunk(sys.stdin, logger)
    if ret:
        write_chunk(sys.stdout, {"finished": True}, '')

    logger.debug("Finished ITSI outlier detection.")


if __name__ == "__main__":
    main()
