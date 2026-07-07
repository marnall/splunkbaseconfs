"""
SSL Certificate Fetch REST Endpoint

REST handler that fetches SSL certificates from a server for use with custom CA
verification. This endpoint is used when users need to configure trust for servers
using internal/private CAs or self-signed certificates.

Usage:
    POST /servicesNS/nobody/TA-Analyst1/ta_analyst1_fetch_certificate
    Body: server_address=<hostname>&port=<port>

Response (success):
    {
        "success": true,
        "cert_type": "INTERNAL-CA|SELF-SIGNED|PUBLIC-CA|AIA-CHAIN",
        "pem": "-----BEGIN CERTIFICATE-----...",
        "subject": "CN=Root CA",
        "issuer": "CN=Root CA",
        ...
    }

Response (error):
    {
        "success": false,
        "error_code": "CONNECTION_TIMEOUT|...|UNSUPPORTED_PLATFORM",
        "error_message": "Human readable error message"
    }
"""

from __future__ import annotations

import ta_analyst1_declare  # noqa: F401
import socket
from typing import Optional

import splunk.admin as admin
from analyst1_logging import get_logger

# Graceful degradation for platforms without cryptography support
# On Splunk 9.x Mac/Windows, the cryptography library is not available
# and we cannot bundle it (platform-specific binaries).
# On older Splunk with OpenSSL 1.0.2, cryptography raises RuntimeError.
try:
    from ta_analyst1.cert_fetcher import (
        get_root_ca_certificate,
        CertFetchError,
        validate_hostname,
    )
    CERT_FETCH_AVAILABLE = True
    CERT_FETCH_IMPORT_ERROR = None
except (ImportError, RuntimeError) as e:
    # ImportError: cryptography not installed
    # RuntimeError: OpenSSL version too old (e.g., "linking against OpenSSL 1.0.2")
    CERT_FETCH_AVAILABLE = False
    CERT_FETCH_IMPORT_ERROR = str(e)
    # Define stubs to prevent NameError on module load
    get_root_ca_certificate = None
    CertFetchError = Exception
    validate_hostname = None

logger = get_logger("ta_analyst1_fetch_certificate")

# Error codes for structured error responses
ERROR_CODES = {
    "CONNECTION_TIMEOUT": "CONNECTION_TIMEOUT",
    "CONNECTION_FAILED": "CONNECTION_FAILED",
    "NO_CERTIFICATE": "NO_CERTIFICATE",
    "INVALID_HOSTNAME": "INVALID_HOSTNAME",
    "FETCH_ERROR": "FETCH_ERROR",
    "UNSUPPORTED_PLATFORM": "UNSUPPORTED_PLATFORM",
}

# Default HTTPS port
DEFAULT_PORT = 443


