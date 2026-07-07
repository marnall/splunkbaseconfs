import json
import os
import re
import sys
from collections import defaultdict
import traceback

# Add the "lib" directory to the Python path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Add the directory where this script resides to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from splunk.persistconn.application import PersistentServerConnectionApplication

import splunklib
import splunklib.client as client

from constants import KV_AT_TIME_POLICIES_COLLECTION, MISSING_JOB_ID, METHOD_NOT_ALLOWED, ITSI_SERVICE_ID, ITSI_KPI_ID,\
    FIELD_TO_SNAKE_CASE_DICT, JOB_ID_NOT_FOUND, ENTITY_KEY, ENTITY_TITLE, ALL_DATA_RECEIVED, ENTITY_AT_CONFIGURATIONS, \
    NA, USE_STATIC, ITSI_SERVICE_ID

from kpis_utils import get_valid_entity_identifier
from util import setup_logging

PATH_INFO = "path_info"

# Set up logger
logger = setup_logging.get_logger()


class ATConfigurationsAPIHandler(PersistentServerConnectionApplication):
    """
    The ATConfigurationsAPIHandler class serves as a RESTful API endpoint for handling
    machine learning-assisted KPI thresholding configurations within Splunk IT Service Intelligence (ITSI) environment.

    The API supports the following HTTP methods:

    - GET: Retrieves assisted thresholding (AT) configurations associated with a given job ID
           in the Splunk ITSI environment. The job ID should be provided as part of the REST URI.
    - DELETE: Deletes the AT configurations associated with a given job ID from the Splunk KV Store.
    """

    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()
        self.service = None
        self.entity_level_processing = False

    def handle(self, in_string):
        try:
            request = json.loads(in_string)
            method = request.get("method", "")
            rest_path = request.get('rest_path', "")

            if rest_path.startswith("/api/v1/kpis_at_configurations/entities"):
                self.entity_level_processing = True

            job_id = self.extract_job_id(request)
            if not job_id:
                return self.create_response(400, error=MISSING_JOB_ID)

            logger.info(f"Processing request for job_id={job_id}")

            self.initialize_service_if_needed(request)

            if method == "GET":
                transformed_configurations = self.handle_get(job_id)
                return self.create_response(200, result=transformed_configurations)
            elif method == "DELETE":
                self.handle_delete(job_id)
                return self.create_response(200, result=f"Job_id {job_id} deleted")
            else:
                return self.create_response(405, error=METHOD_NOT_ALLOWED)

        except splunklib.binding.HTTPError as e:
            return self.handle_http_error(e)
        except Exception as e:
            logger.exception(e)
            # the full_traceback provide all traces of the exception e.
            full_traceback = traceback.format_exc()
            return self.create_response(500, error=f"Server error: {str(e)}, full trace back {full_traceback}")
            

    def handle_get(self, job_id):
        transformed_configurations = self.process_request_for_job_id(job_id)
        return transformed_configurations

    def handle_delete(self, job_id):
        try:
            collection = self.service.kvstore[KV_AT_TIME_POLICIES_COLLECTION]
            return collection.data.delete_by_id(str(job_id))
        except splunklib.binding.HTTPError as e:
            logger.exception(f"Failed to delete _key={job_id} from KV Store, error: {e}")
            raise e

    def initialize_service_if_needed(self, request):
        if self.service is None:
            self.initialize_service(request)

    def initialize_service(self, request):
        """Initialize the Splunk service connection."""
        try:
            session_key = request["session"]["authtoken"]
            port = self.extract_management_port(request)

            # Prepare arguments for client.Service
            service_kwargs = {
                "token": session_key,
                "owner": "nobody"
            }

            # Only add port to the arguments if it is not None
            if port is not None:
                service_kwargs["port"] = port

            self.service = client.Service(**service_kwargs)
        except Exception as e:
            logger.error(f"Failed to initialize Splunk service connection, error={str(e)}")
            self.service = None

    @staticmethod
    def extract_management_port(request):
        """
        Extracts the port number from the 'rest_uri' within a request dictionary.
        The 'rest_uri' is expected under request['server']['rest_uri'].

        Args:
            request (dict): The request dictionary containing the server information.

        Returns:
            int or None: The extracted port number as an integer, or None if not found.
        """
        try:
            # Extract the rest_uri from the server dictionary
            rest_uri = request.get("server", {}).get("rest_uri", "")

            match = re.search(r':(\d+)', rest_uri)
            if match:
                # Convert the matched group to an integer
                return int(match.group(1))
            else:
                # Return None if no port is found in the URI
                return None
        except ValueError as e:
            # Handle cases where the port number is not a valid integer
            logger.error(f"Invalid port number in request, error={str(e)}")
            return None

    @staticmethod
    def extract_job_id(request):
        path_info = request.get(PATH_INFO)
        if not path_info:
            return None
        return path_info.split('/')[-1].strip()

    def process_request_for_job_id(self, job_id):
        kpis_at_configurations = self.get_kpis_at_configurations_from_kv_store(job_id)
        transformed_configurations = self.transform_data(kpis_at_configurations)
        transformed_configurations["job_id"] = job_id
        logger.info(f"Processed request for job_id={job_id}")
        return transformed_configurations

    def handle_http_error(self, error):
        if error.status == 404:
            return self.create_response(error.status, error=JOB_ID_NOT_FOUND)
        raise error

    def get_kpis_at_configurations_from_kv_store(self, job_id):
        """
        Fetch KPIs AT configurations from KV Store using job_id
        """
        try:
            collection = self.service.kvstore[KV_AT_TIME_POLICIES_COLLECTION]
            return collection.data.query_by_id(str(job_id))
        except splunklib.binding.HTTPError as e:
            logger.exception(f"Failed to query KV Store for job_id={job_id}, error: {e}")
            raise e

    @staticmethod
    def create_response(status, result=None, error=None):
        """
        Create response to send back to client.
        """
        return {
            "payload": {"result": result, "error": error},
            "status": status
        }

    @staticmethod
    def transform_record(record):
        """Transforms a record to have snake_case keys"""
        transformed = {}
        for key, value in list(record.items()):
            # We also exclude ITSI_SERVICE_ID here, we have this field in results, 
            # but not save it into kv store for consistency
            if key not in (ITSI_KPI_ID, ITSI_SERVICE_ID, ENTITY_KEY, ENTITY_TITLE):
                transformed[FIELD_TO_SNAKE_CASE_DICT[key]] = value
            if key == USE_STATIC:
                transformed[FIELD_TO_SNAKE_CASE_DICT[USE_STATIC]] = value == "True"
        return transformed

    def transform_data(self, input_data):
        if self.entity_level_processing:
            return self.transform_entities_data(input_data)

        return self.transform_kpis_data(input_data)

    def transform_kpis_data(self, input_data):
        kpi_dict = defaultdict(list)

        records = json.loads(input_data['data'])

        for record in records:
            kpi_id = record[ITSI_KPI_ID]
            transformed_record = self.transform_record(record)
            kpi_dict[kpi_id].append(transformed_record)

        output_data = {'data': [
            {ITSI_KPI_ID: kpi_id, 'kpi_at_configurations': kpi_at_configurations}
            for kpi_id, kpi_at_configurations in list(kpi_dict.items())
        ], ALL_DATA_RECEIVED: input_data[ALL_DATA_RECEIVED]}

        return output_data

    def transform_entities_data(self, input_data):
        """
        Transforms input data containing KPIs, entities, and their configurations into a structured format.
        The transformation aggregates entities under their respective KPI IDs, along with their configurations.

        Example input format:
        {
            "data": json.dumps([
                {
                    "kpi_id": "5c840c54-ba84-4edb-9e3c-5e624dad2c78",
                    "entity_key": "130e1f7f-ad8b-4718-9d9b-acef32af244f",
                    "entity_title": "entity1",
                    "recommendation_flag": "SUCCESSFUL",
                    ... // other attributes
                },
                ... // more records
            ]),
            "all_data_received": True
        }

        Example output format:
        {
            "data": [
                {
                    "kpi_id": "5c840c54-ba84-4edb-9e3c-5e624dad2c78",
                    "entities": [
                        {
                            "entity_key": "130e1f7f-ad8b-4718-9d9b-acef32af244f",
                            "entity_title": "entity1",
                            "entity_at_configurations": [
                                {
                                    "recommendation_flag": "SUCCESSFUL",
                                    "algorithm": "stdev",
                                    "cron_expression": "0 0 * * 0,4,5,6",
                                    "duration": 60,
                                    ... // other configuration attributes
                                },
                                ... // more configurations
                            ]
                        }
                        ... // more entities
                    ]
                }
                ... // more KPI groups
            ],
            "all_data_received": True
        }
        """
        # Initialize a nested dictionary to hold KPIs, entities, and their configurations
        # This structure allows for dynamically adding KPIs, entities, and their configurations
        # without having to check if the keys already exist in the dictionary.
        # Structure of kpi_dict after processing:
        # {
        #   kpi_id: {
        #     entity_key_or_title: {
        #       ENTITY_AT_CONFIGURATIONS: [
        #         { ...configuration details... },
        #         ... // more configurations
        #       ],
        #       ENTITY_KEY: entity_key,  # added later in the code
        #       ENTITY_TITLE: entity_title  # added later in the code
        #     },
        #     ... // more entities under the same KPI
        #   },
        #   ... // more KPIs
        # }
        kpi_dict = defaultdict(lambda: defaultdict(lambda: {ENTITY_AT_CONFIGURATIONS: []}))

        records = json.loads(input_data['data'])

        for record in records:
            kpi_id = record[ITSI_KPI_ID]
            transformed_record = self.transform_record(record)

            entity_key = record.get(ENTITY_KEY, NA)
            entity_title = record.get(ENTITY_TITLE, NA)

            # Determine the key to use for grouping based on validity of entity_key
            key_to_use = get_valid_entity_identifier(entity_key, entity_title)
            if not key_to_use:
                raise ValueError("Valid entity identifier not found for the given key or title.")

            # Append the transformed record to the appropriate list
            kpi_dict[kpi_id][key_to_use][ENTITY_AT_CONFIGURATIONS].append(transformed_record)

            # Ensure both entity_key and entity_title are available in the output
            kpi_dict[kpi_id][key_to_use][ENTITY_KEY] = entity_key
            kpi_dict[kpi_id][key_to_use][ENTITY_TITLE] = entity_title

        output_data = {
            'data': [
                {
                    ITSI_KPI_ID: kpi_id,
                    'entities': [
                        {
                            ENTITY_KEY: details[ENTITY_KEY],
                            ENTITY_TITLE: details[ENTITY_TITLE],
                            ENTITY_AT_CONFIGURATIONS: details[ENTITY_AT_CONFIGURATIONS]
                        } for key, details in list(entity_details.items())
                    ]
                } for kpi_id, entity_details in list(kpi_dict.items())
            ], ALL_DATA_RECEIVED: input_data[ALL_DATA_RECEIVED]
        }

        return output_data
