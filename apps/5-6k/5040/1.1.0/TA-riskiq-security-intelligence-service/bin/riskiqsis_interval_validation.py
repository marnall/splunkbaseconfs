"""Validation for the interval field."""

from splunktaucclib.rest_handler.endpoint import validator


class IntervalValidator(validator.Validator):
    """This class extends base class of Validator. Class to validate the interval field."""

    def validate(self, value, data):
        """We define Custom validation here for verifying credentials when storing account information."""
        data_type = data.get('data_type')
        interval = int(data.get('interval'))

        try:
            if data_type == 'newly_observed_host':
                if interval < 86400:
                    self.put_msg("Time interval must be a positive integer greater than or equal to 86400 for 'Newly\
                                 Observed Host' Data Type")
                    return False
                return True
            else:
                if interval < 3600:
                    self.put_msg("Time interval must be a positive integer greater than or equal to 3600 for all the \
                                 Data Types except 'Newly Observed Host'")
                    return False
                return True
        except Exception:
            self.put_msg("Internal exception occured. Please try again.")
            return False
