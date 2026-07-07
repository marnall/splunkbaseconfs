import splunk
import splunk.entity as en
import json
import requests
import traceback
import urllib
from Utils.dtools_logger import DToolsLogger
from Utils.app_env import AppEnv


class DomainProfile(splunk.rest.BaseRestHandler):

    def handle_GET(self):
        logger = DToolsLogger.setup("DomainProfile", "dt_domain_profile.log")
        logger.info("starting domain_profile script.")

        sessionKey = self.sessionKey
        app_env = AppEnv()

        dt_api_enrich_cmd = splunk.entity.getEntity(
            '/configs/conf-macros',
            'dt_api_enrich_cmd',
            namespace=app_env.package_id,
            sessionKey=sessionKey,
            owner='nobody'
        )['definition']

        logger.info("response: {0}".format(json.dumps(dt_api_enrich_cmd)))

        score_type = ""
        if dt_api_enrich_cmd == "noop":
            score_type = ""
        elif dt_api_enrich_cmd == "domaintools domain mode=whois_parsed silent=t":
            score_type = ""
        elif dt_api_enrich_cmd == "domaintools domain mode=reputation silent=t":
            score_type = "reputation"
        elif dt_api_enrich_cmd == "domaintools domain mode=whois_reputation silent=t":
            score_type = "reputation"
        elif dt_api_enrich_cmd == "domaintools domain mode=whois_risk silent=t":
            score_type = "risk"
        elif dt_api_enrich_cmd == "domaintools domain mode=iris_enrich field=domain silent=t":
            score_type = "iris_enrich"

        self.response.write(json.dumps({'score_type': score_type}))
