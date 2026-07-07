"""Utilities related to netskope modular input."""

import netskope_utils
import six
import const

from splunktaucclib.rest_handler.endpoint import DataInputModel
from netskope_utils import read_conf_file, GetSessionKey


class NetskopeEventsIteratorModel(DataInputModel):
    """NetskopeModel validator."""

    def validate(self, name, data, existing=None):
        """Validate Input parameters."""
        interval = timeout = retry_count = None
        is_first_call_page = None
        is_first_call_application = None
        is_first_call_audit = None
        is_first_call_infrastructure = None
        is_first_call_network = None
        is_first_call_incident = None
        is_first_call_endpoint = None
        session_key = GetSessionKey().session_key

        # Get the existing data if any for hidden fields
        conf_file_stanzas = read_conf_file(session_key, "inputs")
        for input_stanza in conf_file_stanzas:
            if "netskope_events_v2://" in input_stanza and input_stanza.split("://")[-1] == name:
                interval = conf_file_stanzas[input_stanza].get("interval")
                timeout = conf_file_stanzas[input_stanza].get("timeout")
                retry_count = conf_file_stanzas[input_stanza].get("retry_count")
                is_first_call_page = conf_file_stanzas[input_stanza].get("is_first_call_page")
                is_first_call_application = conf_file_stanzas[input_stanza].get("is_first_call_application")
                is_first_call_audit = conf_file_stanzas[input_stanza].get("is_first_call_audit")
                is_first_call_infrastructure = conf_file_stanzas[input_stanza].get("is_first_call_infrastructure")
                is_first_call_network = conf_file_stanzas[input_stanza].get("is_first_call_network")
                is_first_call_incident = conf_file_stanzas[input_stanza].get("is_first_call_incident")
                is_first_call_endpoint = conf_file_stanzas[input_stanza].get("is_first_call_endpoint")

        # Add hidden fields to avoid insertion error
        data["interval"] = const.ITERATOR_INTERVAL_SEC if interval is None else interval
        data["timeout"] = const.EVENTS_TIMEOUT if timeout is None else timeout
        data["retry_count"] = const.RETRY_COUNT if retry_count is None else retry_count
        data["is_first_call_page"] = (
            const.IS_FIRST_CALL if is_first_call_page is None else is_first_call_page
        )
        data["is_first_call_application"] = (
            const.IS_FIRST_CALL if is_first_call_application is None else is_first_call_application
        )
        data["is_first_call_audit"] = (
            const.IS_FIRST_CALL if is_first_call_audit is None else is_first_call_audit
        )
        data["is_first_call_infrastructure"] = (
            const.IS_FIRST_CALL if is_first_call_infrastructure is None else is_first_call_infrastructure
        )
        data["is_first_call_network"] = (
            const.IS_FIRST_CALL if is_first_call_network is None else is_first_call_network
        )
        data["is_first_call_incident"] = (
            const.IS_FIRST_CALL if is_first_call_incident is None else is_first_call_incident
        )
        data["is_first_call_endpoint"] = (
            const.IS_FIRST_CALL if is_first_call_endpoint is None else is_first_call_endpoint
        )

        start_datetime = data.get("start_datetime")
        is_start_datetime_not_exists = (not start_datetime) or (
            isinstance(start_datetime, six.string_types)
            and start_datetime.strip() == ""
        )
        if is_start_datetime_not_exists:
            data["start_datetime"] = netskope_utils.get_default_datetime(
                last_days=const.ITERATOR_DEFAULT_STARTDATETIME_DAYS_BACK
            )

        super(NetskopeEventsIteratorModel, self).validate(name, data, existing)


