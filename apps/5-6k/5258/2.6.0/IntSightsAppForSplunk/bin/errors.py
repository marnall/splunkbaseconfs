CHECK_LOG_FILES = 'Please check the log files.'


class CustomException(Exception):
    """Parent class for all custom exceptions."""

    message = 'Internal error occured. {}'.format(CHECK_LOG_FILES)
    reason = 'Unknown reason of error.'

    def __init__(self, message=None, reason=None):
        """
        Initialize an environment.

        @param: str: message: Short displayable description of error (useful for displaying).
        @param: str: reason: Actual detailed reason of error (useful for logging).
        """
        if message:
            self.message = str(message)

        if reason:
            self.reason = str(reason)


class StopExecutionError(CustomException):
    """Stop execution flow."""

    pass


class ConfigurationError(CustomException):
    """Configuration is not as expected."""

    message = 'Internal error occured due to misconfiguration. {}'.format(CHECK_LOG_FILES)


class CollectionNotFoundError(ConfigurationError):
    """Expected collection not found in KVStore."""

    def __init__(self, collection):
        """Initialize an environment."""
        self.message = 'Could not found collection named "{}"'.format(collection)
        self.reason = self.message


class APIError(CustomException):
    """IntSights API related errors."""

    reason = 'Unkonwn API error occured.'
    message = '{} {}'.format(reason, CHECK_LOG_FILES)
    response = None

    def __init__(self, message=None, reason=None, response=None):
        """Initialize an environment."""
        if response:
            self.response = response
        super(APIError, self).__init__(message, reason)


class InvalidAPICredentialsError(APIError):
    """Invalid API Credentials."""

    message = 'API Credentials are invalid. Please recheck the configured IntSights Account.'
    reason = message


class QuotaExceededError(APIError):
    """API Quota Exceeded."""

    message = 'You exceeded your daily API quota.'
    reason = message


class InvestigationForbiddenError(APIError):
    """Investigation is forbidden."""

    message = 'Investigation module is not available in your IntSights Subscription.'
    reason = message


class InvestigationDisabledError(APIError):
    """Investigation is disabled."""

    message = (
        'Investigation module is disabled for the configured IntSights account.'
        ' Please enable it in the IntSights Platform to investigate an IOC.'
    )
    reason = message


class InvestigationFailedError(APIError):
    """Investigation failed."""

    message = 'Invalid provided API parameters.'
    reason = message

    def __init__(self, message=None, reason=None, response=None):
        """Intialize an environment."""
        if message:
            self.message = message
            if not reason:
                self.reason = message
        if response:
            self.response = response
