# ${copyright}
"""
Import flow objects for Catalyst Center
"""
import sys

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(["etc", "apps", "SA-ITOA", "bin"]))
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-ITOA", "lib"]))

# pylint: disable=unused-import
import itsi_py3
import itsi_path
# pylint: enable=unused-import

from ITOA.itoa_object import ItoaObject
from ITOA.setup_logging import getLogger
from ITOA.storage import itoa_storage
from itsi.itsi_utils import ITOAInterfaceUtils

logger = getLogger()


class ItsiCpCatalystCenterStorage(itoa_storage.ITOAStorage):
    """
    Storage class for alternate app namespace
    """

    def __init__(self, **kwargs):
        super().__init__(namespace="DA-ITSI-CP-enterprise-networking", **kwargs)

    def get_app_name(self):
        """
        The app name for this storage object
        """
        return "DA-ITSI-CP-enterprise-networking"


class ItsiCpCatalystCenterTree(ItoaObject):
    """
    Implements ITSI CP Catalyst Center Tree object
    """
    logger = logger
    log_prefix = "[ITSI CP Catalyst Center - Tree] "
    collection_name = "itsi_cp_catalyst_center_trees"
    object_type = "catalyst_center_tree"

    def __init__(self, session_key, current_user_name):
        self.session_key = session_key
        self.current_user_name = current_user_name
        super().__init__(
            session_key, current_user_name, self.object_type, collection_name=self.collection_name,
            is_securable_object=False,
        )

        # Post-ITOA setup
        self.storage_interface = ItsiCpCatalystCenterStorage(collection=self.collection_name)
        itsi_version = ITOAInterfaceUtils.get_app_version(self.session_key, "itsi")
        catalyst_center_cp_version = ITOAInterfaceUtils.get_app_version(
            self.session_key, "DA-ITSI-CP-enterprise-networking"
        )
        self._version = f"{itsi_version}:{catalyst_center_cp_version}"


class ItsiCpCatalystCenterRecord(ItoaObject):
    """
    Implements ITSI CP Catalyst Center Record object
    """
    logger = logger
    log_prefix = "[ITSI CP Catalyst Center - Record] "
    collection_name = "itsi_cp_catalyst_center_records"
    object_type = "catalyst_center_record"

    def __init__(self, session_key, current_user_name):
        self.session_key = session_key
        self.current_user_name = current_user_name
        super().__init__(
            session_key, current_user_name, self.object_type, collection_name=self.collection_name,
            is_securable_object=False,
        )

        # Post-ITOA setup
        self.storage_interface = ItsiCpCatalystCenterStorage(collection=self.collection_name)
        itsi_version = ITOAInterfaceUtils.get_app_version(self.session_key, "itsi")
        catalyst_center_cp_version = ITOAInterfaceUtils.get_app_version(
            self.session_key, "DA-ITSI-CP-enterprise-networking"
        )
        self._version = f"{itsi_version}:{catalyst_center_cp_version}"
