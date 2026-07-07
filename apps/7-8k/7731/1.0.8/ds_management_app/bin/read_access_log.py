import os,re, csv,json
from datetime import datetime
from splunk.clilib.bundle_paths import make_splunkhome_path
import splunk.appserver.mrsparkle.lib.util as splunk_lib_util

CHECKPOINT_KEY="splunkd_access"
LOG_FILE_PATH = splunk_lib_util.make_splunkhome_path(['var', 'log', 'splunk', 'splunkd_access.log'])
CHECKPOINT_FILE= splunk_lib_util.make_splunkhome_path(['var', 'run', 'ds_management_app', 'checkpoint', 'splunkd_access_checkpoint.json'])
CSV_FILE_PATH= splunk_lib_util.make_splunkhome_path(['etc', 'apps', 'ds_management_app', 'lookups', 'dc_phonehome_time.csv'])

# Regex pattern to match the required logs
log_pattern = re.compile(
    r'(?P<ip>\d+\.\d+\.\d+\.\d+) - - \[(?P<timestamp>[^\]]+)\] "GET \/static\/ds_management_app\/apps_download_list\/(?P<filename>[^\s]+)'
)

def get_checkpoint(key):
    if not os.path.exists(CHECKPOINT_FILE):
        return None

    with open(CHECKPOINT_FILE, "r") as file:
        try:
            checkpoint_data = json.load(file)
        except json.JSONDecodeError:
            return None

    return checkpoint_data.get(key)

def update_checkpoint(key, value):
    checkpoint_dir = os.path.dirname(CHECKPOINT_FILE)
    if not os.path.exists(checkpoint_dir):
        os.makedirs(checkpoint_dir)

    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as file:
            try:
                checkpoint_data = json.load(file)
            except json.JSONDecodeError:
                checkpoint_data = {}
    else:
        checkpoint_data = {}

    checkpoint_data[key] = value

    with open(CHECKPOINT_FILE, "w") as file:
        json.dump(checkpoint_data, file)


# Helper functions
def parse_timestamp(timestamp):
    dt = datetime.strptime(timestamp, "%d/%b/%Y:%H:%M:%S.%f %z")
    return int(dt.timestamp())

def read_log_file():
    # Fetch checkpoint data (position and inode)
    checkpoint_data = get_checkpoint(CHECKPOINT_KEY) or {}
    last_position = checkpoint_data.get("position", 0)
    last_inode = checkpoint_data.get("inode", None)

    current_inode = os.stat(LOG_FILE_PATH).st_ino

    # If the file has been rotated (inode changed), start reading from the beginning
    if last_inode != current_inode:
        last_position = 0  # Reset the position

    # Check if the file exists
    if not os.path.exists(CSV_FILE_PATH):
        with open(CSV_FILE_PATH, "w") as file:
            pass 

    with open(LOG_FILE_PATH, 'r') as log_file, open(CSV_FILE_PATH, "a", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["_time", "guid", "ip", "hostname", "os"])
        if os.stat(CSV_FILE_PATH).st_size == 0:  # Add headers if the CSV is empty
            writer.writeheader()

        # Move to the last read position
        log_file.seek(last_position)

        for line in log_file:
            try:
                match = log_pattern.match(line)

                if match:
                    time = match.group("timestamp")
                    epoch_time = parse_timestamp(time)
                    filename = match.group("filename")  # Extract the filename
                    ip = match.group("ip")
                    # Split the filename using "__" as the delimiter
                    parts = filename.split("__")
                    if len(parts) == 4:  # Ensure the expected format
                        guid = parts[0]
                        hostname = parts[2]
                        operatingSystem = parts[3].replace(".txt", "")  # Remove the `.txt` extension
                        writer.writerow({
                        "_time": epoch_time,
                        "guid": guid,
                        "ip": ip,
                        "hostname": hostname,
                        "os":operatingSystem
                    })
            except json.JSONDecodeError:
                # Handle any malformed log entries (skip in this case)
                continue

        # Update the checkpoint with the new file position and inode
        new_position = log_file.tell()
        update_checkpoint(CHECKPOINT_KEY, {
            "position": new_position,
            "inode": current_inode
        })

if __name__ == "__main__":
    read_log_file()