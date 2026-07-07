# File: varonissaas_search.py
#
# Copyright (c) Varonis, 2024-2025
#
# This unpublished material is proprietary to Varonis SaaS. All
# rights reserved. The methods and techniques described herein are
# considered trade secrets and/or confidential. Reproduction or
# distribution, in whole or in part, is forbidden except by express
# written permission of Varonis SaaS.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional, TypeVar

from varonissaas_consts import VDSP_MAX_DAYS_BACK
from varonissaas_tools import *


TFilter = TypeVar("TFilter", bound="Filter")
TFilterGroup = TypeVar("TFilterGroup", bound="FilterGroup")
TQuery = TypeVar("TQuery", bound="Query")
TRows = TypeVar("TRows", bound="Rows")
TRequestParams = TypeVar("TRequestParams", bound="RequestParams")
TSearchRequest = TypeVar("TSearchRequest", bound="SearchRequest")
TAlertSearchQueryBuilder = TypeVar("TAlertSearchQueryBuilder", bound="AlertSearchQueryBuilder")
TSearchRequestBuilder = TypeVar("TSearchRequestBuilder", bound="SearchRequestBuilder")
TEventSearchQueryBuilder = TypeVar("TEventSearchQueryBuilder", bound="EventSearchQueryBuilder")

ALERT_STATUSES = {"new": 1, "under investigation": 2, "closed": 3}
ALERT_SEVERITIES = {"high": 0, "medium": 1, "low": 2, "informational": 3}
CLOSE_REASONS = {
    "none": 0,
    "other": 1,
    "benign activity": 2,
    "true positive": 3,
    "environment misconfiguration": 4,
    "alert recently customized": 5,
    "inaccurate alert logic": 6,
    "authorized activity": 7,
}


""" MODELS """


class EmOperator(Enum):
    In = 1
    NotIn = 2
    Between = 3
    Equals = 4
    NotEquals = 5
    Contains = 6
    NotContains = 7
    LastDays = 10
    IncludesAny = 11
    IncludesAll = 12
    ExcludesAll = 13
    GreaterThan = 14
    LessThan = 0xF
    QueryId = 0x10
    NotInQueryId = 17
    IsEmpty = 20
    InNestedSearch = 21
    NotInNestedSearch = 22
    HasValue = 23


class FilterOperator(Enum):
    And = 0
    Or = 1


class Filter:
    def __init__(self):
        self.path = None
        self.operator = None
        self.values = []

    def set_path(self: TFilter, path: str) -> TFilter:
        self.path = path
        return self

    def set_operator(self: TFilter, operator: EmOperator) -> TFilter:
        self.operator = operator.value
        return self

    def add_value(self: TFilter, value: Any) -> TFilter:
        self.values.append(value)  # FilterValue(value)
        return self

    def __repr__(self) -> str:
        return f"{self.path} {self.operator} {self.values}"


class FilterGroup:
    def __init__(self):
        self.filterOperator = None
        self.filters = []

    def set_filter_operator(self: TFilterGroup, filter_operator: FilterOperator) -> TFilterGroup:
        self.filterOperator = filter_operator.value
        return self

    def add_filter(self: TFilterGroup, filter_: Filter) -> TFilterGroup:
        self.filters.append(filter_)
        return self

    def __repr__(self) -> str:
        return f"Filter Operator: {self.filterOperator}, Filters: {self.filters}"


class Query:
    def __init__(self):
        self.entityName = None
        self.filter = FilterGroup()

    def set_entity_name(self: TQuery, entity_name: str) -> TQuery:
        self.entityName = entity_name
        return self

    def set_filter(self: TQuery, filter_: FilterGroup) -> TQuery:
        self.filter = filter_
        return self

    def __repr__(self) -> str:
        return f"Entity Name: {self.entityName}, Filter: {self.filter}"


class Rows:
    def __init__(self):
        self.columns = []
        self.filter = []
        self.grouping = None
        self.ordering = []

    def set_columns(self: TRows, columns: list[str]) -> TRows:
        self.columns = columns
        return self

    def add_filter(self: TRows, filter_) -> TRows:
        self.filter.append(filter_)
        return self

    def add_ordering(self: TRows, ordering) -> TRows:
        self.ordering.append(ordering)
        return self

    def __repr__(self) -> str:
        return f"Columns: {self.columns}, Filter: {self.filter}, Grouping: {self.grouping}, Ordering: {self.ordering}"


