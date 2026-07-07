import json
import logging
import logging.handlers
import os
import re
import sys
import time

import splunk
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunk.clilib.cli_common import getMergedConf, getWebConfKeyValue


# Add app lib directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from defusedxml import minidom  # pylint: disable=wrong-import-position


uuid_re = re.compile(
    r"[0-9a-fA-F]{8}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{12}"
)


# Setup logging to file
logger = logging.getLogger("saml_cli_auth_rest")

splunk_log_handler = logging.handlers.RotatingFileHandler(
    make_splunkhome_path(["var", "log", "splunk", "saml_cli_auth_rest.log"]),
    mode="a"
)
splunk_log_handler.setFormatter(logging.Formatter(
    "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
))
logger.addHandler(splunk_log_handler)
splunk.setupSplunkLogger(
    logger,
    make_splunkhome_path(["etc", "log.cfg"]),
    make_splunkhome_path(["etc", "log-local.cfg"]),
    "python",
)
logger.setLevel(logging.INFO)


class RestHandler(splunk.rest.BaseRestHandler):  # pylint: disable=too-few-public-methods
    def handle_GET(self):
        remoteAddr = self.request.get("remoteAddr", "127.0.0.1")

        if "X_FORWARDED_FOR" in self.request.get("headers", {}):
            remoteAddr = self.request["headers"]["X_FORWARDED_FOR"].split(", ")[0]

        uuid = self.request["query"].get("uuid")
        if uuid is None:
            logger.error("action=failure, src=%s, reason=missing uuid param", remoteAddr)
            self.response.setStatus(403)
            return {"status": "forbidden"}

        if uuid_re.match(uuid) is None:
            logger.error("action=failure, src=%s, reason=invalid uuid param", remoteAddr)
            self.response.setStatus(403)
            return {"status": "forbidden"}

        filename = make_splunkhome_path(["tmp", "saml_cli_auth", uuid])

        if self.pathParts[-1].lower() == "retrieve":
            if not os.path.exists(filename):
                self.response.setStatus(404)
                return {"status": "not found"}

            with open(filename) as f:
                content = f.read()

            xml = minidom.parseString(content)

            return {
                "username": xml.getElementsByTagName("username")[0].childNodes[0].nodeValue,
                "sessionkey": xml.getElementsByTagName("sessionkey")[0].childNodes[0].nodeValue,
                "cookie": xml.getElementsByTagName("cookie")[0].childNodes[0].nodeValue,
            }

        # Retrieve username
        _, content = splunk.rest.simpleRequest(
            "/services/authentication/current-context",
            sessionKey=self.sessionKey,
            method="GET",
            raiseAllErrors=True,
            getargs={"output_mode": "json"}
        )
        content = json.loads(content)
        username = content["entry"][0]["content"]["username"]

        if os.path.exists(filename):
            logger.error("action=failure, src=%s, user=%s, reason=uuid in use",
                         remoteAddr, username)
            self.response.setStatus(403)
            return {"status": "forbidden"}

        # Retrieve server settings to get mgmtPort and hostname
        mgmtHostPort = getWebConfKeyValue("mgmtHostPort")
        if ":" in mgmtHostPort:
            mgmtHostPort = mgmtHostPort.split(":")[-1]

        cookie_name = "splunkd_%s" % mgmtHostPort

        output = "<auth><username>%s</username><sessionkey>%s</sessionkey>" \
                 "<cookie>%s</cookie></auth>" % (username, self.sessionKey, cookie_name)

        logger.info("action=success, src=%s, user=%s", remoteAddr, username)

        # Create the directory if necessary
        try:
            os.makedirs(os.path.dirname(filename))
        except OSError:
            pass

        # Output the XML
        with open(filename, "w") as f:
            f.write(output)

        # Wait for the CLI script to grab the file
        webSettings = getMergedConf("saml_cli_auth").get("web", {"time_before_cleanup": 3})
        try:
            sleep = int(webSettings.get("time_before_cleanup", 2))
        except ValueError:
            sleep = 2

        time.sleep(sleep)

        # Cleanup the file
        os.remove(filename)

        return {"status": "success"}
