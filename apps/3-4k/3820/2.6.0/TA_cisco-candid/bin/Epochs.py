import url_constants
from Error import InvalidInputParameter
from datetime import datetime


class Epoch(object):
    """Class for handling rest calls for epochs NAE API."""

    def __init__(self, restClient, fabric_id):
        """Initialize Epoch instance with required parameters."""
        self.rc = restClient
        self.base_url = url_constants.EPOCHS
        self.fabric_id = fabric_id

    def get_last_n_epochs(self, param_dict=None):
        """Return response of last N epochs."""
        if param_dict:
            for key in param_dict.keys():
                if key not in url_constants.EPOCH_PARAMS:
                    raise InvalidInputParameter(key)
        else:
            param_dict = {}

        param_dict["$fabric_id"] = self.fabric_id
        url = self.rc.add_query_params_to_url(url=self.base_url, query_param_dict=param_dict)
        new_url = self.rc.get_endpoint_url(url=url)
        resp = self.rc.get_custom_response(url=new_url)
        data = self.rc.get_data_from_response(resp)
        return data

    def get_epoch_by_id(self, epoch_id):
        """Return response of specific epoch_id."""
        param_dict = {}
        param_dict["$epoch_id"] = epoch_id
        param_dict["$processed"] = True
        url = self.rc.add_query_params_to_url(url=self.base_url, query_param_dict=param_dict)
        new_url = self.rc.get_endpoint_url(url=url)
        resp = self.rc.get_custom_response(url=new_url)
        data = self.rc.get_data_from_response(resp)
        return data

    def get_latest_epoch(self):
        """Return latest epoch of specific fabric."""
        param_dict = {}
        param_dict["$fabric_id"] = self.fabric_id
        param_dict["$page"] = 0
        param_dict["$size"] = 1
        param_dict["$sort"] = "-analysis_start_time"

        url = self.rc.add_query_params_to_url(url=self.base_url, query_param_dict=param_dict)
        new_url = self.rc.get_endpoint_url(url=url)
        resp = self.rc.get_custom_response(url=new_url)
        data = self.rc.get_data_from_response(resp)
        return data

    def get_epochs_by_time(self, start_time=None, end_time=None, page=None, size=None):
        """Return epochs of given time range."""
        try:
            param_dict = {}
            param_dict["$fabric_id"] = self.fabric_id
            param_dict["$processed"] = True
            if start_time:
                param_dict["$from_collection_time_msecs"] = start_time
            if end_time:
                param_dict["$to_collection_time_msecs"] = end_time
            else:
                param_dict["$to_collection_time_msecs"] = datetime.utcnow()
            if page:
                param_dict["$page"] = page
            if size:
                param_dict["$size"] = size
            url = self.rc.add_query_params_to_url(url=self.base_url, query_param_dict=param_dict)
            new_url = self.rc.get_endpoint_url(url=url)
            resp = self.rc.get_custom_response(url=new_url)
            data = self.rc.get_data_from_response(resp)
            return data
        except Exception:
            # return []
            raise
