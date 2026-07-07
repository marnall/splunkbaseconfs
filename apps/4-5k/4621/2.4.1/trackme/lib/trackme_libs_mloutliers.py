#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Standard library imports
import os
import sys
import json
import time
import re
import logging

# Networking and URL handling imports
import requests
from urllib.parse import urlencode
import urllib3

# Disable insecure request warnings for urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append lib lib
sys.path.append(os.path.join(splunkhome, "etc", "apps", "trackme", "lib"))
from trackme_libs_logging import get_effective_logger

# import trackme libs
from trackme_libs import run_splunk_search

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces, escape_backslash

# import trackme filter engine (Virtual Groups DSL) for tenant-level entity scoping
from trackme_filter_engine import apply_filter, validate_filter

# logging:
# To avoid overriding logging destination of callers, the libs will not set on purpose any logging definition
# and rely on callers themselves


_RELATIVE_TOKEN_RE = re.compile(r"^-(\d+)([smhdw])$")
_RELATIVE_TOKEN_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


def _relative_token_to_seconds(value):
    """Convert a Splunk-style relative-time token (e.g. ``"-30d"`` / ``"-12h"``)
    to the corresponding offset in seconds.

    Returns ``None`` if ``value`` is not a relative-time token. Single source of
    truth for both :func:`parse_user_datetime` and
    :func:`get_training_window_cutoff_epoch` so they cannot drift.
    """
    m = _RELATIVE_TOKEN_RE.match(str(value).strip())
    if not m:
        return None
    return int(m.group(1)) * _RELATIVE_TOKEN_UNIT_SECONDS[m.group(2)]


def parse_user_datetime(value):
    """Parse a user-provided datetime spec into an integer epoch second.

    Accepted forms:
      - integer epoch seconds (or its string form, e.g. "1769644800")
      - ISO date strings: "YYYY-MM-DD", "YYYY-MM-DDTHH:MM", "YYYY-MM-DDTHH:MM:SS"
      - the literal "now"
      - relative tokens "-Ns" / "-Nm" / "-Nh" / "-Nd" / "-Nw" (e.g. "-30d")

    ISO strings are interpreted as local-time naive datetimes (matching the
    pre-existing parsing in the period-exclusion REST handler).

    Raises ValueError on parse failure.
    """
    s = str(value).strip()
    if not s:
        raise ValueError("empty datetime value")

    # Plain integer epoch seconds (or a string of an int).
    try:
        return int(s)
    except (TypeError, ValueError):
        pass

    # Literal "now".
    if s.lower() == "now":
        return int(time.time())

    # Relative tokens like "-30d", "-12h", "-2w".
    seconds = _relative_token_to_seconds(s)
    if seconds is not None:
        return int(time.time()) - seconds

    # ISO date / datetime forms (naive — matches existing handler behaviour).
    from datetime import datetime as _dt
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return int(round(_dt.strptime(s, fmt).timestamp()))
        except ValueError:
            continue

    raise ValueError(
        f"cannot parse '{value}' — accepted: epoch seconds, "
        "ISO 'YYYY-MM-DD' / 'YYYY-MM-DDTHH:MM' / 'YYYY-MM-DDTHH:MM:SS', "
        "'now', or relative '-Nd' / '-Nh' / '-Nm' / '-Ns' / '-Nw'"
    )


def get_training_window_cutoff_epoch(period_calculation):
    """Return the epoch second below which a period_exclusion's ``latest`` is
    considered out of the model's training window.

    ``period_calculation`` is a Splunk-style relative-time expression — supports
    arbitrary digit counts and the full set of time units (``-30d``, ``-90d``,
    ``-7d``, ``-365d``, ``-12h``, ``-60m``, ``-2w``, ``-30s``). Falls back to a
    30-day window if the value is not a relative-time token. Note that absolute
    epochs and ISO dates are intentionally rejected here even though
    :func:`parse_user_datetime` accepts them — ``period_calculation`` is
    semantically a relative window, never an absolute timestamp.

    The trainer (in :func:`train_mlmodel`) and the REST API endpoint
    (``post_outliers_manage_model_period_exclusion``) both call this helper so
    the rejection rule cannot drift between the two.
    """
    seconds = _relative_token_to_seconds(period_calculation)
    if seconds is not None:
        return int(time.time()) - seconds
    # Conservative default: 30 days.
    return int(time.time()) - 30 * 86400


# Default values applied when a vtenant record is missing the new 2.3.22
# scoping keys (the tenant exists but the schema migration hasn't run yet,
# or the tenant predates the migration). Defaults preserve the pre-2.3.22
# behaviour: all priorities are eligible, no filter expression.
_OUTLIERS_DEFAULT_PRIORITY_FILTER = "critical,high,medium,low"
_OUTLIERS_DEFAULT_FILTER_EXPRESSION = ""


def _parse_priority_filter_csv(value):
    """Parse the comma-separated priority filter into a normalised set of
    priority strings. Returns None when the filter is effectively empty
    (treated as 'match all priorities')."""
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    items = {p.strip().lower() for p in raw.split(",") if p.strip()}
    if not items:
        return None
    return items


def is_outliers_eligible_for_entity(vtenant_account, entity_dict):
    """Decide whether an entity is in scope for ML Outliers detection given
    the tenant's `tenant_mloutliers_priority_filter` and
    `tenant_mloutliers_filter_expression` settings (introduced in 2.3.22).

    Args:
        vtenant_account: dict, the tenant's KV record (must contain
            tenant_-prefixed keys; pre-migration tenants may be missing
            the keys entirely, in which case migration-equivalent defaults
            are applied — preserves prior behaviour exactly).
        entity_dict: dict with at least one of `priority`, `tags`, `labels`,
            `data_index`, `data_sourcetype`, `object`. Missing fields are
            treated as empty by the filter engine (CONDITION evaluates False
            for them, which is the correct semantics).

    Returns:
        (eligible: bool, reason: str). `reason` is one of:
        - ""                     when the entity is eligible
        - "priority_filter"      when the entity's priority is excluded
        - "filter_expression"    when the entity does not match the expression
        - "filter_expression_invalid" when the configured expression is
          unparseable (fail-closed — treats the tenant as having an
          impossibly-narrow filter; the admin must fix the expression).

    Read-time fallback: when a vtenant key is absent (pre-migration window),
    we apply the migrated default. Empty string is also treated as "no
    override" for the filter expression.
    """
    if not isinstance(vtenant_account, dict):
        # Defensive: caller passed something unexpected. Fail open
        # rather than block all training silently.
        return True, ""

    # `vtenant_account` is the conf-derived dict returned by
    # `trackme_vtenant_account()` — keys are UNPREFIXED (`mloutliers`,
    # `mloutliers_dsm`, matching trackme_vtenants.conf and
    # vtenant_account_default in collections_data.py). The tenant_-prefixed
    # names live on the KV record (kv_trackme_virtual_tenants) and are
    # consumed by the describe layer, not by the runtime training path.
    priority_filter_raw = vtenant_account.get(
        "mloutliers_priority_filter", _OUTLIERS_DEFAULT_PRIORITY_FILTER
    )
    if priority_filter_raw is None:
        priority_filter_raw = _OUTLIERS_DEFAULT_PRIORITY_FILTER
    priority_filter = _parse_priority_filter_csv(priority_filter_raw)

    if priority_filter is not None:
        entity_priority = str(entity_dict.get("priority", "") or "").strip().lower()
        if entity_priority and entity_priority not in priority_filter:
            return False, "priority_filter"

    filter_expression = vtenant_account.get(
        "mloutliers_filter_expression", _OUTLIERS_DEFAULT_FILTER_EXPRESSION
    )
    if filter_expression is None:
        filter_expression = _OUTLIERS_DEFAULT_FILTER_EXPRESSION
    filter_expression = str(filter_expression).strip()

    if filter_expression:
        # validate_filter returns None when the expression is parseable, an
        # error string otherwise. apply_filter alone cannot distinguish
        # "unparseable" from "legitimate non-match" because it is fail-closed
        # by design (returns [] in both cases). Calling validate_filter first
        # gives operators a distinct skip reason for misconfigured tenants.
        if validate_filter(filter_expression) is not None:
            return False, "filter_expression_invalid"
        try:
            matched = apply_filter([entity_dict], filter_expression)
        except Exception:
            matched = []
        if not matched:
            return False, "filter_expression"

    return True, ""


