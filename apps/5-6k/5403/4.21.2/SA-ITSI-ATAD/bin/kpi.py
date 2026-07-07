import json
import sys

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path
from ITOA.itoa_factory import instantiate_object
from ITOA.storage import itoa_generic_persistables


# KPI Class
# Backed either by a file or the KV store
class KPIBase(object):
    """
    Provides an interface between the threshold generation logic and KPI objects.

    KPI can be backed by
    - one of the KPIs stored in the ITSI service object
    - a temporary object in the KV store (e.g. in case a service KPI has not yet been saved)
    - a file
    """

    def __init__(self, logger=None):
        if logger is None:
            raise ValueError("Must supply a logger.")
        self.logger = logger
        self._kpi = None

    def initialize_interface(self, session_key, owner="nobody", namespace=None, **kwargs):
        raise NotImplementedError

    def fetch_kpi(self):
        raise NotImplementedError

    def get_kpi(self):
        if self._kpi is None:
            self.fetch_kpi()
        return self._kpi

    def _update_thresholds(self, policy=None, thresholds=None):
        """
        The mechanism for updating thresholds is common for any mode of operation:
        retrieve the fetched KPI object, and update it by reference using provided
        policy and thresholds.  Mode-specific methods are responsible for persisting
        the KPI object.

        @param policy: policy ID
        @param thresholds: list of threshold levels structures;
                           each structure is a dict with 'thresholdValue' field populated
        """
        threshold_spec = self.get_kpi()[
            'time_variate_thresholds_specification']
        threshold_spec['policies'][
            policy]['aggregate_thresholds']['thresholdLevels'] = thresholds

    def update_thresholds(self, policy=None, thresholds=None):
        """
        Persist updated thresholds

        @param policy: policy ID
        @param thresholds: list of threshold levels structures;
                           each structure is a dict with 'thresholdValue' field populated
        """
        raise NotImplementedError

    def get_tzoffset(self):
        """
        Returns a timezone offset in the format expected by splunk.util.parseISOOffset(tzoffset)
        """
        default = '+00:00'
        if isinstance(self._kpi, dict):
            return self._kpi.get('tz_offset', default)
        else:
            return default


class ServiceKPI(KPIBase):
    def __init__(self, logger=None, service_data=None, kpi_id=None):
        if not isinstance(kpi_id, str):
            raise ValueError(
                "Null or non-string KPI ID sent to KPI constructor.")
        self.kpi_id = str(kpi_id)
        # KPI load/save operations are performed via different interface classes
        # depending on how exactly threshold data are being passed.
        # interface class instance if passing data in a saved ITSI service
        # store fetched object so that it's easy to update
        self._kvstore_data = service_data
        self.session_key = None
        self.owner = None
        super(ServiceKPI, self).__init__(logger)

    def initialize_interface(self, session_key, owner="nobody", namespace=None, **kwargs):
        self.session_key = session_key
        self.owner = owner

    def fetch_kpi(self):
        if self._kvstore_data is None:
            self.logger.warn("Could not load kpi from empty service data!")
            return None
        self.logger.debug("Loading settings from saved KPI in KV store.")
        for kpi in self._kvstore_data.get("kpis", []):
            if kpi["_key"] == self.kpi_id:
                self._kpi = kpi
                return kpi
        self.logger.warn('Could not lookup KPI for a seemingly stale KPI with id: %s', self.kpi_id)
        return None

    def update_thresholds(self, policy=None, thresholds=None):
        self._update_thresholds(policy, thresholds)


