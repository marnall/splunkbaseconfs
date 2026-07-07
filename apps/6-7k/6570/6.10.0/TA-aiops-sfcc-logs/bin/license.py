import logging
import binascii
import fcntl
import os
import errno
import random

from uuid import uuid4
from datetime import datetime, timezone
from contextlib import contextmanager
from time import time, sleep
from functools import wraps
from base64 import b64decode
from urllib.parse import urljoin
from dataclasses import dataclass
from json import loads, dump, load, dumps
from json.decoder import JSONDecodeError
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from requests import exceptions

from utils import enforce_secure_connection


@dataclass
class LicenseTokenFileLock:
    """File lock using fcntl for coordinating license token access.

    Attributes:
        lock_file_path: Path to the lock file.
        timeout: Maximum seconds to wait for lock acquisition.
    """

    lock_file_path: str
    timeout: float = 20.0

    @contextmanager
    def acquire(self, exclusive=False):
        """Acquires the lock with a timeout.

        Args:
            exclusive: If True, acquires an exclusive (writer) lock.
                If False, acquires a shared (reader) lock.

        Yields:
            None: Control is yielded back to the caller while lock is held.

        Raises:
            TimeoutError: If the lock cannot be acquired within the timeout period.
            IOError: If a file operation fails for reasons other than lock contention.
        """
        os.makedirs(os.path.dirname(self.lock_file_path), exist_ok=True)

        fd = None
        acquired = False

        try:
            fd = open(self.lock_file_path, "w+")

            lock_type = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            lock_type |= fcntl.LOCK_NB  # Non-blocking to allow timeout handling

            start_time = time()

            while True:
                try:
                    fcntl.flock(fd, lock_type)
                    acquired = True
                    break
                except IOError as e:
                    if e.errno not in (errno.EAGAIN, errno.EWOULDBLOCK):
                        raise

                    if (time() - start_time) >= self.timeout:
                        logging.error(
                            f"Timeout ({self.timeout}s) waiting for lock: {self.lock_file_path}"
                        )
                        raise TimeoutError(
                            f"Could not acquire lock on {self.lock_file_path} within {self.timeout} seconds"
                        )

                    # Jitter prevents thundering herd on lock contention
                    sleep(0.1 + random.uniform(0, 0.1))

            yield

        finally:
            if acquired and fd:
                fcntl.flock(fd, fcntl.LOCK_UN)

            if fd:
                fd.close()


@dataclass
class LicenseConfigParams:
    """Configuration parameters required for license validation.

    Attributes:
        license_id: Unique identifier for the license.
        private_key: Base64-encoded RSA private key for token decryption.
        server_url: URL of the license server API.
        client_id: Client identifier for API authentication.
    """

    license_id: str
    private_key: str
    server_url: str
    client_id: str

    def is_configured(self) -> bool:
        """Checks if all configuration fields are properly set.

        Returns:
            True if all fields have non-empty, non-placeholder values.
        """
        return not self.has_empty_fields() and not self.has_default_values()

    def has_empty_fields(self) -> bool:
        """Checks if any required field is None.

        Returns:
            True if any required field is None.
        """
        return any(
            field is None
            for field in [
                self.license_id,
                self.private_key,
                self.client_id,
                self.server_url,
            ]
        )

    def has_default_values(self) -> bool:
        """Checks if any field still has the placeholder default value.

        Returns:
            True if any field equals the placeholder 'xxx-xxx-xxx-xxx'.
        """
        return any(
            field == "xxx-xxx-xxx-xxx"
            for field in [
                self.license_id,
                self.private_key,
                self.client_id,
                self.server_url,
            ]
        )


