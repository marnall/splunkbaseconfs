from FilterCondition import FilterCondition
from Filters import Filters
from Query import Query
from RequestParams import RequestParams
from Rows import Rows
from SearchRequest import SearchRequest
from AlertAttributes import AlertAttributes
from EventAttributes import EventAttributes

from datetime import timedelta

from Constants import MAX_DAYS_BACK, ALERT_STATUSES, ALERT_SEVERITIES


class QueryBuilder:

    @staticmethod
    def build_alert_query(threat_model_names,
                          threat_model_ids,
                          alertIds, start_time,
                          end_time, ingest_time_from,
                          ingest_time_to, device_names,
                          user_names,
                          last_days,
                          alert_statuses,
                          alert_severities,
                          alert_category_ids,
                          extra_fields,
                          descending_order):

        search_request = SearchRequest() \
            .set_query(
            Query().set_entity_name("Alert")
            .set_filter(Filters().set_filter_operator(0))
        ) \
            .set_rows(
            Rows()
            .set_grouping("")
        ) \
            .set_request_params(
            RequestParams().set_search_source(1).set_search_source_name("MainTab")
        )

        alert_attributes = AlertAttributes()
        for column in alert_attributes.get_fields(extra_fields):
            search_request.rows.add_column(column)

        filter_condition = FilterCondition()\
            .set_path("Alert.AggregationFilter")\
            .set_operator("Equals")\
            .add_value({"Alert.AggregationFilter": 1})\

        search_request.query.filter.add_filter(filter_condition)

        if ingest_time_from and ingest_time_to:
            ingest_time_condition = FilterCondition().set_path(alert_attributes.Alert_IngestTime) \
                .set_operator("Between") \
                .add_value({alert_attributes.Alert_IngestTime: ingest_time_from.isoformat(
            ), f"{alert_attributes.Alert_IngestTime}0": ingest_time_to.isoformat()})
            search_request.query.filter.add_filter(ingest_time_condition)
        else:
            days_back = MAX_DAYS_BACK
            if start_time is None and end_time is None and last_days is None:
                last_days = days_back
            elif start_time is None and end_time is not None:
                start_time = end_time - timedelta(days=days_back)
            elif end_time is None and start_time is not None:
                end_time = start_time + timedelta(days=days_back)

            time_condition = FilterCondition().set_path(alert_attributes.Alert_TimeUTC)
            if start_time and end_time:
                time_condition = time_condition \
                    .set_operator("Between") \
                    .add_value({alert_attributes.Alert_TimeUTC: start_time.isoformat(
                ), f"{alert_attributes.Alert_TimeUTC}0": end_time.isoformat()})  # "displayValue": start_time.isoformat(),
            if last_days:
                time_condition \
                    .set_operator("LastDays") \
                    .add_value({alert_attributes.Alert_TimeUTC: last_days, "displayValue": last_days})
            search_request.query.filter.add_filter(time_condition)

        if threat_model_names:
            rule_condition = FilterCondition() \
                .set_path(alert_attributes.Alert_Rule_Name) \
                .set_operator("In")
            for threat_model_name in threat_model_names:
                rule_condition.add_value({alert_attributes.Alert_Rule_Name: threat_model_name, "displayValue": "New"})
            search_request.query.filter.add_filter(rule_condition)

        if threat_model_ids:
            rule_id_condition = FilterCondition() \
                .set_path(alert_attributes.Alert_Rule_ID) \
                .set_operator("In")
            for threat_model_id in threat_model_ids:
                rule_id_condition.add_value({alert_attributes.Alert_Rule_ID: threat_model_id, "displayValue": "New"})
            search_request.query.filter.add_filter(rule_id_condition)

        if alert_category_ids:
            category_condition = FilterCondition() \
                .set_path(alert_attributes.Alert_Rule_Category_ID) \
                .set_operator("In")
            for alert_category_id in alert_category_ids:
                category_condition.add_value({alert_attributes.Alert_Rule_Category_ID: alert_category_id})
            search_request.query.filter.add_filter(category_condition)

        if alertIds:
            alert_condition = FilterCondition() \
                .set_path(alert_attributes.Alert_ID) \
                .set_operator("In")
            for alertId in alertIds:
                alert_condition.add_value({alert_attributes.Alert_ID: alertId, "displayValue": "New"})
            search_request.query.filter.add_filter(alert_condition)

        if device_names:
            device_condition = FilterCondition() \
                .set_path(alert_attributes.Alert_Device_HostName) \
                .set_operator("In")
            for device_name in device_names:
                device_condition.add_value({alert_attributes.Alert_Device_HostName: device_name, "displayValue": device_name})
            search_request.query.filter.add_filter(device_condition)

        if user_names:
            user_condition = FilterCondition() \
                .set_path(alert_attributes.Alert_User_Identity_Name) \
                .set_operator("In")
            for user_name in user_names:
                user_condition.add_value({alert_attributes.Alert_User_Identity_Name: user_name, "displayValue": user_name})
            search_request.query.filter.add_filter(user_condition)

        if not alert_statuses:
            alert_statuses = ALERT_STATUSES.keys()
        if not alert_severities:
            severities = ALERT_SEVERITIES.keys()

        if alert_statuses:
            status_condition = FilterCondition() \
                .set_path(alert_attributes.Alert_Status_ID) \
                .set_operator("In")
            for status in alert_statuses:
                status_id = ALERT_STATUSES[status.lower()]
                status_condition.add_value({alert_attributes.Alert_Status_ID: status_id, "displayValue": status})
            search_request.query.filter.add_filter(status_condition)

        if alert_severities:
            severity_condition = FilterCondition() \
                .set_path(alert_attributes.Alert_Rule_Severity_ID) \
                .set_operator("In")
            for severity in alert_severities:
                severity_id = ALERT_SEVERITIES[severity.lower()]
                severity_condition.add_value({alert_attributes.Alert_Rule_Severity_ID: severity_id, "displayValue": severity})
            search_request.query.filter.add_filter(severity_condition)

        if descending_order:
            search_request.rows.add_ordering({"path": "Alert.TimeUTC", "sortOrder": "Desc"})
        else:
            search_request.rows.add_ordering({"path": "Alert.TimeUTC", "sortOrder": "Asc"})

        search_request_json = search_request.to_json()
        return search_request_json

    @staticmethod
    def build_event_query(alertIds, start_time, end_time, last_days, extra_fields, descending_order):
        days_back = MAX_DAYS_BACK
        if start_time is None and end_time is None and last_days is None:
            last_days = days_back
        elif start_time is None and end_time is not None:
            start_time = end_time - timedelta(days=days_back)
        elif end_time is None and start_time is not None:
            end_time = start_time + timedelta(days=days_back)

        search_request = SearchRequest() \
            .set_query(
            Query()
            .set_entity_name("Event")
            .set_filter(Filters().set_filter_operator(0))
        ) \
            .set_rows(Rows().set_grouping("")) \
            .set_request_params(RequestParams().set_search_source(1).set_search_source_name("MainTab"))

        event_attributes = EventAttributes()
        for column in event_attributes.get_fields(extra_fields):
            search_request.rows.add_column(column)

        if alertIds and len(alertIds) > 0:
            time_condition = FilterCondition() \
                .set_path(event_attributes.Event_Alert_ID) \
                .set_operator("In")
            for alertId in alertIds:
                time_condition.add_value({event_attributes.Event_Alert_ID: alertId, "displayValue": alertId})

            search_request.query.filter.add_filter(time_condition)

        time_condition = FilterCondition().set_path(event_attributes.Event_TimeUTC)
        if start_time and end_time:
            time_condition = time_condition \
                .set_operator("Between") \
                .add_value({event_attributes.Event_TimeUTC: start_time.isoformat(),
                            f"{event_attributes.Event_TimeUTC}0": end_time.isoformat()})
            
        if last_days:
            time_condition \
                .set_operator("LastDays") \
                .add_value({event_attributes.Event_TimeUTC: last_days, "displayValue": last_days})
        search_request.query.filter.add_filter(time_condition)

        if descending_order:
            search_request.rows.add_ordering({"path": event_attributes.Event_TimeUTC, "sortOrder": "Desc"})
        else:
            search_request.rows.add_ordering({"path": event_attributes.Event_TimeUTC, "sortOrder": "Asc"})

        search_request_json = search_request.to_json()
        return search_request_json
