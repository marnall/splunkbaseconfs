# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

"""
Use this module to Update the rules engine property from custom command
"""

import sys
import json
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(["etc", "apps", "SA-ITOA", "lib"]))
sys.path.append(
    make_splunkhome_path(["etc", "apps", "SA-ITOA", "lib", "SA_ITOA_app_common"])
)

from SA_ITOA_app_common.splunklib.searchcommands import (
    Configuration,
    StreamingCommand,
    dispatch,
    Option,
)
from splunk import rest
from ITOA.setup_logging import setup_logging


@Configuration()
class UpdateProperties(StreamingCommand):
    logger = setup_logging(
        "configurations.log", "itsi.change.rules_engine_properties"
    )

    def stream(self, records):
        obj = {}
        for record in records:
            fields = record.keys()

            for field in list(fields):
                if field == "_time":
                    continue
                obj[field] = record[field]
        self.logger.info(f"All fields = {obj}")
        try:
            response, content = rest.simpleRequest(
                "/servicesNS/nobody/SA-ITOA/event_management_interface/configurations/",
                sessionKey=self.service.token,
                method="POST",
                postargs=obj,
                raiseAllErrors=True,
            )
            self.logger.info(
                f"content return from configurations is {json.loads(content)}"
            )
            yield {"_raw": json.loads(content)}
        except Exception as e:
            self.logger.error(
                f"content return from configurations is {e}"
            )
            yield {"_raw": {"status": 400, "message": "An unexpected error occurred"}}


dispatch(UpdateProperties, sys.argv, sys.stdin, sys.stdout, __name__)
