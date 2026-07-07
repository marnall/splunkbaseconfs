#!/usr/bin/env python
# Copyright (C) 2015-2019 Splunk Inc. All Rights Reserved.
from exec_anaconda import exec_anaconda_or_die

exec_anaconda_or_die()
import cexc
from cexc import BaseChunkHandler, CommandType

from util.param_util import parse_args, parse_namespace_model_name, parse_cdtsm_by_columns
from util import command_util
from util.mlspl_loader import MLSPLConf
from util.search_util import add_distributed_search_info
from util.telemetry_util import (
    log_uuid,
    log_apply_time,
    log_apply_container_time,
    Timer,
    log_experiment_details,
    log_model_id,
)
from util.telemetry_sagemaker_util import log_sagemaker_apply
from util.telemetry_cdtsm_util import log_cdtsm_apply, log_cdtsm_apply_time
from sagemaker_int.constants import SAGEMAKER, MODEL_ALGO_NAME
from util.dsdl_container_loader import ContainerConf
from dsdl.docker_util import read_container_hpa_enabled
from ai_commander.ai_commander_util import AICommanderUtil
from util.telemetry_vertex_util import log_vertex_apply
from vertex_int.constants import VERTEX, VERTEX_MODEL_ALGO_NAME

from chunked_controller import ChunkedController

logger = cexc.get_logger('apply')
messages = cexc.get_messages_logger()


def _cdtsm_is_anomaly_mode(mode_param):
    """True if mode is anomaly (or legacy anomaly_detection)."""
    m = str(mode_param or "forecast").strip().lower()
    return m in ("anomaly", "anomaly_detection")


def _cdtsm_spl_args_indicate_anomaly_mode(args, raw_args=None):
    """Return True if mode=anomaly (or legacy mode=anomaly_detection) appears in CDTSM SPL."""
    for tok in args or []:
        if isinstance(tok, str) and tok.startswith("mode="):
            val = tok.split("=", 1)[1].strip().strip('"').strip("'")
            if _cdtsm_is_anomaly_mode(val):
                return True
    if raw_args:
        for i, tok in enumerate(raw_args):
            if tok == "mode" and i + 2 < len(raw_args) and raw_args[i + 1] == "=":
                val = raw_args[i + 2].strip().strip('"').strip("'")
                if _cdtsm_is_anomaly_mode(val):
                    return True
    return False


def _cdtsm_metric_fields_usage_suffix(is_anomaly):
    """Mode-appropriate CDTSM syntax hint (forecast vs anomaly)."""
    if is_anomaly:
        return (
            "Usage: | apply CDTSM <field1> <field2> ... [BY <split_col> | BY <col1>, <col2>] mode=anomaly "
            "[time_field=_time] [context_length=...] [detection_length=...]"
        )
    return "Usage: | apply CDTSM <field1> <field2> ... [BY <split_col> | BY <col1>, <col2>] [time_field=_time] [forecast_k=10]"


def _cdtsm_wildcard_rejection_message(is_anomaly):
    """User-facing error when '*' is used for metric fields (mode-specific usage)."""
    label = "fields_to_detect_anomaly" if is_anomaly else "fields_to_forecast"
    return (
        f"CDTSM does not support wildcard '*' for {label}. "
        f"Please specify explicit field names. {_cdtsm_metric_fields_usage_suffix(is_anomaly)}"
    )


def _cdtsm_is_by_keyword_token(raw_args_list, idx):
    """Return True if the raw_args token at ``idx`` is the standalone ``BY`` keyword.

    Excludes ``by=value`` (single token) and ``by`` followed by ``=`` (separate
    tokens, i.e. the ``by = value`` form), both of which are valid key=value
    forms handled elsewhere. Only the bare ``BY`` keyword (case-insensitive)
    used to introduce grouping columns is flagged here.
    """
    if idx < 0 or idx >= len(raw_args_list):
        return False
    tok = raw_args_list[idx]
    if not isinstance(tok, str):
        return False
    if tok.strip().lower() != 'by':
        return False
    if idx + 1 < len(raw_args_list):
        nxt = raw_args_list[idx + 1]
        if isinstance(nxt, str) and nxt.startswith('='):
            return False
    return True


def _cdtsm_raise_by_after_params_error(args, raw_args):
    """Raise a mode-specific error when ``BY`` is placed after key=value params.

    The CDTSM positional syntax requires ``BY`` to immediately follow the
    metric field name(s). When users write e.g. ``apply CDTSM cpu mode=anomaly
    BY host``, the BY clause is silently ignored by the generic Splunk arg
    parser; surface this as a clear error instead.
    """
    is_anomaly = _cdtsm_spl_args_indicate_anomaly_mode(args, raw_args)
    fields_label = "fields_to_detect" if is_anomaly else "fields_to_forecast"
    raise RuntimeError(
        f"CDTSM: BY fields should follow {fields_label}. "
        "Place the BY clause immediately after the metric field name(s), "
        "before any key=value parameters. "
    )


def _cdtsm_raise_by_unquoted_multi_field_error():
    """Raise an error when multiple BY fields are passed without double quotes.

    Splunk's argv splits on whitespace so ``BY host city`` (or ``BY host,
    city``) loses the grouping intent — the second column gets misclassified
    as a metric. Require users to quote multi-field BY values, e.g.
    ``BY "host,city"`` or ``BY "host, city"``.
    """
    raise RuntimeError(
        "CDTSM: Multiple group by fields should be enclosed within double quotes. "
    )


def _get_cdtsm_algo_from_apply_command(apply_cmd):
    try:
        return apply_cmd.controller.processor.algo
    except AttributeError:
        return None


