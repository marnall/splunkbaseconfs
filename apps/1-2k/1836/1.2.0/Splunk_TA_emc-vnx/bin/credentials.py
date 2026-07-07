"""
Handles credentials related stuff
"""

import splunk.rest as sr
import logging
import time
import re
import xml.dom.minidom as xdm
from splunk import ResourceNotFound
from splunk.models.base import SplunkAppObjModel
from splunk.models.field import Field

import splunk.entity as entity

_LOGGER = logging.getLogger("data_loader")


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

    _log_template = "Failed to %s user credential for %s, app=%s"

    def __init__(self, session_key, host_path="https://localhost:8089"):
        self._session_key = session_key
        self._host_path = host_path

    @staticmethod
    def get_session_key(username, password,
                        host_path="https://localhost:8089", retry=3):
        """
        Get session key by using login username and passwrod
        @return: session_key
        """

        eid = "".join((host_path, "/services/auth/login"))
        postargs = {
            "username": username,
            "password": password,
        }

        for _ in range(retry):
            response, content = sr.simpleRequest(eid, postargs=postargs)
            if response.status == 200:
                xml_obj = xdm.parseString(content)
                session_nodes = xml_obj.getElementsByTagName("sessionKey")
                return session_nodes[0].firstChild.nodeValue
        raise Exception("Failed to get session key %d: %s"
                        % (response.status, response.reason))

    def update(self, realm, user, password, app, owner="nobody", retry=3):
        """
        Update the password for a user and realm.
        @return: The encrypted password value.
        """

        for _ in range(retry):
            res = self.delete(realm, user, app, owner)
            if not res:
                _LOGGER.error(self._log_template, "delete", realm, app)
                continue
            try:
                return self.create(realm, user, password, app, owner, retry=1)
            except Exception:
                pass
        raise Exception(self._log_template % ("delete", realm, app))

    def create(self, realm, user, password, app, owner="nobody", retry=3):
        """
        Create a new stored credential.
        @return: The encrypted password value.
        """
        cred = SplunkStoredCredential(app, owner, user,
                                      host_path=self._host_path,
                                      sessionKey=self._session_key)
        cred.realm = realm
        cred.password = password

        for _ in range(retry):
            if cred.create():
                return self.get_encrypted_password(realm, user, app, owner)
            else:
                _LOGGER.error(self._log_template, "create", realm, app)
                continue
        raise Exception(self._log_template % ("create", realm, app))

    def delete(self, realm, user, app, owner="nobody", retry=3):
        """
        Delete the encrypted entry
        @return: True for success, False for failure
        """

        realm_user = self._build_name(realm, user)
        path = SplunkStoredCredential.build_id(realm_user, app, owner,
                                               host_path=self._host_path)
        for _ in range(retry):
            try:
                response, _ = sr.simpleRequest(path, method="DELETE",
                                               sessionKey=self._session_key)
                if response.status in (200, 201):
                    return True
                else:
                    continue
            except ResourceNotFound:
                _LOGGER.warn("Entity not found for (%s %s %s %s)",
                             realm, user, app, owner)
            return True
        return False

    def get_clear_password(self, realm, user, app, owner="nobody", retry=3):
        """
        @return: clear password for specified realm and user
        """

        return self._get_credentials(realm, user, app, owner,
                                     "clear_password", retry)

    def get_encrypted_password(self, realm, user, app,
                               owner="nobody", retry=3):
        """
        @return: clear password for specified realm and user
        """

        return self._get_credentials(realm, user, app, owner,
                                     "encr_password", retry)

    def get_all_user_credentials(self, app, timeout=30):
        """
        @return: a list of {"realm": realm, "username": username, "app": app}
        """
        try:
            # list all user credentials
            entities = entity.getEntities(['admin', 'passwords'], namespace=app, owner='nobody', sessionKey=self._session_key)

            # list Splunk_TA_emc-vnx user credentials
            user_credentials = {i: ent for i, ent in entities.items() if ent['eai:acl']['app'] == app}
        except Exception as e:
            _LOGGER.error("EMC VNX Error: Could not get %s credentials from splunk. Error: %s" % (app, str(e)))
            raise Exception("EMC VNX Error: Could not get %s credentials from splunk. Error: %s" % (app, str(e)))

        return user_credentials.items()

    def _get_credentials(self, realm, user, app, owner, prop, retry):
        """
        @return: clear or encrypted password for specified realm, user
        """
        for _ in range(retry):
            realm_user = self._build_name(realm, user)
            try:
                entity_id = SplunkStoredCredential.build_id(
                                                     realm_user, app, owner,
                                                     host_path=self._host_path)
                cred = SplunkStoredCredential.get(entity_id, self._session_key)
                return getattr(cred, prop)
            except Exception:
                _LOGGER.error("Failed to get encrypted password for "
                              "(%s %s %s %s)", realm, user, app, owner)
                continue
        return None

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
