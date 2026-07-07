import os
import tempfile
import time
from logging import Logger
from time import sleep
from urllib.parse import unquote

import requests
from OpenSSL.crypto import FILETYPE_PEM, X509, PKey, dump_certificate, dump_privatekey, load_certificate, load_privatekey
from requests_aws4auth.aws4auth import AWS4Auth

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class AwsCredentialsProvider:
    ROLE_ALIAS = 'AuditSiemDevice'
    REFRESH_CREDS_SLEEP_IN_SECONDS = 60
    CREDENTIALS_TTL_SECONDS = 2700

    def __init__(self, aws_region: str, auth_endpoint: str, device_name: str, certificate: str, private_key: str, logger: Logger,
                 proxy_config=None):
        self._aws_region = aws_region
        self._auth_endpoint = auth_endpoint
        self._device_name = device_name
        self._certificate = self._load_certificate(certificate)
        self._private_key = self._load_private_key(private_key)
        self._logger = logger
        self._proxy_config = proxy_config
        self._aws_credentials = None
        self._credentials_created_at = 0

    @property
    def aws_credentials(self) -> AWS4Auth:
        return self._aws_credentials

    def _credentials_expired(self) -> bool:
        if not self._aws_credentials:
            return True
        return (time.monotonic() - self._credentials_created_at) >= self.CREDENTIALS_TTL_SECONDS

    def get_or_create_aws_credentials(self) -> AWS4Auth:
        if self._aws_credentials and not self._credentials_expired():
            self._logger.debug('Reusing existing AWS credentials')
            return self._aws_credentials
        if self._aws_credentials:
            self._logger.info('AWS credentials expired, refreshing')
        self._logger.info('Creating new AWS credentials')
        self._aws_credentials = self._create_aws_auth()
        self._credentials_created_at = time.monotonic()
        return self._aws_credentials

    def refresh_aws_credentials(self) -> None:
        try:
            self._aws_credentials = self._create_aws_auth()
            self._credentials_created_at = time.monotonic()
        except Exception as exp:
            self._logger.exception(f'Failed refreshing AWS credentials: {exp}')
            sleep(self.REFRESH_CREDS_SLEEP_IN_SECONDS)

    @staticmethod
    def _get_aws_iot_cert():
        cert_path = os.path.join(BASE_DIR, 'certs', 'AmazonRootCA1.pem')
        if not os.path.exists(cert_path):
            raise FileNotFoundError(f'CA certificate not found: {cert_path}')
        return cert_path

    def _prepare_cert_files(self):
        cert_pem = dump_certificate(FILETYPE_PEM, self._certificate)
        key_pem = dump_privatekey(FILETYPE_PEM, self._private_key)

        def _write_secure_temp(content):
            with tempfile.NamedTemporaryFile(delete=False, dir='/dev/shm') as f:
                f.write(content)
                f.flush()
                path = f.name
            os.chmod(path, 0o600)
            return path

        cert_path = _write_secure_temp(cert_pem)
        key_path = _write_secure_temp(key_pem)

        return cert_path, key_path

    def _build_request_kwargs(self, cert_path, key_path):
        headers = {'x-amzn-iot-thingname': self._device_name}

        verify = True
        if self._proxy_config and isinstance(self._proxy_config, dict):
            verify = self._proxy_config.get('verify', True)

        if verify:
            verify = self._get_aws_iot_cert()

        request_kwargs = {'headers': headers, 'cert': (cert_path, key_path), 'verify': verify, 'timeout': 30}

        if self._proxy_config and self._proxy_config.get('https'):
            proxy_dict = {'http': self._proxy_config.get('http'), 'https': self._proxy_config.get('https')}
            request_kwargs['proxies'] = proxy_dict
            self._logger.info('Using proxy for AWS credentials request')
        return request_kwargs

    def _fetch_and_validate_credentials(self, cert_path, key_path):
        credentials_url = f'https://{self._auth_endpoint}/role-aliases/{self.ROLE_ALIAS}/credentials'
        request_kwargs = self._build_request_kwargs(cert_path, key_path)

        response = requests.get(credentials_url, **request_kwargs)

        response.raise_for_status()
        payload = response.json()
        credentials = payload.get('credentials', {})

        required_keys = ('accessKeyId', 'secretAccessKey', 'sessionToken')
        missing = [k for k in required_keys if k not in credentials]

        if missing:
            raise KeyError(f'Missing credential keys: {missing}.')

        return credentials

    def _get_aws_credentials(self):
        cert_path = None
        key_path = None

        try:
            cert_path, key_path = self._prepare_cert_files()

            credentials = self._fetch_and_validate_credentials(cert_path, key_path)

            return credentials

        finally:
            for path in (cert_path, key_path):
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                    except Exception:
                        self._logger.error('Error deleting cert files', exc_info=True)
                        pass

    def _create_aws_auth(self) -> AWS4Auth:
        try:
            credentials = self._get_aws_credentials()
            return AWS4Auth(credentials['accessKeyId'], credentials['secretAccessKey'], self._aws_region, 'execute-api',
                            session_token=credentials['sessionToken'])

        except requests.exceptions.RequestException as e:
            self._logger.warning(f'Network error: {e}')
            raise

        except Exception as err:
            self._logger.error(f'Failed to fetch AWS credentials from IoT Role Alias: {err}')
            raise

    def validate_user_configurations(self) -> bool:
        try:
            if self._certificate.has_expired() or not self._certificate.get_subject() or not self._private_key.check():
                raise ValueError('Invalid certificate or private key. Please verify your credentials and try again.')

            self._get_aws_credentials()

        except Exception as err:
            self._logger.error(f'Validation failed: {str(err)}')
            raise ValueError('Invalid certificate or private key. Please verify your credentials and try again.')

        return True

    @staticmethod
    def _load_private_key(private_key: str) -> PKey:
        decoded_key = unquote(private_key)
        return load_privatekey(FILETYPE_PEM, decoded_key.encode('utf-8'))

    @staticmethod
    def _load_certificate(certificate: str) -> X509:
        decoded_cert = unquote(certificate)
        return load_certificate(FILETYPE_PEM, decoded_cert.encode('utf-8'))
