from splunktaucclib.rest_handler.endpoint import DataInputModel
from splunktaucclib.rest_handler.endpoint.validator import Validator


class InvalidInterval(Exception):
    """Exception class for Invalid Interval."""

    pass


class CyberVisionModel(DataInputModel):
    """CyberVision validator."""

    def validate(self, name, data, existing=None):
        """Validate Input parameters."""
        # Add hidden fields to avoid insertion error
        data['page_size'] = data.get('page_size', '')
        super(CyberVisionModel, self).validate(name, data, existing)


class IntervalValidator(Validator):
    """Class to validate the interval."""

    def validate(self, value, data):
        """Validates the interval value."""
        interval = data.get("interval")
        try:
            interval = int(interval)
            if interval < 60:
                raise InvalidInterval
            return True
        except InvalidInterval:
            self.put_msg("Interval should be greater than or equal to 60 seconds.")
            return False
        except Exception:
            self.put_msg("Interval should be greater than or equal to 60 seconds.")
            return False
