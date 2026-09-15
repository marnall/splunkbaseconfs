import import_declare_test  # noqa: F401  (UCC path bootstrap — must stay first)

from splunklib import modularinput as smi

from grafana_input import stream_grafana_events, validate_grafana_input

SCHEME = "risk"
SOURCETYPE = "ransomleak:risk"

# Risk POSTURE: who is exposed right now, and how the exposure is trending.
# These are the metrics an alert fires on, which is why this input polls more
# often than `ransomleak_metrics` even though both bucket by UTC day.
#
# The split between the two inputs is a DEFAULT, not a constraint: both offer
# the whole metric catalogue in the multi-select, so an operator who wants one
# input or a different division gets it without editing the add-on.
DEFAULT_METRICS = "human_risk_score,assignments_overdue,overdue_users"
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
        error_code="RansomLeakRiskIngestError",
        error_message="Exception while ingesting RansomLeak risk metrics: ",
    )