def _log_cdtsm_apply_phase_timing_summary(apply_cmd, total_time):
    try:
        if not getattr(apply_cmd, 'controller_options', {}).get('is_ctsm', False):
            return

        controller = getattr(apply_cmd, 'controller', None)
        if controller is None:
            return

        algo = _get_cdtsm_algo_from_apply_command(apply_cmd)
        if algo is not None and hasattr(algo, 'get_cdtsm_apply_timing_summary'):
            phase_timings = algo.get_cdtsm_apply_timing_summary()
        else:
            phase_timings = {}

        csv_render_time = float(getattr(controller, '_csv_render_time', 0.0) or 0.0)
        csv_parse_time = float(getattr(controller, '_csv_parse_time', 0.0) or 0.0)
        load_data_time = float(getattr(controller, '_load_data_time', 0.0) or 0.0)
        # CPU-time CEXC counters preserved for backwards compatibility with
        # the existing summary line below. The 8-phase wall-clock breakdown
        # further down uses ``_read_wall_time``/``_write_wall_time`` instead
        # so each phase reflects real wall-clock seconds.
        cexc_read_time = float(getattr(apply_cmd, '_read_time', 0.0) or 0.0)
        cexc_write_time = float(getattr(apply_cmd, '_write_time', 0.0) or 0.0)
        chunking_time = cexc_read_time + cexc_write_time
        materialization_time = (
            float(phase_timings.get('materialization', 0.0) or 0.0)
            + csv_parse_time
            + csv_render_time
        )

        logger.info(
            "CDTSM apply final timing summary - chunks=%d, rows=%d, input_bytes=%d, "
            "chunking=%.6fs, load_data=%.6fs, materialization=%.6fs, preprocessing=%.6fs, "
            "api=%.6fs, postprocessing=%.6fs, processor=%.6fs, total=%.6fs",
            int(getattr(controller, '_chunk_count', 0) or 0),
            int(getattr(controller, '_csv_input_rows', 0) or 0),
            int(getattr(controller, '_csv_input_bytes', 0) or 0),
            chunking_time,
            load_data_time,
            materialization_time,
            float(phase_timings.get('preprocessing', 0.0) or 0.0),
            float(phase_timings.get('api', 0.0) or 0.0),
            float(phase_timings.get('postprocessing', 0.0) or 0.0),
            float(getattr(controller, '_processor_process_time', 0.0) or 0.0),
            float(total_time),
        )

        # User-facing wall-clock phase breakdown. Every phase below uses
        # ``time.perf_counter()``-based wall-clock timing (either directly,
        # or via wall-clock counters added in ``cexc/__init__.py`` and
        # ``chunked_controller.py``), so the phases are mutually exclusive
        # wall-clock intervals that sum to ``total_time`` within a tiny
        # residual (microseconds × N chunks for the inter-iteration Python
        # loop overhead inside ``BaseChunkHandler.run``).
        #
        # In execution order:
        #
        #   1. setup               One-time getinfo handler call: argument
        #                          parsing, ``ChunkedController`` construction
        #                          (which builds ``ApplyPredictAIProcessor``
        #                          and ``PredictAI``), ``mlspl.conf`` reads,
        #                          required-field resolution. Measured by
        #                          wrapping ``self.setup()`` on the getinfo
        #                          chunk with ``perf_counter`` in
        #                          ``ApplyCommand.handler``.
        #   2. data_loading        Wall time of all CEXC stdin reads
        #                          (``_read_wall_time`` — includes pipe-
        #                          blocking time between chunks) plus
        #                          ``controller._load_data_time`` (per-chunk
        #                          CSV parse + DataFrame ingest).
        #   3. input_assembly      ``ApplyPredictAIProcessor.process``:
        #                          ``pd.concat`` of buffered input chunks +
        #                          full-frame field validation.
        #   4. preprocessing       Time conversions, fill_null, validations,
        #                          and multi-resolution context calculation
        #                          (algo's ``preprocessing`` + per-payload
        #                          ``materialization`` buckets).
        #   5. inference           Wall-clock HTTP round-trips to the CDTSM
        #                          model service (includes network wait —
        #                          this is the only place we attribute it).
        #   6. postprocessing      API response demux + per-group/per-column
        #                          ``run_postprocessing`` module + threshold/
        #                          score column assembly.
        #   7. output_preparation  Final BY group collation, output dataframe
        #                          construction, timestamp finalization,
        #                          outbound CSV render (``to_csv`` plus
        #                          anything else inside ``get_output_body``,
        #                          measured by wrapping that call with
        #                          ``perf_counter``), and CEXC stdout write
        #                          wall time (``_write_wall_time`` — includes
        #                          pipe-flush blocking time).
        #   8. processor_teardown  Post-apply ``gc.collect`` to reclaim
        #                          intermediate frames before returning to
        #                          the CEXC loop.
        algo_preprocessing = float(phase_timings.get('preprocessing', 0.0) or 0.0)
        algo_materialization = float(phase_timings.get('materialization', 0.0) or 0.0)
        algo_api = float(phase_timings.get('api', 0.0) or 0.0)
        algo_postprocessing = float(phase_timings.get('postprocessing', 0.0) or 0.0)
        algo_output_preparation = float(phase_timings.get('output_preparation', 0.0) or 0.0)
        algo_input_assembly = float(phase_timings.get('input_assembly', 0.0) or 0.0)
        algo_processor_teardown = float(phase_timings.get('processor_teardown', 0.0) or 0.0)
        setup_time = float(getattr(apply_cmd, '_cdtsm_setup_time', 0.0) or 0.0)
        cexc_read_wall_time = float(getattr(apply_cmd, '_read_wall_time', 0.0) or 0.0)
        cexc_write_wall_time = float(getattr(apply_cmd, '_write_wall_time', 0.0) or 0.0)
        csv_output_wall_time = float(
            getattr(apply_cmd, '_cdtsm_csv_output_wall_time', 0.0) or 0.0
        )

        phase1_setup = setup_time
        phase2_data_loading = load_data_time + cexc_read_wall_time
        phase3_input_assembly = algo_input_assembly
        phase4_preprocessing = algo_preprocessing + algo_materialization
        phase5_inference = algo_api
        phase6_postprocessing = algo_postprocessing
        phase7_output_preparation = (
            algo_output_preparation + csv_output_wall_time + cexc_write_wall_time
        )
        phase8_processor_teardown = algo_processor_teardown

        accounted = (
            phase1_setup
            + phase2_data_loading
            + phase3_input_assembly
            + phase4_preprocessing
            + phase5_inference
            + phase6_postprocessing
            + phase7_output_preparation
            + phase8_processor_teardown
        )
        residual = max(0.0, float(total_time) - accounted)

        logger.info(
            "CDTSM apply phase breakdown (8 categories, wall-clock) - "
            "1.setup=%.4fs (one_time_getinfo_construction), "
            "2.data_loading=%.4fs (load_data=%.4fs + cexc_read_wall=%.4fs), "
            "3.input_assembly=%.4fs (chunk_concat + field_validation), "
            "4.preprocessing=%.4fs (algo_preprocessing=%.4fs + context_calc/materialization=%.4fs), "
            "5.inference=%.4fs (api_only), "
            "6.postprocessing=%.4fs (api_postprocess + run_postprocessing module), "
            "7.output_preparation=%.4fs (algo_output_prep=%.4fs + csv_output_wall=%.4fs + cexc_write_wall=%.4fs), "
            "8.processor_teardown=%.4fs (post_apply_gc), "
            "residual=%.4fs (inter_chunk_python_loop_overhead), total=%.4fs",
            phase1_setup,
            phase2_data_loading,
            load_data_time,
            cexc_read_wall_time,
            phase3_input_assembly,
            phase4_preprocessing,
            algo_preprocessing,
            algo_materialization,
            phase5_inference,
            phase6_postprocessing,
            phase7_output_preparation,
            algo_output_preparation,
            csv_output_wall_time,
            cexc_write_wall_time,
            phase8_processor_teardown,
            residual,
            float(total_time),
        )
    except Exception:
        logger.debug("CDTSM: failed to log final apply phase timing summary", exc_info=True)