class RequestParams:
    def __init__(self):
        self.searchSource = None
        self.searchSourceName = None

    def set_search_source(self: TRequestParams, search_source: int) -> TRequestParams:
        self.searchSource = search_source
        return self

    def set_search_source_name(self: TRequestParams, search_source_name: str) -> TRequestParams:
        self.searchSourceName = search_source_name
        return self

    def __repr__(self) -> str:
        return f"Search Source: {self.searchSource}, Search Source Name: {self.searchSourceName}"


class SearchRequest:
    def __init__(self):
        self.query = Query()
        self.rows = Rows()
        self.requestParams = RequestParams()

    def set_query(self: TSearchRequest, query: Query) -> TSearchRequest:
        self.query = query
        return self

    def set_rows(self: TSearchRequest, rows: Rows) -> TSearchRequest:
        self.rows = rows
        return self

    def set_request_params(self: TSearchRequest, request_params: RequestParams) -> TSearchRequest:
        self.requestParams = request_params
        return self

    def __repr__(self) -> str:
        return f"Query: {self.query}, Rows: {self.rows}, Request Params: {self.requestParams}"

    def to_dict(self) -> str:
        result = object_to_dict(self)
        return result

    def __eq__(self, __value: object) -> bool:
        if isinstance(__value, dict):
            return self.to_dict() == __value
        elif isinstance(self, type(__value)):
            return self.to_dict() == __value.to_dict()
        else:
            return False


class AlertAttributes:
    Id = "Alert.ID"
    RuleName = "Alert.Rule.Name"
    RuleId = "Alert.Rule.ID"
    Time = "Alert.TimeUTC"
    RuleSeverityName = "Alert.Rule.Severity.Name"
    RuleSeverityId = "Alert.Rule.Severity.ID"
    RuleCategoryName = "Alert.Rule.Category.Name"
    LocationCountryName = "Alert.Location.CountryName"
    LocationSubdivisionName = "Alert.Location.SubdivisionName"
    StatusName = "Alert.Status.Name"
    StatusId = "Alert.Status.ID"
    EventsCount = "Alert.EventsCount"
    InitialEventUtcTime = "Alert.Initial.Event.TimeUTC"
    UserName = "Alert.User.Name"
    UserSamAccountName = "Alert.User.SamAccountName"
    UserAccountTypeName = "Alert.User.AccountType.Name"
    DeviceHostname = "Alert.Device.HostName"
    DeviceIsMaliciousExternalIp = "Alert.Device.IsMaliciousExternalIP"
    DeviceExternalIpThreatTypesName = "Alert.Device.ExternalIPThreatTypesName"
    DataIsFlagged = "Alert.Data.IsFlagged"
    DataIsSensitive = "Alert.Data.IsSensitive"
    FilerPlatformName = "Alert.Filer.Platform.Name"
    AssetPath = "Alert.Asset.Path"
    FilerName = "Alert.Filer.Name"
    CloseReasonName = "Alert.CloseReason.Name"
    LocationBlacklistedLocation = "Alert.Location.BlacklistedLocation"
    LocationAbnormalLocation = "Alert.Location.AbnormalLocation"
    SidId = "Alert.User.SidID"
    Aggregate = "Alert.AggregationFilter"
    IngestTime = "Alert.IngestTime"
    UserIdentityName = "Alert.User.Identity.Name"

    Columns = [
        Id,
        RuleName,
        RuleId,
        Time,
        RuleSeverityName,
        RuleSeverityId,
        RuleCategoryName,
        LocationCountryName,
        LocationSubdivisionName,
        StatusName,
        StatusId,
        EventsCount,
        InitialEventUtcTime,
        UserName,
        UserSamAccountName,
        UserAccountTypeName,
        DeviceHostname,
        DeviceIsMaliciousExternalIp,
        DeviceExternalIpThreatTypesName,
        DataIsFlagged,
        DataIsSensitive,
        FilerPlatformName,
        AssetPath,
        FilerName,
        CloseReasonName,
        LocationBlacklistedLocation,
        LocationAbnormalLocation,
        SidId,
        IngestTime,
    ]


