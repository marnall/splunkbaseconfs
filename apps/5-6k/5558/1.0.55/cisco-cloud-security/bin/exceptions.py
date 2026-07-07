"""A module containing the implementation of custom exceptions """


class ReportingAPIClientException(Exception):
    """A custom exception for reporting API client if any error."""

    def __init__(self, error_code=None, error_msg=None):
        self.error_code = error_code
        self.error_msg = error_msg
        super().__init__(self.error_code, self.error_msg)

    def __str__(self):
        return "ReportingAPIClientException"


class UmbrellaDashboardAPIClientException(Exception):
    """A custom exception for umbrella dashboard API client if any error."""

    def __init__(self, error_code=None, error_msg=None):
        self.error_code = error_code
        self.error_msg = error_msg
        super().__init__(self.error_code, self.error_msg)

    def __str__(self):
        return "UmbrellaDashboardAPIClientException"


class PrivateResourcesAPIClientException(Exception):
    """A custom exception for private resources API client if any error."""

    def __init__(self, error_code=None, error_msg=None):
        self.error_code = error_code
        self.error_msg = error_msg
        super().__init__(self.error_code, self.error_msg)

    def __str__(self):
        return self.error_msg


class FetchDestinationException(Exception):
    """A custom exception for fetching destination lists api if any error."""

    def __init__(self, error_code=None, error_msg=None):
        self.error_code = error_code
        self.error_msg = error_msg
        super().__init__(self.error_code, self.error_msg)

    def __str__(self):
        return "FetchDestinationException"


class DLPAPIException(Exception):
    """Custom exception for DLP API errors."""

    def __init__(self, error_code, error_msg):
        self.error_code = error_code
        self.error_msg = error_msg
        super().__init__(self.error_msg)

    def __str__(self):
        return self.error_msg if self.error_msg else "DLPAPIException"


class DestinationListHealthException(Exception):
    """A custom exception for destination list health if any error."""

    def __init__(self, error_code=None, error_msg=None):
        self.error_code = error_code
        self.error_msg = error_msg
        super().__init__(self.error_code, self.error_msg)

    def __str__(self):
        return "DestinationListHealthException"


class AppDiscoveryException(Exception):
    """A custom exception for app discovery scheduler if any error."""

    def __init__(self, error_code=None, error_msg=None):
        self.error_code = error_code
        self.error_msg = error_msg
        super().__init__(self.error_code, self.error_msg)

    def __str__(self):
        return "AppDiscoveryException"


class InvestigateListHealthException(Exception):
    """A custom exception for investigate api health if any error."""

    def __init__(self, error_code=None, error_msg=None):
        self.error_code = error_code
        self.error_msg = error_msg
        super().__init__(self.error_code, self.error_msg)

    def __str__(self):
        return "InvestigateListHealthException"


class InvestigateDestinationException(Exception):
    """A custom exception for investigate destinations if any error."""

    def __init__(self, error_code=None, error_msg=None):
        self.error_code = error_code
        self.error_msg = error_msg
        super().__init__(self.error_code, self.error_msg)

    def __str__(self):
        return "InvestigateDestinationException"


class DestinationReportException(Exception):
    """A custom exception for destination report if any error."""

    def __init__(self, error_code=None, error_msg=None):
        self.error_code = error_code
        self.error_msg = error_msg
        super().__init__(self.error_code, self.error_msg)

    def __str__(self):
        return "DestinationReportException"


class InvestigatereportDownloadException(Exception):
    """A custom exception for investigate report download if any error."""

    def __init__(self, error_code=None, error_msg=None):
        self.error_code = error_code
        self.error_msg = error_msg
        super().__init__(self.error_code, self.error_msg)

    def __str__(self):
        return "InvestigatereportDownloadException"


class OrgAccountsException(Exception):
    """A custom exception for org accounts if any error."""

    def __init__(self, error_msg=None):
        self.error_msg = error_msg
        super().__init__(self.error_msg)

    def __str__(self):
        return self.error_msg if self.error_msg else "OrgAccountsException"


class ModularInputExistsException(Exception):
    """A custom exception for modular input manager if input already exists."""

    def __init__(self, error_msg=None):
        self.error_msg = error_msg
        super().__init__(self.error_msg)

    def __str__(self):
        return self.error_msg if self.error_msg else "ModularInputExistsException"


class ModularInputNotFoundException(Exception):
    """A custom exception for modular input manager if input does not exist."""

    def __init__(self, error_msg=None):
        self.error_msg = error_msg
        super().__init__(self.error_msg)

    def __str__(self):
        return self.error_msg if self.error_msg else "ModularInputNotFoundException"


class KvStoreRecordNotFoundException(Exception):
    """A custom exception for KV Store if record is not found."""

    def __init__(self, error_msg=None):
        self.error_msg = error_msg
        super().__init__(self.error_msg)

    def __str__(self):
        return self.error_msg if self.error_msg else "KvStoreRecordNotFoundException"


class NewInstallationException(Exception):
    """Exception raised when no existing OAuth settings are found, indicating a new installation."""

    def __init__(self, error_msg=None):
        self.error_msg = error_msg or "No active oauth settings found. Considering new installation."
        super().__init__(self.error_msg)

    def __str__(self):
        return self.error_msg


class MigrationFailedException(Exception):
    """Exception raised when migration fails due to inability to determine orgId."""

    def __init__(self, error_msg=None):
        self.error_msg = error_msg or "Migration failed. Unable to determine orgId for active oauth settings."
        super().__init__(self.error_msg)

    def __str__(self):
        return self.error_msg


class AlertsException(Exception):
    """A custom exception for Alerts Modular Input if any error."""

    def __init__(self, error_code=None, error_msg=None):
        self.error_code = error_code
        self.error_msg = error_msg
        super().__init__(self.error_code, self.error_msg)

    def __str__(self):
        return self.error_msg if self.error_msg else "AlertsException"
