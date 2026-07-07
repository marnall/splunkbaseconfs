import requests
import urllib3
import sys
import re
import ta_druva_declare
from splunktaucclib.rest_handler.error import RestError
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
import logging
import os
from typing import Dict, Tuple, Optional, Any
from dataclasses import dataclass

util.remove_http_proxy_env_vars()


# Constants
TEST_PROXY_CONN_URL = "https://apis.druva.com/token"
COMMON_CONN_FAILURE_ERR = "Failed to establish the connection with the proxy server. Please check the server details below or try again later."
DEFAULT_TIMEOUT = (30, 60)  # (connect_timeout, read_timeout)

# HTTP Status Codes
HTTP_STATUS_CODES = {
    401: "Unauthorized: Invalid proxy username or password",
    407: "Proxy Authentication Required", 
    408: "Request Timeout"
}

# Exception mapping for timeout errors
TIMEOUT_ERRORS = {
    requests.exceptions.ConnectTimeout: COMMON_CONN_FAILURE_ERR,
    requests.exceptions.ReadTimeout: COMMON_CONN_FAILURE_ERR,
    urllib3.exceptions.ConnectTimeoutError: COMMON_CONN_FAILURE_ERR,
    urllib3.exceptions.ReadTimeoutError: COMMON_CONN_FAILURE_ERR,
    urllib3.exceptions.MaxRetryError: COMMON_CONN_FAILURE_ERR,
    urllib3.exceptions.NewConnectionError: COMMON_CONN_FAILURE_ERR,
    urllib3.connection.HTTPSConnection: COMMON_CONN_FAILURE_ERR,
}


@dataclass
class ProxyConfig:
    """Data class to hold proxy configuration."""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"
    enabled: bool = False

    def __post_init__(self):
        """Validate proxy configuration after initialization."""
        if not self.host:
            raise ValueError("Proxy host cannot be empty")
        if not isinstance(self.port, int):
            raise ValueError("Proxy port must be an integer")
        if self.protocol not in ["http", "https"]:
            raise ValueError("Proxy protocol must be either 'http' or 'https'")


