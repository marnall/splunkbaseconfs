# Standard library imports
import sys
import os

# Local imports
import reach_search_execution_helper
import reach_logger_manager as log

BASE_RESULT_PATH = os.path.sep.join(os.path.abspath(__file__).split(
    os.sep)[:-2] + ['appserver', 'static', 'search_results', 'single_execution'])


def main():
    """Method to start the single collection."""
    session_key = sys.stdin.readline().strip()
    logger = log.setup_logging('reach_single_execution', session_key)

    content = {
        "session_key": session_key,
        "base_result_path": BASE_RESULT_PATH
    }
    try:
        reach_search_execution_helper.start_collection(content, logger)
    except Exception:
        # Update Status to Partially Completed
        logger.error(
            "Reach Error: Error occurred. Updating status to Partially Completed")
        reach_search_execution_helper.SettingsConfFile(
            session_key, logger).update_settings_conf_file({"status": "Partially Completed"})
    finally:
        # Self Disable the script
        logger.debug(
            "Reach Debug: Self disabling the reach_input_single_execution.py script")

        encoded_script_name = "%24SPLUNK_HOME%252Fetc%252Fapps%252F"\
            "reach_security_app_for_splunk%252Fbin%252Freach_input_single_execution.py"
        reach_search_execution_helper.disable_enable_script(
            "disable", encoded_script_name, session_key, logger)


if __name__ == '__main__':
    main()
