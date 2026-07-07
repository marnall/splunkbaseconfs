class HdxCommandFatalError(Exception):
    """
    Base class for fatal errors in HDX commands. Will be presented to the user with minimal wrapping.
    """

    message: str  # duck-typing for error_exit

    def escaped(self) -> "HdxCommandFatalError":
        """
        Escape any curly braces to work around Splunk's wild choice to assume
        that python interpolation is in any way safe to run on an arbitrary
        `Exception`-wrapped string
        """
        return self.__class__(self.message.replace("{", "{{").replace("}", "}}"))

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class HdxClientError(Exception):
    message: str  # duck-typing for Splunk error_exit

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
