import os
import sys
import time
import json
from hlcp.commands import InstallPackageCommand
from hlcp.utils import get_and_configure_logger
from hlcp.collections import Collection

splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(
    os.path.join(splunkhome, "etc", "apps", "HurricaneLabsContentPlus", "lib")
)
from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)

logger = get_and_configure_logger("hlcp")


@Configuration()
class hlcpInstall(GeneratingCommand):
    package_ids = Option(require=False, validate=validators.List())
    package_name = Option(require=False)
    force = Option(require=False, validate=validators.Boolean(), default=False)

    def generate(self):
        session_key = self._metadata.searchinfo.session_key  # type: ignore
        catalog = Collection(session_key=session_key, collection_name="hlcp_catalog")
        package_ids_from_name = []
        if self.package_name:
            for package_id, content in catalog.asdict().items():
                if content.get("package_title") == self.package_name:
                    package_ids_from_name.append(package_id)

            self.package_ids = package_ids_from_name
        else:
            if not self.package_ids:
                raise ValueError(
                    "This command needs either package_names or package_ids to be set."
                )
        command = InstallPackageCommand(session_key)
        packages_to_install = list(self.package_ids)
        for install_summary in command.run(packages_to_install, force=self.force):
            yield {"_time": time.time(), "_raw": json.dumps(install_summary)}


dispatch(hlcpInstall, sys.argv, sys.stdin, sys.stdout, __name__)
