import url_constants


class Fabric(object):
    """Class for handling rest calls for fabric NAE API."""

    def __init__(self, restClient):
        """Initialize Epoch instance with required parameters."""
        self.rc = restClient
        self.base_url = url_constants.ACI_FABRIC

    def get_fabric(self, fabric_id=None):
        """Return response for specific fabric id otherwise for all fabric."""
        if fabric_id is not None:
            return self.rc.get_custom_response(
                url=self.rc.get_endpoint_url(url=self.base_url + "/{0}", fabric_id=fabric_id)
            )
        else:
            return self.rc.get_custom_response(self.rc.get_endpoint_url(url=self.base_url))

    def get_fabric_ids(self):
        """Return all the fabric id configured in NAE."""
        resp = self.get_fabric()
        data = self.rc.get_data_from_response(resp)
        fab_ids = []
        for fab in data:
            fab_ids.append(fab["uuid"])
        return fab_ids

    def get_fabric_id_from_name(self, fabric_name):
        """Return id of fabric from given fabric name."""
        resp = self.get_fabric()
        data = self.rc.get_data_from_response(resp)
        for fab in data:
            if fab["unique_name"] == fabric_name:
                return fab["uuid"]
        return None

    def get_fabric_interval(self, fabric_id):
        """Return interval of specific fabric."""
        resp = self.get_fabric(fabric_id=fabric_id)
        data = self.rc.get_data_from_response(resp)
        return data["interval"]

    def get_hostnames(self, fabric_id):
        """Return APIC Hostnames of specific fabric."""
        resp = self.get_fabric()
        data = self.rc.get_data_from_response(resp)
        for fab in data:
            if fab["uuid"] == fabric_id:
                return fab["apic_hostnames"]
        return None
