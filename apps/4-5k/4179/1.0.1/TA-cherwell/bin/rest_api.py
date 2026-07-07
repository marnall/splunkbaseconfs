
# Local imports
from api_connection import Connection


class RestApiService:

    def __init__(self, url, username, password, client_id, helper, proxy=False, ssl_verify=True):
        """ This method initializes an object of RestApiService class with required parameters.

        :param url: Cherwell instance URL
        :param username: Username of the provided account
        :param password: Password of the provided account
        :param client_id: Client ID of the provided account
        :param helper: Object of BaseModInput class
        :param proxy: Boolean value that signifies whether to use proxy or not
        :param ssl_verify: Boolean value that signifies whether to validate certificate or not
        """

        self.con = Connection(url, username, password, client_id, helper, proxy, ssl_verify)
        self.helper = helper
        self.con.connect()

    def rest_call(self, method, url, data=None):
        """ This method calls the rest_call method of Connection class.

        :param method: HTTP method to be used ex. GET/POST/PUT/DELETE
        :param url: Endpoint to hit
        :param data: Payload that needs to passed
        :return: REST call response
        """

        return self.con.rest_call(method, url, data=data)

    def get_field_id(self, obj_id, field_name):
        """ Get field id of the field_name from the schema of the object

        :param obj_id: ID of the business object
        :param field_name: Field name of which we reuiqre field id
        :return: Field id
        """
        response = self.rest_call("get", "/api/V1/getbusinessobjectschema/busobid/%s" % obj_id)
        for each_field in response["fieldDefinitions"]:
            if each_field["name"] == field_name:
                return each_field["fieldId"]

        raise ValueError("Field: {} for business object {} not found in Cherwell instance".format(field_name, obj_id))

    def get_service_info(self):
        """ This method is used to get various details like time zone, etc of the Cherwell instance.

        :return: REST response containing the details of the Cherwell instance
        """

        response = self.rest_call("get", "/api/V1/serviceinfo")
        return response

    def get_object_name_id(self, obj_name):
        """ This method is used to get object name and id using the value provided by the user.

        :param obj_name: Business object name as provided by the user
        :return: REST response
        """

        obj_name = obj_name.lower()
        response = self.rest_call("get", "/api/V1/getbusinessobjectsummaries/type/All")
        for each_object in response:
            if each_object.get("displayName").lower() == obj_name or each_object.get("name").lower() == obj_name:
                return each_object

        raise Exception("Object: %s Not found in Cherwell instance" % obj_name)

    @staticmethod
    def sort_scheme(field_id, descending=True):
        """  Return the json dictionary required in search_results api to sort the objects

        :param field_id: The field_id by which the objects should be sorted
        :param descending: If the sorting should be in descending order. Default: Ascending
        :return: Required dictionary
        """
        if not field_id:
            return dict()
        return {
            "fieldId": field_id,
            "sortDirection": int(not descending)
        }

    @staticmethod
    def filter_scheme(field_id, operator, value):
        """ Return the json dictionary required in search_results api to filter out the objects

        :param field_id: The Field_id by which the filter should be done
        :param operator: Possible values: ['eq', 'gt', 'lt', 'contains', 'startswith']
        :param value: Value for the filter condition
        :return: Required dictionary
        """
        if not field_id:
            return dict()
        return {
            "fieldId": field_id,
            "operator": operator, 
            "value": value
        }

    def get_results(self, **kwargs):
        """ Get records for the business object.

        :param kwargs:
        # Paramteres #
        - busobid/busObID: The internal ID for a Business Object type, such as Incident or Task.
        - association: The internal ID for the Business Object association.
        - fields:  a list of Field IDs to return.
        - filters: a list of filters
        - includeAllFields: a flag to include all Fields in search results.
        - pageSize: The number of rows to return per page.
        - pageNumber: The page number of the result set to return.
        - scope: The name or internal ID of an item's scope.
        - scopeowner: The internal ID or name of the Scope owner.
        - searchID: the internal ID of a Stored Query.
        - searchName: the display name of a Stored Query.
        - searchText: a text string used to filter search results.
        - sorting: a set of objects used to sort search results. Object consists of fieldId and sortDirection.
        :return: List of records
        """

        response = self.rest_call("post", "/api/V1/getsearchresults", data=kwargs)
        return response.get("businessObjects")

    def close_session(self):
        """ Logout from the API.
        """

        self.con.close_session()