class LicenseStateFile:
    """Repository for license state persistence using a JSON file.

    This class handles reading and writing license tokens to disk with proper
    file locking to ensure thread-safe access across multiple processes.

    Attributes:
        _FILE_NAME: Name of the JSON file storing license state.
        _LOCK_FILE_NAME: Name of the lock file used for synchronization.
    """

    _FILE_NAME = "license_state.json"
    _LOCK_FILE_NAME = "license_state.lock"

    def __init__(self, storage_dir: str):
        """Initializes the state file repository.

        Args:
            storage_dir: Directory path where state files will be stored.
        """
        self._storage_dir = storage_dir
        self._file_path = os.path.join(self._storage_dir, self._FILE_NAME)
        self._lock_path = os.path.join(self._storage_dir, self._LOCK_FILE_NAME)
        self._lock = LicenseTokenFileLock(self._lock_path)

    def _ensure_directory_exists(self):
        """Creates the storage directory if it does not exist."""
        os.makedirs(self._storage_dir, exist_ok=True)

    def get(self, license_id: str) -> str:
        """Retrieves the cached license token for the given license ID.

        Args:
            license_id: The license identifier to look up.

        Returns:
            The encrypted token string if found, None otherwise.
        """
        self._ensure_directory_exists()

        try:
            with self._lock.acquire(exclusive=False):
                if not os.path.exists(self._file_path):
                    return None

                with open(self._file_path, "r") as f:
                    try:
                        data = load(f)
                        token = data.get(license_id)
                        if token:
                            return token
                    except JSONDecodeError:
                        logging.error(
                            f"Failed to decode license state file: {self._file_path}"
                        )
                        return None
        except Exception as e:
            logging.error(f"Error reading license state: {e}")
            return None

        return None

    def save(self, license_id: str, token: str) -> None:
        """Persists a license token to the state file.

        Args:
            license_id: The license identifier to store.
            token: The encrypted token string to cache.

        Raises:
            Exception: If the file cannot be written.
        """
        self._ensure_directory_exists()

        try:
            with self._lock.acquire(exclusive=True):
                data = {}
                if os.path.exists(self._file_path):
                    try:
                        with open(self._file_path, "r") as f:
                            data = load(f)
                    except JSONDecodeError:
                        logging.warning(
                            f"License state file corrupted, creating new one: {self._file_path}"
                        )

                data[license_id] = token

                with open(self._file_path, "w") as f:
                    dump(data, f)
        except Exception as e:
            logging.error(f"Error saving license state: {e}")
            raise


def log_license_event(action, component, message, metadata=None, exception=None):
    """Logs a structured license event in CloudEvents format.

    Args:
        action: The event action type (e.g., 'get_token.http_request.sent').
        component: The component name that generated the event.
        message: Human-readable description of the event.
        metadata: Optional dict of additional metadata to include.
        exception: Optional exception to include in the event metadata.
    """
    payload = {"component": component, "message": message}
    if metadata:
        payload["metadata"] = metadata

    if exception:
        if not payload.get("metadata"):
            payload["metadata"] = {}
        payload["metadata"]["exception.type"] = type(exception).__name__
        payload["metadata"]["exception.message"] = str(exception)

    event_id = str(uuid4())
    timestamp = datetime.now(timezone.utc).replace(tzinfo=None).isoformat("T") + "Z"

    event_data = {
        "specversion": "1.0",
        "type": f"license.{action}",
        "source": "source",
        "subject": "addon.license",
        "id": event_id,
        "time": timestamp,
        "data": {
            "id": event_id,
            "time": timestamp,
            "data": payload,
        },
    }

    logging.info("License event=%s", dumps(event_data))


@dataclass
class LicenseToken:
    """Domain model representing a decrypted SFCC license token.

    Encapsulates all validation logic for determining if a license is valid
    and what permissions it grants.

    Attributes:
        status: License status (e.g., 'active', 'revoked', 'expired').
        scopes: List of input types this license permits, or ['*'] for all.
        issued_at: Token issuance timestamp in milliseconds since epoch.
        expiration: Token validity duration in seconds.
    """

    status: str
    scopes: list
    issued_at: int
    expiration: int

    @classmethod
    def from_dict(cls, data: dict):
        """Creates a LicenseToken from a dictionary.

        Args:
            data: Dictionary containing license token fields.

        Returns:
            A new LicenseToken instance populated from the dictionary.
        """
        return cls(
            status=data.get("status", "").lower(),
            scopes=data.get("scopes", []),
            issued_at=int(data.get("issued_at", 0)),
            expiration=int(data.get("expiration", 0)),
        )

    def is_expired(self) -> bool:
        """Checks if the token's time validity window has passed.

        Returns:
            True if the token is expired or has missing timestamp fields.
        """
        if not self.issued_at or not self.expiration:
            return True

        # Expiration is duration in seconds, issued_at is epoch ms
        expiry_timestamp_ms = self.issued_at + (self.expiration * 1000)
        current_timestamp_ms = time() * 1000

        return current_timestamp_ms > expiry_timestamp_ms

    def allows_input_type(self, input_type: str) -> bool:
        """Checks if this license grants permission for the specified input type.

        Args:
            input_type: The input type to check permissions for.

        Returns:
            True if the license permits the input type or grants wildcard access.
        """
        return "*" in self.scopes or input_type in self.scopes


