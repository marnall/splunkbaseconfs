import json
import requests

from splunktaucclib.rest_handler.endpoint.validator import Validator


class AccountValidator(Validator):
    """This class extends base class of Validator."""

    def validate(self, value, data):
        """We define Custom validation here for verifying credentials when storing account information."""
        try:
            base_url = data["endgame_api"]
            if base_url.endswith('/'):
                base_url = base_url[:-1]
            endgame_url = base_url + '/api/auth/login'
            username = data["username"]
            password = data["password"]
            headers = {'content-type': 'application/json'}
            credentials = {"username": username, "password": password}
            response = requests.post(endgame_url, headers=headers,
                                     data=json.dumps(credentials))
            response.raise_for_status()

            try:
                stringified_response = json.dumps(response.content)
                json_response = json.loads(stringified_response)
                token = json.loads(json_response.encode('utf-8'))['metadata']['token']

                if not token:
                    raise Exception()
            except Exception:
                raise Exception("Authentication Failed")

        except requests.exceptions.ConnectionError:
            self.put_msg("Unable to connect to the given Endgame API. Please check the URL")
            return False

        except Exception as e:
            self.put_msg(
                "Please check Endgame API URL or credentials. Cause -> " + str(e))
            return False
        return True