class NetskopeAlertsIteratorModel(DataInputModel):
    """NetskopeModel validator."""

    def validate(self, name, data, existing=None):
        """Validate Input parameters."""
        interval = timeout = retry_count = None
        is_first_call_all = None
        is_first_call_compromisedcredential = None
        is_first_call_ctep = None
        is_first_call_dlp = None
        is_first_call_malsite = None
        is_first_call_malware = None
        is_first_call_policy = None
        is_first_call_quarantine = None
        is_first_call_remediation = None
        is_first_call_securityassessment = None
        is_first_call_uba = None
        is_first_call_watchlist = None
        is_first_call_device = None
        is_first_call_content = None

        session_key = GetSessionKey().session_key

        # Get the existing data if any for hidden fields
        conf_file_stanzas = read_conf_file(session_key, "inputs")
        for input_stanza in conf_file_stanzas:
            if "netskope_alerts_v2://" in input_stanza and input_stanza.split("://")[-1] == name:
                interval = conf_file_stanzas[input_stanza].get("interval")
                timeout = conf_file_stanzas[input_stanza].get("timeout")
                retry_count = conf_file_stanzas[input_stanza].get("retry_count")
                is_first_call_all = conf_file_stanzas[input_stanza].get("is_first_call_all")
                is_first_call_compromisedcredential = conf_file_stanzas[input_stanza].get(
                    "is_first_call_compromisedcredential"
                )
                is_first_call_ctep = conf_file_stanzas[input_stanza].get("is_first_call_ctep")
                is_first_call_dlp = conf_file_stanzas[input_stanza].get("is_first_call_dlp")
                is_first_call_malsite = conf_file_stanzas[input_stanza].get("is_first_call_malsite")
                is_first_call_malware = conf_file_stanzas[input_stanza].get("is_first_call_malware")
                is_first_call_policy = conf_file_stanzas[input_stanza].get("is_first_call_policy")
                is_first_call_quarantine = conf_file_stanzas[input_stanza].get("is_first_call_quarantine")
                is_first_call_remediation = conf_file_stanzas[input_stanza].get("is_first_call_remediation")
                is_first_call_securityassessment = conf_file_stanzas[input_stanza].get(
                    "is_first_call_securityassessment"
                )
                is_first_call_uba = conf_file_stanzas[input_stanza].get("is_first_call_uba")
                is_first_call_watchlist = conf_file_stanzas[input_stanza].get("is_first_call_watchlist")
                is_first_call_device = conf_file_stanzas[input_stanza].get("is_first_call_device")
                is_first_call_content = conf_file_stanzas[input_stanza].get("is_first_call_content")

        # Add hidden fields to avoid insertion error
        data["interval"] = const.ITERATOR_INTERVAL_SEC if interval is None else interval
        data["timeout"] = const.EVENTS_TIMEOUT if timeout is None else timeout
        data["retry_count"] = const.RETRY_COUNT if retry_count is None else retry_count
        data["is_first_call_all"] = (
            const.IS_FIRST_CALL if is_first_call_all is None else is_first_call_all
        )
        data["is_first_call_compromisedcredential"] = (
            const.IS_FIRST_CALL
            if is_first_call_compromisedcredential is None
            else is_first_call_compromisedcredential
        )
        data["is_first_call_ctep"] = (
            const.IS_FIRST_CALL if is_first_call_ctep is None else is_first_call_ctep
        )
        data["is_first_call_dlp"] = (
            const.IS_FIRST_CALL if is_first_call_dlp is None else is_first_call_dlp
        )
        data["is_first_call_malsite"] = (
            const.IS_FIRST_CALL if is_first_call_malsite is None else is_first_call_malsite
        )
        data["is_first_call_malware"] = (
            const.IS_FIRST_CALL if is_first_call_malware is None else is_first_call_malware
        )
        data["is_first_call_policy"] = (
            const.IS_FIRST_CALL if is_first_call_policy is None else is_first_call_policy
        )
        data["is_first_call_quarantine"] = (
            const.IS_FIRST_CALL if is_first_call_quarantine is None else is_first_call_quarantine
        )
        data["is_first_call_remediation"] = (
            const.IS_FIRST_CALL if is_first_call_remediation is None else is_first_call_remediation
        )
        data["is_first_call_securityassessment"] = (
            const.IS_FIRST_CALL if is_first_call_securityassessment is None else is_first_call_securityassessment
        )
        data["is_first_call_uba"] = (
            const.IS_FIRST_CALL if is_first_call_uba is None else is_first_call_uba
        )
        data["is_first_call_watchlist"] = (
            const.IS_FIRST_CALL if is_first_call_watchlist is None else is_first_call_watchlist
        )
        data["is_first_call_device"] = (
            const.IS_FIRST_CALL if is_first_call_device is None else is_first_call_device
        )
        data["is_first_call_content"] = (
            const.IS_FIRST_CALL if is_first_call_content is None else is_first_call_content
        )

        start_datetime = data.get("start_datetime")
        is_start_datetime_not_exists = (not start_datetime) or (
            isinstance(start_datetime, six.string_types)
            and start_datetime.strip() == ""
        )
        if is_start_datetime_not_exists:
            data["start_datetime"] = netskope_utils.get_default_datetime(
                last_days=const.ITERATOR_DEFAULT_STARTDATETIME_DAYS_BACK
            )

        super(NetskopeAlertsIteratorModel, self).validate(name, data, existing)


