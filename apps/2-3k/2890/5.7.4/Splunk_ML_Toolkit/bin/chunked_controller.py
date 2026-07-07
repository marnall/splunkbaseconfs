#!/usr/bin/env python
# Copyright (C) 2015-2019 Splunk Inc. All Rights Reserved.
import csv
import importlib
import time
from io import StringIO

from decimal import Decimal, InvalidOperation

import pandas as pd
from decimal import Decimal
import cexc
from util.base_util import match_field_globs
from util.param_util import missing_keys_in_dict
from util.telemetry_util import log_sourcetype_inference

logger = cexc.get_logger(__name__)
messages = cexc.get_messages_logger()


# We don't want the sourcetype inference data to be logged too many times
# per search in order to limit the amount of data sent to the telemetry server.
_MAX_NUM_SOURCETYPE_LOGGED = 10


class ChunkedController(object):
    """The controller connects CEXC commands to ML-SPL processors.

    - abstracting our interaction with the CEXC protocol and calling command
    - converting CSVs to pandas DataFrames
    - initializing and calling the processor's process method
    - notifying rest end point after a model is saved
    """

    def __init__(self, getinfo, controller_options):
        """Set a variety of attributes on self, call initializer methods.

        Args:
            getinfo (dict): getinfo metadata
            controller_options (dict): controller options passed from caller
        """
        # Attributes
        self._csv_parse_time = 0.0
        self._csv_render_time = 0.0
        # Total size in bytes of CSV input received across all chunks
        self._csv_input_bytes = 0
        self._chunk_count = 0
        self._csv_input_rows = 0
        self._processor_process_time = 0.0
        self._load_data_time = 0.0

        # Number of times the sourcetype inference info has been logged for this search.
        self._num_sourcetype_logged = 0

        # Check required searchinfo fields
        required_searchinfo_fields = ('sid', 'splunkd_uri', 'session_key', 'app', 'username')

        missing_keys = missing_keys_in_dict(required_searchinfo_fields, getinfo['searchinfo'])
        if missing_keys:
            logger.debug(
                'searchinfo in getinfo missing the following keys: %s', ', '.join(missing_keys)
            )
            raise RuntimeError('Protocol error has occurred while instantiating the search')

        # Parse options
        self.getinfo, self.controller_options, process_options = self.split_options(
            controller_options, getinfo
        )

        # Store process_options for later use (e.g., for CDTSM converter logic)
        self.process_options = process_options

        # Create our own searchinfo context with the information we need to pass to subsequent functions.
        searchinfo = {k: self.getinfo['searchinfo'][k] for k in required_searchinfo_fields}

        # initializer methods
        self.processor = self.initialize_processor(
            self.controller_options['processor'], process_options, searchinfo
        )
        self.resource_limits = self.get_resource_limits(self.processor)

        self.body = None

    @staticmethod
    def split_options(options, getinfo):
        """Split apart controller and processor options.

        Args:
            options (dict): controller options
            getinfo (dict): getinfo metadata

        Returns:
            getinfo (dict): the get info dictionary passed to controller
            controller_options (dict): the controller options to be used
            process_options (dict): the process options to pass to the processor
        """
        # Default value
        controller_options = {}
        controller_options['use_processor_output'] = options.pop('apply', True)
        controller_options['processor'] = options.pop('processor')
        if 'model_name' in options:
            controller_options['model_name'] = options.get('model_name')
        if 'namespace' in options:
            controller_options['namespace'] = options.get('namespace')

        # Construct process option
        process_options = options
        process_options['tmp_dir'] = getinfo['searchinfo']['dispatch_dir']
        if (
            controller_options['processor'] == 'ApplyProcessor'
            or controller_options['processor'] == 'ApplyOnnxProcessor'
        ):
            process_options['dispatch_dir'] = getinfo['searchinfo']['dispatch_dir']
        return getinfo, controller_options, process_options

    @staticmethod
    def initialize_processor(processor_name, process_options, searchinfo):
        """Import and initialize a processor.

        Processors are stored in ./bin/processors/
        The processors all inherit from the BaseProcessor class.

        Args:
            processor_name (str): processor name
            process_options (dict): process options
            searchinfo (dict): information required for search

        Returns:
            processor (object): initialized processor
        """
        try:
            processor_module = importlib.import_module('processors.{}'.format(processor_name))
            processor_class = getattr(processor_module, processor_name)
        except AttributeError:
            logger.debug('Failed to import ML-SPL processor "%s"' % processor_name)
            raise RuntimeError('Failed to import ML-SPL processor.')

        try:
            processor = processor_class(process_options, searchinfo)
        except Exception as e:
            cexc.log_traceback()
            logger.debug(
                'Error while initializing processor "%s": %s' % (processor_name, str(e))
            )
            raise RuntimeError(str(e))
        return processor

    @staticmethod
    def parse_relevant_fields(sio, relevant_fields):
        """Get relevant fields from processor & parse them from StringIO to dataframe.

        Args:
            sio (StringIO): buffer
            relevant_fields (list): list of field names

        Returns:
            df (dataframe): dataframe loaded from input data buffer
        """
        dict_reader = csv.DictReader(sio)
        input_fields = dict_reader.fieldnames
        fields_to_parse = match_field_globs(input_fields, relevant_fields)
        sio.seek(0)
        return pd.read_csv(sio, usecols=[str(f) for f in fields_to_parse])

    def get_required_fields(self):
        """Fetch required fields from processor's relevant fields.

        Required fields are sent back during the getinfo exchange. This is how
        Splunk knows which fields will be needed by our command and is akin
        to setting required fields with the SPL fields command.

        Returns:
            required_fields (list): list of required fields
        """
        return self.processor.get_relevant_fields()

    @staticmethod
    def get_resource_limits(processor):
        """Fetch resource limits from the processor.

        Args:
            processor (object): initialized processor

        Returns:
            resource_limits (dict): resource limits with keys such as
                max_memory_usage
        """
        try:
            resource_limits = processor.resource_limits
        except AttributeError:
            processor_str = processor.__class__.__name__
            logger.debug(
                'No resource limits were loaded for ML-SPL processor "%s"' % processor_str
            )
            resource_limits = None
        return resource_limits

    def load_data(self, body):
        """Load fields from search results into a DataFrame.

        In addition to literally converting the body into a data frame, note that
        the processor also receives the dataframe here.

        Args:
            body (str): csv body chunk from CEXC process
        """

        def safe_decimal(x):
            try:
                x = x.strip()
                return Decimal(x) if x else None
            except (InvalidOperation, AttributeError):
                return x

        load_data_t0 = time.perf_counter()
        self.body = body

        if len(body) != 0:
            sio = StringIO(body)

            with cexc.Timer() as csv_t:
                if self.controller_options['use_processor_output']:
                    # Check if this is CDTSM route (ApplyPredictAIProcessor)
                    if self.controller_options.get('processor') == 'ApplyPredictAIProcessor':
                        # For CDTSM, apply Decimal converter to all time series columns
                        converters = {}
                        if (
                            'params' in self.process_options
                            and 'fields_to_forecast' in self.process_options['params']
                        ):
                            # Get forecast columns (comma-separated string)
                            fields_to_forecast = self.process_options['params'][
                                'fields_to_forecast'
                            ]

                            # Get time_field (default to '_time')
                            time_field = self.process_options['params'].get(
                                'time_field', '_time'
                            )

                            # Handle wildcard (*) - expand to all columns except time_field and __ prefixed
                            if fields_to_forecast.strip() == '*':
                                # Read CSV header to get all column names
                                dict_reader = csv.DictReader(sio)
                                all_columns = dict_reader.fieldnames or []
                                sio.seek(0)  # Reset for later read

                                # Filter out time_field and columns starting with "__"
                                forecast_columns = [
                                    col
                                    for col in all_columns
                                    if col != time_field and not col.startswith('__')
                                ]
                                logger.debug(
                                    f"CDTSM: Expanded wildcard '*' to columns: {forecast_columns} "
                                    f"(excluded time_field:'{time_field}' and '__' prefixed fields)"
                                )
                            else:
                                forecast_columns = [
                                    col.strip() for col in fields_to_forecast.split(',')
                                ]

                            # Build converters dict for all forecast columns
                            converters = {
                                col: lambda x: safe_decimal(x) for col in forecast_columns
                            }
                            logger.debug(
                                f"CDTSM: Applying Decimal converters to columns: {forecast_columns}"
                            )

                        with cexc.Timer() as converter_read_t:
                            df = pd.read_csv(sio, converters=converters)
                        logger.info(
                            "CDTSM: read_csv with Decimal converters completed in %.6f seconds "
                            "(rows=%d, columns=%d, converter_columns=%d)",
                            converter_read_t.interval,
                            len(df),
                            len(df.columns),
                            len(converters),
                        )

                    else:
                        # For normal apply routes, just read CSV without converters
                        df = pd.read_csv(sio)
                else:
                    relevant_fields = self.get_required_fields()
                    df = self.parse_relevant_fields(sio, relevant_fields)
            self._csv_parse_time += csv_t.interval
            # Track total CSV input size in bytes across chunks
            self._csv_input_bytes += len(body)
            self._chunk_count += 1
            self._csv_input_rows += len(df)
            logger.debug(
                'chunk body=%d bytes, rows=%d, columns=%d, csv_read_time=%f',
                len(body),
                len(df),
                len(df.columns),
                csv_t.interval,
            )
            if self._num_sourcetype_logged < _MAX_NUM_SOURCETYPE_LOGGED:
                if log_sourcetype_inference(df, row_idx=-1):
                    self._num_sourcetype_logged += 1
        else:
            df = pd.DataFrame()
        self.processor.receive_input(df)
        load_data_elapsed = time.perf_counter() - load_data_t0
        self._load_data_time += load_data_elapsed
        logger.info(
            "ChunkedController: load_data completed in %.6f seconds "
            "(chunks=%d, rows=%d, input_bytes=%d, cumulative_load_data_time=%.6f, "
            "cumulative_csv_parse_time=%.6f)",
            load_data_elapsed,
            self._chunk_count,
            self._csv_input_rows,
            self._csv_input_bytes,
            self._load_data_time,
            self._csv_parse_time,
        )

    def execute(self):
        """Call the processor's process method."""
        with cexc.Timer() as processor_t:
            self.processor.process()
        self._processor_process_time += processor_t.interval
        logger.info(
            "ChunkedController: processor '%s' processed accumulated chunks in %.6f seconds "
            "(chunks=%d, rows=%d, input_bytes=%d, cumulative_processor_time=%.6f, "
            "cumulative_load_data_time=%.6f, cumulative_csv_parse_time=%.6f)",
            self.processor.__class__.__name__,
            processor_t.interval,
            self._chunk_count,
            self._csv_input_rows,
            self._csv_input_bytes,
            self._processor_process_time,
            self._load_data_time,
            self._csv_parse_time,
        )

    def output_results(self):
        """Get processor's output and convert to CSV string if do_apply.

        If do_apply is set to false, then the body will not be converted.

        Returns:
            body (str): a CSV data payload for CEXC
        """
        with cexc.Timer() as csv_t:
            if self.controller_options['use_processor_output']:
                body = self.processor.get_output().to_csv(index=False)
            else:
                body = self.body
        self._csv_render_time += csv_t.interval
        return body

    def finalize(self):
        """Save model and notify REST endpoint about new lookup."""
        if "model_name" in self.controller_options:
            self.processor.save_model()