class LicenseAPIClient:
    """HTTP client for the license server API.

    Handles communication with the remote license server to fetch encrypted
    license tokens.

    Attributes:
        ENDPOINT: API endpoint path for token requests.
    """

    ENDPOINT = "api/license/token"

    def __init__(self, helper):
        """Initializes the API client.

        Args:
            helper: Splunk modular input helper with send_http_request method.
        """
        self.helper = helper

    def fetch_token(self, server_url: str, client_id: str, license_id: str) -> str:
        """Fetches an encrypted license token from the server.

        Args:
            server_url: Base URL of the license server.
            client_id: Client identifier for API authentication.
            license_id: License identifier to fetch token for.

        Returns:
            The encrypted token string from the server.

        Raises:
            requests.exceptions.RequestException: If the HTTP request fails.
            JSONDecodeError: If the response is not valid JSON.
            ValueError: If the response is missing the 'token' field.
        """
        base_url = server_url if server_url.endswith("/") else server_url + "/"
        url = urljoin(base_url, self.ENDPOINT)
        payload = {"license_key_id": license_id}
        headers = {
            "Content-Type": "application/json",
            "X-CLIENT-ID": client_id,
        }

        try:
            response = self._send_request(url, payload, headers)
            return self._parse_response(response)
        except (
            ValueError,
            JSONDecodeError,
            exceptions.Timeout,
            exceptions.HTTPError,
            exceptions.ConnectionError,
            exceptions.RequestException,
        ) as e:
            self._log_error(e)
            raise

    def _send_request(self, url, payload, headers):
        """Sends the HTTP POST request to the license server."""
        log_license_event(
            "get_token.http_request.sent",
            "LicenseAPIClient",
            "An HTTP Request sent to get License token from the server.",
        )

        response = self.helper.send_http_request(
            url, method="POST", payload=payload, headers=headers, timeout=45
        )
        response.raise_for_status()
        return response

    def _parse_response(self, response) -> str:
        """Extracts and validates the token from the server response."""
        data = response.json()
        token = data.get("token")

        if not token:
            log_license_event(
                "get_token.validated",
                "LicenseAPIClient",
                "The License data received from the server is missing 'token' field or it is empty.",
            )
            raise ValueError("Server response missing 'token' field")

        return token

    def _log_error(self, exception: Exception):
        """Logs an error event with an appropriate message based on exception type."""
        if isinstance(exception, JSONDecodeError):
            msg = (
                "A decode error occured when trying to parse the License token to JSON."
            )
        elif isinstance(exception, ValueError):
            msg = "The License data received from the server is missing 'token' field."
        elif isinstance(exception, exceptions.ConnectionError):
            msg = "An HTTP Request Connection error occured when trying to get License token from the server."
        elif isinstance(exception, exceptions.Timeout):
            msg = "An HTTP Request timeout error occured when trying to get License token from the server."
        elif isinstance(exception, exceptions.HTTPError):
            msg = "An HTTP Response error from server returned when trying to get License token."
        else:
            msg = "An HTTP Request error occured when trying to get License token from the server."

        log_license_event(
            "get_token.error.raised", "LicenseAPIClient", msg, exception=exception
        )


def decrypt(data, private_key_pem_str):
    """Decrypts the given data with supplied PKCS8 PEM private key.

    Args:
        data (bytes): Data represented as bytes
        private_key_pem_str (str): PKCS8 PEM private key

    Returns:
        str: Data decrypted.
    """
    try:
        private_key = RSA.import_key(private_key_pem_str)
        decryptor = PKCS1_OAEP.new(private_key)
        data = decryptor.decrypt(data)

        return data.decode("utf-8")
    except (ValueError, TypeError) as err:
        log_license_event(
            "decrypt.error.raised",
            "LicenseDecrypt",
            "An error occured when trying import the private key or decrypt the data.",
            exception=err,
        )
        raise err


