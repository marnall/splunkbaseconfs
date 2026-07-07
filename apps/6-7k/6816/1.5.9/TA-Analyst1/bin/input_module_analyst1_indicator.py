# encoding = utf-8

from analyst1_indicator_sync.managers import SyncManager
from analyst1_logging import get_logger

logger = get_logger("ta_analyst1_input")


def use_single_instance_mode():
    return True


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    pass


def collect_events(helper, ew):
    try:
        logger.debug("Starting Analyst1 IOC data collection")
        sync_manager = SyncManager(helper, ew)
        sync_manager.execute()
        logger.debug("Analyst1 IOC data collection completed")

    except Exception as e:
        logger.exception("Analyst1 IOC data Collection Failed.")
        raise e
