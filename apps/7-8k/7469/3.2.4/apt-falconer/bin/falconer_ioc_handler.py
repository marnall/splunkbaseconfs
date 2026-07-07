import os
import json
import datetime
from splunk.persistconn.application import PersistentServerConnectionApplication

APP_NAME = "apt-falconer"
LOOKUP_FILE = "falconer_threatintel.csv"
LOOKUP_FIELDS = ["ioc", "type", "source", "_time", "description"]
DEBUG_PATH = "/tmp/falconer_debug.log"

class FalconerIOCHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(FalconerIOCHandler, self).__init__()

    def log(self, message):
        with open(DEBUG_PATH, "a") as f:
            f.write(f"[{datetime.datetime.now().isoformat()}] {message}\n")

    def handle(self, in_string):
        self.log("⚡️ Endpoint hit")

        try:
            # Parse raw JSON input
            payload = json.loads(in_string)
            self.log(f"📦 Received Payload: {json.dumps(payload)}")

            # Validate all required fields
            for field in LOOKUP_FIELDS:
                if field not in payload:
                    raise ValueError(f"Missing required field: {field}")

            # Build full lookup file path
            lookup_path = os.path.join(
                os.environ.get("SPLUNK_HOME", "/opt/splunk"),
                "etc", "apps", APP_NAME, "lookups", LOOKUP_FILE
            )

            line = ",".join([payload.get(k, "") for k in LOOKUP_FIELDS])
            with open(lookup_path, "a") as f:
                f.write(f"{line}\n")

            self.log(f"✅ Appended line to lookup: {line}")
            return {
                "payload": {"message": "IOC successfully added"},
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