# ──────────────────────────────────────────────────────────────────────────────
# AI Agent automated-action eligibility — shared by ML Advisor and every
# Components Advisor batch (Feed Lifecycle / FLX Threshold / FQM / Component
# Health).
#
# Lives in this module to share the underlying parser plumbing with
# ``is_outliers_eligible_for_entity`` above; both functions read CSV priority
# lists and TrackMe filter DSL expressions from ``vtenant_account`` and call
# the same ``apply_filter`` / ``validate_filter`` from ``trackme_filter_engine``.
# A future cleanup may move this into a dedicated ``trackme_libs_ai_filters``
# module — kept here for now to avoid an unnecessary import-graph change on a
# feature PR.
# ──────────────────────────────────────────────────────────────────────────────

_AI_AUTOMATED_DEFAULT_PRIORITY_FILTER = "critical,high"
_AI_AUTOMATED_DEFAULT_FILTER_EXPRESSION = ""


def get_ai_automated_priority_filter(vtenant_account):
    """Return the effective AI automated-action priority filter for the
    tenant as a comma-separated string.

    Falls back to ``critical,high`` when the field is absent / empty / None.
    The SPL-side ``| where priority IN (...)`` clause MUST be derived from
    this exact value so the cheap pre-filter and the Python post-filter
    agree on the priority set — any divergence would let entities through
    that the user wanted skipped (or skip entities the user wanted
    included).
    """
    if not isinstance(vtenant_account, dict):
        return _AI_AUTOMATED_DEFAULT_PRIORITY_FILTER
    raw = vtenant_account.get(
        "ai_automated_priority_filter", _AI_AUTOMATED_DEFAULT_PRIORITY_FILTER
    )
    if raw is None:
        return _AI_AUTOMATED_DEFAULT_PRIORITY_FILTER
    raw = str(raw).strip()
    if not raw:
        # Empty CSV is the engine's "match-all" sentinel — preserve it so
        # the SPL pre-filter clause is omitted (no ``| where priority IN``).
        return ""
    return raw


def get_ai_automated_filter_expression(vtenant_account):
    """Return the tenant's AI automated-action filter expression (raw
    string). Empty string when unset or absent."""
    if not isinstance(vtenant_account, dict):
        return _AI_AUTOMATED_DEFAULT_FILTER_EXPRESSION
    raw = vtenant_account.get(
        "ai_automated_filter_expression", _AI_AUTOMATED_DEFAULT_FILTER_EXPRESSION
    )
    if raw is None:
        return _AI_AUTOMATED_DEFAULT_FILTER_EXPRESSION
    return str(raw).strip()


def is_ai_automated_eligible_for_entity(vtenant_account, entity_dict):
    """Decide whether an entity is in scope for an automated AI Advisor
    action (ML Advisor batch OR any Components Advisor batch) given the
    tenant's ``ai_automated_priority_filter`` and
    ``ai_automated_filter_expression`` settings.

    This is the SINGLE shared gate for all five automated batches. The
    cheap SPL pre-filter (``| where priority IN (...)``) handles the
    priority dimension at search time; this function re-checks priority
    (in case the SPL clause was bypassed in a future refactor) AND adds
    the filter-expression DSL on top.

    Args:
        vtenant_account: dict, the tenant's KV record (UCC-derived). When
            the AI automated keys are absent, defaults are applied
            (``critical,high`` for priority, ``""`` for expression) — see
            ``get_ai_automated_priority_filter`` / ``..._filter_expression``.
        entity_dict: dict with at least one of `priority`, `tags`, `labels`,
            `data_index`, `data_sourcetype`, `object`, `component`. Missing
            fields are treated as empty by the filter engine.

    Returns:
        (eligible: bool, reason: str). ``reason`` is one of:
        - ""                            when the entity is eligible
        - "priority_filter"             entity priority excluded by CSV
        - "filter_expression"           entity does not match the expression
        - "filter_expression_invalid"   tenant ships an unparseable expression
          (fail-closed — every entity is skipped with this reason; the
          per-cycle summary log surfaces the count so an operator can fix
          the misconfiguration. We do NOT silently include all entities
          and burn LLM tokens against the operator's intent.)

    Interactive launches (AI Assistant consent card or direct REST call)
    must NOT call this function — the filter gates the scheduled batches
    only. The on-demand REST handlers always honour the analyst's chosen
    entity, regardless of priority or filter expression.
    """
    if not isinstance(vtenant_account, dict):
        # Defensive: caller passed something unexpected. Fail open
        # rather than block all batches silently.
        return True, ""

    priority_filter_raw = get_ai_automated_priority_filter(vtenant_account)
    priority_filter = _parse_priority_filter_csv(priority_filter_raw)

    if priority_filter is not None:
        entity_priority = str(entity_dict.get("priority", "") or "").strip().lower()
        if entity_priority and entity_priority not in priority_filter:
            return False, "priority_filter"

    filter_expression = get_ai_automated_filter_expression(vtenant_account)

    if filter_expression:
        # ``validate_filter`` returns None when the expression is parseable,
        # an error string otherwise. ``apply_filter`` alone cannot
        # distinguish "unparseable" from "legitimate non-match" because it
        # is fail-closed by design (returns [] in both cases). Calling
        # ``validate_filter`` first gives operators a distinct skip reason
        # for misconfigured tenants.
        if validate_filter(filter_expression) is not None:
            return False, "filter_expression_invalid"
        try:
            matched = apply_filter([entity_dict], filter_expression)
        except Exception:
            matched = []
        if not matched:
            return False, "filter_expression"

    return True, ""


def get_effective_outliers_volume_kpi(vtenant_account, component, global_default):
    """Return the effective volume KPI metric for ML Outliers training,
    layering the tenant-level override on top of the global default.

    The tenant override (`tenant_mloutliers_volume_kpi`, introduced in
    2.3.22) applies to dsm and dhm only — flx, fqm and wlk ignore it and
    always use the global default. An empty/missing tenant value also
    falls through to the global default.
    """
    if component not in ("dsm", "dhm"):
        return global_default
    if not isinstance(vtenant_account, dict):
        return global_default
    # Conf-derived dict — unprefixed key. See is_outliers_eligible_for_entity
    # for the prefix-vs-no-prefix rationale.
    tenant_value = vtenant_account.get("mloutliers_volume_kpi", "") or ""
    tenant_value = str(tenant_value).strip()
    if not tenant_value:
        return global_default
    return tenant_value


