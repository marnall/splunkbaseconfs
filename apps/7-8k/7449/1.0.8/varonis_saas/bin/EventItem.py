class EventItem:
    def __init__(self, row: dict):
        self.row = row
        self.mapped_row = {
            "Data Source Type" : row.get('Event.Filer.Platform.Name'),
            "Generation Time (UTC)" : row.get('Event.TimeUTC'),
            "Event Operation" : row.get('Event.Operation.Name'),
            "Event Description" : row.get('Event.Description'),
            "Event Type" : row.get('Event.Type.Name'),
            "Account Name (Acting Account)" : row.get('Event.ByAccount.SamAccountName'),
            "Path (Affected Resource)" : row.get('Event.OnResource.Path'),
            "Object Name (Affected Resource)" : row.get('Event.OnObjectName'),
            "Event Status" : row.get('Event.Status.Name'),
            "Data Source (Affected Resource)" : row.get('Event.Filer.Name'),
            "Event Time" : row.get('Event.TimeUTC'),
            #"Event Count" : row.get('Not explicitly present'),
            "Collection Device Hostname" : row.get('Event.Destination.DeviceName'),
            #"Collection Method" : row.get('Not explicitly present'),
            "Original Event ID" : row.get('Event.ID'),
            #"Logon Type" : row.get('Not explicitly present'),
            #"Account Expiration Status (Acting Account)" : row.get('Not explicitly present'),
            "SAM Account Name (Acting Account)" : row.get('Event.ByAccount.SamAccountName'),
            "Account Type (Acting Account)" : row.get('Event.ByAccount.Type.Name'),
            "Distinguished Name (Acting Account)" : row.get('Event.ByAccount.Identity.Name'),
            "Directory Services (Acting Account)" : row.get('Event.ByAccount.Domain.Name'),
            "Disabled Account (Acting Account)" : row.get('Event.ByAccount.IsDisabled'),
            #"Password Status (Acting Account)" : row.get('Not explicitly present'),
            "Locked-Out Account (Acting Account)" : row.get('Event.ByAccount.IsLockout'),
            #"Affiliation (Acting Account)" : row.get('Not explicitly present'),
            "Client IP (Source Device)" : row.get('Event.IP'),
            #"Threat Detection Policy Name (Alert)" : row.get('Not explicitly present'),
            #"Alert Category (Alert)" : row.get('Not explicitly present'),
            #"Alert Severity (Alert)" : row.get('Not explicitly present'),
            #"Alert Time UTC (Alert)" : row.get('Event.TimeUTC'),
            "Alert ID (Alert)" : row.get('Event.Alert.ID'),
            "Directory Services (Affected Resource)" : row.get('Event.OnResource.ObjectType.Name'),
            "Object Type (Affected Resource)" : row.get('Event.OnResource.ObjectType.Name'),
            #"Total Record Count (Incl. Subfolders) (Affected Resource)" : row.get('Not explicitly present'),
            "Account Name (Affected Account)" : row.get('Event.OnAccount.SamAccountName'),
            "Disabled Account (Affected Account)" : row.get('Event.OnAccount.IsDisabled'),
            #"Password Status (Affected Account)" : row.get('Not explicitly present'),
            "SAM Account Name (Affected Account)" : row.get('Event.OnAccount.SamAccountName'),
            #"Privileged Account Type (Affected Account)" : row.get('Not explicitly present'),
            #"Account Expiration Status (Affected Account)" : row.get('Not explicitly present'),
            "Locked-Out Account (Affected Account)" : row.get('Event.OnAccount.IsLockout'),
            #"Affiliation (Affected Account)" : row.get('Not explicitly present')
        }

    def __getitem__(self, key: str):
        if hasattr(self.row, key):
            return getattr(self.row, key)
        raise KeyError(f"{key} not found in EventItem")

    def to_dict(self):
        return self.mapped_row
