"""Util class - Supporting Python file for execute search string."""
import splunk.search as splunkSearch
import logger_manager as log

_LOGGER = log.setup_logging("netapp_app_eseries_perf_util")

APP_NAME = 'netapp_app_eseries_perf'


def execute_search(search_string, session_key):
    """
    Execute search  and return resultSet.

    :param search_string: Valid Search String
    :param session_key: Valid Session Key
    """
    try:
        return splunkSearch.searchAll(search_string, sessionKey=session_key, namespace=APP_NAME)
    except Exception:
        _LOGGER.exception("Symantec Email Error: Failed to execute search.Please contact administrator.")
        return None
