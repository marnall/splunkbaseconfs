import os
import sys
import time
import json
from hlcp.commands import SendMetricsCommand
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
class hlcpMetrics(GeneratingCommand):
    def generate(self):
        session_key = self._metadata.searchinfo.session_key  # type: ignore
        command = SendMetricsCommand(session_key)

        for output in command.run():
            yield {"_time": time.time(), "_raw": json.dumps(output)}


dispatch(hlcpMetrics, sys.argv, sys.stdin, sys.stdout, __name__)
