class CofenseTriageGenericException(Exception):
    """Base class for other exceptions."""

    pass


class DataCollectionError(CofenseTriageGenericException):
    """Raised when there is an error in Data Collection."""

    def __init__(self, input_name, endpoint, error_msg):
        """Init method."""
        self.input_name = input_name
        self.endpoint = endpoint
        self.message = 'Data collection failed for input {} and endpoint {} due to {}'.format(
            self.input_name,
            self.endpoint,
            error_msg
        )
        super(DataCollectionError, self).__init__(self.message)

    def __str__(self):
        """Override str method."""
        return self.message


class UnknownError(CofenseTriageGenericException):
    """Raised in case of an unknown error."""

    def __init__(self, error_msg):
        """Init method."""
        self.message = 'Script failed due to an unknown error {}'.format(error_msg)
        super(UnknownError, self).__init__(self.message)

    def __str__(self):
        """Override str method."""
        return self.message


class DataIngestionError(CofenseTriageGenericException):
    """Raised in case of failure to ingest data into Splunk."""

    def __init__(self, error_msg):
        """Init method."""
        self.message = 'Data ingestion failed due to an unknown error {}'.format(error_msg)
        super(DataIngestionError, self).__init__(self.message)

    def __str__(self):
        """Override str method."""
        return self.message


class InputValidationError(CofenseTriageGenericException):
    """Raised in case of an unknown error."""

    def __init__(self, error_msg):
        """Init method."""
        self.message = '{}'.format(error_msg)
        super(InputValidationError, self).__init__(self.message)

    def __str__(self):
        """Override str method."""
        return self.message


class OAuthError(CofenseTriageGenericException):
    """Raised in case of an unknown error."""

    def __init__(self, error_msg):
        """Init method."""
        self.message = 'Could not generate OAuth token because {}'.format(error_msg)
        super(OAuthError, self).__init__(self.message)

    def __str__(self):
        """Override str method."""
        return self.message