class EventAttributes:
    EventAlertId = "Event.Alert.ID"
    EventGuid = "Event.ID"
    EventTypeName = "Event.Type.Name"
    EventTimeUtc = "Event.TimeUTC"
    EventStatusName = "Event.Status.Name"
    EventDescription = "Event.Description"
    EventLocationCountryName = "Event.Location.Country.Name"
    EventLocationSubdivisionName = "Event.Location.Subdivision.Name"
    EventLocationBlacklistedLocation = "Event.Location.BlacklistedLocation"
    EventOperationName = "Event.Operation.Name"
    EventByAccountIdentityName = "Event.ByAccount.Identity.Name"
    EventByAccountTypeName = "Event.ByAccount.Type.Name"
    EventByAccountDomainName = "Event.ByAccount.Domain.Name"
    EventByAccountSamAccountName = "Event.ByAccount.SamAccountName"
    EventFilerName = "Event.Filer.Name"
    EventFilerPlatformName = "Event.Filer.Platform.Name"
    EventIp = "Event.IP"
    EventDeviceExternalIp = "Event.Device.ExternalIP.IP"
    EventDestinationIp = "Event.Destination.IP"
    EventDeviceName = "Event.Device.Name"
    EventDestinationDeviceName = "Event.Destination.DeviceName"
    EventByAccountIsDisabled = "Event.ByAccount.IsDisabled"
    EventByAccountIsStale = "Event.ByAccount.IsStale"
    EventByAccountIsLockout = "Event.ByAccount.IsLockout"
    EventDeviceExternalIpThreatTypesName = "Event.Device.ExternalIP.ThreatTypes.Name"
    EventDeviceExternalIpIsMalicious = "Event.Device.ExternalIP.IsMalicious"
    EventDeviceExternalIpReputationName = "Event.Device.ExternalIP.Reputation.Name"
    EventOnObjectName = "Event.OnObjectName"
    EventOnResourceObjectTypeName = "Event.OnResource.ObjectType.Name"
    EventOnAccountSamAccountName = "Event.OnAccount.SamAccountName"
    EventOnResourceIsSensitive = "Event.OnResource.IsSensitive"
    EventOnAccountIsDisabled = "Event.OnAccount.IsDisabled"
    EventOnAccountIsLockout = "Event.OnAccount.IsLockout"
    EventOnResourcePath = "Event.OnResource.Path"

    Columns = [
        EventAlertId,
        EventGuid,
        EventTypeName,
        EventTimeUtc,
        EventStatusName,
        EventDescription,
        EventLocationCountryName,
        EventLocationSubdivisionName,
        EventLocationBlacklistedLocation,
        EventOperationName,
        EventByAccountIdentityName,
        EventByAccountTypeName,
        EventByAccountDomainName,
        EventByAccountSamAccountName,
        EventFilerName,
        EventFilerPlatformName,
        EventIp,
        EventDeviceExternalIp,
        EventDestinationIp,
        EventDeviceName,
        EventDestinationDeviceName,
        EventByAccountIsDisabled,
        EventByAccountIsStale,
        EventByAccountIsLockout,
        EventDeviceExternalIpThreatTypesName,
        EventDeviceExternalIpIsMalicious,
        EventDeviceExternalIpReputationName,
        EventOnObjectName,
        EventOnResourceObjectTypeName,
        EventOnAccountSamAccountName,
        EventOnResourceIsSensitive,
        EventOnAccountIsDisabled,
        EventOnAccountIsLockout,
        EventOnResourcePath,
    ]


class ThreatModelAttributes:
    Id = "ruleID"
    Name = "ruleName"
    Category = "ruleArea"
    Source = "ruleSource"
    Severity = "severity"

    Columns = [Id, Name, Category, Source, Severity]


