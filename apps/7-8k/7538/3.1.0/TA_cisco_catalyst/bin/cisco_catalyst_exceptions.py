"""Custom exception classes for Cisco Catalyst."""


class CyberVisionInvalidGlobalAccount(Exception):
    """Exception Class for CyberVision global account."""

    pass


class CyberVisionInvalidServerAddress(Exception):
    """Exception Class for CyberVision Server Address."""

    pass


class CyberVisionInvalidStartDate(Exception):
    """Exception Class for Invalid Start Date."""

    pass


class CyberVisionInvalidInterval(Exception):
    """Exception class for Invalid Interval."""

    pass


class CybervisionFileSaveError(Exception):
    """Exception class for File Save Error."""

    pass


class SDWANFileSaveError(Exception):
    """Exception class for File Save Error."""

    pass


class ISEFileSaveError(Exception):
    """Exception class for File Save Error."""

    pass


class ISEInvalidGlobalAccount(Exception):
    """Exception Class for ISE global account."""

    pass


class SDWANInvalidGlobalAccount(Exception):
    """Exception Class for SDWAN global account."""

    pass


class AuthenticationError(Exception):
    """Exception Class for Authentication Error."""

    pass


class InvalidStatusCodeError(Exception):
    """Custom exception class for unexpected HTTP status codes."""

    pass


class PxgridCreateUsername(Exception):
    """Custom exception class for pxGrid create username."""

    pass


class PxGridUsernameConflict(Exception):
    """Custom exception class for pxGrid username conflict."""

    pass


class ISEReportsConverting(Exception):
    """Custom exception class for pxGrid username conflict."""

    pass