def train_mlmodel(
    service,
    splunkd_uri,
    session_key,
    username,
    tenant_id,
    component,
    object_value,
    key_value,
    tenant_trackme_metric_idx,
    mode,
    entities_outliers,
    entity_outlier,
    entity_outlier_dict,
    model_json_def,
):

    get_effective_logger().debug(f"starting function train_mlmodel")

    # Define an header for requests authenticated communications with splunkd
    header = {
        "Authorization": "Splunk %s" % session_key,
        "Content-Type": "application/json",
    }

    # if mode = live
    if mode == "live":
        try:
            is_disabled = entity_outlier_dict["is_disabled"]
            kpi_metric = entity_outlier_dict["kpi_metric"]
            kpi_span = entity_outlier_dict["kpi_span"]
            method_calculation = entity_outlier_dict["method_calculation"]
            density_lowerthreshold = entity_outlier_dict["density_lowerthreshold"]
            density_upperthreshold = entity_outlier_dict["density_upperthreshold"]
            alert_lower_breached = entity_outlier_dict["alert_lower_breached"]
            alert_upper_breached = entity_outlier_dict["alert_upper_breached"]
            period_calculation = entity_outlier_dict["period_calculation"]
            time_factor = entity_outlier_dict["time_factor"]
            perc_min_lowerbound_deviation = entity_outlier_dict[
                "perc_min_lowerbound_deviation"
            ]
            perc_min_upperbound_deviation = entity_outlier_dict[
                "perc_min_upperbound_deviation"
            ]
            min_value_for_lowerbound_breached = entity_outlier_dict.get(
                "min_value_for_lowerbound_breached", 0
            )
            min_value_for_upperbound_breached = entity_outlier_dict.get(
                "min_value_for_upperbound_breached", 0
            )
            static_lower_threshold = entity_outlier_dict.get(
                "static_lower_threshold", None
            )
            static_upper_threshold = entity_outlier_dict.get(
                "static_upper_threshold", None
            )
            period_exclusions = entity_outlier_dict.get("period_exclusions", [])
            # ensure period_exclusions is a list, otherwise set it to an empty list
            if not isinstance(period_exclusions, list):
                period_exclusions = []

            # get the algorithm
            algorithm = entity_outlier_dict.get("algorithm", "DensityFunction")

            # get the boundaries_extraction_macro
            boundaries_extraction_macro = entity_outlier_dict.get(
                "boundaries_extraction_macro", "splk_outliers_extract_boundaries"
            )

            # optional extra parameters for the fit command
            fit_extra_parameters = entity_outlier_dict.get("fit_extra_parameters", None)

            # optional extra parameters for the apply command
            apply_extra_parameters = entity_outlier_dict.get(
                "apply_extra_parameters", None
            )

            # optional period_calculation_latest
            period_calculation_latest = entity_outlier_dict.get(
                "period_calculation_latest", "now"
            )

            rules_summary = {
                "is_disabled": is_disabled,
                "kpi_metric": kpi_metric,
                "kpi_span": kpi_span,
                "method_calculation": method_calculation,
                "density_lowerthreshold": density_lowerthreshold,
                "density_upperthreshold": density_upperthreshold,
                "period_calculation": period_calculation,
                "period_calculation_latest": period_calculation_latest,
                "time_factor": time_factor,
                "perc_min_lowerbound_deviation": perc_min_lowerbound_deviation,
                "perc_min_upperbound_deviation": perc_min_upperbound_deviation,
                "alert_lower_breached": alert_lower_breached,
                "alert_upper_breached": alert_upper_breached,
                "min_value_for_lowerbound_breached": min_value_for_lowerbound_breached,
                "min_value_for_upperbound_breached": min_value_for_upperbound_breached,
                "static_lower_threshold": static_lower_threshold,
                "static_upper_threshold": static_upper_threshold,
                "period_exclusions": period_exclusions,
                "algorithm": algorithm,
                "boundaries_extraction_macro": boundaries_extraction_macro,
                "fit_extra_parameters": fit_extra_parameters,
                "apply_extra_parameters": apply_extra_parameters,
            }

            get_effective_logger().debug(
                f'Processing outliers entity="{entity_outlier}", rules_summary="{rules_summary}"'
            )

        except Exception as e:
            msg = f'tenant_id="{tenant_id}", component="{component}", object="{object_value}", entity_outlier="{entity_outlier}", failed to extract one or more expected settings from the entity, is this record corrupted? Exception="{str(e)}"'
            get_effective_logger().error(msg)
            raise Exception(msg)

    elif mode == "simulation":

        # log debug
        get_effective_logger().debug("mode is simulation")

        # log debug
        get_effective_logger().debug(f"model_json_def={model_json_def}")

        # load the model definition as a dict
        try:
            model_json_def = json.loads(model_json_def)
            # log debug
            get_effective_logger().debug(
                f'successfully loaded model_json_def="{json.dumps(model_json_def, indent=4)}"'
            )
        except Exception as e:
            msg = f'failed to load the submitted model_json_def="{model_json_def}" with exception="{e}"'
            get_effective_logger().error(msg)
            raise Exception(msg)

        # get definitions from the model_json_def
        is_disabled = model_json_def["is_disabled"]
        kpi_metric = model_json_def["kpi_metric"]
        kpi_span = model_json_def["kpi_span"]
        method_calculation = model_json_def["method_calculation"]
        density_lowerthreshold = model_json_def["density_lowerthreshold"]
        density_upperthreshold = model_json_def["density_upperthreshold"]
        alert_lower_breached = model_json_def["alert_lower_breached"]
        alert_upper_breached = model_json_def["alert_upper_breached"]
        period_calculation = model_json_def["period_calculation"]
        # optional
        period_calculation_latest = model_json_def.get(
            "period_calculation_latest", "now"
        )
        time_factor = model_json_def["time_factor"]
        perc_min_lowerbound_deviation = model_json_def["perc_min_lowerbound_deviation"]
        perc_min_upperbound_deviation = model_json_def["perc_min_upperbound_deviation"]
        min_value_for_lowerbound_breached = model_json_def.get(
            "min_value_for_lowerbound_breached", 0
        )
        min_value_for_upperbound_breached = model_json_def.get(
            "min_value_for_upperbound_breached", 0
        )
        static_lower_threshold = model_json_def.get("static_lower_threshold", None)
        static_upper_threshold = model_json_def.get("static_upper_threshold", None)

        # period exclusions is an exception and is defined at the level of the model KVstore record
        period_exclusions = entity_outlier_dict.get("period_exclusions", [])
        # ensure period_exclusions is a list, otherwise set it to an empty list
        if not isinstance(period_exclusions, list):
            period_exclusions = []

        # get the algorithm
        algorithm = entity_outlier_dict.get("algorithm", "DensityFunction")

        # get the boundaries_extraction_macro
        boundaries_extraction_macro = entity_outlier_dict.get(
            "boundaries_extraction_macro", "splk_outliers_extract_boundaries"
        )

        # optional extra parameters for the fit command
        fit_extra_parameters = entity_outlier_dict.get("fit_extra_parameters", None)

        # optional extra parameters for the apply command
        apply_extra_parameters = entity_outlier_dict.get("apply_extra_parameters", None)

        rules_summary = {
            "is_disabled": is_disabled,
            "kpi_metric": kpi_metric,
            "kpi_span": kpi_span,
            "method_calculation": method_calculation,
            "density_lowerthreshold": density_lowerthreshold,
            "density_upperthreshold": density_upperthreshold,
            "period_calculation": period_calculation,
            "period_calculation_latest": period_calculation_latest,
            "time_factor": time_factor,
            "perc_min_lowerbound_deviation": perc_min_lowerbound_deviation,
            "perc_min_upperbound_deviation": perc_min_upperbound_deviation,
            "alert_lower_breached": alert_lower_breached,
            "alert_upper_breached": alert_upper_breached,
            "min_value_for_lowerbound_breached": min_value_for_lowerbound_breached,
            "min_value_for_upperbound_breached": min_value_for_upperbound_breached,
            "static_lower_threshold": static_lower_threshold,
            "static_upper_threshold": static_upper_threshold,
            "period_exclusions": period_exclusions,
            "algorithm": algorithm,
            "boundaries_extraction_macro": boundaries_extraction_macro,
            "fit_extra_parameters": fit_extra_parameters,
            "apply_extra_parameters": apply_extra_parameters,
        }

        get_effective_logger().debug(
            f'Processing outliers entity="{entity_outlier}", rules_summary="{rules_summary}"'
        )

    #
    # Proceed
    #

    # Define the Splunk searches
    ml_model_gen_search = None
    ml_model_render_search = None

    # Set the densityFunction threshold parameters
    if float(density_lowerthreshold) > 0 and float(density_upperthreshold) > 0:
        density_threshold_str = f"lower_threshold={density_lowerthreshold} upper_threshold={density_upperthreshold}"
        validated_lower_threshold = density_lowerthreshold
        validated_upper_threshold = density_upperthreshold
    else:
        density_threshold_str = "lower_threshold=0.005 upper_threshold=0.005"
        validated_lower_threshold = 0.005
        validated_upper_threshold = 0.005
        error_msg = f"""\
            "densityFunction threshold parameters are incorrects for this entity,
            lower_threshold and upper_threshold must both be a positive value,
            will be using using factory value.
            """
        get_effective_logger().error(
            f'tenant_id="{tenant_id}", component="{component}", object="{object_value}", {error_msg}'
        )

    # Construct the where NOT conditions, and also verifies if the period_exclusions are valid
    where_conditions = ""
    if period_exclusions:
        for period in period_exclusions:
            get_effective_logger().debug(f"period_exclusion: {period}")

            # get the period_latest (KV stores epochs as strings; coerce defensively)
            try:
                period_latest = int(period["latest"])
            except (TypeError, ValueError):
                period_latest = 0

            # The cutoff is computed from period_calculation (e.g. "-30d") via the
            # shared helper so the API endpoint validation cannot drift from the
            # trainer's rejection rule.
            period_calculation_timestamp = get_training_window_cutoff_epoch(period_calculation)

            # if the period_earliest and period_latest are not valid, then we need to skip this period_exclusion
            if period_latest < period_calculation_timestamp:
                get_effective_logger().info(
                    f"tenant_id={tenant_id}, object={object_value}, model_id={entity_outlier} rejecting period exclusion as it is now out of the model period calculation: {json.dumps(period, indent=4)}"
                )

                # delete the period_exclusion from the list
                period_exclusions.remove(period)

                # update the entity_outlier_dict
                entity_outlier_dict["period_exclusions"] = period_exclusions

            else:
                get_effective_logger().info(
                    f"tenant_id={tenant_id}, object={object_value}, model_id={entity_outlier} accepting period exclusion: {json.dumps(period, indent=4)}"
                )
                where_conditions += f'``` period_exclusions for this ML model: ```\n| where NOT (_time>{period["earliest"]} AND _time<{period["latest"]})\n'

    else:
        where_conditions = "``` no period_exclusions for this ML model ```"

    # set the lookup name
    # Determine if we should use the native TrackMe density function or MLTK
    use_native = algorithm == "TrackMeNativeDensityFunction"

    if mode == "live":
        ml_model_lookup_name = f"__mlspl_{entity_outlier}.mlmodel"
        ml_model_lookup_shortname = f"{entity_outlier}"
    elif mode == "simulation":
        ml_model_lookup_name = f"__mlspl_simulation_{entity_outlier}.mlmodel"
        ml_model_lookup_shortname = f"simulation_{entity_outlier}"

    #
    # Delete current ML model
    #

    # For native models using KVstore, no file deletion is needed
    # For MLTK models or native models using file storage, delete the file if it exists
    if not use_native or entity_outlier_dict.get("model_storage", "kvstore") == "file":
        # if the current ml model exists, then we need to delete it
        if os.path.exists(
            os.path.join(
                splunkhome,
                "etc",
                "users",
                "splunk-system-user",
                "trackme",
                "lookups",
                ml_model_lookup_name,
            )
        ):

            # Attempt to delete the current ml model
            rest_url = f"{splunkd_uri}/servicesNS/splunk-system-user/trackme/data/lookup-table-files/{ml_model_lookup_name}"

            get_effective_logger().info(
                f'tenant_id="{tenant_id}", component="{component}", object="{object_value}", attempting to delete Machine Learning lookup_name="{ml_model_lookup_name}"'
            )
            try:
                response = requests.delete(
                    rest_url,
                    headers=header,
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 204):
                    get_effective_logger().warning(
                        f'tenant_id="{tenant_id}", component="{component}", object="{object_value}", failure to delete ML lookup_name="{ml_model_lookup_name}", this might be expected if the model does not exist yet or has been deleted manually, url="{rest_url}", response.status_code="{response.status_code}", response.text="{response.text}"'
                    )
                else:
                    get_effective_logger().info(
                        f'tenant_id="{tenant_id}", component="{component}", object="{object_value}", action="success", deleted lookup_name="{ml_model_lookup_name}" successfully'
                    )

                    # Update ml_model_filesize / ml_model_lookup_share
                    if mode == "live":
                        entity_outlier_dict["ml_model_filesize"] = "pending"
                        entity_outlier_dict["ml_model_lookup_share"] = "pending"
                    elif mode == "simulation":
                        entity_outlier_dict["ml_model_simulation_filesize"] = "pending"
                        entity_outlier_dict["ml_model_simulation_lookup_share"] = "pending"

            except Exception as e:
                get_effective_logger().error(
                    f'tenant_id="{tenant_id}", component="{component}", object="{object_value}", failure to delete ML lookup_name="{ml_model_lookup_name}" with exception="{str(e)}"'
                )

    #
    # Set and run the Machine Learning model training search
    #

    # Get the model storage preference (kvstore or file), defaults to kvstore for native
    model_storage = entity_outlier_dict.get("model_storage", "kvstore")

    # define the gen search, handle the search depending on if time_factor is set to none or not
    if use_native:
        # --- Native TrackMe density function implementation ---
        # Uses trackmefit which implements proper per-group fitting via simple for-loops

        # Build exclude_dist parameter if specified in fit_extra_parameters
        exclude_dist_param = ""
        if fit_extra_parameters:
            # Parse exclude_dist from MLTK-style extra params (e.g. exclude_dist="beta")
            import re
            exclude_match = re.search(r'exclude_dist\s*=\s*["\']?([^"\']+)["\']?', str(fit_extra_parameters))
            if exclude_match:
                exclude_dist_param = f' exclude_dist="{exclude_match.group(1)}"'

        if time_factor == "none":
            fit_command = f'trackmefit feature="{kpi_metric}" lower_threshold={validated_lower_threshold} upper_threshold={validated_upper_threshold} into="{ml_model_lookup_shortname}" tenant_id="{tenant_id}" model_storage="{model_storage}"{exclude_dist_param}'

            ml_model_gen_search = remove_leading_spaces(
                f"""\
                | mstats {method_calculation}(trackme.{kpi_metric}) as {kpi_metric} where index="{tenant_trackme_metric_idx}" tenant_id="{tenant_id}" object_category="splk-{component}" object="{escape_backslash(object_value)}" by object span="{kpi_span}"
                {where_conditions}
                | {fit_command}
                | `{boundaries_extraction_macro}`
                | foreach LowerBound UpperBound [ eval <<FIELD>> = if(isnum('<<FIELD>>'), '<<FIELD>>', 0) ]
                | fields _time {kpi_metric} LowerBound UpperBound
                | stats count as metrics_count
                """
            )
        else:
            fit_command = f'trackmefit feature="{kpi_metric}" by="factor" lower_threshold={validated_lower_threshold} upper_threshold={validated_upper_threshold} into="{ml_model_lookup_shortname}" tenant_id="{tenant_id}" model_storage="{model_storage}"{exclude_dist_param}'

            ml_model_gen_search = remove_leading_spaces(
                f"""\
                | mstats {method_calculation}(trackme.{kpi_metric}) as {kpi_metric} where index="{tenant_trackme_metric_idx}" tenant_id="{tenant_id}" object_category="splk-{component}" object="{escape_backslash(object_value)}" by object span="{kpi_span}"
                {where_conditions}
                | eval factor=strftime(_time, "{time_factor}")
                | {fit_command}
                | `{boundaries_extraction_macro}`
                | foreach LowerBound UpperBound [ eval <<FIELD>> = if(isnum('<<FIELD>>'), '<<FIELD>>', 0) ]
                | fields _time {kpi_metric} LowerBound UpperBound
                | stats count as metrics_count
                """
            )

        # Define the render (apply) search for native implementation
        if time_factor == "none":
            apply_command = f'trackmeapply model_name="{ml_model_lookup_shortname}" tenant_id="{tenant_id}" model_storage="{model_storage}"'

            ml_model_render_search = remove_leading_spaces(
                f"""
                | mstats {method_calculation}(trackme.{kpi_metric}) as {kpi_metric} where index="{tenant_trackme_metric_idx}"
                tenant_id="{tenant_id}" object_category="splk-{component}" object="{escape_backslash(object_value)}" by object span="{kpi_span}"
                | {apply_command}
                | foreach LowerBound UpperBound [ eval <<FIELD>> = if(isnum('<<FIELD>>'), '<<FIELD>>', 0) ]
                | fields _time {kpi_metric} BoundaryRanges LowerBound UpperBound
            """
            )
        else:
            apply_command = f'trackmeapply model_name="{ml_model_lookup_shortname}" tenant_id="{tenant_id}" model_storage="{model_storage}"'

            ml_model_render_search = remove_leading_spaces(
                f"""
                | mstats {method_calculation}(trackme.{kpi_metric}) as {kpi_metric} where index="{tenant_trackme_metric_idx}"
                tenant_id="{tenant_id}" object_category="splk-{component}" object="{escape_backslash(object_value)}" by object span="{kpi_span}"
                | eval factor=strftime(_time, "{time_factor}")
                | {apply_command}
                | foreach LowerBound UpperBound [ eval <<FIELD>> = if(isnum('<<FIELD>>'), '<<FIELD>>', 0) ]
                | fields _time {kpi_metric} BoundaryRanges LowerBound UpperBound
            """
            )

    else:
        # --- MLTK implementation (DensityFunction or other MLTK algorithms) ---
        # Quote the by clause field name for compatibility with AI Toolkit 5.7.0+ (pandas 3.0)

        if time_factor == "none":
            fit_command = f"fit {algorithm} {kpi_metric} {density_threshold_str} into {ml_model_lookup_shortname}"

            # if any, add extra parameters to the fit command
            if fit_extra_parameters:
                fit_command += f" {fit_extra_parameters}"

            ml_model_gen_search = remove_leading_spaces(
                f"""\
                | mstats {method_calculation}(trackme.{kpi_metric}) as {kpi_metric} where index="{tenant_trackme_metric_idx}" tenant_id="{tenant_id}" object_category="splk-{component}" object="{escape_backslash(object_value)}" by object span="{kpi_span}"
                {where_conditions}
                | {fit_command}
                | `{boundaries_extraction_macro}`
                | foreach LowerBound UpperBound [ eval <<FIELD>> = if(isnum('<<FIELD>>'), '<<FIELD>>', 0) ]
                | fields _time {kpi_metric} LowerBound UpperBound
                | stats count as metrics_count
                """
            )

        else:
            fit_command = f'fit {algorithm} {kpi_metric} {density_threshold_str} into {ml_model_lookup_shortname}'

            # if any, add extra parameters to the fit command (before the by clause)
            if fit_extra_parameters:
                fit_command += f" {fit_extra_parameters}"

            # by clause must be last for MLTK compatibility
            fit_command += ' by "factor"'

            ml_model_gen_search = remove_leading_spaces(
                f"""\
                | mstats {method_calculation}(trackme.{kpi_metric}) as {kpi_metric} where index="{tenant_trackme_metric_idx}" tenant_id="{tenant_id}" object_category="splk-{component}" object="{escape_backslash(object_value)}" by object span="{kpi_span}"
                {where_conditions}
                | eval factor=strftime(_time, "{time_factor}")
                | {fit_command}
                | `{boundaries_extraction_macro}`
                | foreach LowerBound UpperBound [ eval <<FIELD>> = if(isnum('<<FIELD>>'), '<<FIELD>>', 0) ]
                | fields _time {kpi_metric} LowerBound UpperBound
                | stats count as metrics_count
                """
            )

        # define the render search depending on if time_factor is set to none or not, to be stored for further usage purposes
        if time_factor == "none":
            apply_command = f"apply {ml_model_lookup_shortname}"

            # if any, add extra parameters to the apply command
            if apply_extra_parameters:
                apply_command += f" {apply_extra_parameters}"

            ml_model_render_search = remove_leading_spaces(
                f"""
                | mstats {method_calculation}(trackme.{kpi_metric}) as {kpi_metric} where index="{tenant_trackme_metric_idx}"
                tenant_id="{tenant_id}" object_category="splk-{component}" object="{escape_backslash(object_value)}" by object span="{kpi_span}"
                | {apply_command}
                | `{boundaries_extraction_macro}`
                | foreach LowerBound UpperBound [ eval <<FIELD>> = if(isnum('<<FIELD>>'), '<<FIELD>>', 0) ]
                | fields _time {kpi_metric} BoundaryRanges LowerBound UpperBound
            """
            )

        else:
            apply_command = f"apply {ml_model_lookup_shortname}"

            # if any, add extra parameters to the apply command
            if apply_extra_parameters:
                apply_command += f" {apply_extra_parameters}"

            ml_model_render_search = remove_leading_spaces(
                f"""
                | mstats {method_calculation}(trackme.{kpi_metric}) as {kpi_metric} where index="{tenant_trackme_metric_idx}"
                tenant_id="{tenant_id}" object_category="splk-{component}" object="{escape_backslash(object_value)}" by object span="{kpi_span}"
                | eval factor=strftime(_time, "{time_factor}")
                | {apply_command}
                | `{boundaries_extraction_macro}`
                | foreach LowerBound UpperBound [ eval <<FIELD>> = if(isnum('<<FIELD>>'), '<<FIELD>>', 0) ]
                | fields _time {kpi_metric} BoundaryRanges LowerBound UpperBound
            """
            )

    # set kwargs
    kwargs_oneshot = {
        "earliest_time": str(period_calculation),
        "latest_time": str(period_calculation_latest),
        "output_mode": "json",
        "count": 0,
    }

    #
    # Run
    #

    # run search

    # track the search runtime
    start = time.time()

    # proceed
    try:
        reader = run_splunk_search(
            service,
            ml_model_gen_search,
            kwargs_oneshot,
            24,
            5,
        )

        for item in reader:
            if isinstance(item, dict):
                # log
                get_effective_logger().info(
                    f'tenant_id="{tenant_id}", component="{component}", object="{object_value}", kpi_metric="{kpi_metric}", entity_outlier="{entity_outlier}", Machine Learning model training search executed successfully, run_time="{round(time.time() - start, 3)}", results="{json.dumps(item, indent=0)}"'
                )

            # retrieve the current share level
            if mode == "live":
                entity_outlier_dict["ml_model_lookup_share"] = "pending"
            elif mode == "simulation":
                entity_outlier_dict["ml_model_lookup_share"] = "pending"

            # Update ml_model_lookup_share
            entity_outlier_dict["ml_model_lookup_share"] = "private"

            # Update owner and perms
            entity_outlier_dict["ml_model_lookup_owner"] = "splunk-system-user"

    except Exception as e:
        msg = f'tenant_id="{tenant_id}", component="{component}", object="{object_value}", kpi_metric="{kpi_metric}", entity_outlier="{entity_outlier}", Machine Learning model training search failed with exception="{str(e)}", run_time="{str(time.time() - start)}"'
        get_effective_logger().error(msg)
        raise Exception(msg)

    if mode == "live":

        # Update last_exec
        entity_outlier_dict["last_exec"] = time.time()

        # Update ml_model_gen_search
        entity_outlier_dict["ml_model_gen_search"] = ml_model_gen_search

        # Update
        entity_outlier_dict["ml_model_render_search"] = ml_model_render_search

        # Update rules_access_search
        entity_outlier_dict["rules_access_search"] = (
            f'| inputlookup trackme_{component}_outliers_entity_rules_tenant_{tenant_id} where _key="{key_value}"'
        )

        if use_native and entity_outlier_dict.get("model_storage", "kvstore") == "kvstore":
            # Native models stored in KVstore: no file-based model, use kvstore reference
            entity_outlier_dict["ml_model_filename"] = f"kvstore:{ml_model_lookup_shortname}"
            entity_outlier_dict["ml_model_summary_search"] = (
                f'| inputlookup kv_trackme_native_ml_models_tenant_{tenant_id} where _key="{ml_model_lookup_shortname}"'
            )
            entity_outlier_dict["ml_model_filesize"] = "kvstore"
        else:
            # MLTK models or native file-based: standard file references
            entity_outlier_dict["ml_model_filename"] = ml_model_lookup_name
            entity_outlier_dict["ml_model_summary_search"] = f"| summary {entity_outlier}"

            # Update ml_model_filesize
            try:
                entity_outlier_dict["ml_model_filesize"] = os.path.getsize(
                    os.path.join(
                        splunkhome,
                        "etc",
                        "users",
                        "splunk-system-user",
                        "trackme",
                        "lookups",
                        ml_model_lookup_name,
                    )
                )

            except Exception as e:
                get_effective_logger().info(
                    f'tenant_id="{tenant_id}", size of the ML lookup_name="{ml_model_lookup_name}" cannot be determined yet as the model may not be ready, response="{str(e)}"'
                )
                entity_outlier_dict["ml_model_filesize"] = "pending"

        # Update ml_model_lookup_share and model_storage
        entity_outlier_dict["model_storage"] = entity_outlier_dict.get("model_storage", "kvstore") if use_native else "file"

        # Update the main dict
        entities_outliers[entity_outlier] = entity_outlier_dict

    elif mode == "simulation":

        # Update last_exec
        entity_outlier_dict["ml_model_simulation_last_exec"] = time.time()

        # Update ml_model_gen_search
        entity_outlier_dict["ml_model_simulation_gen_search"] = ml_model_gen_search

        # Update
        entity_outlier_dict["ml_model_simulation_render_search"] = (
            ml_model_render_search
        )

        # Update rules_access_search
        entity_outlier_dict["ml_model_simulation_rules_access_search"] = (
            f'| inputlookup trackme_{component}_outliers_entity_rules_tenant_{tenant_id} where _key="{key_value}"'
        )

        if use_native and entity_outlier_dict.get("model_storage", "kvstore") == "kvstore":
            entity_outlier_dict["ml_model_simulation_filename"] = f"kvstore:{ml_model_lookup_shortname}"
            entity_outlier_dict["ml_model_simulation_summary_search"] = (
                f'| inputlookup kv_trackme_native_ml_models_tenant_{tenant_id} where _key="{ml_model_lookup_shortname}"'
            )
            entity_outlier_dict["ml_model_simulation_filesize"] = "kvstore"
        else:
            entity_outlier_dict["ml_model_simulation_filename"] = ml_model_lookup_name
            entity_outlier_dict["ml_model_simulation_summary_search"] = (
                f"| summary {entity_outlier}"
            )

            # Update ml_model_filesize (only for file-based models)
            try:
                entity_outlier_dict["ml_model_simulation_filesize"] = os.path.getsize(
                    os.path.join(
                        splunkhome,
                        "etc",
                        "users",
                        "splunk-system-user",
                        "trackme",
                        "lookups",
                        ml_model_lookup_name,
                    )
                )
            except Exception as e:
                get_effective_logger().info(
                    f'tenant_id="{tenant_id}", size of the ML lookup_name="{ml_model_lookup_name}" cannot be determined yet as the model may not be ready, response="{str(e)}"'
                )
                entity_outlier_dict["ml_model_simulation_filesize"] = "pending"

        # Update the main dict
        entities_outliers[entity_outlier] = entity_outlier_dict

    #
    # End
    #

    # finally, return entities_outliers
    return entities_outliers, entity_outlier, entity_outlier_dict


