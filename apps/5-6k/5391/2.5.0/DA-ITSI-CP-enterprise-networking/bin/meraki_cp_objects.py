# ${copyright}
"""
Import flow objects for Meraki
"""
import sys

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(["etc", "apps", "SA-ITOA", "bin"]))
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-ITOA", "lib"]))

# pylint: disable=unused-import
import itsi_py3
import itsi_path
# pylint: enable=unused-import

from itsi.itsi_utils import ITOAInterfaceUtils
from ITOA.storage import itoa_storage
from ITOA.setup_logging import getLogger
from ITOA.itoa_object import ItoaObject


logger = getLogger()


class ItsiCpMerakiStorage(itoa_storage.ITOAStorage):
    """
    Storage class for Meraki CP KV collections
    """

    def __init__(self, **kwargs):
        super().__init__(
            namespace="DA-ITSI-CP-enterprise-networking",
            **kwargs)

    def get_app_name(self):
        """
        The app name for this storage object
        """
        return "DA-ITSI-CP-enterprise-networking"


class ItsiCpMerakiTree(ItoaObject):
    """
    Implements ITSI CP Meraki Tree object
    """
    logger = logger
    log_prefix = "[ITSI CP Meraki - Tree] "
    collection_name = "itsi_cp_meraki_trees"
    object_type = "meraki_tree"

    def __init__(self, session_key, current_user_name):
        self.session_key = session_key
        self.current_user_name = current_user_name
        super().__init__(
            session_key,
            current_user_name,
            self.object_type,
            collection_name=self.collection_name,
            is_securable_object=False,
        )
        self.storage_interface = ItsiCpMerakiStorage(
            collection=self.collection_name)
        itsi_version = ITOAInterfaceUtils.get_app_version(
            self.session_key, "itsi")
        cp_version = ITOAInterfaceUtils.get_app_version(
            self.session_key, "DA-ITSI-CP-enterprise-networking")
        self._version = f"{itsi_version}:{cp_version}"


class ItsiCpMerakiRecord(ItoaObject):
    """
    Implements ITSI CP Meraki Record object
    """
    logger = logger
    log_prefix = "[ITSI CP Meraki - Record] "
    collection_name = "itsi_cp_meraki_records"
    object_type = "meraki_record"

    def __init__(self, session_key, current_user_name):
        self.session_key = session_key
        self.current_user_name = current_user_name
        super().__init__(
            session_key,
            current_user_name,
            self.object_type,
            collection_name=self.collection_name,
            is_securable_object=False,
        )
        self.storage_interface = ItsiCpMerakiStorage(
            collection=self.collection_name)
        itsi_version = ITOAInterfaceUtils.get_app_version(
            self.session_key, "itsi")
        cp_version = ITOAInterfaceUtils.get_app_version(
            self.session_key, "DA-ITSI-CP-enterprise-networking")
        self._version = f"{itsi_version}:{cp_version}"
