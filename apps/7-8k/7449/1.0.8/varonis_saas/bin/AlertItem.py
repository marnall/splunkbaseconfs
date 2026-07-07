from uuid import UUID
from datetime import datetime


class AlertItem:
    def __init__(self, row: dict):
        self.row = row
        self.mapped_row = {
            "Alert ID": row.get('Alert.ID'),
            "Threat Detection Policy Name": row.get('Alert.Rule.Name'),
            # "Time": row.get('Alert.Time'),
            "Alert Severity": row.get('Alert.Rule.Severity.Name'),
            "Alert Category": row.get('Alert.Rule.Category.Name'),
            "Country": row.get('Alert.Location.CountryName'),
            "States": row.get('Alert.Location.SubdivisionName'),
            "Status": row.get('Alert.Status.Name'),
            "Close Reason": row.get('Alert.CloseReason.Name'),
            "Blacklisted Location": row.get('Alert.Location.BlacklistedLocation') == '1',
            "Abnormal Locations": row.get('Alert.Location.AbnormalLocation'),
            "No. of Alerted Events": row.get('Alert.EventsCount'),
            "Name (Specific Account) (Acting Account)": row.get('Alert.User.Name'),
            "SamAccountName": row.get('Alert.User.SamAccountName'),
            "Privileged Account Type (Acting Account)": row.get('Alert.User.AccountType.Name'),
            "Contains Malicious External IPs (Source Device)": row.get('Alert.Device.IsMaliciousExternalIP') == '1',
            "Aggregated External IP Threat Types (Source Device)": row.get('Alert.Device.ExternalIPThreatTypesName'),
            "Assets (Affected Resource)": row.get('Alert.Asset.Path'),
            "Flagged data exposed (Affected Resource)": row.get('Alert.Data.IsFlagged') == '1',
            "Sensitive Data Exposed (Affected Resource)": row.get('Alert.Data.IsSensitive') == '1',
            "Data Source Types": row.get('Alert.Filer.Platform.Name'),
            "Data Sources/Domains (Affected Resource)": row.get('Alert.Filer.Name'),
            "Alert Time UTC": row.get('Alert.Initial.Event.TimeUTC'),
            "Device Names (Source Device)": row.get('Alert.Device.HostName'),
            "Ingest Time": row.get('Alert.IngestTime')
        }

    def __getitem__(self, key: str):
        if hasattr(self.row, key):
            return getattr(self.row, key)
        raise KeyError(f"{key} not found in AlertItem")

    def to_dict(self):
        return self.mapped_row
