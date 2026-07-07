""" Copyright © 2019-2020, EPAM Systems, all rights reserved. """

""" This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/. """

import six
from six.moves import range
from six.moves import zip

BASE_SEARCH = (
    "| mstats median(_value) as alert_value WHERE index={index} "
    'metric_name={metric_name} system_name="{system_name}"'
)
DEFAULT_PERIOD_MINUTES = 30 * 24 * 60
MAX_ALERT_PERIOD_MINUTES = 15

SEVERITIES = {
    1: {
        six.u("severityColorLight"): six.u("#E3F0F6"),
        six.u("severityColor"): six.u("#AED3E5"),
        six.u("severityLabel"): six.u("info"),
    },
    2: {
        six.u("severityColorLight"): six.u("#DCEFD7"),
        six.u("severityColor"): six.u("#99D18B"),
        six.u("severityLabel"): six.u("normal"),
    },
    3: {
        six.u("severityColorLight"): six.u("#FFF4C5"),
        six.u("severityColor"): six.u("#FFE98C"),
        six.u("severityLabel"): six.u("low"),
    },
    4: {
        six.u("severityColorLight"): six.u("#FEE6C1"),
        six.u("severityColor"): six.u("#FCB64E"),
        six.u("severityLabel"): six.u("medium"),
    },
    5: {
        six.u("severityColorLight"): six.u("#FBCBB9"),
        six.u("severityColor"): six.u("#F26A35"),
        six.u("severityLabel"): six.u("high"),
    },
    6: {
        six.u("severityColorLight"): six.u("#E5A6A6"),
        six.u("severityColor"): six.u("#B50101"),
        six.u("severityLabel"): six.u("critical"),
    },
}


def get_median_period(timestamps, precision):
    """Calculate the median timedelta of a rising timestamp series."""

    def round_to_precision(number, precision):
        return int(round(number / float(precision)) * precision)

    if not timestamps:
        return None
    if timestamps[0] == 0:
        timestamps.pop(0)
    if len(timestamps) < 2:
        return None
    deltas = []
    for t1, t2 in zip(timestamps, timestamps[1:]):
        deltas.append(t2 - t1)
    deltas.sort()
    midpoint, is_odd = divmod(len(deltas), 2)
    if is_odd:
        median = deltas[midpoint]
    else:
        median = (deltas[midpoint - 1] + deltas[midpoint]) / 2.0
    return round_to_precision(median, precision)


def get_severity(severity_key, threshold):
    severity = SEVERITIES[severity_key].copy()
    severity[six.u("severityValue")] = severity_key
    severity[six.u("thresholdValue")] = threshold
    return severity


def serialize_metric(data, checkpoint_data):
    checkpoint_key = "{} # {}".format(data["SystemName"], data["EventName"])
    period_seconds = get_median_period(checkpoint_data[checkpoint_key], 60)
    if not period_seconds:
        period_seconds = int(data["Period"])
    if period_seconds == 0:
        period_minutes = DEFAULT_PERIOD_MINUTES
    else:
        period_minutes = period_seconds / 60
    base_metric_data = {
        six.u("title"): data["MetricName"].replace("_", " "),
        six.u("_key"): data["_key"],
        six.u("threshold_field"): "alert_value",
        six.u("aggregate_statop"): "median",
        six.u("urgency"): six.text_type(3 + 2 * int(data["Rating"])),
        six.u("alert_period"): min(period_minutes, MAX_ALERT_PERIOD_MINUTES),
        six.u("search_alert_earliest"): period_minutes * 2,
        six.u("unit"): data["Unit"],
        six.u("base_search"): BASE_SEARCH.format(
            index="*", metric_name=data["MetricName"], system_name=data["SystemName"]
        ),
    }

    direction = data["Direction"]
    if direction in ("EXCEEDS", "FALLSBELOW"):
        threshold_values = [
            int(data[field])
            for field in [
                "Yellowtogreen",
                "Greentoyellow",
                "Redtoyellow",
                "Yellowtored",
            ]
        ]
        if direction == "EXCEEDS":
            threshold_values.sort()
            base_severity_value = 2
            levels = []
            for i in range(4):
                levels.append(get_severity(i + 3, threshold_values[i]))
        else:
            threshold_values.sort(reverse=True)
            base_severity_value = 6
            levels = []
            for i in range(4):
                levels.append(get_severity(i + 2, threshold_values[i]))
    else:
        base_severity_value = 1
        levels = []

    normalized_levels = []
    current = {six.u("severityValue"): base_severity_value, six.u("thresholdValue"): 0}

    for level in levels:
        if level["severityValue"] in (2, 6):
            normalized_levels.append(level)

        if current["thresholdValue"] == level["thresholdValue"]:
            if (
                current["severityValue"] not in (2, 6)
                and current["severityValue"] < level["severityValue"]
            ):
                current = level
        else:
            if current["severityValue"] not in (2, 6):
                normalized_levels.append(current)
            current = level

    base_severity = SEVERITIES[base_severity_value]
    base_metric_data["aggregate_thresholds"] = {
        six.u("thresholdLevels"): normalized_levels,
        six.u("baseSeverityColorLight"): base_severity[six.u("severityColorLight")],
        six.u("gap_severity_color_light"): six.u("#EEEEEE"),
        six.u("baseSeverityValue"): base_severity_value,
        six.u("baseSeverityColor"): base_severity[six.u("severityColor")],
        six.u("renderBoundaryMin"): 0,
        six.u("baseSeverityLabel"): base_severity[six.u("severityLabel")],
    }

    return base_metric_data
