"""
A streaming version of hlcp_install.py that, instead of being passed package_ids
via parameter, grabs them from event fields.
"""

import os
import sys
from hlcp.commands import InstallPackageCommand
from hlcp.utils import get_and_configure_logger

splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(
    os.path.join(splunkhome, "etc", "apps", "HurricaneLabsContentPlus", "lib")
)
from splunklib.searchcommands import (
    dispatch,
    StreamingCommand,
    Configuration,
    Option,
    validators,
)

logger = get_and_configure_logger("hlcp")


@Configuration()
class hlcpInstallStreaming(StreamingCommand):
    force = Option(require=False, validate=validators.Boolean(), default=False)

    def stream(self, records):
        session_key = self._metadata.searchinfo.session_key  # type: ignore
        command = InstallPackageCommand(session_key)
        for record in records:
            if "package_id" not in record:
                continue
            for install_summary in command.run(
                package_ids=[record["package_id"]], force=self.force
            ):
                yield install_summary


dispatch(hlcpInstallStreaming, sys.argv, sys.stdin, sys.stdout, __name__)
