"""Custom Exceptions."""
from passivetotal_utils import post_message


class CustomError(Exception):
    """Generic Class for all custom errors."""

    pass


class QuotaException(CustomError):
    """Generic quota exception to control errors."""

    def __init__(self, session_key):
        """Initialize object."""
        message = "API Limit Exceeded. Looks like you reached your quota for today. " \
            "Please come back tomorrow to resume your investigation " \
            "or contact support for details on enterprise plans."
        post_message(session_key, "error", message)
        super(QuotaException, self).__init__(message)


class QueryFieldNotExistsError(CustomError):
    """Query Field does not exist in given events."""

    pass
