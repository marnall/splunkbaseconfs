from splunktaucclib.rest_handler.endpoint.validator import Validator

class SAMLInputValidation(Validator):
    def validate(self, value, data):
        try:
            if not value.startswith("https"):
                msg = "URL must be HTTPS (e.g. https://yoursite.com/file.conf)"
                raise Exception(msg)
            else:
                return True
        except Exception as exc:
            self.put_msg(exc)
            return False
