#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import splunk_ta_o365_bootstrap

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.error import RestError
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
import logging
from datetime import datetime, timedelta, timezone
from rh_common import parse_utc_datetime_strict
from solnlib import conf_manager
from splunk_ta_o365.common.settings import APP_NAME
from splunk_ta_o365.modinputs.message_trace.consts import (
    MAX_LOOKBACK_DAYS,
    RWS_REALM_BASE_URIS,
    TENANTS_CONF_NAME,
)

util.remove_http_proxy_env_vars()

RWS_MAX_LOOKBACK_DAYS = 10


class MessageTraceValidator(validator.Validator):
    def __init__(self):
        super(MessageTraceValidator, self).__init__()

    def validate(self, value, data):
        return self.date_validations(data)

    def date_validations(self, data):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        start_date_input = data.get("start_date_time")
        if not start_date_input:
            if data.get("input_mode") == "index_once":
                self.put_msg("Start date/time is required for Index Once input.")
                return False
            return True

        try:
            start_date_time = parse_utc_datetime_strict(start_date_input)
        except ValueError:
            self.put_msg("Valid Datetime format is 'YYYY-MM-DDTHH:MM:SS' (UTC)")
            return False
        if start_date_time > now:
            self.put_msg("The Start date/time cannot be in the future")
            return False
        old_date = now - timedelta(days=MAX_LOOKBACK_DAYS)
        if start_date_time < old_date:
            self.put_msg(
                "Start date/time cannot be older than %d days in the past."
                % MAX_LOOKBACK_DAYS
            )
            return False
        if data.get("input_mode") == "index_once":
            end_date_input = data.get("end_date_time")
            if not end_date_input:
                self.put_msg("End date/time is required for Index Once input.")
                return False
            try:
                end_date_time = parse_utc_datetime_strict(end_date_input)
            except ValueError:
                self.put_msg("Valid Datetime format is 'YYYY-MM-DDTHH:MM:SS' (UTC)")
                return False
            if end_date_time > now:
                self.put_msg("The End date/time cannot be in the future")
                return False
            if start_date_time > end_date_time:
                self.put_msg(
                    "The Start date/time cannot be ahead of the End date/time."
                )
                return False
        return True


class MessageTraceUTCDateValidator(validator.Validator):
    def __init__(self):
        super(MessageTraceUTCDateValidator, self).__init__()

    def validate(self, value, data):
        try:
            parse_utc_datetime_strict(value)
            return True
        except ValueError:
            self.put_msg("Valid Datetime format is 'YYYY-MM-DDTHH:MM:SS' (UTC)")
            return False


def _get_tenant_endpoint(session_key, tenant_name):
    cfm = conf_manager.ConfManager(session_key, APP_NAME)
    conf = cfm.get_conf(TENANTS_CONF_NAME)
    tenant = conf.get(stanza_name=tenant_name, only_current_app=True)
    return tenant.get("endpoint")


def _get_max_lookback_days(session_key, tenant_name):
    if not tenant_name:
        return MAX_LOOKBACK_DAYS
    try:
        endpoint = _get_tenant_endpoint(session_key, tenant_name)
    except Exception:
        return MAX_LOOKBACK_DAYS
    if endpoint in RWS_REALM_BASE_URIS:
        return RWS_MAX_LOOKBACK_DAYS
    return MAX_LOOKBACK_DAYS


def _get_tenant_lookback_validation_error(session_key, data):
    start_date_input = data.get("start_date_time")
    if not start_date_input:
        return None
    try:
        start_date_time = parse_utc_datetime_strict(start_date_input)
    except ValueError:
        return None

    max_lookback_days = _get_max_lookback_days(session_key, data.get("tenant_name"))
    old_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        days=max_lookback_days
    )
    if start_date_time < old_date:
        return "Start date/time cannot be older than %d days in the past." % (
            max_lookback_days
        )
    return None


fields = [
    field.RestField(
        "message_trace_input_configuration_help_link",
        required=False,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField(
        "input_mode",
        required=True,
        encrypted=False,
        default="continuously_monitor",
        validator=None,
    ),
    field.RestField(
        "start_date_time",
        required=False,
        encrypted=False,
        default=None,
        validator=MessageTraceUTCDateValidator(),
    ),
    field.RestField(
        "end_date_time",
        required=False,
        encrypted=False,
        default=None,
        validator=MessageTraceUTCDateValidator(),
    ),
    field.RestField(
        "tenant_name",
        required=True,
        encrypted=False,
        default=None,
        validator=MessageTraceValidator(),
    ),
    field.RestField(
        "index",
        required=True,
        encrypted=False,
        default="default",
        validator=validator.Pattern(
            regex=r"""^^[A-Za-z0-9][\w-]*$""",
        ),
    ),
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default="300",
        validator=validator.Pattern(
            regex=r"""^\-[1-9]\d*$|^\d*$""",
        ),
    ),
    field.RestField(
        "query_window_size",
        required=False,
        encrypted=False,
        default="60",
        validator=None,
    ),
    field.RestField(
        "delay_throttle",
        required=False,
        encrypted=False,
        default="1440",
        validator=None,
    ),
    field.RestField("disabled", required=False, validator=None),
]
model = RestModel(fields, name=None)

endpoint = DataInputModel(
    "splunk_ta_o365_message_trace",
    model,
)


class MessageTraceRestHandler(AdminExternalHandler):
    def _validate_tenant_lookback(self):
        message = _get_tenant_lookback_validation_error(
            self.getSessionKey(), self.payload
        )
        if message:
            raise RestError(400, message)

    def handleCreate(self, confInfo):
        self._validate_tenant_lookback()
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleEdit(self, confInfo):
        self._validate_tenant_lookback()
        AdminExternalHandler.handleEdit(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=MessageTraceRestHandler,
    )