def _decrypt_and_parse_token(token_str: str, private_key_pem: str) -> LicenseToken:
    """Decodes, decrypts, and parses an encrypted license token.

    Args:
        token_str: Base64-encoded encrypted token string.
        private_key_pem: PEM-formatted RSA private key for decryption.

    Returns:
        A LicenseToken instance containing the decrypted token data.

    Raises:
        binascii.Error: If base64 decoding fails.
        ValueError: If decryption fails.
        JSONDecodeError: If the decrypted data is not valid JSON.
    """
    license_token_decoded = b64decode(token_str)
    decrypted_license_data = decrypt(license_token_decoded, private_key_pem)
    license_data = loads(decrypted_license_data)
    return LicenseToken.from_dict(license_data)


class LicenseValidator:
    """Validates license tokens against configuration and server state.

    This class orchestrates the full license validation flow: checking
    configuration, retrieving tokens from cache or server, and validating
    token status and scopes.

    Dependencies are injected via constructor to support testing:
        state_repo: Object with get(license_id) -> str|None and
            save(license_id, token) methods.
        api_client: Object with fetch_token(server_url, client_id, license_id)
            -> str method.
    """

    def __init__(
        self,
        config: LicenseConfigParams,
        state_repo,
        api_client,
        private_key_decoded: str,
        input_type: str,
        input_name: str,
    ):
        """Initializes the validator with all required dependencies.

        Args:
            config: License configuration parameters.
            state_repo: Repository for caching license tokens.
            api_client: Client for fetching tokens from the license server.
            private_key_decoded: Decoded PEM private key for token decryption.
            input_type: The input type to validate permissions for.
            input_name: The input name for logging purposes.
        """
        self._config = config
        self._state_repo = state_repo
        self._api_client = api_client
        self._private_key = private_key_decoded
        self._input_type = input_type
        self._input_name = input_name

    def validate(self) -> bool:
        """Validates that the license is properly configured and active.

        Returns:
            True if the license is valid and permits the configured input type,
            False otherwise.
        """
        log_failure_msg = (
            f"Failed license checking and validating data_input={self._input_name}"
        )

        if not self._config.is_configured():
            if self._config.has_empty_fields():
                log_license_event(
                    "configurations.fields.checked",
                    "LicenseIsConfigured",
                    "One or many of configuration fields are with empty value. Configure the License!",
                )
            elif self._config.has_default_values():
                log_license_event(
                    "configurations.fields.checked",
                    "LicenseIsConfigured",
                    "One or many of configuration fields are with the default value. Set the specific values for the fields!",
                )
            log_license_event(
                "configurations.checked",
                "LicenseRequired",
                "The License is not properly configured.",
            )
            logging.error(log_failure_msg)
            return False

        license_token = self._get_or_fetch_token()

        if not license_token.status:
            log_license_event(
                "status.validated",
                "LicenseIsActive",
                "Field 'status' not found in token.",
            )
            logging.error(log_failure_msg)
            return False

        if license_token.status == "revoked":
            log_license_event(
                "status.validated",
                "LicenseIsActive",
                "AIOPS License has been revoked.",
            )
            logging.error(log_failure_msg)
            return False

        if license_token.status == "expired":
            log_license_event(
                "status.validated",
                "LicenseIsActive",
                "The License has been expired.",
            )
            logging.error(log_failure_msg)
            return False

        if not license_token.scopes:
            log_license_event(
                "scope.validated",
                "LicenseInputAllowedToIngest",
                "The License doesn't contain scopes inside.",
            )
            logging.error(log_failure_msg)
            return False

        if not license_token.allows_input_type(self._input_type):
            log_license_event(
                "scope.input.validated",
                "LicenseInputAllowedToIngest",
                "The License doesn't allow the ingestion of the data source.",
            )
            logging.error(log_failure_msg)
            return False

        log_license_event(
            "usage.allowed", "LicenseRequired", "The use of Add-on is allowed."
        )
        return True

    def _get_or_fetch_token(self) -> LicenseToken:
        """Retrieves a valid license token from cache or fetches from server.

        Returns:
            A decrypted and parsed LicenseToken.

        Raises:
            Exception: If token cannot be fetched from the server.
        """
        cached_token_str = self._state_repo.get(self._config.license_id)

        if cached_token_str:
            try:
                candidate = _decrypt_and_parse_token(
                    cached_token_str, self._private_key
                )

                if not candidate.expiration:
                    log_license_event(
                        "token.fields.validated",
                        "LicenseIsTokenExpired",
                        "Field 'expiration' not found in token.",
                    )
                elif not candidate.issued_at:
                    log_license_event(
                        "token.fields.validated",
                        "LicenseIsTokenExpired",
                        "Field 'issued_at' not found in token.",
                    )
                elif not candidate.is_expired():
                    return candidate

            except (ValueError, TypeError, binascii.Error, JSONDecodeError):
                pass  # Cache invalid or corrupted, fetch fresh token

        raw_token = self._api_client.fetch_token(
            self._config.server_url, self._config.client_id, self._config.license_id
        )

        try:
            self._state_repo.save(self._config.license_id, raw_token)
        except Exception as save_err:
            # Cache failure is non-fatal; token will be re-fetched next run
            logging.error(
                f"Failed to cache license token (will retry next run): {save_err}"
            )

        return _decrypt_and_parse_token(raw_token, self._private_key)


