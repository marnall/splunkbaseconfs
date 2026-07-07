import url_constants
from Error import InvalidInputParameter
import json


class Event(object):
    """Class for handling rest calls for events NAE API."""

    def __init__(self, restClient, fabric_id):
        """Initialize event instance with required parameters."""
        self.rc = restClient
        self.base_url = url_constants.SMART_EVENTS_BASE_URL
        self.fabric_id = fabric_id

    def get_events(self, param_dict):
        """Return identifier and category of Smart Events for specific epoch id provided in param_dict."""
        keys = param_dict.keys()
        smart_events_identifier_category = []

        if "$epoch_id" not in keys:
            raise InvalidInputParameter("epoch_id")
        for key in keys:
            if key not in url_constants.EVENTS_BY_CATEGORY_LIST:
                raise InvalidInputParameter(key)

        url = self.rc.add_query_params_to_url(url=url_constants.SMART_EVENTS_BY_CATEGORY, query_param_dict=param_dict)
        new_url = self.rc.get_endpoint_url(url=url)

        resp = self.rc.get(new_url)

        assert resp.status_code == 200, resp.content
        smart_events = self.rc.get_data_from_response(resp)

        if smart_events:
            for event in smart_events:
                category = None
                if self.rc.header_key_otp == "X-CANDID-LOGIN-OTP":
                    category = event['category']['name']
                if event['identifier']:
                    identifier_category = {}
                    identifier_category["identifier"] = event['identifier']
                    identifier_category["category"] = category
                    smart_events_identifier_category.append(identifier_category)

        if "page=" in new_url or resp.status_code != 200:
            # specific page is being requested, no more page to be fetched.
            return smart_events_identifier_category
        else:
            # specific page not requested so need to get all pages until has_more_data is false
            page_num = 0
            content_obj = json.loads(resp.content)
            has_more_data = content_obj['value']['data_summary']['has_more_data']
            while has_more_data is True:
                page_num += 1
                if "?" in new_url:
                    temp_url = new_url + '&' + '$page=' + str(page_num)
                else:
                    temp_url = new_url + '?' + '$page=' + str(page_num)

                # print 'There is more data, getting page ' + str(page_num)
                resp = self.rc.get(temp_url)

                assert resp.status_code == 200, resp.content
                smart_events = self.rc.get_data_from_response(resp)

                content_obj = json.loads(resp.content)
                has_more_data = content_obj['value']['data_summary']['has_more_data']

                if smart_events:
                    for event in smart_events:
                        category = None
                        if self.rc.header_key_otp == "X-CANDID-LOGIN-OTP":
                            category = event['category']['name']
                        if event['identifier']:
                            identifier_category = {}
                            identifier_category["identifier"] = event['identifier']
                            identifier_category["category"] = category
                            smart_events_identifier_category.append(identifier_category)
            return smart_events_identifier_category

    def make_event_category_url(self, category, uuid):
        """Create and return url based on provided category."""
        event_category = url_constants.EVENT_CATEGORY_DICT[category]
        url = self.base_url + event_category
        url = self.rc.get_endpoint_url(url=url.format(self.fabric_id, uuid))
        return url

    def make_event_detail_url(self, uuid):
        """Create and return Smart Event Detail url."""
        param_dict = {"$event_id": str(uuid)}
        url = self.rc.add_query_params_to_url(url=url_constants.SMART_EVENTS_DETAIL, query_param_dict=param_dict)
        url = self.rc.get_endpoint_url(url=url)
        return url

    def get_event_details(self, category, uuid):
        """Return Smart Event Detail response for provided smart event uuid."""
        if category is not None:
            url = self.make_event_category_url(category=category, uuid=uuid)
        else:
            url = self.make_event_detail_url(uuid=uuid)
        resp = self.rc.get_custom_response(url=url)
        data = self.rc.get_data_from_response(resp)
        return data

    def get_event_lifecycle(self, uuid):
        """Return Smart Event Lifecycle response for provided smart event uuid."""
        url = self.make_event_lifecycle_url(uuid=uuid)
        resp = self.rc.get_custom_response(url=url)
        data = self.rc.get_data_from_response(resp)
        return data

    def make_event_lifecycle_url(self, uuid):
        """Create and return smart event lifecycle url."""
        param_dict = {"$event_id": str(uuid)}
        url = self.rc.add_query_params_to_url(url=url_constants.SMART_EVENT_LIFECYCLE, query_param_dict=param_dict)
        url = self.rc.get_endpoint_url(url=url)
        return url


#    def get_system_event_details(self, category, uuid):
#        url = self.make_system_event_category_url(category=category, uuid=uuid)
