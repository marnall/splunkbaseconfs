# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
import csv

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path
from ITOA.setup_logging import logger
from ITOA.splunk_search_chunk_protocol import SearchChunkProtocol
from ITOA.itoa_common import is_string_numeric, get_csv_dict_writer, get_log_message_for_exception


class FillDataGapsBackfillCommand(SearchChunkProtocol):
    """
    This custom search command is specifically used to fill gaps for KPI with "last available value",
    while backfilling the KPI. We need a custom search command to perform filling of gaps, coz
    streamstats SPL command would not stick in missing bucket or entity results. While backfilling
    KPI, we may encounter missing bucket or entity results. To fill those gaps (generate results for
    entities and/or timestamps/buckets) with "last reported value", for entity/service aggregate,
    we use this command.
    NOTE: Filling Gaps for KPI with "Custom Value" means overriding N/A values for KPI, with
    a custom value, which doesn't involve adding missing entity or timestamp events. Therefore,
    we don't use this custom search command in that scenario. setseverityfields command handles that
    case.
    """
    def __init__(self):
        hand_shake_output_data = {
            'type': 'reporting'
        }
        super(FillDataGapsBackfillCommand, self).__init__(output_meta_data=hand_shake_output_data, logger=logger)

        # entity_split_field arg is needed when KPI has "split by entity" option enabled, i.e.
        # kpi generates entity results. kpi_type arg is not required in that case.
        self.entity_split_field = self.args.get('entity_split_field')
        self.alert_period = self.args.get('alert_period')
        self.is_service_aggregate = False

        # arg kpi_type is needed for "service_aggregate" KPI (no entity results)
        if self.args.get('kpi_type') == 'service_aggregate':
            self.is_service_aggregate = True
        self.cached_results = {}
        self.last_timestamp = None
        self.existing_entity_results = set([])
        self.entity_results_to_add = None

        if self.is_service_aggregate:
            self.expected_fieldnames = ['_time', 'alert_value']
        else:
            self.expected_fieldnames = ['_time', 'alert_value', self.entity_split_field]

    def validate_search_args(self):
        """
        Validate search arguments
        @rtype: tuple
        @return: return boolean flag and messages
        """
        entity_split_field = self.args.get('entity_split_field')
        alert_period = self.args.get('alert_period')
        kpi_type = self.args.get('kpi_type')
        msgs = []

        if not kpi_type and not entity_split_field and not alert_period:
            message = ('Invalid options passed to "fillgapsbackfill" command; must have alert period and '
                       'kpi type or entity split field.')
            logger.error(message)

            msgs.append(message)
        if not kpi_type:
            # Validate entity_split_field
            if not entity_split_field:
                logger.error(message)
                message = '`entity_split_field` argument not provided to "fillgapsbackfill" search command.'
                msgs.append(message)

        if not alert_period:
            message = '`alert_period` argument not provided to "fillgapsbackfill" search command.'
            logger.error(message)
            msgs.append(message)

        try:
            int(alert_period)
        except (ValueError, TypeError):
            message = '`alert_period` argument provided to "fillgapsbackfill" search command, is not integer.'
            logger.error(message)
            msgs.append(message)

        if len(msgs) > 0:
            return False, msgs
        else:
            return True, msgs

    def pre_processing(self):
        """
        Override function
        Convert alert period to integer from string
        @return:
        """
        self.alert_period = int(self.alert_period) * 60  # convert to seconds

    def run(self, metadata, reader, chunk):
        """
        Override function
        Read the chunk data and, override N/A values and fill gaps.
        @return:
        """
        out_metadata = {'finished': metadata.get('finished', False)}

        if reader.fieldnames:
            if self.is_service_aggregate:
                self._cache_and_fill_aggregate_results(self.writer, reader)
            else:
                self._cache_and_fill_entity_results(self.writer, reader)
                # if it is the last chunk, then check for missing entity results at current timestamp.
                if metadata.get('finished', False):
                    self.entity_results_to_add = set(self.cached_results.keys()).difference(self.existing_entity_results)
                    if self.entity_results_to_add:
                        out_metadata = {'finished': False}

        self.write_chunk(out_metadata, self.output_buf.getvalue())

    def post_processing(self):
        """
        Perform post processing.
        @return:
        """
        # check for missing entities at final timestamp in results. If there are any, fill them with cached entity results.
        if self.entity_results_to_add:
            output_buf = self.get_string_buffer()
            writer_last_bucket = get_csv_dict_writer(output_buf, fieldnames=self.expected_fieldnames)
            self._write_missing_entity_results(writer_last_bucket)

            self.write_chunk({'finished': True}, output_buf.getvalue())

    def _write_missing_bucket_results(self, writer, curr_timestamp):
        """
        Fill cached results for buckets or timestamps, for which results do not
        exist. Compares last result's timestamp and current result's timestamp,
        to find if there are missing results for buckets in between, as per
        the alert period of KPI.
        @param writer: csv writer object
        @param curr_timestamp: timestamp of current results
        @return:
        """
        new_time_bucket = int(self.last_timestamp) + self.alert_period
        if new_time_bucket >= curr_timestamp:
            return
        logger.debug('Data gaps found between timestamp %s and timestamp %s. Filling results for missing timestamps.' %
                     (self.last_timestamp, curr_timestamp))

        while new_time_bucket < curr_timestamp:
            if self.is_service_aggregate:
                aggregate_result_to_add = {
                    'alert_value': self.cached_results['alert_value'],
                    '_time': new_time_bucket
                }
                writer.writerow(aggregate_result_to_add)
            else:
                for entity_title in self.cached_results:
                    entity_to_add = {
                        'alert_value': self.cached_results[entity_title]['alert_value'],
                        '_time': new_time_bucket,
                        self.entity_split_field: entity_title
                    }
                    writer.writerow(entity_to_add)
            new_time_bucket += self.alert_period

    def _write_missing_entity_results(self, writer):
        """
        Fill missing entity results for current timestamp/bucket using cached results.
        @param writer: csv writer object
        @return:
        """
        for entity_title in self.entity_results_to_add:
            entity_to_add = {
                'alert_value': self.cached_results[entity_title]['alert_value'],
                '_time': self.last_timestamp,
                self.entity_split_field: entity_title
            }
            writer.writerow(entity_to_add)

    def _cache_and_fill_entity_results(self, writer, reader):
        """
        Read entity results, cache them and fill missing entity and
        bucket/timestamp results.
        @param writer: csv writer object
        @param reader: csv DictReader object
        @return:
        """
        for result in reader:
            entity_name = result.get(self.entity_split_field)
            curr_timestamp = result.get('_time')

            if self.last_timestamp is None or curr_timestamp == self.last_timestamp:
                # collect entity results for a specific timestamp or bucket.
                self.existing_entity_results.add(entity_name)
            else:
                # check the difference between last entity results and cached entity results, and write the missing
                # entity results in last timestamp
                self.entity_results_to_add = set(self.cached_results.keys()).difference(self.existing_entity_results)
                logger.debug('Data gaps found for entities="%s", at timestamp="%s"' %
                             (list(self.entity_results_to_add), self.last_timestamp))
                self._write_missing_entity_results(writer)
                self._write_missing_bucket_results(writer, int(curr_timestamp))
                self.existing_entity_results = set([entity_name])

            # cache latest alert value, if it is not a gap or N/A
            if entity_name in self.cached_results:
                if result.get('alert_value') and result.get('alert_value').strip() != 'N/A':
                    logger.debug('New alert value found for entity="%s" at timestamp="%s". Updating cache with alert '
                                 'value.' % (entity_name, curr_timestamp))
                    self.cached_results[entity_name] = {
                        'alert_value': result.get('alert_value'),
                        '_time': curr_timestamp
                    }
                else:
                    logger.debug('Data gap found for entity="%s" at timestamp="%s". Filling data gap with cached alert '
                                 'value of entity.' % (entity_name, curr_timestamp))
                    result['alert_value'] = self.cached_results[entity_name]['alert_value']
            else:
                logger.debug('New entity="%s" found at timestamp="%s". Adding entity\'s alert value to the cache.' %
                             (entity_name, curr_timestamp))
                self.cached_results[entity_name] = {
                    'alert_value': result.get('alert_value'),
                    '_time': curr_timestamp
                }

            self.last_timestamp = curr_timestamp
            writer.writerow(result)

    def _cache_and_fill_aggregate_results(self, writer, reader):
        """
        If KPI has only service aggregate results, read service aggregate results, cache
        them and, override N/A aggregate and missing bucket results.
        @param writer: csv writer object
        @param reader: csv DictReader object
        @return:
        """
        for result in reader:
            curr_timestamp = result.get('_time')
            if self.last_timestamp is not None and self.cached_results:
                self._write_missing_bucket_results(writer, int(curr_timestamp))

            if result.get('alert_value') and result.get('alert_value').strip() != 'N/A':
                logger.debug('New "service_aggregate" alert value found at timestamp="%s". Updating cache with alert '
                             'value.' % curr_timestamp)
                self.cached_results['alert_value'] = result.get('alert_value')
                self.cached_results['_time'] = curr_timestamp
            else:
                if self.cached_results:
                    logger.debug('"service_aggregate" data gap found at timestamp="%s". Filling data gap with cached alert '
                                 'value.' % curr_timestamp)
                    result['alert_value'] = self.cached_results['alert_value']

            self.last_timestamp = curr_timestamp
            writer.writerow(result)


if __name__ == "__main__":
    fill_gaps_command = None
    try:
        fill_gaps_command = FillDataGapsBackfillCommand()
        fill_gaps_command.execute()
    except Exception as e:
        logger.exception(e)
        if fill_gaps_command is not None:
            fill_gaps_command.exit_with_error({'finished': True}, [get_log_message_for_exception(e)])
        else:
            raise