class TempKPI(KPIBase):

    def __init__(self, logger=None, temp_collection_name=None, temp_object_key=None):
        if not isinstance(temp_collection_name, str):
            raise ValueError(
                "Null or non-string collection name sent to KPI constructor.")
        if not isinstance(temp_object_key, str):
            raise ValueError(
                "Null or non-string object ID sent to KPI constructor.")
        self.temp_collection_name = str(temp_collection_name)
        self.temp_object_key = str(temp_object_key)
        # KPI load/save operations are performed via different interface classes
        # depending on how exactly threshold data are being passed.
        # interface class instance if passing data in a temp collection
        self._temp_kpi_model = None
        self._temp_kpi_collection_interface = None
        # since we didn't know the collection name up front, create
        # TempKpiModel class here
        self.TempKpiModel = type("TempKpiModel", (itoa_generic_persistables.ItoaGenericModel,), {
            'backing_collection': temp_collection_name,
            'logger': logger
        })
        super(TempKPI, self).__init__(logger)

    def initialize_interface(self, session_key, owner="nobody", namespace=None, **kwargs):
        self._temp_kpi_collection_interface = self.TempKpiModel.initialize_interface(
            session_key, owner=owner, namespace=namespace, **kwargs)

    def fetch_kpi(self):
        self.logger.debug("Loading settings from temporary object with key=%s in collection %s.",
                          self.temp_object_key, self.temp_collection_name)
        self._temp_kpi_model = self.TempKpiModel.fetch_from_key(
            self.temp_object_key, interface=self._temp_kpi_collection_interface)
        self._kpi = self._temp_kpi_model.data
        return self._kpi

    def update_thresholds(self, policy=None, thresholds=None):
        self._update_thresholds(policy, thresholds)
        self._temp_kpi_model.save()


class FileBackedKPI(KPIBase):

    def __init__(self, logger=None, filename=None):
        if filename is None:
            raise ValueError(
                "Must supply a filename if not using the KV store.")
        self.kpi_file = filename
        super(FileBackedKPI, self).__init__(logger)

    def initialize_interface(self, session_key, owner="nobody", namespace=None, **kwargs):
        pass  # no-op for file-backed KPIs

    def fetch_kpi(self):
        self.logger.debug("Loading settings from file %s.", self.kpi_file)
        with open(self.kpi_file) as data_file:
            self._kpi = json.load(data_file)
        return self._kpi

    def update_thresholds(self, policy=None, thresholds=None):
        self._update_thresholds(policy, thresholds)
        with open(self.kpi_file, 'w') as data_file:
            json.dump(self._kpi, data_file)


# Service Class
class Service(object):
    """
        Provides an interface to fetch and batch update ITSI Service objects.

        Service can be backed by
        - one of the Services stored in the ITSI service object
     """

    def __init__(self, logger=None):
        self._service_object = None
        # store fetched object so that it's easy to update
        self._kvstore_data = None
        self.session_key = None
        self.owner = None
        self.logger = logger

    def initialize_interface(self, session_key, owner="nobody"):
        self.session_key = session_key
        self.owner = owner
        self._service_object = instantiate_object(self.session_key, self.owner, "service")

    def fetch_service(self, service_id=None):
        """
        Return service data based on service id

        @param service_id: the id of service
        """
        if not isinstance(service_id, str):
            raise ValueError(
                "Null or non-string object service_id.")
        if self._kvstore_data is None:
            self.logger.warn("Empty service data! Bulk fetch services first")
            return None
        self.logger.debug("Loading single service from saved services.")
        for service in self._kvstore_data:
            if service["_key"] == service_id:
                return service
        self.logger.warn('Could not lookup service for a seemingly stale service with id: %s', service_id)
        return None

    def bulk_fetch_service(self, service_ids_list=None):
        """
        Bulk fetch list of service data

        @param service_ids_list: the list of services id
        """
        if len(service_ids_list) == 0:
            self.logger.warn("Could not bulk_fetch with empty service ids!")
            return None
        get_bulk_filter = {'$or': []}
        for service_id in service_ids_list:
            get_bulk_filter['$or'].append({'_key': service_id})
        self._kvstore_data = self._service_object.get_bulk(
            self.owner,
            filter_data=get_bulk_filter,
            req_source='itsi_at')
        if self._kvstore_data is None:
            self.logger.warn("Could not load service from list of service ids: %s", service_ids_list)
            return None

    def batch_update_services(self):
        """
        The function to batch update ITSI services object.
        """
        if self._kvstore_data is None:
            self.logger.warn("Empty services data, bulk fetch services first")
            return None
        self.logger.debug("batch_update %s services", len(self._kvstore_data))
        # Adding ignore_refresh_impacted_objects because for applying AT we do not need to perform async check on dependencies 
        # which is invoked in itoa_object.py in SA-ITOA
        self._service_object.save_batch(
            self.owner,
            self._kvstore_data,
            False,
            req_source="itsi_at",
            ignore_refresh_impacted_objects=True
        )