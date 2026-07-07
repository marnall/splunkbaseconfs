# ${copyright}
import sys

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(["etc", "apps", "SA-ITOA", "bin"]))
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-ITOA", "lib"]))

import itsi_path
import itsi_py3

from ITOA.itoa_object import ItoaObject
from ITOA.setup_logging import getLogger
from ITOA.storage import itoa_storage
from itsi.itsi_utils import ITOAInterfaceUtils

logger = getLogger()


class ItsiCpAppDynamicsStorage(itoa_storage.ITOAStorage):
    """
    Storage class for alternate app namespace
    """

    def __init__(self, **kwargs):
        super(ItsiCpAppDynamicsStorage, self).__init__(namespace="DA-ITSI-CP-appdynamics", **kwargs)

    def get_app_name(self):
        return "DA-ITSI-CP-appdynamics"


class ItsiCpAppDynamicsTree(ItoaObject):
    """
    Implements ITSI CP AppDynamics Tree object
    """
    logger = logger
    log_prefix = "[ITSI CP AppDynamics - Tree] "
    collection_name = "itsi_cp_appdynamics_trees"
    object_type = "appdynamics_tree"

    def __init__(self, session_key, current_user_name):
        self.session_key = session_key
        self.current_user_name = current_user_name
        super(ItsiCpAppDynamicsTree, self).__init__(
            session_key, current_user_name, self.object_type, collection_name=self.collection_name,
            is_securable_object=False,
        )

        # Post-ITOA setup
        self.storage_interface = ItsiCpAppDynamicsStorage(collection=self.collection_name)
        itsi_version = ITOAInterfaceUtils.get_app_version(self.session_key, "itsi")
        appd_cp_version = ITOAInterfaceUtils.get_app_version(self.session_key, "DA-ITSI-CP-appdynamics")
        self._version = f"{itsi_version}:{appd_cp_version}"


class ItsiCpAppDynamicsRecord(ItoaObject):
    """
    Implements ITSI CP AppDynamics Record object
    """
    logger = logger
    log_prefix = "[ITSI CP Splunk AppDynamics - Record] "
    collection_name = "itsi_cp_appdynamics_records"
    object_type = "appdynamics_record"

    def __init__(self, session_key, current_user_name):
        self.session_key = session_key
        self.current_user_name = current_user_name
        super(ItsiCpAppDynamicsRecord, self).__init__(
            session_key, current_user_name, self.object_type, collection_name=self.collection_name,
            is_securable_object=False,
        )

        # Post-ITOA setup
        self.storage_interface = ItsiCpAppDynamicsStorage(collection=self.collection_name)
        itsi_version = ITOAInterfaceUtils.get_app_version(self.session_key, "itsi")
        appd_cp_version = ITOAInterfaceUtils.get_app_version(self.session_key, "DA-ITSI-CP-appdynamics")
        self._version = f"{itsi_version}:{appd_cp_version}"
