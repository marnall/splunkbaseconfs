import os
import sys
import time
import json
from hlcp.commands import UpdateCatalogCommand
from hlcp.utils import get_and_configure_logger

splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(
    os.path.join(splunkhome, "etc", "apps", "HurricaneLabsContentPlus", "lib")
)
from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
)

logger = get_and_configure_logger("hlcp")


@Configuration()
class hlcpFetch(GeneratingCommand):
    def generate(self):
        session_key = self._metadata.searchinfo.session_key  # type: ignore
        command = UpdateCatalogCommand(session_key)
        package_ids = []
        for package_id in command.run():
            logger.debug("Updated package %s in catalog", package_id)
            package_ids.append(package_id)

        output = {
            "message": (
                "Successfully updated local package catalog. Grabbed metadata for"
                f" {len(package_ids)} packages."
            ),
            "package_ids": package_ids,
        }
        logger.info(
            "Successfully updated local package catalog. Grabbed metadata for %s"
            " packages.",
            len(package_ids),
        )
        yield {"_time": time.time(), "_raw": json.dumps(output)}


dispatch(hlcpFetch, sys.argv, sys.stdin, sys.stdout, __name__)