class AlertItem:
    def __init__(self):
        self.ID: str = None
        self.Name: str = None
        self.Time: datetime = None
        self.Severity: str = None
        self.SeverityId: int = None
        self.Category: str = None
        self.Country: Optional[list[str]] = None
        self.State: Optional[list[str]] = None
        self.Status: str = None
        self.StatusId: int = None
        self.CloseReason: Optional[str] = None
        self.BlacklistLocation: Optional[bool] = None
        self.AbnormalLocation: Optional[str] = None
        self.NumOfAlertedEvents: int = None
        self.UserName: Optional[str] = None
        self.SamAccountName: Optional[str] = None
        self.PrivilegedAccountType: Optional[str] = None
        self.ContainMaliciousExternalIP: Optional[bool] = None
        self.IPThreatTypes: Optional[str] = None
        self.Asset: Optional[str] = None
        self.AssetContainsFlaggedData: Optional[bool] = None
        self.AssetContainsSensitiveData: Optional[bool] = None
        self.Platform: str = None
        self.FileServerOrDomain: str = None
        self.EventUTC: Optional[datetime] = None
        self.DeviceName: str = None
        self.IngestTime: datetime = None

        self.Url: str = None

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"{key} not found in AlertItem")

    def to_dict(self) -> dict[str, Any]:
        return object_to_dict(self)


class EventItem:
    def __init__(self):
        self.ID: Optional[str] = None
        self.AlertId: Optional[str] = None
        self.Type: Optional[str] = None
        self.TimeUTC: Optional[datetime] = None
        self.Status: Optional[str] = None
        self.Description: Optional[str] = None
        self.Country: Optional[str] = None
        self.State: Optional[str] = None
        self.BlacklistedLocation: Optional[bool] = None
        self.EventOperation: Optional[str] = None
        self.ByUserAccount: Optional[str] = None
        self.ByUserAccountType: Optional[str] = None
        self.ByUserAccountDomain: Optional[str] = None
        self.BySamAccountName: Optional[str] = None
        self.Filer: Optional[str] = None
        self.Platform: Optional[str] = None
        self.SourceIP: Optional[str] = None
        self.ExternalIP: Optional[str] = None
        self.DestinationIP: Optional[str] = None
        self.SourceDevice: Optional[str] = None
        self.DestinationDevice: Optional[str] = None
        self.IsDisabledAccount: Optional[bool] = None
        self.IsLockoutAccount: Optional[bool] = None
        self.IsStaleAccount: Optional[bool] = None
        self.IsMaliciousIP: Optional[bool] = None
        self.ExternalIPThreatTypes: Optional[str] = None
        self.ExternalIPReputation: Optional[str] = None
        self.OnObjectName: Optional[str] = None
        self.OnObjectType: Optional[str] = None
        self.OnSamAccountName: Optional[str] = None
        self.IsSensitive: Optional[bool] = None
        self.OnAccountIsDisabled: Optional[bool] = None
        self.OnAccountIsLockout: Optional[bool] = None
        self.Path: Optional[str] = None

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"{key} not found in EventItem")

    def to_dict(self) -> dict[str, Any]:
        return object_to_dict(self)


class ThreatModelItem:
    def __init__(self):
        self.Id: Optional[str] = None
        self.Name: Optional[list[str]] = None
        self.Category: Optional[str] = None
        self.Severity: Optional[str] = None
        self.Source: Optional[str] = None

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"{key} not found in EventItem")

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in self.__dict__.items() if value is not None}


""" MAPPERS """


