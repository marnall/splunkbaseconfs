"""Utilities related to netskope modular input."""

import netskope_utils
import const
import six

from splunktaucclib.rest_handler.endpoint import DataInputModel
from netskope_utils import DEFAULT_LAST_DAYS, read_conf_file, GetSessionKey


class NetskopeClientsModel(DataInputModel):
    """NetskopeClientsModel validator."""

    def validate(self, name, data, existing=None):
        """Validate Input parameters."""
        limit = offset = failed_window_retries = None
        session_key = GetSessionKey().session_key
        # Get the existing data if any for hidden fields
        conf_file_stanzas = read_conf_file(session_key, "inputs")
        for input_stanza in conf_file_stanzas:
            if "netskope_clients://" in input_stanza and input_stanza.split("://")[-1] == name:
                limit = conf_file_stanzas[input_stanza].get("limit")
                offset = conf_file_stanzas[input_stanza].get("offset")
                failed_window_retries = conf_file_stanzas[input_stanza].get("failed_window_retries")

        # Add hidden fields to avoid insertion error
        data['limit'] = '' if limit is None else limit
        data['offset'] = '' if offset is None else offset
        data["failed_window_retries"] = (
            const.FAILED_WINDOW_RETRIES if failed_window_retries is None else failed_window_retries
        )

        # Create default start datetime if not provided
        start_datetime = data.get('start_datetime')
        if (not start_datetime) or (isinstance(start_datetime, six.string_types) and start_datetime.strip() == ''):
            data['start_datetime'] = netskope_utils.get_default_datetime(last_days=DEFAULT_LAST_DAYS)

        super(NetskopeClientsModel, self).validate(name, data, existing)
