"""Utilities related to simulation modular input."""

import ta_safebreach_declare  # noqa: F401
import six
import datetime

from splunktaucclib.rest_handler.endpoint import DataInputModel
import ta_safebreach_const


def get_default_datetime(last_days=ta_safebreach_const.DEFAULT_LAST_DAYS):
    """Return default datetime."""
    return (datetime.datetime.utcnow() - datetime.timedelta(days=last_days)).strftime(
        ta_safebreach_const.START_DATETIME_FORMAT
    )[:-4] + "Z"


class SimulationInputModel(DataInputModel):
    """SimulationInputModel validator."""

    def validate(self, name, data, existing=None):
        """Validate Input parameters."""
        # Create default start datetime if not provided
        start_datetime = data.get('start_date_time')
        if (not start_datetime) or (isinstance(start_datetime, six.string_types) and start_datetime.strip() == ''):
            data['start_date_time'] = get_default_datetime(last_days=ta_safebreach_const.DEFAULT_LAST_DAYS)

        super(SimulationInputModel, self).validate(name, data, existing)


class InsightsInputModel(DataInputModel):
    """SimulationInputModel validator."""

    def validate(self, name, data, existing=None):
        """Validate Input parameters."""
        # Create default start datetime if not provided
        start_datetime = data.get('start_date_time')
        if (not start_datetime) or (isinstance(start_datetime, six.string_types) and start_datetime.strip() == ''):
            data['start_date_time'] = get_default_datetime(last_days=ta_safebreach_const.DEFAULT_LAST_DAYS)

        super(InsightsInputModel, self).validate(name, data, existing)

class AuditInputModel(DataInputModel):
    """SimulationInputModel validator."""

    def validate(self, name, data, existing=None):
        """Validate Input parameters."""
        # Create default start datetime if not provided
        start_datetime = data.get('start_date_time')
        if (not start_datetime) or (isinstance(start_datetime, six.string_types) and start_datetime.strip() == ''):
            data['start_date_time'] = get_default_datetime(last_days=ta_safebreach_const.DEFAULT_LAST_DAYS)

        super(AuditInputModel, self).validate(name, data, existing)