class SearchAlertObjectMapper:
    def map(self, json_data: dict[str, Any]) -> list[AlertItem]:
        key_valued_objects = convert_json_to_key_value(json_data)

        mapped_items = []
        for obj in key_valued_objects:
            mapped_items.append(self.map_item(obj))

        return mapped_items

    def map_item(self, row: dict[str, Any]) -> AlertItem:
        alert_item = AlertItem()
        alert_item.ID = row[AlertAttributes.Id]
        alert_item.Name = row[AlertAttributes.RuleName]
        alert_item.Time = row[AlertAttributes.Time]
        alert_item.Severity = row[AlertAttributes.RuleSeverityName]
        alert_item.SeverityId = try_convert(row[AlertAttributes.RuleSeverityId], lambda x: int(x))
        alert_item.Category = row[AlertAttributes.RuleCategoryName]
        alert_item.Country = row[AlertAttributes.LocationCountryName]
        alert_item.State = row[AlertAttributes.LocationSubdivisionName]
        alert_item.Status = row[AlertAttributes.StatusName]
        alert_item.StatusId = try_convert(row[AlertAttributes.StatusId], lambda x: int(x))
        alert_item.CloseReason = row[AlertAttributes.CloseReasonName]
        alert_item.BlacklistLocation = row.get(AlertAttributes.LocationBlacklistedLocation)
        alert_item.AbnormalLocation = row[AlertAttributes.LocationAbnormalLocation]
        alert_item.NumOfAlertedEvents = try_convert(row[AlertAttributes.EventsCount], lambda x: int(x))
        alert_item.UserName = row[AlertAttributes.UserName]
        alert_item.SamAccountName = row[AlertAttributes.UserSamAccountName]
        alert_item.PrivilegedAccountType = row[AlertAttributes.UserAccountTypeName]
        alert_item.ContainMaliciousExternalIP = try_convert(
            row.get(AlertAttributes.DeviceIsMaliciousExternalIp),
            lambda x: parse_bool_list(x),
        )
        alert_item.IPThreatTypes = row[AlertAttributes.DeviceExternalIpThreatTypesName]
        alert_item.Asset = row[AlertAttributes.AssetPath]
        alert_item.AssetContainsFlaggedData = try_convert(row[AlertAttributes.DataIsFlagged], lambda x: parse_bool_list(x))
        alert_item.AssetContainsSensitiveData = try_convert(row[AlertAttributes.DataIsSensitive], lambda x: parse_bool_list(x))
        alert_item.Platform = row[AlertAttributes.FilerPlatformName]
        alert_item.FileServerOrDomain = row[AlertAttributes.FilerName]
        alert_item.DeviceName = row[AlertAttributes.DeviceHostname]
        alert_item.IngestTime = try_convert(
            row.get(AlertAttributes.IngestTime),
            lambda x: datetime.strptime(x, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc),
        )
        alert_item.EventUTC = try_convert(
            row.get(AlertAttributes.InitialEventUtcTime),
            lambda x: datetime.strptime(x, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc),
        )

        return alert_item


class SearchEventObjectMapper:
    def map(self, json_data: dict[str, Any]) -> list[EventItem]:
        key_valued_objects = convert_json_to_key_value(json_data)

        mapped_items = []
        for obj in key_valued_objects:
            mapped_items.extend(self.map_item(obj))

        return mapped_items

    def map_item(self, row: dict[str, Any]) -> list[EventItem]:
        alertIds = row.get(EventAttributes.EventAlertId)
        alertIds = multi_value_to_string_list(alertIds)

        event_items = []

        for alertId in alertIds:
            event_item = EventItem()

            event_item.AlertId = alertId
            event_item.ID = row.get(EventAttributes.EventGuid, "")
            event_item.Type = row.get(EventAttributes.EventTypeName)
            event_item.TimeUTC = try_convert(
                row.get(EventAttributes.EventTimeUtc),
                lambda x: datetime.strptime(x, "%Y-%m-%dT%H:%M:%S.%f%z").replace(tzinfo=timezone.utc),
            )
            event_item.Status = row.get(EventAttributes.EventStatusName)
            event_item.Description = row.get(EventAttributes.EventDescription)
            event_item.Country = row.get(EventAttributes.EventLocationCountryName)
            event_item.State = row.get(EventAttributes.EventLocationSubdivisionName)
            event_item.BlacklistedLocation = try_convert(
                row.get(EventAttributes.EventLocationBlacklistedLocation),
                lambda x: parse_bool(x),
            )
            event_item.EventOperation = row.get(EventAttributes.EventOperationName)
            event_item.ByUserAccount = row.get(EventAttributes.EventByAccountIdentityName)
            event_item.ByUserAccountType = row.get(EventAttributes.EventByAccountTypeName)
            event_item.ByUserAccountDomain = row.get(EventAttributes.EventByAccountDomainName)
            event_item.BySamAccountName = row.get(EventAttributes.EventByAccountSamAccountName)
            event_item.Filer = row.get(EventAttributes.EventFilerName)
            event_item.Platform = row.get(EventAttributes.EventFilerPlatformName)
            event_item.SourceIP = row.get(EventAttributes.EventIp)
            event_item.ExternalIP = row.get(EventAttributes.EventDeviceExternalIp)
            event_item.DestinationIP = row.get(EventAttributes.EventDestinationIp)
            event_item.SourceDevice = row.get(EventAttributes.EventDeviceName)
            event_item.DestinationDevice = row.get(EventAttributes.EventDestinationDeviceName)
            event_item.IsDisabledAccount = try_convert(
                row.get(EventAttributes.EventByAccountIsDisabled),
                lambda x: parse_bool(x),
            )
            event_item.IsLockoutAccount = try_convert(
                row.get(EventAttributes.EventByAccountIsLockout),
                lambda x: parse_bool(x),
            )
            event_item.IsStaleAccount = try_convert(row.get(EventAttributes.EventByAccountIsStale), lambda x: parse_bool(x))
            event_item.IsMaliciousIP = try_convert(
                row.get(EventAttributes.EventDeviceExternalIpIsMalicious),
                lambda x: parse_bool(x),
            )
            event_item.ExternalIPThreatTypes = row.get(EventAttributes.EventDeviceExternalIpThreatTypesName, "")
            event_item.ExternalIPReputation = row.get(EventAttributes.EventDeviceExternalIpReputationName)
            event_item.OnObjectName = row.get(EventAttributes.EventOnObjectName)
            event_item.OnObjectType = row.get(EventAttributes.EventOnResourceObjectTypeName)
            event_item.OnSamAccountName = row.get(EventAttributes.EventOnAccountSamAccountName)
            event_item.IsSensitive = try_convert(
                row.get(EventAttributes.EventOnResourceIsSensitive),
                lambda x: parse_bool(x),
            )
            event_item.OnAccountIsDisabled = try_convert(
                row.get(EventAttributes.EventOnAccountIsDisabled),
                lambda x: parse_bool(x),
            )
            event_item.OnAccountIsLockout = try_convert(
                row.get(EventAttributes.EventOnAccountIsLockout),
                lambda x: parse_bool(x),
            )
            event_item.Path = row.get(EventAttributes.EventOnResourcePath)
            event_items.append(event_item)

        return event_items