class ApplyCommand(BaseChunkHandler):
    """ApplyCommand uses the ChunkedController & ApplyProcessor to make
    predictions."""

    @staticmethod
    def handle_arguments(getinfo):
        """Take the getinfo metadata and return controller_options.

        Args:
            getinfo (dict): getinfo metadata

        Returns:
            controller_options (dict): options to be sent to controller
        """

        raw_args = getinfo['searchinfo']['raw_args']
        args = getinfo['searchinfo']['args']

        # Known CDTSM parameter names for detecting params with spaces around '='
        ctsm_param_names = {
            'time_field',
            'forecast_k',
            'holdback',
            'by',
            'fields_to_forecast',
            'quantiles',
            'conf_interval',
            'show_input',
            'model_name',
            'mode',
            'method',
            'context_length',
            'detection_length',
            'detection_window_earliest',
            'detection_window_latest',
            'context_window_earliest',
            'context_window_latest',
            'stride',
            'quantile',
            'quantile_lower',
            'quantile_upper',
            'multiplier',
            'threshold_direction',
            'on_span',
            'off_span',
            'on_ratio',
            'off_ratio',
        }

        # Helper function to check if CDTSM-specific parameters are present
        def has_ctsm_params(raw_args_list):
            """Check if CDTSM-specific parameters are present in arguments.

            Handles both 'param=value' and 'param = value' (with spaces) syntax.
            """
            ctsm_params_prefixes = [
                'time_field=',
                'forecast_k=',
                'holdback=',
                'by=',
                'fields_to_forecast=',
                'quantiles=',
                'conf_interval=',
                'show_input=',
                'model_name=',
                'mode=',
                'method=',
                'context_length=',
                'detection_length=',
                'detection_window_earliest=',
                'detection_window_latest=',
                'context_window_earliest=',
                'context_window_latest=',
                'stride=',
                'quantile=',
                'quantile_lower=',
                'quantile_upper=',
                'multiplier=',
                'threshold_direction=',
                'on_span=',
                'off_span=',
                'on_ratio=',
                'off_ratio=',
            ]
            for i, arg in enumerate(raw_args_list):
                # Check for 'param=value' format
                if any(arg.startswith(param) for param in ctsm_params_prefixes):
                    return True
                # Check for 'param = value' format (param followed by '=' as next arg)
                if (
                    arg in ctsm_param_names
                    and i + 1 < len(raw_args_list)
                    and raw_args_list[i + 1].startswith('=')
                ):
                    return True
            return False

        # Helper function to check if an arg is a CDTSM parameter (handles spaces around '=')
        def is_ctsm_param_start(args_list, index):
            """Check if the arg at index is the start of a CDTSM parameter."""
            if index >= len(args_list):
                return False
            arg = args_list[index]
            # Check for 'param=value' format
            if '=' in arg:
                return True
            # Check for 'param = value' format (arg is a known param name and next is '=')
            if arg in ctsm_param_names:
                return True
            # Check if next arg is '=' (handles space before '=')
            if index + 1 < len(args_list) and args_list[index + 1] == '=':
                return True
            return False

        # Determine if first arg is "CDTSM" with indicators it's the algorithm (not a saved model)
        is_ctsm_first_arg = len(args) > 0 and args[0].upper() == 'CDTSM'
        has_ctsm_parameters = is_ctsm_first_arg and has_ctsm_params(raw_args)

        # Check if there are positional args after CDTSM (forecast fields)
        # Need to ensure args[1] is not a parameter name (handles 'param = value' with spaces)
        has_positional_fields = (
            is_ctsm_first_arg and len(args) > 1 and not is_ctsm_param_start(args, 1)
        )
        logger.info("Has positional fields: %s", has_positional_fields)
        # Check for new CDTSM syntax: apply CDTSM <col1> <col2> ... time_field=<field> [params]
        # OR check if first arg is "CDTSM" with CDTSM-specific parameters (not a saved model named CDTSM)
        if is_ctsm_first_arg and (has_positional_fields or has_ctsm_parameters):
            # CDTSM Algorithm Flow
            logger.info(
                "Detected CDTSM algorithm flow (positional fields or CDTSM-specific parameters present)"
            )

            # Check for new syntax with positional fields
            if has_positional_fields:
                # New CDTSM syntax: apply CDTSM <col1> <col2> ... time_field=<field>
                logger.info("Using new CDTSM syntax with positional forecast fields")

                known_param_names = {
                    'time_field',
                    'forecast_k',
                    'holdback',
                    'conf_interval',
                    'quantiles',
                    'show_input',
                    'fields_to_forecast',
                    'model_name',
                    'mode',
                    'method',
                    'context_length',
                    'detection_length',
                    'detection_window_earliest',
                    'detection_window_latest',
                    'context_window_earliest',
                    'context_window_latest',
                    'stride',
                    'quantile',
                    'quantile_lower',
                    'quantile_upper',
                    'multiplier',
                    'threshold_direction',
                    'on_span',
                    'off_span',
                    'on_ratio',
                    'off_ratio',
                }

                # Collect forecast columns (all positional args after CDTSM before key=value params).
                # Supports per-group runs: | apply CDTSM <metrics...> BY <split_col> [time_field=...]
                # (BY is matched case-insensitively.)
                forecast_cols = []
                by_positional = None
                key_value_start_idx = 1  # Start after "CDTSM"
                i = 1
                while i < len(args):
                    arg = args[i]
                    if '=' in arg:
                        key_value_start_idx = i
                        break
                    if arg in known_param_names or (i + 1 < len(args) and args[i + 1] == '='):
                        key_value_start_idx = i
                        break
                    if arg.lower() == 'by':
                        if by_positional is not None:
                            raise RuntimeError(
                                'CDTSM: duplicate BY clause is not supported. '
                                'Use one BY clause.'
                            )
                        if i + 1 >= len(args):
                            raise RuntimeError(
                                'CDTSM: BY requires a grouping column name. '
                                'Example: | apply CDTSM cpu BY city forecast_k=10'
                            )
                        next_arg = args[i + 1]
                        if next_arg.lower() == 'by':
                            raise RuntimeError(
                                'CDTSM: expected a column name after BY, not another BY.'
                            )
                        if next_arg == '*':
                            raise RuntimeError(
                                'CDTSM: wildcard "*" is not allowed as the BY grouping column.'
                            )
                        by_parts = parse_cdtsm_by_columns(next_arg)
                        if not by_parts:
                            raise RuntimeError(
                                'CDTSM: BY requires at least one grouping column name. '
                                'Example: | apply CDTSM cpu BY city forecast_k=10 '
                                'or | apply CDTSM cpu BY city, state forecast_k=10'
                            )
                        for bp in by_parts:
                            if bp == '*' or '*' in bp:
                                raise RuntimeError(
                                    'CDTSM: wildcard "*" is not allowed in BY grouping column names.'
                                )
                        # When the BY value resolves to multiple grouping columns,
                        # require the raw token to be wrapped in double quotes so
                        # the SPL parser preserves the user's intent (e.g.
                        # ``BY "host,city"``). Bare comma-separated tokens like
                        # ``BY host,city`` are ambiguous and easy to mistype, so
                        # reject them with a clear, actionable error.
                        if len(by_parts) > 1:
                            raw_by_value = raw_args[i + 1] if (i + 1) < len(raw_args) else ''
                            raw_stripped = raw_by_value.strip()
                            if not (
                                len(raw_stripped) >= 2
                                and raw_stripped[0] == '"'
                                and raw_stripped[-1] == '"'
                            ):
                                _cdtsm_raise_by_unquoted_multi_field_error()
                        by_positional = ", ".join(by_parts)
                        i += 2
                        # After consuming ``BY <value>``, the next token (if any)
                        # must be a key=value parameter or end-of-args. Any
                        # additional positional token here is the signature of
                        # an unquoted multi-field BY (e.g. ``BY host city`` or
                        # ``BY host, city``) — both cases are rejected uniformly
                        # so users learn to quote multi-field BY values.
                        if i < len(args):
                            next_after = args[i]
                            if (
                                '=' not in next_after
                                and next_after not in known_param_names
                                and not (i + 1 < len(args) and args[i + 1] == '=')
                                and next_after.lower() != 'by'
                            ):
                                _cdtsm_raise_by_unquoted_multi_field_error()
                        continue
                    if arg == '*':
                        raise RuntimeError(
                            _cdtsm_wildcard_rejection_message(
                                _cdtsm_spl_args_indicate_anomaly_mode(args, raw_args)
                            )
                        )
                    if ',' in arg:
                        raise RuntimeError(
                            f'CDTSM does not support comma-separated field names. '
                            f'Found "{arg}". Please use space-separated field names instead. '
                            f'{_cdtsm_metric_fields_usage_suffix(_cdtsm_spl_args_indicate_anomaly_mode(args, raw_args))}'
                        )
                    forecast_cols.append(arg)
                    i += 1
                else:
                    key_value_start_idx = len(args)

                if not forecast_cols:
                    raise RuntimeError(
                        'CDTSM syntax requires at least one field to forecast. '
                        'Usage: | apply CDTSM <col1> <col2> ... [BY <split_col> | BY <c1>, <c2>] '
                        '[time_field=<field>] [forecast_k=...]'
                    )

                # Parse remaining key=value parameters
                remaining_raw_args = (
                    raw_args[key_value_start_idx:]
                    if key_value_start_idx < len(raw_args)
                    else []
                )

                # A bare ``BY`` keyword inside the key=value tail means the
                # user placed the BY clause after a key=value parameter (e.g.
                # ``apply CDTSM cpu mode=anomaly BY host``). The generic SPL
                # parser would silently consume it as ``split_by`` and the BY
                # would never take effect — surface this as a clear, mode-
                # specific error so the misordering is caught up front.
                for ridx in range(len(remaining_raw_args)):
                    if _cdtsm_is_by_keyword_token(remaining_raw_args, ridx):
                        _cdtsm_raise_by_after_params_error(args, raw_args)

                raw_options = parse_args(remaining_raw_args)

                # Set CDTSM-specific options
                raw_options['namespace'] = None
                raw_options['model_name'] = None
                raw_options['algo_name'] = 'CDTSM'
                raw_options['is_ctsm'] = True

                # Add fields_to_forecast to params
                if 'params' not in raw_options:
                    raw_options['params'] = {}

                if 'model_name' not in raw_options.get('params', {}):
                    raw_options['params']['model_name'] = 'CDTSM'
                raw_options['params']['fields_to_forecast'] = ','.join(forecast_cols)

                # Set default time_field to _time if not provided
                if 'time_field' not in raw_options.get('params', {}):
                    raw_options['params']['time_field'] = '_time'

                if by_positional:
                    existing_by = raw_options['params'].get('by')
                    if existing_by is not None and str(existing_by).strip():
                        if parse_cdtsm_by_columns(
                            str(existing_by).strip()
                        ) != parse_cdtsm_by_columns(by_positional):
                            raise RuntimeError(
                                'CDTSM: the grouping column from BY conflicts with by=. '
                                f'Use only one (BY {by_positional} vs by={existing_by}).'
                            )
                    raw_options['params']['by'] = by_positional

                # Validate that user didn't also provide fields_to_forecast as param
                if any(arg.startswith('fields_to_forecast=') for arg in remaining_raw_args):
                    raise RuntimeError(
                        'Parameter "fields_to_forecast" should not be specified as key=value with new syntax. '
                        'Use: | apply CDTSM <col1> <col2> ... [time_field=<field>] [forecast_k=...] [quantiles=...]'
                    )

                logger.info(
                    f"Apply command invoked with new CDTSM syntax: "
                    f"time_field:{raw_options['params']['time_field']}, fields:{forecast_cols}"
                )
                runtime = ""
                is_timeseriesfm = False

            else:
                # CDTSM-specific parameters present but no positional fields
                # This means using "apply CDTSM <params>" where CDTSM params indicate algorithm usage
                logger.info(
                    "CDTSM-specific parameters detected without positional fields - treating as CDTSM algorithm"
                )

                # In the all-key=value form there are no positional metric
                # tokens at all, so a bare ``BY`` keyword anywhere after
                # ``CDTSM`` (e.g. ``apply CDTSM fields_to_forecast=cpu BY
                # host``) means the BY clause is mis-ordered. Reject with a
                # mode-specific error rather than silently consuming it via
                # the generic SPL ``split_by`` path.
                ctsm_tail = raw_args[1:]
                for ridx in range(len(ctsm_tail)):
                    if _cdtsm_is_by_keyword_token(ctsm_tail, ridx):
                        _cdtsm_raise_by_after_params_error(args, raw_args)

                # Parse all arguments starting from first (skip "CDTSM")
                raw_options = parse_args(raw_args[1:])
                raw_options['namespace'] = None
                raw_options['model_name'] = None
                raw_options['algo_name'] = 'CDTSM'
                raw_options['is_ctsm'] = True

                if 'params' not in raw_options:
                    raw_options['params'] = {}
                if 'model_name' not in raw_options['params']:
                    raw_options['params']['model_name'] = 'CDTSM'

                # Validate required CDTSM parameters
                if 'fields_to_forecast' not in raw_options.get('params', {}):
                    raise RuntimeError(
                        'CDTSM algorithm requires fields to forecast. '
                        'Use syntax: | apply CDTSM <col1> <col2> ... [time_field=<field>] [forecast_k=...] [quantiles=...]'
                    )

                # Reject wildcard and comma-separated fields_to_forecast
                fields_param = raw_options['params'].get('fields_to_forecast', '')
                if fields_param == '*' or '*' in fields_param.split(','):
                    _params = raw_options.get('params', {})
                    _mode = str(_params.get('mode', 'forecast')).strip().lower()
                    raise RuntimeError(
                        _cdtsm_wildcard_rejection_message(_cdtsm_is_anomaly_mode(_mode))
                    )
                if ',' in fields_param:
                    _params = raw_options.get('params', {})
                    _mode = str(_params.get('mode', 'forecast')).strip().lower()
                    _is_anomaly = _cdtsm_is_anomaly_mode(_mode)
                    _label = "fields_to_detect_anomaly" if _is_anomaly else "fields_to_forecast"
                    raise RuntimeError(
                        f'CDTSM does not support comma-separated field names in {_label} parameter. '
                        f'Please use space-separated positional arguments instead. '
                        f'{_cdtsm_metric_fields_usage_suffix(_is_anomaly)}'
                    )

                # Set default time_field to _time if not provided
                if 'time_field' not in raw_options.get('params', {}):
                    raw_options['params']['time_field'] = '_time'

                logger.info(
                    f"Apply command invoked with CDTSM algorithm (params present): "
                    f"time_field:{raw_options['params'].get('time_field')}, "
                    f"fields:{raw_options['params'].get('fields_to_forecast')}"
                )
                runtime = ""
                is_timeseriesfm = False

        # Check for model= parameter syntax and reject it
        elif any(v.startswith("model=") for v in raw_args):
            model_param = next(
                (v.split("=", 1)[1] for v in raw_args if v.startswith("model=")), None
            )
            raise RuntimeError(f'The "model=" parameter syntax is not supported. ')
        else:
            # Standard model-based apply: require first positional argument as model name
            if len(args) == 0:
                raise RuntimeError(
                    'First argument must be a saved model name or CDTSM. '
                    'Examples: | apply my_model OR | apply CDTSM cpu memory time_field=timestamp'
                )

            # Standard model-based apply
            first_arg = getinfo['searchinfo']['args'][0]
            is_timeseriesfm = first_arg.lower() == 'timeseriesfm'

            runtime = next(
                (
                    v.split("=", 1)[1]
                    for v in getinfo['searchinfo']['args']
                    if v.startswith("runtime=")
                ),
                "",
            )

            if is_timeseriesfm:
                # TimeSeriesFM: special handling without model name
                raw_options = parse_args(getinfo['searchinfo']['raw_args'][1:])
                raw_options['namespace'] = None
                raw_options['model_name'] = 'TimeSeriesFM'  # Use algorithm name as identifier
                raw_options['algo_name'] = 'TimeSeriesFM'
                raw_options['is_timeseriesfm'] = True

            elif (
                "onnx" in getinfo['searchinfo']['raw_args'][0]
                and getinfo['searchinfo']['raw_args'][0] != 'onnx'
            ):
                raw_options = parse_args(getinfo['searchinfo']['raw_args'][1:])
                (
                    raw_options['namespace'],
                    raw_options['model_name'],
                    raw_options['model_param_thresh'],
                    raw_options['model_param_activation'],
                ) = parse_namespace_model_name(getinfo['searchinfo']['args'][0])

            else:
                raw_options = parse_args(getinfo['searchinfo']['raw_args'][1:])
                (
                    raw_options['namespace'],
                    raw_options['model_name'],
                ) = parse_namespace_model_name(
                    getinfo['searchinfo']['args'][0], runtime=runtime
                )

        controller_options = ApplyCommand.handle_raw_options(raw_options, runtime)

        # Only log model details if not TimeSeriesFM or CDTSM
        is_ctsm = raw_options.get('is_ctsm', False)
        if not is_ctsm and not is_timeseriesfm:
            log_experiment_details(controller_options['model_name'])
            log_model_id(controller_options['model_name'])

        searchinfo = getinfo['searchinfo']
        getinfo['searchinfo'] = add_distributed_search_info(
            process_options=None, searchinfo=searchinfo
        )
        controller_options['mlspl_conf'] = MLSPLConf(getinfo['searchinfo'])
        return controller_options

    @staticmethod
    def handle_raw_options(raw_options, runtime=""):
        """Load command specific options.

        Args:
            raw_options (dict): raw options
            runtime (str): runtime parameter from SPL query

        Raises:
            RuntimeError

        Returns:
            raw_options (dict): modified raw_options
        """
        # Store runtime for telemetry logging
        raw_options['runtime'] = runtime.lower() if runtime else ""

        # Determine processor type based on model type and runtime
        if raw_options.get('is_ctsm', False):
            # CDTSM uses PredictAI processor (zero-shot forecasting)
            raw_options['processor'] = 'ApplyPredictAIProcessor'
            logger.info("Using ApplyPredictAIProcessor for CDTSM algorithm")
        elif raw_options.get('is_timeseriesfm', False):
            # TimeSeriesFM uses specialized processor (no model required)
            raw_options['processor'] = 'ApplyTimeSeriesFMProcessor'
            logger.info("Using ApplyTimeSeriesFMProcessor for TimeSeriesFM algorithm")
        elif runtime.lower() in SAGEMAKER:
            # SageMaker models use dedicated processor
            raw_options['processor'] = 'ApplySagemakerProcessor'
            logger.info(f"Using ApplySagemakerProcessor for SageMaker runtime: {runtime}")
        elif runtime.lower() in VERTEX:
            raw_options['processor'] = 'ApplyVertexProcessor'
            logger.info(f"Using ApplyVertexProcessor for Vertex runtime: {runtime}")
        elif raw_options.get('model_name') and raw_options['model_name'].endswith('.onnx'):
            # ONNX models
            raw_options['processor'] = 'ApplyOnnxProcessor'
        else:
            # Standard MLTK models
            raw_options['processor'] = 'ApplyProcessor'

        if 'args' in raw_options and not raw_options.get('is_ctsm', False):
            raise RuntimeError('Apply does not accept positional arguments.')
        return raw_options

    def _setup_watchdog(self):
        """Initialize and start watchdog"""
        resource_limits = getattr(self.controller, 'resource_limits', None) or {}
        memory_limit = resource_limits.get('max_memory_usage_mb') or 300
        self.watchdog = command_util.get_watchdog(time_limit=-1, memory_limit=memory_limit)
        self.watchdog.start()

    def setup(self):
        """Parse search string, choose processor, initialize controller.

        Returns:
            (dict): get info response (command type) and required fields. This
                response will be sent back to the CEXC process on the getinfo
                exchange (first chunk) to establish our execution type and
                required fields.
        """
        controller_options = self.handle_arguments(self.getinfo)
        self.controller = ChunkedController(self.getinfo, controller_options)

        # Store controller_options for telemetry logging
        self.controller_options = controller_options

        # Initialize container telemetry holder; populated after model is loaded for AITKContainer
        self._apply_container_telemetry = None

        exec_type = CommandType.STATEFUL

        required_fields = self.controller.get_required_fields()

        # For CDTSM, only keep the time field and raw time series columns in required_fields
        if self.controller_options.get('is_ctsm', False):
            ctsm_exec_type = CommandType.EVENTS
            filtered_fields = []
            params = controller_options.get('params', {})

            # Add time_field
            time_field = params.get('time_field', '_time')
            filtered_fields.append(time_field)

            # Add fields_to_forecast (raw time series columns)
            fields_to_forecast = params.get('fields_to_forecast', '')
            logger.debug(f"CDTSM: fields_to_forecast: {fields_to_forecast}")
            if fields_to_forecast:
                columns = [
                    col.strip().strip('"').strip("'")
                    for col in fields_to_forecast.split(',')
                    if col.strip()
                ]

                # Reject wildcard '*' - explicit field names are required
                if '*' in columns:
                    _mode = str(params.get('mode', 'forecast')).strip().lower()
                    raise RuntimeError(
                        _cdtsm_wildcard_rejection_message(_cdtsm_is_anomaly_mode(_mode))
                    )

                filtered_fields.extend(columns)

            for by_col in parse_cdtsm_by_columns(params.get('by')):
                if by_col and by_col not in filtered_fields:
                    filtered_fields.append(by_col)

            logger.debug(
                f"CDTSM: Filtered required_fields to only time series columns: {filtered_fields}"
            )

            logger.info(
                f"CDTSM: Filtered required_fields to only time series columns: {filtered_fields}"
            )
            required_fields = filtered_fields

            return {'type': ctsm_exec_type, 'required_fields': required_fields}

        # Set clear_required_fields for CDTSM to prevent Splunk from adding default fields
        result = {'type': exec_type, 'required_fields': required_fields}
        # result['clear_required_fields'] = True

        return result

    def get_output_body(self):
        """Collect output body from controller.

        Returns:
            (str): body
        """
        return self.controller.output_results()

    def handler(self, metadata, body):
        """Main handler we override from BaseChunkHandler.

        Handles the reading and writing of data to the CEXC process, and
        finishes negotiation of the termination of the process.

        Args:
            metadata (dict): metadata information
            body (str): data payload from CEXC

        Returns:
            (dict): metadata to be sent back to CEXC
            output_body (str): data payload to be sent back to CEXC
        """

        if command_util.should_early_return(metadata):
            return {}

        if command_util.is_getinfo_chunk(metadata):
            # Explicitly time the one-time getinfo setup so the CDTSM phase
            # summary in ``_log_cdtsm_apply_phase_timing_summary`` can attribute
            # controller/processor/algo construction + arg parsing time.
            # On slow filesystems (mlspl.conf reads, secrets lookup) this can
            # be multi-second and was otherwise invisible to all other timers.
            import time as _time

            _setup_t0 = _time.perf_counter()
            try:
                return self.setup()
            finally:
                self._cdtsm_setup_time = _time.perf_counter() - _setup_t0
        finished_flag = metadata.get('finished', False)

        if not self.watchdog:
            self._setup_watchdog()

        # Skip to next chunk if this chunk is empty
        if len(body) == 0:
            return {}

        # Load data, execute and collect results.

        if self.controller_options.get('is_ctsm', False):
            self.controller.load_data(body)

            if finished_flag:
                self.controller.execute()
                # Wall-clock timer around output body retrieval so the CDTSM
                # phase summary can attribute outbound CSV serialization
                # time (``to_csv``) under the ``output_preparation`` phase.
                # The CEXC controller's ``_csv_render_time`` is CPU-time only
                # and is not used by the wall-clock breakdown.
                import time as _time

                _csv_out_t0 = _time.perf_counter()
                try:
                    output_body = self.get_output_body()
                finally:
                    self._cdtsm_csv_output_wall_time = getattr(
                        self, '_cdtsm_csv_output_wall_time', 0.0
                    ) + (_time.perf_counter() - _csv_out_t0)
            else:
                output_body = None

            if finished_flag:
                # Gracefully terminate watchdog
                if self.watchdog.started:
                    self.watchdog.join()
        else:
            self.controller.load_data(body)
            self.controller.execute()
            output_body = self.controller.output_results()

            if finished_flag:
                # Gracefully terminate watchdog
                if self.watchdog.started:
                    self.watchdog.join()

            # Gather container telemetry after execution if this is an AITKContainer model
            try:
                algo_name = getattr(self.controller, 'algo_name', None) or getattr(
                    self.controller.processor, 'algo_name', None
                )
                if algo_name and 'AITKContainer' in str(algo_name):
                    searchinfo = self.getinfo['searchinfo']
                    model_name = self.controller_options.get('model_name')
                    stanza_name = model_name if model_name else "__dev__"
                    hpa_enabled = 0
                    container_id = None
                    cluster_type = None
                    auth_mode = None
                    min_replicas = None
                    max_replicas = None
                    min_cpu = None
                    max_cpu = None
                    min_memory = None
                    max_memory = None
                    try:
                        if model_name:
                            hpa_enabled = (
                                1 if read_container_hpa_enabled(searchinfo, model_name) else 0
                            )
                        container_conf = ContainerConf(searchinfo, "dsdl_container")
                        stanza = container_conf.get_stanza(stanza_name)
                        if not stanza and stanza_name != "__dev__":
                            stanza = container_conf.get_stanza("__dev__")
                        if stanza:
                            container_id = (stanza.get("id") or "").strip()
                            cluster_type = (stanza.get("cluster") or "").strip()
                            if cluster_type and cluster_type.lower() == "kubernetes":
                                try:
                                    conn_conf = ContainerConf(
                                        searchinfo, "container_connections"
                                    )
                                    conn_stanza = conn_conf.get_stanza(cluster_type)
                                    if conn_stanza:
                                        auth_mode = (conn_stanza.get("auth_mode") or "").strip()
                                except Exception:
                                    pass
                            if hpa_enabled:
                                min_replicas = (stanza.get("min_replicas") or "").strip()
                                max_replicas = (stanza.get("max_replicas") or "").strip()
                            min_cpu = (stanza.get("min_cpu") or "").strip()
                            max_cpu = (stanza.get("max_cpu") or "").strip()
                            min_memory = (stanza.get("min_memory") or "").strip()
                            max_memory = (stanza.get("max_memory") or "").strip()
                    except Exception:
                        pass
                    self._apply_container_telemetry = {
                        'hpa_enabled': hpa_enabled,
                        'container_id': container_id,
                        'cluster_type': cluster_type,
                        'auth_mode': auth_mode,
                        'min_replicas': min_replicas,
                        'max_replicas': max_replicas,
                        'min_cpu': min_cpu,
                        'max_cpu': max_cpu,
                        'min_memory': min_memory,
                        'max_memory': max_memory,
                        'model_name': model_name,
                    }
            except Exception:
                pass

        # Our final farewell
        return ({'finished': finished_flag}, output_body)