class NetskopeEventsCSVIteratorModel(DataInputModel):
    """NetskopeModel validator."""

    def validate(self, name, data, existing=None):
        """Validate Input parameters."""
        interval = timeout = retry_count = None
        session_key = GetSessionKey().session_key

        # Get the existing data if any for hidden fields
        conf_file_stanzas = read_conf_file(session_key, "inputs")
        for input_stanza in conf_file_stanzas:
            if "netskope_events_v2_csv://" in input_stanza and input_stanza.split("://")[-1] == name:
                interval = conf_file_stanzas[input_stanza].get("interval")
                timeout = conf_file_stanzas[input_stanza].get("timeout")
                retry_count = conf_file_stanzas[input_stanza].get("retry_count")

        # Add hidden fields to avoid insertion error
        data["interval"] = const.ITERATOR_INTERVAL_SEC if interval is None else interval
        data["timeout"] = const.EVENTS_TIMEOUT if timeout is None else timeout
        data["retry_count"] = const.RETRY_COUNT if retry_count is None else retry_count

        super(NetskopeEventsCSVIteratorModel, self).validate(name, data, existing)


class NetskopeAlertsCSVIteratorModel(DataInputModel):
    """NetskopeModel validator."""

    def validate(self, name, data, existing=None):
        """Validate Input parameters."""
        interval = timeout = retry_count = None
        session_key = GetSessionKey().session_key

        # Get the existing data if any for hidden fields
        conf_file_stanzas = read_conf_file(session_key, "inputs")
        for input_stanza in conf_file_stanzas:
            if "netskope_alerts_v2_csv://" in input_stanza and input_stanza.split("://")[-1] == name:
                interval = conf_file_stanzas[input_stanza].get("interval")
                timeout = conf_file_stanzas[input_stanza].get("timeout")
                retry_count = conf_file_stanzas[input_stanza].get("retry_count")

        # Add hidden fields to avoid insertion error
        data["interval"] = const.ITERATOR_INTERVAL_SEC if interval is None else interval
        data["timeout"] = const.EVENTS_TIMEOUT if timeout is None else timeout
        data["retry_count"] = const.RETRY_COUNT if retry_count is None else retry_count

        super(NetskopeAlertsCSVIteratorModel, self).validate(name, data, existing)


class NetskopeClientsIteratorModel(DataInputModel):
    """NetskopeModel validator."""

    def validate(self, name, data, existing=None):
        """Validate Input parameters."""
        interval = timeout = retry_count = netskope_iterator_name = None
        session_key = GetSessionKey().session_key

        # Get the existing data if any for hidden fields
        conf_file_stanzas = read_conf_file(session_key, "inputs")
        for input_stanza in conf_file_stanzas:
            if "netskope_clients_iterator://" in input_stanza and input_stanza.split("://")[-1] == name:
                interval = conf_file_stanzas[input_stanza].get("interval")
                timeout = conf_file_stanzas[input_stanza].get("timeout")
                retry_count = conf_file_stanzas[input_stanza].get("retry_count")
                netskope_iterator_name = conf_file_stanzas[input_stanza].get("netskope_iterator_name")

        # Add hidden fields to avoid insertion error
        data["interval"] = const.ITERATOR_INTERVAL_SEC if interval is None else interval
        data["timeout"] = const.CLIENTS_TIMEOUT if timeout is None else timeout
        data["retry_count"] = const.RETRY_COUNT if retry_count is None else retry_count
        data["netskope_iterator_name"] = "" if netskope_iterator_name is None else netskope_iterator_name

        super(NetskopeClientsIteratorModel, self).validate(name, data, existing)


class NetskopeEventsMultiIteratorModel(DataInputModel):
    """NetskopeModel validator for Multi Iterator Event Type."""

    def validate(self, name, data, existing=None):
        """Validate Input parameters."""
        retry_count = timeout = netskope_iterator_name = interval = None
        session_key = GetSessionKey().session_key

        # Get the existing data if any for hidden fields
        conf_file_stanzas = read_conf_file(session_key, "inputs")
        for input_stanza in conf_file_stanzas:
            if "netskope_events_multi_iterator://" in input_stanza and input_stanza.split("://")[-1] == name:
                retry_count = conf_file_stanzas[input_stanza].get("retry_count")
                timeout = conf_file_stanzas[input_stanza].get("timeout")
                netskope_iterator_name = conf_file_stanzas[input_stanza].get("netskope_iterator_name")
                interval = conf_file_stanzas[input_stanza].get("interval")

        # Add hidden fields to avoid insertion error
        data["retry_count"] = const.RETRY_COUNT if retry_count is None else retry_count
        data["timeout"] = const.EVENTS_TIMEOUT if timeout is None else timeout
        data["netskope_iterator_name"] = "" if netskope_iterator_name is None else netskope_iterator_name
        data["interval"] = const.ITERATOR_INTERVAL_SEC if interval is None else interval

        super(NetskopeEventsMultiIteratorModel, self).validate(name, data, existing)
