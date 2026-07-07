class SplunkSecretsManager:
    """Enhanced secrets manager with multi-user support"""

    SECRETS_REALM = 'cyberark_audit_realm'
    CERT_NAME = 'certificate'
    PKEY_NAME = 'pkey'

    def __init__(self, service, logger):
        self._service = service
        self._logger = logger

    @property
    def service(self):
        return self._service

    @property
    def logger(self):
        return self._logger

    def get_secret(self, secret_name: str):
        """Get a secret by name from the secrets realm"""
        for storage_password in self.service.storage_passwords:
            if storage_password.realm == self.SECRETS_REALM and storage_password.username == secret_name:
                return storage_password.clear_password
        raise ValueError(f'Failure fetching credentials from passwords storage: {secret_name}')

    def save_user_credentials(self, device_name: str, certificate: str, private_key: str):
        """Save or update credentials for a specific device"""
        cert_name = f'cert_{device_name}'
        pkey_name = f'pkey_{device_name}'

        # Save certificate
        self._save_or_update_secret(cert_name, certificate)
        self.logger.info(f'Saved certificate for device: {device_name}')

        # Save private key
        self._save_or_update_secret(pkey_name, private_key)
        self.logger.info(f'Saved private key for device: {device_name}')

    def save_proxy_credentials(self, device_name: str, proxy_username: str, proxy_password: str):
        """Save or update credentials for a specific device"""
        proxy_username_key = f'proxy_username_{device_name}'
        proxy_password_key = f'proxy_password_{device_name}'

        self._save_or_update_secret(proxy_username_key, proxy_username)
        self.logger.info(f'Saved proxy username for device: {device_name}')

        self._save_or_update_secret(proxy_password_key, proxy_password)
        self.logger.info(f'Saved proxy password for device: {device_name}')

    def delete_user_credentials(self, device_name: str):
        """Delete credentials for a specific device"""
        cert_name = f'cert_{device_name}'
        pkey_name = f'pkey_{device_name}'

        # Delete certificate
        self._delete_secret(cert_name)
        self.logger.info(f'Deleted certificate for device: {device_name}')

        # Delete private key
        self._delete_secret(pkey_name)
        self.logger.info(f'Deleted private key for device: {device_name}')

    def delete_proxy_credentials(self, device_name: str) -> None:
        """Delete proxy credentials for a specific device."""
        proxy_user_name = f'proxy_username_{device_name}'
        proxy_pass_name = f'proxy_password_{device_name}'

        try:
            self._delete_secret(proxy_user_name)
            self._delete_secret(proxy_pass_name)
            self.logger.info(f'Deleted proxy credentials for device: {device_name}')
        except ValueError:
            # Credentials might not exist - this is fine
            self.logger.info(f'No proxy credentials to delete for device: {device_name}')

    def _save_or_update_secret(self, secret_name: str, secret_value: str):
        """Save or update a secret in the storage passwords"""
        existing_secret = self._find_secret(secret_name)

        if existing_secret:
            # Update existing secret
            existing_secret.update(password=secret_value)
            self.logger.debug(f'Updated existing secret: {secret_name}')
        else:
            # Create new secret
            self.service.storage_passwords.create(password=secret_value, username=secret_name, realm=self.SECRETS_REALM)
            self.logger.debug(f'Created new secret: {secret_name}')

    def _delete_secret(self, secret_name: str):
        """Delete a secret from storage passwords"""
        existing_secret = self._find_secret(secret_name)

        if existing_secret:
            existing_secret.delete()
            self.logger.debug(f'Deleted secret: {secret_name}')
        else:
            self.logger.warning(f'Secret not found for deletion: {secret_name}')

    def _find_secret(self, secret_name: str):
        """Find a secret by name in the secrets realm"""
        for storage_password in self.service.storage_passwords:
            if storage_password.realm == self.SECRETS_REALM and storage_password.username == secret_name:
                return storage_password
        return None