def return_lightsimulation_search(
    tenant_id, component, object_value, metric_idx, model_json_def
):

    # log debug
    get_effective_logger().debug("mode is simulation")

    # log debug
    get_effective_logger().debug(f"model_json_def={model_json_def}")

    # load the model definition as a dict
    if not isinstance(model_json_def, dict):
        try:
            model_json_def = json.loads(model_json_def)
            # log debug
            get_effective_logger().debug(
                f'successfully loaded model_json_def="{json.dumps(model_json_def, indent=4)}"'
            )
        except Exception as e:
            msg = f'failed to load the submitted model_json_def="{model_json_def}" with exception="{e}"'
            get_effective_logger().error(msg)
            raise Exception(msg)

    # get definitions from the model_json_def
    kpi_metric = model_json_def["kpi_metric"]
    kpi_span = model_json_def["kpi_span"]
    method_calculation = model_json_def["method_calculation"]
    density_lowerthreshold = model_json_def["density_lowerthreshold"]
    density_upperthreshold = model_json_def["density_upperthreshold"]
    alert_lower_breached = model_json_def["alert_lower_breached"]
    alert_upper_breached = model_json_def["alert_upper_breached"]
    period_calculation = model_json_def["period_calculation"]
    # optional period_calculation_latest
    period_calculation_latest = model_json_def.get("period_calculation_latest", "now")
    time_factor = model_json_def["time_factor"]
    perc_min_lowerbound_deviation = model_json_def["perc_min_lowerbound_deviation"]
    perc_min_upperbound_deviation = model_json_def["perc_min_upperbound_deviation"]
    min_value_for_lowerbound_breached = model_json_def.get(
        "min_value_for_lowerbound_breached", 0
    )
    min_value_for_upperbound_breached = model_json_def.get(
        "min_value_for_upperbound_breached", 0
    )
    static_lower_threshold = model_json_def.get("static_lower_threshold", None)
    static_upper_threshold = model_json_def.get("static_upper_threshold", None)
    algorithm = model_json_def.get("algorithm", "DensityFunction")
    boundaries_extraction_macro = model_json_def.get(
        "boundaries_extraction_macro", "splk_outliers_extract_boundaries"
    )
    fit_extra_parameters = model_json_def.get("fit_extra_parameters", None)
    apply_extra_parameters = model_json_def.get("apply_extra_parameters", None)

    rules_summary = {
        "kpi_metric": kpi_metric,
        "kpi_span": kpi_span,
        "method_calculation": method_calculation,
        "density_lowerthreshold": density_lowerthreshold,
        "density_upperthreshold": density_upperthreshold,
        "period_calculation": period_calculation,
        "period_calculation_latest": period_calculation_latest,
        "time_factor": time_factor,
        "perc_min_lowerbound_deviation": perc_min_lowerbound_deviation,
        "perc_min_upperbound_deviation": perc_min_upperbound_deviation,
        "alert_lower_breached": alert_lower_breached,
        "alert_upper_breached": alert_upper_breached,
        "min_value_for_lowerbound_breached": min_value_for_lowerbound_breached,
        "min_value_for_upperbound_breached": min_value_for_upperbound_breached,
        "static_lower_threshold": static_lower_threshold,
        "static_upper_threshold": static_upper_threshold,
        "algorithm": algorithm,
        "boundaries_extraction_macro": boundaries_extraction_macro,
        "fit_extra_parameters": fit_extra_parameters,
        "apply_extra_parameters": apply_extra_parameters,
    }

    get_effective_logger().debug(f'Processing outliers simulation rules_summary="{rules_summary}"')

    #
    # Proceed
    #

    # Define the Splunk searches
    ml_model_gen_search = None

    # Set the densityFunction threshold parameters
    if float(density_lowerthreshold) > 0 and float(density_upperthreshold) > 0:
        density_threshold_str = f"lower_threshold={density_lowerthreshold} upper_threshold={density_upperthreshold}"
        validated_lower_threshold = density_lowerthreshold
        validated_upper_threshold = density_upperthreshold
    else:
        density_threshold_str = "lower_threshold=0.005 upper_threshold=0.005"
        validated_lower_threshold = 0.005
        validated_upper_threshold = 0.005
        error_msg = f"""\
            "densityFunction threshold parameters are incorrects for this entity,
            lower_threshold and upper_threshold must both be a positive value,
            will be using using factory value.
            """
        get_effective_logger().error(
            f'tenant_id="{tenant_id}", component="{component}", object="{object_value}", {error_msg}'
        )

    # Determine if we should use the native TrackMe density function or MLTK
    use_native = algorithm == "TrackMeNativeDensityFunction"

    # define the gen search, handle the search depending on if time_factor is set to none or not
    if use_native:
        # --- Native TrackMe density function implementation (inline, no model persistence) ---

        # Build exclude_dist parameter if specified in fit_extra_parameters
        exclude_dist_param = ""
        if fit_extra_parameters:
            import re
            exclude_match = re.search(r'exclude_dist\s*=\s*["\']?([^"\']+)["\']?', str(fit_extra_parameters))
            if exclude_match:
                exclude_dist_param = f' exclude_dist="{exclude_match.group(1)}"'

        if time_factor == "none":
            fit_command = f'trackmefit feature="{kpi_metric}" lower_threshold={validated_lower_threshold} upper_threshold={validated_upper_threshold}{exclude_dist_param}'

            ml_model_gen_search = remove_leading_spaces(
                f"""\
                | mstats {method_calculation}(trackme.{kpi_metric}) as {kpi_metric} where index="{metric_idx}" tenant_id="{tenant_id}" object_category="splk-{component}" object="{escape_backslash(object_value)}" by object span="{kpi_span}"
                | {fit_command}
                | `{boundaries_extraction_macro}`
                | foreach LowerBound UpperBound [ eval <<FIELD>> = if(isnum('<<FIELD>>'), '<<FIELD>>', 0) ]
                """
            )
        else:
            fit_command = f'trackmefit feature="{kpi_metric}" by="factor" lower_threshold={validated_lower_threshold} upper_threshold={validated_upper_threshold}{exclude_dist_param}'

            ml_model_gen_search = remove_leading_spaces(
                f"""\
                | mstats {method_calculation}(trackme.{kpi_metric}) as {kpi_metric} where index="{metric_idx}" tenant_id="{tenant_id}" object_category="splk-{component}" object="{escape_backslash(object_value)}" by object span="{kpi_span}"
                | eval factor=strftime(_time, "{time_factor}")
                | {fit_command}
                | `{boundaries_extraction_macro}`
                | foreach LowerBound UpperBound [ eval <<FIELD>> = if(isnum('<<FIELD>>'), '<<FIELD>>', 0) ]
                """
            )

    else:
        # --- MLTK implementation ---
        # Quote the by clause field name for compatibility with AI Toolkit 5.7.0+ (pandas 3.0)

        if time_factor == "none":

            fit_command = f"fit {algorithm} {kpi_metric} {density_threshold_str}"

            # if any, add extra parameters to the fit command
            if fit_extra_parameters:
                fit_command += f" {fit_extra_parameters}"

            ml_model_gen_search = remove_leading_spaces(
                f"""\
                | mstats {method_calculation}(trackme.{kpi_metric}) as {kpi_metric} where index="{metric_idx}" tenant_id="{tenant_id}" object_category="splk-{component}" object="{escape_backslash(object_value)}" by object span="{kpi_span}"
                | {fit_command}
                | `{boundaries_extraction_macro}`
                | foreach LowerBound UpperBound [ eval <<FIELD>> = if(isnum('<<FIELD>>'), '<<FIELD>>', 0) ]
                """
            )

        else:

            fit_command = f'fit {algorithm} {kpi_metric} {density_threshold_str}'

            # if any, add extra parameters to the fit command (before the by clause)
            if fit_extra_parameters:
                fit_command += f" {fit_extra_parameters}"

            # by clause must be last for MLTK compatibility
            fit_command += ' by "factor"'

            ml_model_gen_search = remove_leading_spaces(
                f"""\
                | mstats {method_calculation}(trackme.{kpi_metric}) as {kpi_metric} where index="{metric_idx}" tenant_id="{tenant_id}" object_category="splk-{component}" object="{escape_backslash(object_value)}" by object span="{kpi_span}"
                | eval factor=strftime(_time, "{time_factor}")
                | {fit_command}
                | `{boundaries_extraction_macro}`
                | foreach LowerBound UpperBound [ eval <<FIELD>> = if(isnum('<<FIELD>>'), '<<FIELD>>', 0) ]
                """
            )

    # log debug
    get_effective_logger().debug(f'ml_model_gen_search="{ml_model_gen_search}"')

    return ml_model_gen_search


