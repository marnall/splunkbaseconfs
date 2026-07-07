from splunk.clilib.bundle_paths import make_splunkhome_path
import splunk.appserver.mrsparkle.lib.util as splunk_lib_util
import time

def log(level, message, file_name="getdiagdefault.log"):
    try:
        # Ensure the log file has the .log extension
        if not file_name.endswith('.log'):
            file_name += '.log'

        # Generate the full path to the log file
        log_file_path = make_splunkhome_path(['var', 'log', 'splunk', file_name])

        # Ensure log file exists and write the log message
        with open(log_file_path, "a") as log_file:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            log_file.write(f"{timestamp} {level}: {message}\n")
    except Exception as e:
        # Handle any errors related to file handling or logging
        print(f"Logging error: {str(e)}")
