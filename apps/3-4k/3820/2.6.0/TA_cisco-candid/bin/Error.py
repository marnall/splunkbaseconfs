class Error(Exception):
    """Base class for exceptions."""

    pass


class InvalidInputParameter(Error):
    """Exception for invalid input dictionary parameters."""

    def ___init__(self, input_parameter):
        """Initialize with error message."""
        self.message = "Unknown parameter supplied: " + input_parameter

    def __str__(self):
        """Return string representation."""
        return self.message
