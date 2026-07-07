
import ta_cisco_ni_declare
import splunk.admin as admin

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

util.remove_http_proxy_env_vars()


class CustomConfigMigrationHandler(ConfigMigrationHandler):
    """
    Manage the Rest Handler for server
    :param ConfigMigrationHandler: inhereting ConfigMigrationHandler
    """

    def interval_validate(self):
        """Validate interval field."""
        interval = self.payload.get("interval")
        try:
            interval = int(interval)
            if interval < 60:
                raise admin.ArgValidationException("Interval must be greater than or equal to 60.")
        except ValueError:
            raise admin.ArgValidationException("Invalid Interval. Please enter valid interval.")

    def time_range_validate(self):
        """Validate time_range field."""
        time_range = self.payload.get("time_range")
        try:
            time_range = int(time_range)
            if time_range < 0:
                raise admin.ArgValidationException("Time Range must be greater than or equal to 0.")
        except ValueError:
            raise admin.ArgValidationException("Invalid Time Range. Please enter valid Time Range.")

    def category_validate(self):
        """Validate advisories_category and anomalies_category field."""
        alert_type = self.payload.get("alert_type")
        if alert_type == 'advisories':
            advisories_category = self.payload.get("advisories_category")
            if advisories_category == "":
                raise admin.ArgValidationException("Field Category is required")
        else:
            anomalies_category = self.payload.get("anomalies_category")
            if anomalies_category == "":
                raise admin.ArgValidationException("Field Category is required")

    def handleCreate(self, confInfo):
        """Handle creation of input in config file."""
        self.interval_validate()
        self.category_validate()
        self.time_range_validate()
        super(CustomConfigMigrationHandler, self).handleCreate(confInfo)

    def handleEdit(self, confInfo):
        """Handles the edit operation. """
        if 'disabled' not in self.payload:
            self.interval_validate()
            self.category_validate()
            self.time_range_validate()
        super(CustomConfigMigrationHandler, self).handleEdit(confInfo)


fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=60,
        validator=None
    ),
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=validator.String(
            min_len=1,
            max_len=80,
        )
    ),
    field.RestField(
        'alert_type',
        required=True,
        encrypted=False,
        default='advisories',
        validator=None
    ),
    field.RestField(
        'anomalies_category',
        required=False,
        encrypted=False,
        default='*',
        validator=None
    ),
    field.RestField(
        'advisories_category',
        required=False,
        encrypted=False,
        default='*',
        validator=None
    ),
    field.RestField(
        'severity',
        required=True,
        encrypted=False,
        default='*',
        validator=None
    ),
    field.RestField(
        'global_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'time_range',
        required=True,
        encrypted=False,
        default=4,
        validator=None
    ),
    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    'cisco_ni',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=CustomConfigMigrationHandler,
    )
