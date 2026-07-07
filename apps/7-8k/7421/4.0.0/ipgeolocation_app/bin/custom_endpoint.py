import traceback

import splunk

from app_utils import get_logger


logger = get_logger("custom_endpoint_slashdownload")


class Download(splunk.rest.BaseRestHandler):
    def handle_POST(self):
        try:
            self.response.setHeader("content-type", "application/zip")
            query = self.request.get("query")
            requested_file = query.get("name")
            f = open("/opt/splunk/etc/apps/ipgeolocation_app/lookups/" + requested_file, "rb")

            while True:
                chunk = f.read(51200)

                if chunk:
                    self.response.write(chunk)
                else:
                    break
        except Exception as e:
            logger.error("Error while processing the /download request")
            logger.error(e)
            logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))

            self.response.status = 500
            self.response.setHeader("content-type", "text/html")
            self.response.write("<p>Uh oh! Something's wrong. Check ipgeolocation.log for troubleshooting</p>")

        return

    # handle verbs, otherwise Splunk will throw an error
    handle_GET = handle_POST
