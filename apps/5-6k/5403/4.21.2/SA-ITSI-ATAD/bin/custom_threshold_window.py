import json
import sys

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path
from ITOA.itoa_factory import instantiate_object


# Custom Threshold Window Class
class CustomThresholdWindow(object):
    """
        Provides an interface to fetch ITSI Custom Threshold Windows objects.
    """

    def __init__(self, logger=None):
        self._ctw_object = None
        # store fetched object so that it's easy to update
        self._kvstore_data = None
        self.session_key = None
        self.owner = None
        self.logger = logger

    def initialize_interface(self, session_key, owner="nobody"):
        self.session_key = session_key
        self.owner = owner
        self._ctw_object = instantiate_object(self.session_key, self.owner, "custom_threshold_windows")

    def get_all_linked_kpis(self, ctw_objects, list_kpis):
        """
        Gets all the KPIs affected by the Custom Threshold Window

        @type: object
        @param self: The self reference

        @type: list
        @param ctw_objects: The list of Active Thresholds Window

        @type: list_kpis
        @param ctw_objects: The list of KPIs in AT calculation

        @rtype: dict
        @return: Returns the KPIs along with the affected Active Custom Threshold Window
        """
        linked_kpis = []
        for window in ctw_objects:
            for service in window.get('linked_services', []):
                for kpi_id in service.get('linked_kpi_ids', []):
                    if kpi_id in list_kpis:
                        linked_kpis.append(kpi_id)
        return linked_kpis

    def bulk_fetch_active_ctw(self, list_kpis):
        """
        Bulk fetch list of active Custom Threshold Window data

        @type: list_kpis
        @param ctw_objects: The list of KPIs in AT calculation

        @rtype: dict
        @return: Returns the KPIs along with the affected Active Custom Threshold Window
        """
        filter_data = {'$and': [
            {'status': 'active'},
            {'window_type': 'percentage'},
        ]}
        self._kvstore_data = self._ctw_object.get_bulk(
            self.owner,
            filter_data=filter_data,
            req_source='itsi_at')
        linked_kpis = self.get_all_linked_kpis(self._kvstore_data, list_kpis)
        return linked_kpis