class ThreatModelObjectMapper:
    def map(self, json_data) -> list[dict[str, Any]]:
        key_valued_objects = json_data

        mapped_items = []
        for obj in key_valued_objects:
            mapped_items.append(self.map_item(obj).to_dict())

        return mapped_items

    def map_item(self, row: dict[str, str]) -> ThreatModelItem:
        threat_model_item = ThreatModelItem()
        threat_model_item.ID = row[ThreatModelAttributes.Id]
        threat_model_item.Name = row[ThreatModelAttributes.Name]
        threat_model_item.Category = row[ThreatModelAttributes.Category]
        threat_model_item.Source = row[ThreatModelAttributes.Source]
        threat_model_item.Severity = row[ThreatModelAttributes.Severity]

        return threat_model_item


class AlertSearchQueryBuilder:
    def __init__(self):
        self.search_query = Query().set_entity_name("Alert").set_filter(FilterGroup().set_filter_operator(FilterOperator.And))

    def with_severities(self: TAlertSearchQueryBuilder, severities: list[str]) -> TAlertSearchQueryBuilder:
        if severities:
            severity_condition = Filter().set_path(AlertAttributes.RuleSeverityId).set_operator(EmOperator.In)
            for severity in severities:
                severity_id = ALERT_SEVERITIES[severity.lower()]
                severity_condition.add_value(
                    {
                        AlertAttributes.RuleSeverityId: severity_id,
                        "displayValue": severity,
                    }
                )
            self.search_query.filter.add_filter(severity_condition)
        return self

    def with_threat_models(self: TAlertSearchQueryBuilder, threat_models: list[str]) -> TAlertSearchQueryBuilder:
        if threat_models:
            rule_condition = Filter().set_path(AlertAttributes.RuleName).set_operator(EmOperator.In)
            for threat_model in threat_models:
                rule_condition.add_value({AlertAttributes.RuleName: threat_model, "displayValue": "New"})
            self.search_query.filter.add_filter(rule_condition)
        return self

    def with_alert_ids(self: TAlertSearchQueryBuilder, alert_ids: list[str]) -> TAlertSearchQueryBuilder:
        if alert_ids:
            alert_condition = Filter().set_path(AlertAttributes.Id).set_operator(EmOperator.In)
            for alert_id in alert_ids:
                alert_condition.add_value({AlertAttributes.Id: alert_id, "displayValue": "New"})
            self.search_query.filter.add_filter(alert_condition)
        return self

    def with_device(self: TAlertSearchQueryBuilder, devices: list[str]) -> TAlertSearchQueryBuilder:
        if devices:
            device_condition = Filter().set_path(AlertAttributes.DeviceHostname).set_operator(EmOperator.In)
            for device in devices:
                device_condition.add_value({AlertAttributes.DeviceHostname: device, "displayValue": device})
            self.search_query.filter.add_filter(device_condition)
        return self

    def with_users(self: TAlertSearchQueryBuilder, users: list[str]) -> TAlertSearchQueryBuilder:
        if users:
            user_condition = Filter().set_path(AlertAttributes.UserIdentityName).set_operator(EmOperator.In)
            for user_name in users:
                user_condition.add_value(
                    {
                        AlertAttributes.UserIdentityName: user_name,
                        "displayValue": user_name,
                    }
                )
            self.search_query.filter.add_filter(user_condition)
        return self

    def with_statuses(self: TAlertSearchQueryBuilder, statuses: list[str]) -> TAlertSearchQueryBuilder:
        if statuses:
            status_condition = Filter().set_path(AlertAttributes.StatusId).set_operator(EmOperator.In)
            for status in statuses:
                status_id = ALERT_STATUSES[status.lower()]
                status_condition.add_value({AlertAttributes.StatusId: status_id, "displayValue": status})
            self.search_query.filter.add_filter(status_condition)
        return self

    def with_time_range(
        self: TAlertSearchQueryBuilder,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
    ) -> TAlertSearchQueryBuilder:
        days_back = VDSP_MAX_DAYS_BACK
        if start_time is None and end_time is not None:
            start_time = end_time - timedelta(days=days_back)
        elif end_time is None and start_time is not None:
            end_time = start_time + timedelta(days=days_back)

        if start_time and end_time:
            time_condition = (
                Filter()
                .set_path(AlertAttributes.Time)
                .set_operator(EmOperator.Between)
                .add_value(
                    {
                        AlertAttributes.Time: start_time.isoformat(),
                        f"{AlertAttributes.Time}0": end_time.isoformat(),
                    }
                )
            )
            self.search_query.filter.add_filter(time_condition)
        return self

    def with_ingest_time_range(
        self: TAlertSearchQueryBuilder,
        start: Optional[datetime],
        end: Optional[datetime],
    ) -> TAlertSearchQueryBuilder:
        if start and end:
            ingest_time_condition = (
                Filter()
                .set_path(AlertAttributes.IngestTime)
                .set_operator(EmOperator.Between)
                .add_value(
                    {
                        AlertAttributes.IngestTime: start.isoformat(),
                        f"{AlertAttributes.IngestTime}0": end.isoformat(),
                    }
                )
            )
            self.search_query.filter.add_filter(ingest_time_condition)
        return self

    def with_last_days(self: TAlertSearchQueryBuilder, last_days: Optional[int]) -> TAlertSearchQueryBuilder:
        if last_days:
            time_condition = (
                Filter()
                .set_path(AlertAttributes.Time)
                .set_operator(EmOperator.LastDays)
                .add_value({AlertAttributes.Time: last_days, "displayValue": last_days})
            )
            self.search_query.filter.add_filter(time_condition)
        return self

    def with_aggregation(self: TAlertSearchQueryBuilder) -> TAlertSearchQueryBuilder:
        aggregation = Filter().set_path(AlertAttributes.Aggregate).set_operator(EmOperator.Equals).add_value({AlertAttributes.Aggregate: 1})
        self.search_query.filter.add_filter(aggregation)
        return self

    def build(self) -> Query:
        return self.search_query


