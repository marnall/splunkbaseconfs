# encoding = utf-8
from __future__ import print_function
import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))
import splunklib.client as client
from logger import Logger


class TokenService:

    def __init__(self):
        self.app_name = "cisco-cloud-security"
        self.realm = "cisco-cloud-security.com"

    @staticmethod
    def get_token(session_token,
                  token_key,
                  org_id=None,
                  host="localhost",
                  realm="cisco-cloud-security.com",
                  app='cisco-cloud-security'):
        ps = None
        Logger().info("Fetching token from store for key with orgId : {0}, {1}".format(token_key, org_id))
        try:
            service = client.connect(host=host, token=session_token, app=app)
            storage_passwords = service.storage_passwords
            token_key = token_key if not org_id else f"{token_key}_{org_id}"
            for pwd in storage_passwords.list():
                if token_key in pwd.username and realm in pwd.realm:
                    ps = {"clear_token": pwd.clear_password, "user": pwd.username, "realm": pwd.realm}
        except Exception as e:
            Logger().error("Unable to get token from store, Exception : {0}".format(str(e)))
            raise Exception("Unable to get token from store for key {0}".format(token_key))

        return {'payload': ps, 'status': 200}

    @staticmethod
    def set_token(session_token,
                  token,
                  token_key,
                  org_id=None,
                  host="localhost",
                  realm="cisco-cloud-security.com",
                  app='cisco-cloud-security'):
        Logger().info("Setting token in store for key with orgId : {0}, {1}".format(token_key, org_id))
        try:
            service = client.connect(host=host, token=session_token, app=app)
            storage_passwords = service.storage_passwords
            token_key = token_key if not org_id else f"{token_key}_{org_id}"
            try:
                storage_passwords.delete(token_key, realm=realm)
                Logger().info("{0} token is deleted if already exists from realm:{1}".format(token_key, realm))
            except Exception as exp:
                Logger().error("Either token not deleted nor existing. Exception : {0}".format(str(exp)))

            storage_passwords.create(token, token_key, realm=realm)
            Logger().info("Token is added for: {0}".format(token_key))
        except Exception as e:
            Logger().error("Error while persisting token in storage. Exception : {0}".format(str(e)))
            raise Exception("Persisting of encrypted token in password store failed for {0}".format(token_key))

        return {'payload': 'Token persisted successfully ', 'status': 200}

    @staticmethod
    def delete_token(
        session_token,
        token_key,
        org_id=None,
        host="localhost",
        realm="cisco-cloud-security.com",
        app="cisco-cloud-security",
    ):
        try:
            service = client.connect(host=host, token=session_token, app=app)
            storage_passwords = service.storage_passwords
            token_key = token_key if not org_id else f"{token_key}_{org_id}"
            storage_passwords.delete(token_key, realm=realm)
            Logger().info(
                "{0} token is deleted from realm:{1}".format(token_key, realm)
            )
        except Exception as e:
            Logger().error(
                "Error while deleting token from storage. Exception : {0}".format(
                    str(e)
                )
            )
            raise Exception(
                "Deleting of token from password store failed for {0}".format(token_key)
            )

        return {"payload": "Token deleted successfully ", "status": 200}