class FetchCertificateHandler(admin.MConfigHandler):
    """
    REST handler for fetching SSL certificates from servers.

    Provides a single endpoint to retrieve root CA certificates needed for
    SSL verification when connecting to servers with internal/private CAs.
    """

    def setup(self):
        """Set up supported arguments for the endpoint."""
        # Required arguments
        self.supportedArgs.addReqArg("server_address")

        # Optional arguments
        self.supportedArgs.addOptArg("port")

    def handleList(self, confInfo):
        """
        Handle GET request - not supported, redirect to POST.

        GET is intentionally not supported because certificate fetching
        should be an explicit action.
        """
        confInfo["status"]["success"] = "false"
        confInfo["status"]["error_message"] = "GET not supported. Use POST."

    def handleCreate(self, confInfo):
        """
        Handle POST request - fetch certificate from server.

        Connects to the specified server, retrieves the certificate chain,
        and returns the root CA certificate with metadata.
        """
        # Check if certificate fetching is available on this platform
        if not CERT_FETCH_AVAILABLE:
            # Provide user-friendly error message based on the cause
            import_error = CERT_FETCH_IMPORT_ERROR or ""
            if "OpenSSL 1.0.2" in import_error:
                # Old OpenSSL version - common on older Splunk Cloud instances
                error_message = (
                    "Certificate fetching is not available on this Splunk instance.\n\n"
                    "This Splunk server uses OpenSSL 1.0.2, which is too old for "
                    "automatic certificate fetching. This is a limitation of the "
                    "server environment, not the add-on.\n\n"
                    "Workaround: Manually obtain the Root CA certificate from your "
                    "IT department and paste it into the Custom CA Certificate field."
                )
            else:
                # Generic platform issue (Mac/Windows Splunk 9.x, etc.)
                error_message = (
                    "Certificate fetching is not available on this platform.\n\n"
                    "This feature requires Splunk 10.x or Splunk 9.x on Linux.\n\n"
                    "Workaround: Manually obtain the Root CA certificate from your "
                    "IT department and paste it into the Custom CA Certificate field."
                )
            self._set_error_response(
                confInfo,
                error_code=ERROR_CODES["UNSUPPORTED_PLATFORM"],
                error_message=error_message
            )
            return

        # Extract arguments
        server_address = self._get_arg("server_address")
        port_str = self._get_arg("port", default=str(DEFAULT_PORT))

        # Parse port from address if included (e.g., "hostname:8443")
        if server_address and ":" in server_address:
            parts = server_address.rsplit(":", 1)
            if len(parts) == 2 and parts[1].isdigit():
                server_address = parts[0]
                port_str = parts[1]

        # Validate port
        try:
            port = int(port_str)
            if port < 1 or port > 65535:
                raise ValueError("Port out of range")
        except ValueError:
            self._set_error_response(
                confInfo,
                error_code=ERROR_CODES["INVALID_HOSTNAME"],
                error_message=f"Invalid port number: {port_str}. Must be between 1 and 65535."
            )
            return

        logger.info(
            f"[Fetch Certificate] Request received: server_address={server_address}, port={port}"
        )

        # Validate hostname first
        try:
            validate_hostname(server_address)
        except ValueError as e:
            logger.warning(
                f"[Fetch Certificate] Invalid hostname: {server_address} - {e}"
            )
            self._set_error_response(
                confInfo,
                error_code=ERROR_CODES["INVALID_HOSTNAME"],
                error_message=str(e)
            )
            return

        # Fetch the certificate
        try:
            pem_content, cert_type, cert_info = get_root_ca_certificate(
                server_address, port
            )

            logger.info(
                f"[Fetch Certificate] Successfully fetched certificate: "
                f"server={server_address}, type={cert_type}, subject={cert_info.get('subject')}"
            )

            # Build success response
            self._set_success_response(
                confInfo,
                cert_type=cert_type,
                pem=pem_content,
                cert_info=cert_info
            )

        except socket.timeout:
            error_msg = f"Connection to {server_address}:{port} timed out"
            logger.warning(f"[Fetch Certificate] {error_msg}")
            self._set_error_response(
                confInfo,
                error_code=ERROR_CODES["CONNECTION_TIMEOUT"],
                error_message=error_msg
            )

        except socket.error as e:
            error_msg = f"Connection to {server_address}:{port} failed: {e}"
            logger.warning(f"[Fetch Certificate] {error_msg}")
            self._set_error_response(
                confInfo,
                error_code=ERROR_CODES["CONNECTION_FAILED"],
                error_message=error_msg
            )

        except CertFetchError as e:
            error_str = str(e)
            # Determine specific error code based on message
            if "No certificate" in error_str:
                error_code = ERROR_CODES["NO_CERTIFICATE"]
            else:
                error_code = ERROR_CODES["FETCH_ERROR"]

            logger.warning(f"[Fetch Certificate] CertFetchError: {error_str}")
            self._set_error_response(
                confInfo,
                error_code=error_code,
                error_message=error_str
            )

        except Exception as e:
            error_msg = f"Unexpected error fetching certificate: {e}"
            logger.error(f"[Fetch Certificate] {error_msg}", exc_info=True)
            self._set_error_response(
                confInfo,
                error_code=ERROR_CODES["FETCH_ERROR"],
                error_message=error_msg
            )

    def _get_arg(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get argument from request, handling list format.

        Args:
            name: Argument name
            default: Default value if not present

        Returns:
            Argument value or default
        """
        value = self.callerArgs.get(name)
        if value is None:
            return default
        if isinstance(value, list):
            return value[0] if value else default
        return value

    def _set_success_response(
        self,
        confInfo,
        cert_type: str,
        pem: str,
        cert_info: dict
    ):
        """
        Set a successful REST response with certificate data.

        Args:
            confInfo: Splunk REST response object
            cert_type: Certificate type (INTERNAL-CA, SELF-SIGNED, PUBLIC-CA, AIA-CHAIN)
            pem: PEM-encoded certificate
            cert_info: Dictionary with certificate metadata
        """
        confInfo["status"]["success"] = "true"
        confInfo["status"]["cert_type"] = cert_type
        confInfo["status"]["pem"] = pem

        # Add all fields from cert_info
        for key, value in cert_info.items():
            if isinstance(value, bool):
                confInfo["status"][key] = "true" if value else "false"
            else:
                confInfo["status"][key] = str(value)

    def _set_error_response(
        self,
        confInfo,
        error_code: str,
        error_message: str
    ):
        """
        Set an error REST response.

        Args:
            confInfo: Splunk REST response object
            error_code: Structured error code
            error_message: Human-readable error message
        """
        confInfo["status"]["success"] = "false"
        confInfo["status"]["error_code"] = error_code
        confInfo["status"]["error_message"] = error_message


if __name__ == "__main__":
    admin.init(FetchCertificateHandler, admin.CONTEXT_NONE)
