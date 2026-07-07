"""
Handles credentials related stuff
"""
from builtins import object
import splunk.entity as entity
import splunk.rest as sr
from splunk import ResourceNotFound
from splunk.models.base import SplunkAppObjModel
from splunk.models.field import Field



class SplunkStoredCredential(SplunkAppObjModel):
    """Class for managing secure credential storage."""

    # Requires Splunk 4.3 or higher.
    resource = "storage/passwords"
    clear_password = Field()
    encr_password = Field()
    username = Field()
    password = Field()
    realm = Field()


class CredentialManager(object):
    """
    Credential related interfaces
    """

    def __init__(self, session_key, host_path="https://localhost:8089"):
        self._session_key = session_key
        self._host_path = host_path

    def update(self, realm, user, password, app, owner="nobody"):
        """
        Update the password for a user and realm.
        @return: The encrypted password value.
        """

        res = self.delete(realm, user, app, owner)
        if not res:
            raise Exception("Failed to delete user credentials for %s  app=%s"  % (realm, app))
        try:
            return self.create(realm, user, password, app, owner)
        except Exception:
            raise Exception("Failed to update user credentials for %s  app=%s"  % (realm, app))

    def create(self, realm, user, password, app, owner="nobody"):
        """
        Create a new stored credential.
        @return: The encrypted password value.
        """
        cred = SplunkStoredCredential(app, owner, user,
                                      host_path=self._host_path,
                                      sessionKey=self._session_key)
        cred.realm = realm
        cred.password = password

        if cred.create():
            return self.get_encrypted_password(realm, user, app, owner)
        raise Exception("Failed to create user credentials for %s  app=%s"  % (realm, app))

    def delete(self, realm, user, app, owner="nobody"):
        """
        Delete the encrypted entry
        @return: True for success, False for failure
        """

        realm_user = self._build_name(realm, user)
        path = SplunkStoredCredential.build_id(realm_user, app, owner,
                                               host_path=self._host_path)
        try:
            response, _ = sr.simpleRequest(path, method="DELETE",
                                           sessionKey=self._session_key, raiseAllErrors=True)
            return True
        except Exception:
            return False

    def get_clear_password(self, realm, user, app, owner="nobody"):
        """
        @return: clear password for specified realm and user
        """

        return self._get_credentials(realm, user, app, owner,
                                     "clear_password")

    def get_encrypted_password(self, realm, user, app,
                               owner="nobody", log_exception=True):
        """
        @return: encrypted password for specified realm and user
        """

        return self._get_credentials(realm, user, app, owner,
                                     "encr_password", log_exception)

    def _get_credentials(self, realm, user, app, owner, prop, log_exception=True):
        """
        @return: clear or encrypted password for specified realm, user
        """
        realm_user = self._build_name(realm, user)
        try:
            entity_id = SplunkStoredCredential.build_id(
                realm_user, app, owner,
                host_path=self._host_path)
            cred = SplunkStoredCredential.get(entity_id, self._session_key)
            return getattr(cred, prop)
        except Exception:
                if log_exception:
                    raise Exception("Failed to get encrypted password for "
                                  "(%s %s %s %s)", realm, user, app, owner)
    @staticmethod
    def _build_name(realm, user):
        return "".join((CredentialManager._escape_string(realm), ":",
                        CredentialManager._escape_string(user), ":"))

    @staticmethod
    def _escape_string(string_to_escape):
        """
        Splunk secure credential storage actually requires a custom style of
        escaped string where all the :'s are escaped by a single \.
        But don't escape the control : in the stanza name.
        """
        return string_to_escape.replace(":", "\\:")