if __name__ == "__main__":
    logger.debug("Starting apply.py.")

    # Create ApplyCommand instance to access controller_options after execution
    apply_cmd = ApplyCommand(handler_data=BaseChunkHandler.DATA_RAW)

    with Timer() as t:
        apply_cmd.run()

    # Log standard apply time
    log_uuid()
    log_apply_time(t.interval)

    # Log SageMaker-specific telemetry and timing metrics if applicable
    if hasattr(apply_cmd, 'controller_options'):
        runtime = apply_cmd.controller_options.get('runtime', '')
        if runtime in SAGEMAKER:
            model_name = apply_cmd.controller_options.get('model_name', 'unknown')
            log_uuid()
            log_sagemaker_apply(model_name, MODEL_ALGO_NAME, t.interval)

            # Log detailed timing metrics from SageMaker invoker
            try:
                metrics = apply_cmd.controller.processor.invoke_metrics
                if metrics:
                    if 'error' in metrics:
                        logger.error(
                            f"endpoint=\"{metrics.get('endpoint', 'unknown')}\" "
                            f"batch_size={metrics.get('batch_size', 0)} "
                            f"chunks={metrics.get('total_chunks', 1)} "
                            f"api_calls={metrics.get('api_call_count', 0)} "
                            f"min_time={metrics.get('min_time', 0):.3f} "
                            f"max_time={metrics.get('max_time', 0):.3f} "
                            f"avg_time={metrics.get('avg_time', 0):.3f} "
                            f"total_time={metrics.get('total_time', 0):.3f} "
                            f"total_apply_time={t.interval:.3f} "
                            f"error=\"{metrics.get('error', 'unknown')}\""
                        )
                    else:
                        logger.info(
                            f"endpoint=\"{metrics.get('endpoint', 'unknown')}\" "
                            f"batch_size={metrics.get('batch_size', 0)} "
                            f"chunks={metrics.get('total_chunks', 1)} "
                            f"api_calls={metrics.get('api_call_count', 0)} "
                            f"min_time={metrics.get('min_time', 0):.3f} "
                            f"max_time={metrics.get('max_time', 0):.3f} "
                            f"avg_time={metrics.get('avg_time', 0):.3f} "
                            f"total_time={metrics.get('total_time', 0):.3f} "
                            f"total_apply_time={t.interval:.3f}"
                        )
            except (AttributeError, TypeError):
                pass  # No metrics available (non-SageMaker or early failure)
        elif runtime in VERTEX:
            model_name = apply_cmd.controller_options.get('model_name', 'unknown')
            log_uuid()
            log_vertex_apply(model_name, VERTEX_MODEL_ALGO_NAME, t.interval)

            try:
                metrics = apply_cmd.controller.processor.invoke_metrics
                if metrics:
                    if 'error' in metrics:
                        logger.error(
                            f"endpoint=\"{metrics.get('endpoint', 'unknown')}\" "
                            f"batch_size={metrics.get('batch_size', 0)} "
                            f"chunks={metrics.get('total_chunks', 1)} "
                            f"api_calls={metrics.get('api_call_count', 0)} "
                            f"min_time={metrics.get('min_time', 0):.3f} "
                            f"max_time={metrics.get('max_time', 0):.3f} "
                            f"avg_time={metrics.get('avg_time', 0):.3f} "
                            f"total_time={metrics.get('total_time', 0):.3f} "
                            f"total_apply_time={t.interval:.3f} "
                            f"error=\"{metrics.get('error', 'unknown')}\""
                        )
                    else:
                        logger.info(
                            f"endpoint=\"{metrics.get('endpoint', 'unknown')}\" "
                            f"batch_size={metrics.get('batch_size', 0)} "
                            f"chunks={metrics.get('total_chunks', 1)} "
                            f"api_calls={metrics.get('api_call_count', 0)} "
                            f"min_time={metrics.get('min_time', 0):.3f} "
                            f"max_time={metrics.get('max_time', 0):.3f} "
                            f"avg_time={metrics.get('avg_time', 0):.3f} "
                            f"total_time={metrics.get('total_time', 0):.3f} "
                            f"total_apply_time={t.interval:.3f}"
                        )
            except (AttributeError, TypeError):
                pass  # No metrics available (non-Vertex or early failure)

    # Log container-related apply telemetry if applicable
    if (
        hasattr(apply_cmd, '_apply_container_telemetry')
        and apply_cmd._apply_container_telemetry
    ):
        t_data = apply_cmd._apply_container_telemetry
        csv_size = (
            getattr(apply_cmd.controller, '_csv_input_bytes', None)
            if hasattr(apply_cmd, 'controller')
            else None
        )
        # Get the full algo_name from controller (e.g., AITKContainer.binary_nn_classifier)
        full_algo_name = getattr(apply_cmd.controller, 'algo_name', None) or 'AITKContainer'
        log_apply_container_time(
            t.interval,
            t_data.get('hpa_enabled', 0),
            full_algo_name,
            t_data.get('container_id'),
            t_data.get('cluster_type'),
            t_data.get('auth_mode'),
            t_data.get('min_replicas'),
            t_data.get('max_replicas'),
            t_data.get('min_cpu'),
            t_data.get('max_cpu'),
            t_data.get('min_memory'),
            t_data.get('max_memory'),
            csv_size,
            t_data.get('model_name'),
        )

    if hasattr(apply_cmd, 'controller_options'):
        is_ctsm = apply_cmd.controller_options.get('is_ctsm', False)
        if is_ctsm:
            # Log only the total CDTSM apply execution time here
            # Stats (rows, columns, resolution) are logged in PredictAI.apply() for better access to internal state
            try:
                _algo = _get_cdtsm_algo_from_apply_command(apply_cmd)
                _is_groupby_flag = 1 if getattr(_algo, "forecast_by", None) else 0
                log_cdtsm_apply_time(total_time=t.interval, is_groupby=_is_groupby_flag)
            except Exception:
                pass  # Time logging failed, continue gracefully
            _log_cdtsm_apply_phase_timing_summary(apply_cmd, t.interval)

    logger.debug("Exiting gracefully. Byee!!")
