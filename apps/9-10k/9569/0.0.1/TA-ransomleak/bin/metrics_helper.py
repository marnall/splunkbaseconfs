import import_declare_test  # noqa: F401  (UCC path bootstrap — must stay first)

from splunklib import modularinput as smi

from grafana_input import stream_grafana_events, validate_grafana_input

SCHEME = "metrics"
SOURCETYPE = "ransomleak:metrics"

# Programme ACTIVITY: what the training and simulation programme is producing.
# Reporting-grade rather than alerting-grade, and backed by the heavier
# aggregate queries in the tenant database (campaign_participant and
# phishing_dispatch joins), so the default interval is longer than the risk
# input's. Both bucket by UTC day, so nothing is gained by polling either of
# them faster than the day moves; the interval only bounds how stale the
# current, partial bucket may be.
#
# The split between the two inputs is a DEFAULT, not a constraint: both offer
# the whole metric catalogue in the multi-select.
DEFAULT_METRICS = (
    "training_completion_rate,phishing_click_rate,phishing_report_rate,"
    "assignments_by_category,auto_assigned_via_grafana")
DEFAULT_LOOKBACK_DAYS = "30"


def validate_input(definition: smi.ValidationDefinition):
    validate_grafana_input(definition, DEFAULT_METRICS)


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    stream_grafana_events(
        inputs, event_writer,
        scheme=SCHEME,
        sourcetype=SOURCETYPE,
        default_metrics=DEFAULT_METRICS,
        default_lookback_days=DEFAULT_LOOKBACK_DAYS,
        error_code="RansomLeakMetricsIngestError",
        error_message="Exception while ingesting RansomLeak programme metrics: ",
    )
