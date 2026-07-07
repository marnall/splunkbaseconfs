# Standard library imports
import sys
import os

# Local imports
import reach_search_execution_helper
import reach_logger_manager as log

# Periodic base result path
BASE_RESULT_PATH = os.path.sep.join(os.path.abspath(__file__).split(
    os.sep)[:-2] + ['appserver', 'static', 'search_results', 'periodic_execution'])


def main():
    """Method to start the periodic collection."""
    session_key = sys.stdin.readline().strip()
    logger = log.setup_logging('reach_periodic_execution', session_key)

    content = {
        "session_key": session_key,
        "execution_type": "periodic",
        "base_result_path": BASE_RESULT_PATH
    }
    try:
        reach_search_execution_helper.start_collection(content, logger)
    except:
        # Update Status to Partially Completed
        logger.error(
            "Reach Error: Error occurred. Updating status to Partially Completed")
        reach_search_execution_helper.SettingsConfFile(
            session_key, logger).update_settings_conf_file(
            {"status": "Partially Completed"}, stanza="reach_periodic_execution")
        sys.exit()

    # TODO: Export to Reach service, Remove the exported file


if __name__ == '__main__':
    main()
