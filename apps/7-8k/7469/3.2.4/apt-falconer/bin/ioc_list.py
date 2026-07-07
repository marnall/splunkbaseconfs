import os
import csv
import json
import datetime
from splunk.persistconn.application import PersistentServerConnectionApplication

APP_NAME = "apt-falconer"
LOOKUP_FILE = "falconer_threatintel.csv"
LOOKUP_FIELDS = ["indicator", "description", "category", "weight", "threat_group"]
DEBUG_ENABLED = True

DEBUG_PATH = os.path.join(os.environ['SPLUNK_HOME'], "var", "log", "splunk", "falconer_lookup_debug.log")

class LookupList(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(LookupList, self).__init__()

    def log(self, message):
        if not DEBUG_ENABLED:
            return
        try:
            with open(DEBUG_PATH, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.datetime.now().isoformat()}] {message}\n")
        except Exception:
            pass

    def handle(self, in_string):
        self.log("📄 IOC_LIST endpoint hit")

        try:
            if isinstance(in_string, bytes):
                in_string = in_string.decode("utf-8")

            incoming = json.loads(in_string)
            self.log(f"📦 Raw input: {json.dumps(incoming)}")

            filter_term = ""
            if "query" in incoming and isinstance(incoming["query"], list):
                for param in incoming["query"]:
                    if isinstance(param, list) and len(param) == 2 and param[0] == "filter":
                        filter_term = param[1].lower()

            self.log(f"🔍 Filter term: {filter_term}")

            lookup_path = os.path.join(
                os.environ['SPLUNK_HOME'],
                "etc", "apps", APP_NAME, "lookups", LOOKUP_FILE
            )

            results = []
            with open(lookup_path, newline='', encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not filter_term or filter_term in row["indicator"].lower():
                        results.append(row)

            self.log(f"✅ Returning {len(results)} result(s)")

            return {
                "status": 200,
                "payload": json.dumps({"results": results})
            }

        except Exception as e:
            self.log(f"❌ Exception: {str(e)}")
            return {
                "status": 500,
                "payload": json.dumps({"error": str(e)})
            }

