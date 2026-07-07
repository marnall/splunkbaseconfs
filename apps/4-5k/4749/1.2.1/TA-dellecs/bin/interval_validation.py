import croniter
import datetime
from splunktaucclib.rest_handler.endpoint import validator


class IntervalValidator(validator.Validator):
    """This class extends base class of Validator."""

    def validate(self, value, data):
        """We define Custom validation here for verifying credentials when storing account information."""
        interval = data.get('interval')
        try:
            interval = int(interval)
            if interval <= 0:
                self.put_msg("Time interval must be a positive integer.")
                return False
            return True
        except Exception:
            try:
                now = datetime.datetime.now()
                cron = croniter.croniter(interval, now)
                cron.get_next(datetime.datetime)
            except Exception:
                self.put_msg("Time interval of input must be in seconds or cron schedule.")
                return False
        if len(str(interval).split()) < 6:
            return True
        else:
            self.put_msg("Time interval of input must be in seconds or cron schedule.")
            return False