def license_required(func):
    """Decorator for functions that checks that the License is set up and valid.

    Args:
        func (function): The function that is decorated.

    Returns:
        func: Function to be executed.
        or
        None: Nothing to be executed.
    """

    @wraps(func)
    def wrapper_license_required(*args, **kwargs):
        helper, _ = args
        data_input_name = helper.get_arg("name")
        log_failure_msg = (
            f"Failed license checking and validating data_input={data_input_name}"
        )

        try:
            logging.info(
                f"Starting license checking and validating data_input={data_input_name}"
            )

            config = LicenseConfigParams(
                license_id=helper.get_global_setting("license_id"),
                private_key=helper.get_global_setting("license_private_key"),
                server_url=helper.get_global_setting("license_server_url"),
                client_id=helper.get_global_setting("license_server_client_id"),
            )

            if not config.server_url:
                logging.info(
                    f"Failed license checking and validating, license server URL not configured data_input={data_input_name}"
                )

                return None

            enforce_secure_connection(config.server_url)

            splunk_home = os.environ.get("SPLUNK_HOME", "/opt/splunk")
            storage_dir = os.path.join(
                splunk_home,
                "var",
                "lib",
                "splunk",
                "modinputs",
                "license",
            )

            state_repo = LicenseStateFile(storage_dir)
            api_client = LicenseAPIClient(helper)
            validator = LicenseValidator(
                config=config,
                state_repo=state_repo,
                api_client=api_client,
                private_key_decoded=b64decode(config.private_key).decode("utf-8"),
                input_type=helper.input_type,
                input_name=data_input_name,
            )

            if not validator.validate():
                return None

            logging.info(
                f"Finishing license checking and validating data_input={data_input_name}"
            )
            return func(*args, **kwargs)

        except binascii.Error as binascii_err:
            log_license_event(
                "decode.error.raised",
                "LicenseRequired",
                "An error occured when trying to decode the License. Malformed encoded data!",
                exception=binascii_err,
            )
            logging.error(log_failure_msg)
            raise binascii_err
        except UnicodeDecodeError as unicode_decode_err:
            log_license_event(
                "decode.error.raised",
                "LicenseRequired",
                "An error occured when trying to decode the License. Invalid bytes, codec can't decode!",
                exception=unicode_decode_err,
            )
            logging.error(log_failure_msg)
            raise unicode_decode_err
        except (
            exceptions.Timeout,
            exceptions.HTTPError,
            exceptions.ConnectionError,
            exceptions.RequestException,
        ) as http_err:
            logging.error(log_failure_msg)
            raise http_err
        except Exception as e:
            logging.error(
                f"Unexpected error during license check for data_input={data_input_name}: {e}"
            )
            raise

    return wrapper_license_required
