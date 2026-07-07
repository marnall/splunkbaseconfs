
import re
import import_declare_test
import traceback
import requests
import splunk.admin as admin
from datetime import datetime, timedelta, timezone
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from solnlib.splunkenv import get_splunkd_uri
import logging

from infoblox_helpers.constants import INTERNAL_VERIFY_SSL, APP_NAME, DATETIME_FORMAT, DATETIME_REGEX
from infoblox_helpers.logger_manager import setup_logging
logger = setup_logging("ta_infoblox_rh_infoblox_threat_intelligence")

util.remove_http_proxy_env_vars()


class CustomHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        """
        This class handles the parameters in the configuration page
        """
        AdminExternalHandler.__init__(self, *args, **kwargs)
    
    def handleCreate(self, conf_info):
        """Handle create."""
        if self.payload.get("start_date"):
            start_date_str = self.payload["start_date"]
            # Validate the date format
            try:
                if not re.match(DATETIME_REGEX, start_date_str):
                    raise ValueError("Invalid start date time.")
                # Check if the date is not in the future
                start_date = datetime.strptime(start_date_str, DATETIME_FORMAT)
                if start_date.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
                    raise ValueError("The start date time cannot be in the future.")
            except Exception:
                # Handle the error, e.g., by logging and raising an exception or returning an error response
                logger.error(f"Invalid start date time format or future date provided: {traceback.format_exc()}")
                raise admin.ArgValidationException("Invalid start date time format or future date time provided.")
        elif self.payload.get("historical_data") != "0":
                # Set start_date to 30 days before the current UTC date and time
                start_date = datetime.now(timezone.utc) - timedelta(days=30)
                # Format the start_date back to string format if needed
                start_date_str = start_date.strftime(DATETIME_FORMAT)[:-3]
                # Here you might want to update the payload or handle it accordingly
                self.payload["start_date"] = start_date_str
                logger.info("No start date time provided. Using start date time of 30 days ago: {}".format(start_date_str))
        super(CustomHandler, self).handleCreate(conf_info)
    
    def handleRemove(self, conf_info):
        """
        :param conf_info: The dictionary containing configurable parameters.
        :return: None
        """
        session_key = self.getSessionKey()
        logger.info("message=checkpoint_deletion_started | Checkpoint deletion started for {} input.".format(self.callerArgs.id))
        try:
            requests.delete(
                "{}/servicesNS/nobody/{}/storage/collections/data/InfobloxAppForSplunk_{}_checkpointer".format(get_splunkd_uri(), APP_NAME, self.callerArgs.id),
                headers={
                    "Authorization": "Splunk {}".format(session_key)
                },
                verify=INTERNAL_VERIFY_SSL
            )
            super(CustomHandler, self).handleRemove(conf_info)
            logger.info("message=checkpoint_deletion_success | Checkpoint deleted for {} input.".format(self.callerArgs.id))
        except Exception:
            logger.error("message=rest_call_error | Error occured.\n{}".format(traceback.format_exc()))

            



fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=3600,
        validator=None
    ),
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=validator.String(
            max_len=80, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'global_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'threat_level',
        required=False,
        encrypted=False,
        default=80,
        validator=None
    ), 
    field.RestField(
        'confidence_level',
        required=False,
        encrypted=False,
        default=80,
        validator=None  
    ),
    field.RestField(
        'historical_data',
        required=False,
        encrypted=False,
        default=0,
        validator=None
    ),
    field.RestField(
        'start_date',
        required=False,
        encrypted=False,
        default=None,
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
    'infoblox_threat_intelligence',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=CustomHandler,
    )