def get_outliers_rules(service, tenant_id, component, object_value, reqinfo, logger=None):
    """
    Get outliers rules from KV store collection.
    Extracted logic from trackmesplkoutliersgetrules.py custom command.
    
    Args:
        service: Splunk service object (from splunklib.client)
        tenant_id: Tenant identifier
        component: Component category (dsm, dhm, flx, fqm, wlk)
        object_value: Object name, use "*" to match all entities
        reqinfo: Request info dictionary containing trackme_conf
        logger: Optional logger instance
    
    Returns:
        List of dictionaries containing outliers rules data
    """
    if logger is None:
        logger = logging
    
    results = []
    
    # Outliers rules storage collection
    collection_rules_name = (
        f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
    )
    collection_rule = service.kvstore[collection_rules_name]

    # Get app level config
    splk_outliers_detection = reqinfo["trackme_conf"]["splk_outliers_detection"]

    # available algorithms
    splk_outliers_mltk_algorithms_list = splk_outliers_detection.get(
        "splk_outliers_mltk_algorithms_list", ["DensityFunction"]
    )

    # default algorithm
    splk_outliers_mltk_algorithms_default = splk_outliers_detection.get(
        "splk_outliers_mltk_algorithms_default", "DensityFunction"
    )

    # available boundaries extraction macros
    splk_outliers_boundaries_extraction_macros_list = splk_outliers_detection.get(
        "splk_outliers_boundaries_extraction_macros_list",
        ["splk_outliers_extract_boundaries"],
    )

    # default bundaries extraction macro
    splk_outliers_boundaries_extraction_macro_default = splk_outliers_detection.get(
        "splk_outliers_boundaries_extraction_macro_default",
        "splk_outliers_extract_boundaries",
    )

    # default period_calculation_latest
    splk_outliers_detection_period_latest_default = splk_outliers_detection.get(
        "splk_outliers_detection_period_latest_default", "now"
    )

    #
    # Get the Outliers rules
    #

    # Define the KV query
    if object_value == "*":
        query_string = {
            "object_category": f"splk-{component}",
        }
    else:
        # Define the KV query
        query_string_filter = {
            "object_category": f"splk-{component}",
            "object": object_value,
        }

        query_string = {"$and": [query_string_filter]}

    # get records
    try:
        record_outliers_rules = collection_rule.data.query(
            query=json.dumps(query_string)
        )

    except Exception as e:
        record_outliers_rules = []

    # log debug
    logger.debug(f'record_outliers_rules="{record_outliers_rules}"')

    # Get the current splk_outliers_min_days_history for config mismatch detection
    current_min_days_history = splk_outliers_detection.get(
        "splk_outliers_min_days_history", 30
    )

    # Loop through entities
    for entity_rules in record_outliers_rules:
        #
        # ML confidence
        #

        ml_confidence = entity_rules.get("confidence", "low")
        ml_confidence_reason = entity_rules.get("confidence_reason", "unknown")

        # Detect if splk_outliers_min_days_history has changed since last training
        stored_min_days_history = entity_rules.get("splk_outliers_min_days_history")

        # For pre-upgrade models that don't have the stored field yet,
        # fall back to parsing the value from the confidence_reason string
        # which always contains "required=Xdays"
        if stored_min_days_history is None and ml_confidence_reason not in ("unknown", "pending"):
            try:
                match = re.search(r'required=(\d+)days', ml_confidence_reason)
                if match:
                    stored_min_days_history = match.group(1)
            except Exception:
                pass

        confidence_config_changed = False
        if stored_min_days_history is not None:
            try:
                if str(stored_min_days_history) != str(current_min_days_history):
                    confidence_config_changed = True
            except Exception:
                pass

        # Get the JSON outliers rules object
        entities_outliers = entity_rules.get("entities_outliers")

        # Load as a dict
        try:
            entities_outliers = json.loads(entity_rules.get("entities_outliers"))
        except Exception as e:
            msg = f'Failed to load entities_outliers with exception="{str(e)}"'
            logger.error(msg)
            continue

        # log debug
        logger.debug(f'entities_outliers="{entities_outliers}"')

        # Get object
        entity_object = entity_rules.get("object")

        # Get object_category
        entity_object_category = entity_rules.get("object_category")

        #
        # Start
        #

        # Loop through outliers entities
        for entity_outlier in entities_outliers:
            # Set as a dict
            entity_outliers_dict = entities_outliers[entity_outlier].copy()

            # ensures retro-compatibility < version 2.0.15 with the auto_correct option, set default True if not defined
            try:
                auto_correct = entity_outliers_dict["auto_correct"]
            except Exception as e:
                entity_outliers_dict["auto_correct"] = 1

            # ensure retro-compatibility < version 2.0.84 with the min_value_for_lowerbound_breached/min_value_for_upperbound_breached, set default value to 0 if not defined
            try:
                min_value_for_lowerbound_breached = entity_outliers_dict[
                    "min_value_for_lowerbound_breached"
                ]
            except Exception as e:
                entity_outliers_dict["min_value_for_lowerbound_breached"] = 0

            try:
                min_value_for_upperbound_breached = entity_outliers_dict[
                    "min_value_for_upperbound_breached"
                ]
            except Exception as e:
                entity_outliers_dict["min_value_for_upperbound_breached"] = 0

            # ensure retro-compatibility with < version 2.0.89, set algorithm with default value if not defined
            try:
                algorithm = entity_outliers_dict["algorithm"]
            except Exception as e:
                entity_outliers_dict["algorithm"] = (
                    splk_outliers_mltk_algorithms_default
                )

            # add algorithms_list
            entity_outliers_dict["algorithms_list"] = (
                splk_outliers_mltk_algorithms_list
            )

            # ensure retro-compatibility with < version 2.0.89, set bundaries extraction macro with default value if not defined
            try:
                boundaries_extraction_macro = entity_outliers_dict[
                    "boundaries_extraction_macro"
                ]
            except Exception as e:
                entity_outliers_dict["boundaries_extraction_macro"] = (
                    splk_outliers_boundaries_extraction_macro_default
                )

            # ensure retro-compatibility with < version 2.0.96, set period_calculation_latest with default value if not defined
            try:
                period_calculation_latest = entity_outliers_dict[
                    "period_calculation_latest"
                ]
            except Exception as e:
                entity_outliers_dict["period_calculation_latest"] = (
                    splk_outliers_detection_period_latest_default
                )

            # add boundaries_extraction_macros_list
            entity_outliers_dict["boundaries_extraction_macros_list"] = (
                splk_outliers_boundaries_extraction_macros_list
            )

            # Add a pseudo time
            entity_outliers_dict["_time"] = time.time()

            # Add the object reference
            entity_outliers_dict["object"] = entity_object

            # Add the object_category reference
            entity_outliers_dict["object_category"] = entity_object_category

            # Add the model_id reference
            entity_outliers_dict["model_id"] = entity_outlier

            # Add ml_confidence and ml_confidence_reason
            entity_outliers_dict["confidence"] = ml_confidence
            entity_outliers_dict["confidence_reason"] = ml_confidence_reason

            # Add config mismatch detection fields
            entity_outliers_dict["confidence_config_changed"] = confidence_config_changed
            entity_outliers_dict["current_min_days_history"] = current_min_days_history
            if stored_min_days_history is not None:
                entity_outliers_dict["trained_min_days_history"] = stored_min_days_history

            # Add _raw
            entity_outliers_dict["_raw"] = json.dumps(entity_outliers_dict)

            # Append to results
            results.append(entity_outliers_dict)

    return results


