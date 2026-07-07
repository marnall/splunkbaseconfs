import json
import os
import sys
import time

from hlcp.commands import CheckCompatibilityCommand
from hlcp.utils import get_and_configure_logger

splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(
    os.path.join(splunkhome, "etc", "apps", "HurricaneLabsContentPlus", "lib")
)
from splunklib.searchcommands import (
    Configuration,
    GeneratingCommand,
    Option,
    dispatch,
    validators,
)

logger = get_and_configure_logger("hlcp")


@Configuration()
class hlcpCheck(GeneratingCommand):
    package_ids = Option(require=False, validate=validators.List())
    force = Option(require=False, validate=validators.Boolean(), default=False)

    def generate(self):
        session_key = self._metadata.searchinfo.session_key  # type: ignore
        command = CheckCompatibilityCommand(session_key)
        if self.package_ids:
            packages_to_check = list(self.package_ids)
        else:
            packages_to_check = None
        for result in command.run(package_ids=packages_to_check, force=self.force):
            yield {"_time": time.time(), "_raw": json.dumps(result)}


dispatch(hlcpCheck, sys.argv, sys.stdin, sys.stdout, __name__)
