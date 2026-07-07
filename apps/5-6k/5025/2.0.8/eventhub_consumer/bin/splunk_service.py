import splunklib.client as client


class SplunkService(object):
    def __init__(self, session_key, app, owner='nobody'):
        """
        :param session_key: Splunk session key for calling Splunk's REST APIs
        :type: session_key: str
        :param app: The app context of the namespace.
        :type app: str
        :param owner: The owner context of the namespace (optional).
        :type owner: str
        """
        self.app = app
        self.owner = owner
        self.connection = client.connect(
            app=app,
            owner=owner,
            token=session_key
        )

    def store_credentials(self, user, password, realm=None):
        try:
            c = self.get_credentials(user, realm)  # if the credential exists, replace it
            self.connection.storage_passwords.delete(username=c.username)
        except Exception:
            pass
        self.connection.storage_passwords.create(
            username=user, 
            password=password,
            realm=realm
        )

    def mask_credentials(self, input_name, **kwargs):
        try:
            kind, input_name = input_name.split("://")
            _input = self.connection.inputs[(input_name, kind)]
            _input.update(**kwargs).refresh()
        except Exception as e:
            raise Exception(f"Error updating inputs.conf: {str(e)}")

    def get_credentials(self, user, realm=None):
        try:
            if realm:
                user = f'{realm}:{user}'
            for storage_password in self.connection.storage_passwords:
                if storage_password.username == user:
                    return storage_password
        except Exception as e:
            raise Exception(f"Could not get {self.app} credentials from splunk. Error: {str(e)}")
        raise CredentialNotFoundError


class CredentialNotFoundError(Exception):
    pass