class EventSearchQueryBuilder:
    def __init__(
        self,
    ):
        self.search_query = Query().set_entity_name("Event").set_filter(FilterGroup().set_filter_operator(FilterOperator.And))

    def with_alert_ids(self: TEventSearchQueryBuilder, alert_ids: list[str]) -> TEventSearchQueryBuilder:
        if alert_ids:
            event_condition = Filter().set_path(EventAttributes.EventAlertId).set_operator(EmOperator.In)
            for alert_id in alert_ids:
                event_condition.add_value({EventAttributes.EventAlertId: alert_id})
            self.search_query.filter.add_filter(event_condition)
        return self

    def with_time_range(
        self: TEventSearchQueryBuilder,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
    ) -> TEventSearchQueryBuilder:
        days_back = VDSP_MAX_DAYS_BACK
        if start_time is None and end_time is not None:
            start_time = end_time - timedelta(days=days_back)
        elif end_time is None and start_time is not None:
            end_time = start_time + timedelta(days=days_back)

        if start_time and end_time:
            time_condition = (
                Filter()
                .set_path(EventAttributes.EventTimeUtc)
                .set_operator(EmOperator.Between)
                .add_value(
                    {
                        EventAttributes.EventTimeUtc: start_time.isoformat(),
                        f"{EventAttributes.EventTimeUtc}0": end_time.isoformat(),
                    }
                )
            )
            self.search_query.filter.add_filter(time_condition)
        return self

    def with_last_days(self: TEventSearchQueryBuilder, last_days: Optional[int]) -> TEventSearchQueryBuilder:
        if last_days:
            time_condition = (
                Filter()
                .set_path(EventAttributes.EventTimeUtc)
                .set_operator(EmOperator.LastDays)
                .add_value({EventAttributes.EventTimeUtc: last_days, "displayValue": last_days})
            )
            self.search_query.filter.add_filter(time_condition)
        return self

    def build(self) -> Query:
        return self.search_query


