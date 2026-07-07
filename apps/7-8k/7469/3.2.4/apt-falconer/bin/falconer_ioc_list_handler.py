import os
import csv
import datetime
from splunk.persistconn.application import PersistentServerConnectionApplication

APP_NAME = "apt-falconer"
LOOKUP_FILE = "falconer_threatintel.csv"
DEBUG_LOG = os.path.join(os.environ['SPLUNK_HOME'], "var", "log", "splunk", "ioc_list_debug.log")

class FalconerIOCListHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(FalconerIOCListHandler, self).__init__()

    def log(self, message):
        with open(DEBUG_LOG, "a") as log:
            log.write(f"[{datetime.datetime.now().isoformat()}] {message}\n")

    def handle(self, args):
        self.log("IOC list endpoint hit")

        try:
            # Build lookup path
            lookup_path = os.path.join(os.environ['SPLUNK_HOME'],"etc","apps",APP_NAME,"lookups",LOOKUP_FILE)

            if not os.path.exists(lookup_path):
                raise FileNotFoundError("IOC CSV not found")

            # Read and filter rows if query params exist
            query = args.get("query", {})
            filter_value = query.get("filter", "").lower()

            rows = []
            with open(lookup_path, "r", newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if filter_value:
                        row_str = " ".join([str(v).lower() for v in row.values()])
                        if filter_value not in row_str:
                            continue
                    rows.append(row)

            self.log(f"Returned {len(rows)} rows")
            return {
                "payload": {"results": rows},
                "status": 200
            }

        except Exception as e:
            self.log(f"❌ Exception: {str(e)}")
            return {
                "payload": {"error": str(e)},
                "status": 500
            }

    def handleStream(self, handle, in_string):
        raise NotImplementedError("Streaming not supported")

    def done(self):
        pass
