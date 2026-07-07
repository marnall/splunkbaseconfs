
import ta_jupiterone_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from ta_jupiterone_log_manager import setup_logging
from ta_jupiterone_validations import IntervalValidator, DateTimeValidator
import datetime

import splunk.rest as rest

util.remove_http_proxy_env_vars()

logger = setup_logging('ta_jupiterone_rh_jupiterone_alerts')


class CustomConfigMigrationHandler(ConfigMigrationHandler):
    """
    Manage the Rest Handler for server
    :param ConfigMigrationHandler: inhereting ConfigMigrationHandler
    """

    def set_default_date_time(self):
        """Set the default value of start_datetime if not provided."""
        start_datetime = self.payload.get('start_datetime')
        if not start_datetime:
            logger.info("JupiterOne Info: Set the start_datetime to default value last 30 days.")
            self.payload['start_datetime'] = str((datetime.datetime.utcnow() - 
            datetime.timedelta(days=30)).isoformat(timespec='milliseconds'))

    def handleCreate(self, confInfo):
        """Handle creation of input in config file."""
        self.set_default_date_time()
        super(CustomConfigMigrationHandler, self).handleCreate(confInfo)

    def handleRemove(self, confInfo):
        """Handle the delete operation"""
        try:
            # Remove the kv store checkpoint value
            rest.simpleRequest("/servicesNS/nobody/TA-JupiterOne/storage/collections/data/TA_JupiterOne_checkpointer/{}".format(self.callerArgs.id + "_alerts"),
                               method='DELETE',
                               sessionKey=self.getSessionKey(),
                               raiseAllErrors=True)
        except Exception:
            logger.error("JupiterOne Error: Error occured while deletion of kvstore checkpoint.")
        super(CustomConfigMigrationHandler, self).handleRemove(confInfo)


fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=300,
        validator=IntervalValidator()
    ),
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='main',
        validator=validator.String(
            min_len=1,
            max_len=80,
        )
    ),
    field.RestField(
        'jupiterone_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'pull_alert_related_objects',
        required=False,
        encrypted=False,
        default=0,
        validator=None
    ),
    field.RestField(
        'start_datetime',
        required=False,
        encrypted=False,
        default=None,
        validator=DateTimeValidator()
    ),

    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    'jupiterone_alerts',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=CustomConfigMigrationHandler,
    )
