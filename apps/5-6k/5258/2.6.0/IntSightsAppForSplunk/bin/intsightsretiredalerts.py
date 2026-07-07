import os
from datetime import datetime, timedelta

from log_manager import setup_logging
from intsights_utils import (
    get_macro_definition,
    create_service
)
from command_utils import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRY,
    SessionKeyProvider,
    AlertsManager,
)

logger_name = os.path.splitext(os.path.basename(__file__))[0]
logger = setup_logging(logger_name)
ALERTS_RETIRING_MACRO = "intsights_alert_retiring_days"


class AlertUtils:
    """Provides the needed information to access the lookups."""

    def __init__(self):
        """Initialize the object."""
        self._alerts_manager = None
        self._serviceobj = None

    @property
    def serviceobj(self):
        """Set the serviceobj as property."""
        if self._serviceobj is None:
            session_key = SessionKeyProvider(logger).session_key
            self._serviceobj = create_service(session_key)
        return self._serviceobj

    @property
    def alerts_manager(self):
        """Set alerts_manager as property."""
        if self._alerts_manager is None:
            self._alerts_manager = AlertsManager(
                self.serviceobj, logger, DEFAULT_BACKOFF_FACTOR, DEFAULT_MAX_RETRY
            )
        return self._alerts_manager

    def retired_policy(self):
        """This will return the retired policy."""
        macro_value = get_macro_definition(self.serviceobj, ALERTS_RETIRING_MACRO)
        try:
            macro_value = int(macro_value.strip())
        except ValueError:
            macro_value = None
        return macro_value


if __name__ == "__main__":
    logger.info("Starting the intsightsretiredalerts script execution.")
    CURRENT_TIME = datetime.utcnow()
    alert_utils = AlertUtils()
    retired_policy_days = alert_utils.retired_policy()
    logger.info(
        "Fetched the Retired Alerts policy from the respected macro :{}".format(
            retired_policy_days
        )
    )
    lastUpdate_list = []
    isClosed_dict = {"isClosed": "true"}
    lastUpdate_list.append(isClosed_dict)
    if retired_policy_days is not None:
        lastupdatetime = (
            CURRENT_TIME
            - timedelta(
                days=retired_policy_days,
                hours=CURRENT_TIME.hour,
                minutes=CURRENT_TIME.minute,
                seconds=CURRENT_TIME.second,
                microseconds=CURRENT_TIME.microsecond,
            )
        ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        lastupdate_dict = {"updateDate": {"$lt": lastupdatetime}}
        lastUpdate_list.append(lastupdate_dict)
    endpoint_query = {"$or": lastUpdate_list}

    logger.info("Deleting retired alerts from intsights_alert_master_lookup...")
    # Responsible to delete data from the master_lookup
    alert_utils.alerts_manager.delete_from_master_lookup(endpoint_query)
    logger.info(
        "Time taken - {} seconds.".format(
            (datetime.utcnow() - CURRENT_TIME).total_seconds()
        )
    )
    logger.info("Completed the execution of intsightsretiredalerts script")
