import uuid
from datetime import datetime, timedelta


class HttpClientMock:

    def __init__(self, url, api_key):
        pass

    @staticmethod
    def execute_search_query(search_query, max_fetch=1000, last_fetched_ingest_time=None):
        time = datetime.now() - timedelta(minutes=1) - timedelta(hours=2)

        data = {
            "columns": [
                "Alert.Rule.Name",
                "Alert.Rule.Severity.Name",
                "Alert.TimeUTC",
                "Alert.Rule.Category.Name",
                "Alert.User.Name",
                "Alert.Status.Name",
                "Alert.ID",
                "Alert.Rule.ID",
                "Alert.Rule.Severity.ID",
                "Alert.Location.CountryName",
                "Alert.Location.SubdivisionName",
                "Alert.Status.ID",
                "Alert.EventsCount",
                "Alert.Initial.Event.TimeUTC",
                "Alert.User.SamAccountName",
                "Alert.User.AccountType.Name",
                "Alert.Device.HostName",
                "Alert.Device.IsMaliciousExternalIP",
                "Alert.Device.ExternalIPThreatTypesName",
                "Alert.Data.IsFlagged",
                "Alert.Data.IsSensitive",
                "Alert.Filer.Platform.Name",
                "Alert.Asset.Path",
                "Alert.Filer.Name",
                "Alert.CloseReason.Name",
                "Alert.Location.BlacklistedLocation",
                "Alert.Location.AbnormalLocation",
                "Alert.User.SidID",
                "Alert.IngestTime"
            ],
            "rows": [
                [
                    "Membership changes: admin groups 1",
                    "Medium",
                    (time + timedelta(seconds=1)).isoformat(),
                    "Privilege Escalation 1",
                    "varadm1 (dev85570.com)",
                    "New",
                    str(uuid.uuid4()),
                    "167",
                    "2",
                    "",
                    "",
                    "1",
                    "1",
                    (time + timedelta(seconds=1)).isoformat(),
                    "varadm",
                    "Admin",
                    "Device 1",
                    "",
                    "",
                    "0",
                    "0",
                    "Active Directory",
                    "dev85570.com(AD-dev85570.com) 1",
                    "AD-dev85570.com 1",
                    "",
                    "",
                    "",
                    "971",
                    (time + timedelta(seconds=1)).isoformat(),
                ],
                [
                    "Membership changes: admin groups 2",
                    "Low",
                    (time + timedelta(seconds=2)).isoformat(),
                    "Privilege Escalation 2",
                    "varadm2 (dev85570.com)",
                    "New",
                    str(uuid.uuid4()),
                    "167",
                    "2",
                    "",
                    "",
                    "1",
                    "1",
                    (time + timedelta(seconds=2)).isoformat(),
                    "varadm",
                    "Admin",
                    "Device 2",
                    "",
                    "",
                    "0",
                    "0",
                    "Active Directory",
                    "dev85570.com(AD-dev85570.com) 2",
                    "AD-dev85570.com 2",
                    "",
                    "",
                    "",
                    "971",
                    (time + timedelta(seconds=2)).isoformat(),
                ],
                [
                    "Membership changes: admin groups 3",
                    "High",
                    (time + timedelta(seconds=3)).isoformat(),
                    "Privilege Escalation 3",
                    "varadm3 (dev85570.com)",
                    "New",
                    str(uuid.uuid4()),
                    "167",
                    "2",
                    "",
                    "",
                    "1",
                    "1",
                    (time + timedelta(seconds=3)).isoformat(),
                    "varadm",
                    "Admin",
                    "Device 3",
                    "",
                    "",
                    "0",
                    "0",
                    "Active Directory",
                    "dev85570.com(AD-dev85570.com) 3",
                    "AD-dev85570.com 3",
                    "",
                    "",
                    "",
                    "971",
                    (time + timedelta(seconds=3)).isoformat(),
                ]
            ],
            "hasResults": True,
            "rowsCount": 3,
            "cappedNumber": 50000,
            "progress": 100,
            "finished": True,
            "entityTagHeaderValue": {
                "tag": "\"3\"",
                "isWeak": False
            },
            "versionId": 3,
            "bookmark": None
        }
        return data

    @staticmethod
    def add_note_to_alerts(query):
        return True

    @staticmethod
    def alert_update_status(query):
        return True

    @staticmethod
    def get_enum(enum_id):
        data = [
                {"dataField": "1", "displayField": "Abnormal service behavior: access to atypical folders"},
                {"dataField": "2", "displayField": "Abnormal service behavior: access to atypical files"},
                {"dataField": "4", "displayField": "Abnormal service behavior: atypical failure to access data"},
                {"dataField": "5", "displayField": "Abnormal admin behavior: access to atypical mailboxes"},
                {"dataField": "6", "displayField": "Abnormal behavior: unusual amount of files with denied access"},
                {"dataField": "7", "displayField": "Abnormal behavior: unusual amount of system files accessed"},
                {"dataField": "8", "displayField": "Abnormal behavior: unusual amount of script files accessed"},
                {"dataField": "9", "displayField": "Abnormal behavior: unusual amount of configuration and backup files accessed"},
                {"dataField": "10", "displayField": "Abnormal behavior: access to an unusual amount of idle data"},
                {"dataField": "11", "displayField": "Abnormal behavior: access to an unusual amount of idle sensitive data"},
                {"dataField": "13", "displayField": "Abnormal behavior: accumulative increase in amount of idle data accessed"},
                {"dataField": "14", "displayField": "Abnormal behavior: accumulative increase in amount of idle and sensitive data accessed"},
                {"dataField": "15", "displayField": "Abnormal behavior: unusual amount of lockout across end-user accounts"}]
        return data


