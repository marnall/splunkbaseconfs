import os
import sys
from datetime import datetime
from utils import log  # Assuming `log` is implemented for logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option


def convert_datetime(original_datetime):
    try:
        # Parse the original datetime string
        dt_obj = datetime.strptime(original_datetime, "%Y-%m-%d,%H-%M-%S")

        # Reformat the datetime object to the desired format
        formatted_datetime = dt_obj.strftime("%d/%m/%Y, %I:%M:%S %p")

        return formatted_datetime
    except Exception as e:
        return "Invalid datetime format"


def parse_file_name(file_name):
    """
    Parses the file name to extract details such as hostname, UUID, date, and time.
    Assumes the file name format: diag_<hostname>_<UUID>_<date>_<time>.tar.gz
    """
    try:
        # Remove the prefix (e.g., "diag_") and the extensions (e.g., ".tar.gz")
        base_name = file_name.replace("diag_", "").replace(".tar.gz", "")

        # Split the remaining part of the file name by "_"
        parts = base_name.split("_")

        # Ensure the file name contains at least a hostname, UUID, and datetime
        if len(parts) < 3:
            return "N/A", "N/A", "N/A", "N/A", "Invalid file format"

        # Extract the date and time (last two parts)
        date, time = parts[-2], parts[-1]

        # Combine the date and time for conversion
        datetime_str = f"{date},{time}"

        # Convert the datetime to a readable format
        formatted_datetime = convert_datetime(datetime_str)

        # Extract the UUID (second-to-last before date and time)
        uuid = parts[-3]

        # Everything before UUID is considered part of the hostname
        hostname = "_".join(parts[:-3]) if len(parts[:-3]) > 0 else "N/A"

        return hostname, uuid, date, time, formatted_datetime
    except Exception as e:
        return "N/A", "N/A", "N/A", "N/A", "Error parsing file name"


@Configuration()
class Getdiaginfo(GeneratingCommand):
    filename = Option(require=False)

    def generate(self):
        try:
            log("INFO", "Executing getdiaginfo custom command", file_name="getdiaginfo")

            # Get the diagnostic directory
            APP_NAME = 'getdiag'
            diag_dir = os.path.join(os.environ['SPLUNK_HOME'], "etc", "apps", APP_NAME, "appserver", "static", "diag")

            if not os.path.exists(diag_dir):
                log("INFO", f"Diagnostic directory does not exist: {diag_dir}", file_name="getdiaginfo")
                yield {"message": f"Diagnostic directory not found: {diag_dir}"}
                return

            if self.filename:
                # Handle delete logic if a file name is provided
                file_path = os.path.join(diag_dir, self.filename)
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    os.remove(file_path)
                    log("INFO", f"File deleted: {self.filename}", file_name="getdiaginfo")
                else:
                    log("ERROR", "coming in else", file_name="getdiaginfo")
                    log("ERROR", f"File not found: {self.filename}", file_name="getdiaginfo")
               

            log("INFO", "Getting.... diag file info...", file_name="getdiaginfo")
            # List all files in the diagnostic directory and extract details
            diag_files = []
            for file_name in os.listdir(diag_dir):
                # Check if the file name starts with "diag" and ends with ".tar.gz"
                if file_name.startswith("diag") and file_name.endswith(".tar.gz"):
                    file_path = os.path.join(diag_dir, file_name)
                    if os.path.isfile(file_path):
                        hostname, uuid, date, time, formatted_datetime = parse_file_name(file_name)
                        diag_files.append({
                            "Host Name": hostname,
                            "UUID": uuid,
                            "Date Submitted": formatted_datetime,
                            "Download": file_name,
                            "Delete": file_name,
                            "Upload_to_Case": file_name,
                        })

            if not diag_files:
                yield {"message": "No diagnostic files found in the directory"}
            else:
                for file_info in diag_files:
                    yield file_info

        except Exception as e:
            log("ERROR", "Error executing getdiaginfo", file_name="getdiaginfo")
            log("ERROR", str(e), file_name="getdiaginfo")
            yield {"status": "error", "_raw": str(e)}


dispatch(Getdiaginfo, sys.argv, sys.stdin, sys.stdout, __name__)
