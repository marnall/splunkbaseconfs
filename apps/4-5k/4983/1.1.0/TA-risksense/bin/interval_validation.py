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
            if interval < 86400:
                self.put_msg("Time interval must be a positive integer greater than or equal to 86400.")
                return False 
            return True
        except Exception:
            try:
                now = datetime.datetime.now()
                cron = croniter.croniter(interval, now)
                first_invocation = cron.get_next(datetime.datetime)
                second_invocation = cron.get_next(datetime.datetime)
                duration =  int((second_invocation - first_invocation).total_seconds())
                if duration < 86400:
                    self.put_msg("Cron schedule must be greater or equal to one day.")
                    return False  
            except Exception:
                self.put_msg("Time interval of input must be in seconds or cron schedule.")
                return False
        if len(str(interval).split()) < 6:
            return True
        else:
            self.put_msg("Time interval of input must be in seconds or cron schedule.")
            return False