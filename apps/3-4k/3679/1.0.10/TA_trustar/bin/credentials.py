"""
Handles credentials related stuff
"""

# Splunk imports
import splunk.rest as sr
from splunk.models.base import SplunkAppObjModel
from splunk.models.field import Field

# Local imports
import logger_manager as log

_LOGGER = log.setup_logging('trustar_modinput')


class SplunkStoredCredential(SplunkAppObjModel):
    """ Class for managing secure credential storage.
    """

    # Requires Splunk 4.3 or higher.
    resource = "storage/passwords"
    clear_password = Field()
    encr_password = Field()
    username = Field()
    password = Field()
    realm = Field()


class CredentialManager(object):
    """ Credential related interfaces.
    """

    _log_template = "Failed to %s user credential for %s, app=%s"

    def __init__(self, session_key, host_path="https://localhost:8089"):
        """ Initializes CredentialManager object with the specified configurations.

        :param session_key: splunk session key
        :param host_path: path to splunk management console
        """
        self._session_key = session_key
        self._host_path = host_path

    def update(self, realm, user, password, app, owner="nobody"):
        """ Update the password for a user and realm.
        
        :param realm: realm for the entity
        :param user: user for the entity
        :param password: new password
        :param app: app for the entity
        :param owner: owner of the entity
        :return: The encrypted password value or None in case of error.
        """

        res = self.delete(realm, user, app, owner)
        if not res:
            _LOGGER.exception(self._log_template, "delete", realm, app)
            raise Exception(self._log_template % ("update", realm, app))
        try:
            return self.create(realm, user, password, app, owner)
        except Exception:
            raise Exception(self._log_template % ("update", realm, app))

    def create(self, realm, user, password, app, owner="nobody"):
        """ Create a new stored credential.
        
        :param realm: realm for the entity
        :param user: user for the entity
        :param password: password for the entity
        :param app: app for the entity
        :param owner: owner of the entity
        :return: The encrypted password value or None in case of error.
        """

        cred = SplunkStoredCredential(app, owner, user, host_path=self._host_path, sessionKey=self._session_key)
        cred.realm = realm
        cred.password = password

        if cred.create():
            return self.get_encrypted_password(realm, user, app, owner)
        _LOGGER.exception(self._log_template, "create", realm, app)
        raise Exception(self._log_template % ("create", realm, app))

    def delete(self, realm, user, app, owner="nobody"):
        """ Delete the encrypted entry.
        
        :param realm: realm for the entity
        :param user: user for the entity
        :param app: app for the entity
        :param owner: owner of the entity
        :return: True for success, False for failure
        """

        realm_user = self._build_name(realm, user)
        path = SplunkStoredCredential.build_id(realm_user, app, owner, host_path=self._host_path)

        try:
            response, _ = sr.simpleRequest(path, method="DELETE", sessionKey=self._session_key, raiseAllErrors=True)
            return True
        except Exception:
            _LOGGER.exception("Entity not found for (%s %s %s %s)", realm, user, app, owner)

        return False

    def get_clear_password(self, realm, user, app, owner="nobody"):
        """ To get password in clear text.
        
        :param realm: realm for the entity
        :param user: user for the entity
        :param app: app for the entity
        :param owner: owner of the entity
        :return: clear password for specified realm and user or None in case of error.
        """

        return self._get_credentials(realm, user, app, owner, "clear_password")

    def get_encrypted_password(self, realm, user, app, owner="nobody", log_exception=True):
        """ To get password in encrypted form.
        
        :param realm: realm for the entity
        :param user: user for the entity
        :param app: app for the entity
        :param owner: owner of the entity
        :param log_exception: flag to decide whether to log error or not while getting encrypted password
        :return: encrypted password for specified realm and user or None in case of error.
        """

        return self._get_credentials(realm, user, app, owner, "encr_password", log_exception)

    def _get_credentials(self, realm, user, app, owner, prop, log_exception=True):
        """ To get password in clear/encrypted form.
        
        :param realm: realm for the entity
        :param user: user for the entity
        :param app: app for the entity
        :param owner: owner of the entity
        :param prop: format of password in which it will be returned(e.g. "clear_password" or "encr_password")
        :param log_exception: flag to decide whether to log error or not while getting credentials
        :return: clear or encrypted password for specified realm, user
        """

        realm_user = self._build_name(realm, user)

        try:
            entity_id = SplunkStoredCredential.build_id(realm_user, app, owner, host_path=self._host_path)
            cred = SplunkStoredCredential.get(entity_id, self._session_key)
            return getattr(cred, prop)
        except Exception:
            if log_exception:
                _LOGGER.exception("Failed to get encrypted password for (%s %s %s %s)", realm, user, app, owner)

        return None

    @staticmethod
    def _build_name(realm, user):
        """ To build name by concatenating realm and user.
        
        :param realm: realm for the entity
        :param user: user for the entity
        :return: built name
        """

        return "".join((CredentialManager._escape_string(realm), ":", CredentialManager._escape_string(user), ":"))

    @staticmethod
    def _escape_string(string_to_escape):
        """ Splunk secure credential storage actually requires a custom style of escaped string where all
         the :'s are escaped by a single \. But don't escape the control : in the stanza name.
        
        :param string_to_escape: string to escape
        :return: escaped string
        """

        return string_to_escape.replace(":", "\\:")