def get_outliers_data(service, tenant_id, component, object_value, reqinfo, logger=None):
    """
    Get outliers data from KV store collection.
    Extracted logic from trackmesplkoutliersgetdata.py custom command.
    
    Args:
        service: Splunk service object (from splunklib.client)
        tenant_id: Tenant identifier
        component: Component category (dsm, dhm, flx, fqm, wlk)
        object_value: Object name, use "*" to match all entities
        reqinfo: Request info dictionary (not currently used but kept for consistency)
        logger: Optional logger instance
    
    Returns:
        List of dictionaries containing outliers data
    """
    if logger is None:
        logger = logging
    
    results = []
    
    # Outliers data storage collection
    collection_data_name = (
        f"kv_trackme_{component}_outliers_entity_data_tenant_{tenant_id}"
    )
    collection_data = service.kvstore[collection_data_name]

    #
    # Get the Outliers data
    #

    # Define the KV query
    if object_value == "*":
        query_string = {
            "object_category": "splk-" + component,
        }
    else:
        # Define the KV query
        query_string_filter = {
            "object_category": "splk-" + component,
            "object": object_value,
        }

        query_string = {"$and": [query_string_filter]}

    # get records
    try:
        record_outliers_data = collection_data.data.query(
            query=json.dumps(query_string)
        )

    except Exception as e:
        record_outliers_data = []

    # if no records, return empty list (don't raise exception like the custom command does)
    if not record_outliers_data:
        logger.debug(
            f'tenant_id="{tenant_id}", component="{component}", object="{object_value}" outliers data record cannot be found or are not yet available for this selection.'
        )
        return results

    # log debug
    logger.debug(f'record_outliers_data="{record_outliers_data}"')

    # Loop through entities
    for entity_data in record_outliers_data:
        # Get object
        entity_object = entity_data.get("object")

        # Get object_category
        entity_object_category = entity_data.get("object_category")

        # Get isOutlier
        entity_is_outliers = entity_data.get("isOutlier")

        # Get isOutlierReason
        entity_is_outliers_reason = entity_data.get("isOutlierReason")

        # Get models_in_anomaly
        entity_models_in_anomaly = entity_data.get("models_in_anomaly")

        # Get models_summary
        try:
            entity_models_summary = json.loads(entity_data.get("models_summary"))
        except Exception as e:
            logger.error(f'Failed to load models_summary with exception="{str(e)}"')
            entity_models_summary = {}

        # Get mtime
        entity_mtime = float(entity_data.get("mtime"))

        #
        # Start
        #

        entity_outliers_results = {}

        # Add each field retrieved
        entity_outliers_results["object"] = entity_object
        entity_outliers_results["object_category"] = entity_object_category
        entity_outliers_results["IsOutlier"] = entity_is_outliers
        entity_outliers_results["isOutlierReason"] = entity_is_outliers_reason
        entity_outliers_results["models_in_anomaly"] = entity_models_in_anomaly
        entity_outliers_results["models_summary"] = entity_models_summary
        # generate an mtime_human which is strftime %c of the epoch time
        entity_outliers_results["mtime"] = entity_mtime
        entity_outliers_results["mtime_human"] = time.strftime(
            "%c", time.localtime(entity_mtime)
        )

        # Add _raw
        entity_outliers_results["_raw"] = json.dumps(entity_outliers_results)

        # Append to results
        results.append(entity_outliers_results)

    return results
