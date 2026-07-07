"""Utilities related to netskope modular input."""

import netskope_utils
import six
import const

from splunktaucclib.rest_handler.endpoint import DataInputModel
from splunktaucclib.rest_handler.error import RestError

BAD_REQUEST_STATUS_CODE = 400


class NetskopeModel(DataInputModel):
    """NetskopeModel validator."""

    def validate(self, name, data, existing=None):
        """Validate Input parameters."""
        # Add hidden fields to avoid insertion error
        data['limit'] = data.get('limit', '')
        data['offset'] = data.get('offset', '')
        data['failed_window_retries'] = data.get('failed_window_retries', const.FAILED_WINDOW_RETRIES)

        if data['event_type'].strip() == "":
            data['event_type'] = data['event_type'].strip()

        if data.get('collection_type') == 'realtime':
            data['interval'] = data.get('interval', const.REALTIME_INTERVAL_SEC)
            data['query_interval'] = data.get('query_interval', const.REALTIME_QUERY_INTERVAL_SEC)
            data['window_divisor'] = data.get('window_divisor', const.REALTIME_WINDOW_DIVISOR)
            data['thread_count'] = data.get('thread_count', const.REALTIME_THREAD_COUNT)

        elif data.get('collection_type') == 'historical':
            start_datetime = data.get('start_datetime')
            is_start_datetime_not_exists = (not start_datetime) or \
                (isinstance(start_datetime, six.string_types) and start_datetime.strip() == '')
            if is_start_datetime_not_exists:
                data['start_datetime'] = netskope_utils.get_default_datetime(
                    last_days=const.HISTORICAL_DEFAULT_STARTDATETIME_DAYS_BACK
                )

            end_datetime = data.get('end_datetime')
            is_end_datetime_not_exists = (not end_datetime) or \
                (isinstance(end_datetime, six.string_types) and end_datetime.strip() == '')
            if is_end_datetime_not_exists:
                data['end_datetime'] = netskope_utils.get_default_datetime(last_days=0)

            start_datetime = netskope_utils.get_epoch_time(data['start_datetime'])
            end_datetime = netskope_utils.get_epoch_time(data['end_datetime'])
            if end_datetime < start_datetime:
                raise RestError(
                    BAD_REQUEST_STATUS_CODE,
                    "Start Datetime should not be greater than End Datetime. Please enter valid timerange."
                )

            data['interval'] = data.get('interval', const.HISTORICAL_INTERVAL_SEC)
            data['query_interval'] = data.get('query_interval', const.HISTORICAL_QUERY_INTERVAL_SEC)
            data['window_divisor'] = data.get('window_divisor', const.HISTORICAL_WINDOW_DIVISOR)
            data['thread_count'] = data.get('thread_count', const.HISTORICAL_THREAD_COUNT)

        super(NetskopeModel, self).validate(name, data, existing)
