"""Mimecast Exceptions."""


class CredentialMissing(Exception):
    """Exception class for Credentials missing."""

    pass


class AccessTokenGenerationFailed(Exception):
    """Exception class for access token generation failed."""

    pass
