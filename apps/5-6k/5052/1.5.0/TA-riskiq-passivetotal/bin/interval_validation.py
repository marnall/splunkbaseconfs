"""Interval Validation."""
from splunktaucclib.rest_handler.endpoint.validator import Validator
import croniter


class IntervalValidator(Validator):
    """Invterval Validation."""

    def validate(self, value, data):
        """Validate interval field."""
        interval = data.get("interval")
        try:
            try:
                interval = int(interval)
                if interval <= 0:
                    self.put_msg("Interval should be a positive integer.")
                    return False
                return True
            except ValueError:
                if croniter.croniter.is_valid(interval):
                    return True
                else:
                    self.put_msg("Invalid Interval. Please enter valid interval.")
                    return False
        except Exception:
            self.put_msg("Internal exception occured. Please try again.")
            return False