class SearchRequestBuilder:
    def __init__(self, query: Query, attribute_paths: list[str]):
        self.query = query
        self.rows = Rows().set_columns(attribute_paths)
        self.request_params = RequestParams()

    def with_ordering(self: TSearchRequestBuilder, column: str, desc: bool) -> TSearchRequestBuilder:
        self.rows.add_ordering({"Path": column, "SortOrder": "Desc" if desc else "Asc"})
        return self

    def with_request_params(self: TSearchRequestBuilder, source: int, source_name: str) -> TSearchRequestBuilder:
        self.request_params.set_search_source_name(source_name).set_search_source(source)
        return self

    def build(self) -> SearchRequest:
        request = SearchRequest()
        request.set_query(self.query).set_rows(self.rows).set_request_params(self.request_params)
        return request


def create_alert_request(
    threat_models: Optional[list[str]] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    ingest_time_start: Optional[datetime] = None,
    ingest_time_end: Optional[datetime] = None,
    device_names: Optional[list[str]] = None,
    last_days: Optional[int] = None,
    users: Optional[list[str]] = None,
    alert_statuses: Optional[list[str]] = None,
    alert_severities: Optional[list[str]] = None,
    alert_ids: Optional[list[str]] = None,
    descending_order: bool = True,
) -> SearchRequest:
    alert_query = (
        AlertSearchQueryBuilder()
        .with_threat_models(threat_models)
        .with_time_range(start_time, end_time)
        .with_ingest_time_range(ingest_time_start, ingest_time_end)
        .with_device(device_names)
        .with_last_days(last_days)
        .with_users(users)
        .with_statuses(alert_statuses)
        .with_severities(alert_severities)
        .with_alert_ids(alert_ids)
        .with_aggregation()
        .build()
    )

    request = (
        SearchRequestBuilder(alert_query, AlertAttributes.Columns)
        .with_ordering(AlertAttributes.IngestTime, descending_order)
        .with_request_params(1, "Phantom")
        .build()
    )

    return request


def create_alerted_events_request(alert_ids: list[str], descending_order=True) -> SearchRequest:
    event_query = EventSearchQueryBuilder().with_alert_ids(alert_ids).with_last_days(365).build()

    request = (
        SearchRequestBuilder(event_query, EventAttributes.Columns)
        .with_ordering(EventAttributes.EventTimeUtc, descending_order)
        .with_request_params(1, "Phantom")
        .build()
    )

    return request


def get_query_range(count: int, page: int = 1) -> Optional[dict[str, int]]:
    """Generate query for range of the search results
    :type count: ``int``
    :param count: Max amount of the search results
    :type page: ``int``
    :param page: Current page, depends on count
    :return: A query range
    :rtype: ``str``
    """
    if count:
        return {"from": (page - 1) * count, "to": page * count - 1}
    return None