class ProxyConnectionTester:
    """Handles proxy connection testing with proper error handling."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def build_proxy_string(self, config: ProxyConfig) -> str:
        """Build proxy URL string from configuration."""
        proxy_string = f"{config.protocol}://"
        
        if config.username and config.password:
            proxy_string += f"{config.username}:{config.password}@"
        
        proxy_string += f"{config.host}:{config.port}"
        return proxy_string

    def build_proxies_dict(self, config: ProxyConfig) -> Dict[str, str]:
        """Build proxies dictionary based on protocol type."""
        proxy_string = self.build_proxy_string(config)
        
        if config.protocol == "http":
            # HTTP proxy can handle both HTTP and HTTPS traffic
            return {
                "http": proxy_string,
                "https": proxy_string
            }
        else:
            # HTTPS proxy only handles HTTPS traffic
            return {config.protocol: proxy_string}

    def get_status_message(self, status_code: int, response_text: str) -> str:
        """Get user-friendly message for HTTP status codes."""
        if status_code in HTTP_STATUS_CODES:
            return HTTP_STATUS_CODES[status_code]
        return f"HTTP Error {status_code}: {response_text}"

    def clean_error_message(self, reasons: list) -> str:
        """Clean and format error messages."""
        if not reasons:
            return COMMON_CONN_FAILURE_ERR
            
        messages = []
        for reason in reasons:
            if isinstance(reason, str):
                messages.append(reason)
            else:
                # Remove HTML tags and brackets from error messages
                message = str(reason)
                message = re.sub(r"<.*?>|\[.*?\]", "", message)
                messages.append(message)
        
        return " ".join(messages)

    def get_error_message(self, exception: Exception) -> str:
        """Extract meaningful error message from exception."""
        try:
            # Try to get detailed error reasons
            if hasattr(exception, 'args') and exception.args:
                if hasattr(exception.args[0], 'reason') and hasattr(exception.args[0].reason, 'args'):
                    reasons = exception.args[0].reason.args
                else:
                    reasons = exception.args
            else:
                reasons = [str(exception)]
        except Exception as fault:
            self.logger.error(f"Error extracting exception details: {fault}")
            reasons = [str(exception)]

        # Check for specific timeout errors first
        for reason in reasons:
            if type(reason) in TIMEOUT_ERRORS:
                return TIMEOUT_ERRORS[type(reason)]

        # Return cleaned general error message
        return self.clean_error_message(reasons)

    def test_connection(self, config: ProxyConfig) -> Tuple[bool, str]:
        """Test proxy connection with proper error handling."""
        if not config.enabled:
            return True, "Proxy is disabled"

        try:
            self.logger.info(f"Testing proxy connection: {config.host}:{config.port}")
            
            proxies = self.build_proxies_dict(config)
            self.logger.debug(f"Using proxies configuration: {proxies}")

            response = requests.post(
                TEST_PROXY_CONN_URL,
                proxies=proxies,
                timeout=DEFAULT_TIMEOUT
            )

            status_code = response.status_code
            
            # Accept 422 as valid response (some APIs return this for test endpoints)
            if status_code >= 400 and status_code != 422:
                message = self.get_status_message(status_code, response.text)
                self.logger.error(f"Proxy connection failed with status {status_code}: {message}")
                return False, message

            self.logger.info("Proxy connection test successful")
            return True, "Connection successful"

        except Exception as e:
            message = self.get_error_message(e)
            self.logger.error(f"Proxy connection test failed: {message}")
            return False, message


class ProxyValidator(validator.Validator):
    """Validator for proxy configuration with comprehensive error handling."""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("ta_druva.proxy_validator")
        self.connection_tester = ProxyConnectionTester(self.logger)

    def validate(self, value: Any, data: Dict[str, Any]) -> bool:
        """Validate proxy configuration."""
        try:
            self.logger.debug(f"ProxyValidator.validate called with value: {value}, data: {data}")
            
            # Check if proxy is enabled
            if data.get("enable_proxy") != "1":
                self.logger.debug("Proxy is disabled, skipping validation")
                return True

            # Build proxy configuration
            config = self._build_proxy_config(data)
            
            # Test connection
            connection_ok, message = self.connection_tester.test_connection(config)
            
            if not connection_ok:
                self.logger.error(f"Proxy validation failed: {message}")
                raise RestError(status=400, message=message)

            self.logger.info("Proxy validation successful")

        except RestError:
            # Re-raise RestError as-is
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during proxy validation: {e}")
            raise RestError(status=400, message=f"Proxy validation error: {str(e)}")
        
        return True

    def _build_proxy_config(self, data: Dict[str, Any]) -> ProxyConfig:
        """Build ProxyConfig from validation data."""
        try:
            return ProxyConfig(
                host=data.get("proxy_host"),
                port=int(data.get("proxy_port")),
                username=data.get("proxy_username"),
                password=data.get("proxy_password"),
                protocol=data.get("proxy_type"),
                enabled=data.get("enable_proxy") == "1"
            )
        except ValueError as e:
            raise RestError(status=400, message=f"Invalid proxy configuration: {str(e)}")


# Field definitions
fields_logging = [
    field.RestField(
        'loglevel',
        required=False,
        encrypted=False,
        default='INFO',
        validator=None
    )
]

# Proxy configuration fields
fields_proxy = [
    field.RestField("enable_proxy", validator=ProxyValidator()),
    field.RestField("proxy_type"),
    field.RestField("proxy_host"),
    field.RestField("proxy_port"),
    field.RestField("proxy_username"),
    field.RestField("proxy_password"),
]

# Model definitions
model_logging = RestModel(fields_logging, name="logging")
model_proxy = RestModel(fields_proxy, name="proxy")

# Endpoint configuration
endpoint = MultipleModel(
    'ta_druva_settings',
    models=[
        model_logging,
        model_proxy,
    ],
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )

