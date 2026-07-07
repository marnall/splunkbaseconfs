"""Exceptions module for service clients."""


class S3ValidationError(Exception):
    """Custom exception for S3 validation errors."""

    def __init__(self, message: str):
        """
        Initialize the S3ValidationError.

        Args:
            message (str): The error message.
        """
        self.message = message
        super().__init__(self.message)
