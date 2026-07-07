"""Shared user-facing error reporting for the JAMF Pro Splunk addon.

Why this exists:
    Each input module needs to surface failures in two places:
      1. splunkd input log (helper.log_error) — visible to operators who
         look at jamf_pro_addon_for_splunk_*.log or the Inputs UI status row.
      2. An indexed event with sourcetype=jamf:input:error — searchable by
         non-admin users with `index=<idx> sourcetype=jamf:input:error`.

    One canonical key=value shape, one emitter. Dashboards and saved searches
    over sourcetype=jamf:input:error can rely on a stable field set across
    config / auth / endpoint / record failures from all three inputs.
"""

import import_declare_test  # noqa: F401  pylint: disable=unused-import


_HOST_DEFAULT = "Jamf-TA-AddOn"

# Closed set of category values. Imported by validators / dashboards.
VALID_CATEGORIES = frozenset({"config", "auth", "endpoint", "record"})


def _kv_escape(value):
    """Escape backslashes and double-quotes so they don't break KV extraction."""
    return str(value).replace('\\', '\\\\').replace('"', '\\"')


def emit_input_error(
    helper,
    ew,
    category,
    label,
    target_url,
    summary,
    record_id=None,
    index=None,
    host=None,
):
    """Log + index a user-actionable input failure as one structured line.

    Emits one line to helper.log_error AND one indexed event with
    sourcetype="jamf:input:error" carrying the same line.

    Output shape:
        status=failed category=<cat> input=<type> stanza="<stanza>" \\
        endpoint="<label>" url="<url>" detail="<summary>" [record_id="<id>"]

    Args:
        helper, ew:    modular-input helper + event writer.
        category:      one of {config, auth, endpoint, record}. Required.
        label:         short name of the endpoint or operation that failed.
        target_url:    URL that was tried (or "(no request was made)" if
                       the failure was pre-flight).
        summary:       one-line description of the failure (the "detail" field).
        record_id:     for category=record, the Jamf ID of the failing record;
                       included as `record_id="<id>"` when set.
        index:         output index; defaults to helper.get_output_index().
        host:          host field; defaults to helper.get_arg('custom_host_name')
                       and finally _HOST_DEFAULT.
    """
    if category not in VALID_CATEGORIES:
        # Programmer error — bad category breaks dashboards. Log loudly and
        # fall back to "endpoint" so the event still indexes.
        helper.log_error(
            "emit_input_error: invalid category=%r; must be one of %s"
            % (category, sorted(VALID_CATEGORIES))
        )
        category = "endpoint"

    stanza = helper.get_input_stanza_names()
    input_type = stanza.split("://", 1)[0] if "://" in stanza else stanza

    base = (
        'status=failed category={category} input={input_type} '
        'stanza="{stanza}" endpoint="{label}" url="{url}" detail="{detail}"'
    ).format(
        category=category,
        input_type=input_type,
        stanza=_kv_escape(stanza),
        label=_kv_escape(label),
        url=_kv_escape(target_url),
        detail=_kv_escape(summary),
    )
    line = base if record_id is None else (
        '%s record_id="%s"' % (base, _kv_escape(record_id))
    )

    helper.log_error(line)

    if index is None:
        try:
            index = helper.get_output_index()
        except Exception:
            index = None
    if host is None:
        try:
            host = helper.get_arg('custom_host_name', None)
        except Exception:
            host = None
    if not host:
        host = _HOST_DEFAULT

    try:
        ew.write_event(helper.new_event(
            data=line,
            sourcetype="jamf:input:error",
            index=index,
            host=host,
        ))
    except Exception as write_err:
        helper.log_error(
            "emit_input_error: failed to write indexed event "
            "(the log entry above still applies): %s" % write_err
        )
