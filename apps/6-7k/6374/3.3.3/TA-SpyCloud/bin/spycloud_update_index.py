import splunk
import splunk.mining.dcutils as dcu
import os
import json
import splunk.rest
import time

APP_NAME = "TA-SpyCloud"

class Update(splunk.rest.BaseRestHandler):

    def handle_POST(self):
        logger = dcu.getLogger()
        logger.debug("spycloud_update_index.py start")
        
        try:
            self.response.setHeader("content-type", "text/html")

            payload = self.request["payload"]
            logger.info("payload: %s", payload)

            index = ""
            for el in payload.split("&"):
                logger.info("el: %s", el)
                key, value = el.split("=")
                index = value

            logger.info("CC Index=%s", index)

            if not self.index_exists(index):
                raise ValueError(f"Index '{index}' is invalid")

            self.update_index("spycloud_compass/SpyCloud_Compass", index)
            self.update_index("spycloud_breach_catalog/SpyCloud_Breach_Catalog", index)
            self.update_index("spycloud_watchlist_identifiers/SpyCloud_Watchlist_Identifiers", index)
            self.update_index("spycloud_watchlist/SpyCloud_Watchlist", index)

            self.write("The SpyCloud index has been updated")

        except Exception as e:
            self.write("Something went wrong: " + str(e))
            logger.error("Error in handle_POST", exc_info=True)

        logger.debug("spycloud_update_index.py end")

    handle_GET = handle_POST

    def update_index(self, modular_input, index):
        logger = dcu.getLogger()

        inputs_path = (
            "/servicesNS/nobody/" + str(APP_NAME) + "/data/inputs/" + str(modular_input)
        )

        try:
            splunk.rest.simpleRequest(
                inputs_path + "/disable",
                method="POST",
                sessionKey=self.sessionKey,
            )

            splunk.rest.simpleRequest(
                inputs_path,
                method="POST",
                sessionKey=self.sessionKey,
                postargs={"index": index},
            )

            splunk.rest.simpleRequest(
                inputs_path + "/enable",
                method="POST",
                sessionKey=self.sessionKey,
            )

            logger.debug("SpyCloud Index Updated: %s", modular_input)
            self.write("SpyCloud Index Updated: " + str(modular_input))

        except Exception as e:
            logger.exception("Unexpected error while enabling input")

            self.write(json.dumps({
                "status": "error",
                "error_code": 500,
                "message": "Unexpected error while enabling the input.",
            }))

    def index_exists(self, index):
        try:
            splunk.rest.simpleRequest(
                f"/services/data/indexes/{index}",
                method="GET",
                sessionKey=self.sessionKey,
            )
            return True
        except splunk.RESTException as e:
            if e.statusCode == 404:
                return False
            raise

    def write(self, msg):
        self.response.write("<p>" + str(msg) + "</p>")
