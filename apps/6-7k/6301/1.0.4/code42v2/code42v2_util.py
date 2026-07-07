# File: code42v2_util.py
#
# Copyright (c) 2022-2026 Splunk Inc., Code42
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.


from datetime import datetime, timedelta, timezone

import dateutil.parser
from py42.sdk.queries.alerts.alert_query import AlertQuery
from py42.sdk.queries.alerts.filters import Actor, AlertState, DateObserved, Severity


def get_thirty_days_ago():
    now = datetime.now(tz=timezone.utc)
    return now - timedelta(days=30)


def parse_datetime(date_str):
    date_time_obj = dateutil.parser.parse(date_str)
    if date_time_obj.utcoffset():
        date_time_obj = date_time_obj.replace(tzinfo=timezone.utc) - date_time_obj.utcoffset()
    else:
        date_time_obj = date_time_obj.replace(tzinfo=timezone.utc)
    return date_time_obj


def build_date_range_filter(date_filter_cls, start_date_str, end_date_str):
    if start_date_str and not end_date_str:
        return date_filter_cls.on_or_after(parse_datetime(start_date_str))
    elif end_date_str and not start_date_str:
        return date_filter_cls.on_or_before(parse_datetime(end_date_str))
    elif end_date_str and start_date_str:
        start_datetime = parse_datetime(start_date_str)
        end_datetime = parse_datetime(end_date_str)
        if start_datetime >= end_datetime:
            raise Exception("Start date cannot be after end date.")
        return date_filter_cls.in_range(start_datetime, end_datetime)
    else:
        return date_filter_cls.on_or_after(get_thirty_days_ago())


def build_alerts_query(start_date, end_date, username=None, alert_state=None, severities=None):
    filters = []
    if username is not None:
        filters.append(Actor.eq(username))
    if alert_state is not None:
        filters.append(AlertState.eq(alert_state))
    if severities:
        filters.append(Severity.is_in(severities))
    filters.append(build_date_range_filter(DateObserved, start_date, end_date))
    query = AlertQuery.all(*filters)
    query.sort_direction = "asc"
    return query
