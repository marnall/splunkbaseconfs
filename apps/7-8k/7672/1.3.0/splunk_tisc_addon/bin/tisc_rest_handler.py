import json
import logging
import re

import requests
from splunktaucclib.rest_handler import admin_external
from splunklib import client
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError
from constants import additional_attributes_label_to_api_field_mapping
from constants import INPUTS_METADATA_KV_STORE, APP_NAME, INPUT_NAME


# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("Starting tisc_rest_handler.py...")

def validate_filter_for_valid_json(incoming_filters):
    try:
        if(json.loads(incoming_filters)):
            return True
        return False
    except ValueError:
        return False

def validate_filter_and_create_json(filter_str):
    # Define allowed tokens and operators
    allowed_tokens = [ "threat_score", "confidence", "reputation", "type", "value"]

    int_operators = ["=", "!=", ">", "<",">=", "<="]
    str_operators = ["=", "!=", "IN"]

    # Combine all operators into a regex pattern
    operator_pattern = '<=|>=|!=|=|>|<|IN'

    # Remove extra spaces and normalize spacing around "AND"
    filter_str = re.sub(r'\s+', ' ', filter_str).strip()

    # Split conditions by 'AND'
    conditions = filter_str.split("AND")

    filters = []
    for condition in conditions:
        condition = condition.strip()

        # Use regex to split around the operator
        match = re.split(f'({operator_pattern})', condition, maxsplit=1)
        if len(match) != 3:
            return False, f"Invalid condition format: '{condition}'"

        token, operator, value = match[0].strip(), match[1].strip(), match[2].strip()

        # Validate token
        if token not in allowed_tokens:
            return False, f"Invalid token: '{token}'"

        # Validate operator based on token type
        if token in ["threat_score", "confidence"]:
            if operator not in int_operators:
                return False, f"Invalid operator '{operator}' for '{token}' token"
            # Ensure value is a valid integer without spaces
            if not value.isdigit():
                return False, f"Invalid integer value '{value}' for '{token}' token"

        else:  # String type token
            if operator not in str_operators:
                return False, f"Invalid operator '{operator}' for '{token}' token"
            # For 'IN' operator, check for a list format
            if operator == "IN":
                if not re.match(r'^\(\s*"[^"]+"\s*(,\s*"[^"]+"\s*)*\)$', value):
                    return False, f"Invalid list of string for IN operator in '{condition}'"
            else:
                # Validate single string format
                if not re.match(r'^".+"$', value):
                    return False, f"Invalid string value '{value}' for '{token}' token"

        value = value.strip('"')
        # Prepare the filter in JSON format
        if operator == "IN":
            value = value.strip('()').replace('"', '')  # Remove parentheses and quotes for 'IN' values
        filters.append({
            "field_name": token,
            "operator": operator,
            "field_value": value
        })

    # Create the final JSON structure
    result = {
        "boolean_operator": "AND",
        "filters": filters
    }

    return True, json.dumps(result, indent=4)

def validate_and_get_additional_attribute_field_names(attr_string):
    if not attr_string or attr_string.strip() == "":
        return True, []

    attributes = [attr.strip() for attr in attr_string.split(",")]
    invalid_attributes = []
    valid_field_names = []

    for label in attributes:
        if label in additional_attributes_label_to_api_field_mapping:
            valid_field_names.append(additional_attributes_label_to_api_field_mapping[label])
        else:
            invalid_attributes.append(label)

    if invalid_attributes:
        return False, invalid_attributes
    return True, valid_field_names


class TISCRestHandler(admin_external.AdminExternalHandler):

    def __init__(self, *args, **kwargs):
        admin_external.AdminExternalHandler.__init__(self, *args, **kwargs)

    def delete_existing_metadata_records(self, input_name):
        try:
            service = client.connect(app=APP_NAME, token=self.getSessionKey())
            kvstore = service.kvstore[INPUTS_METADATA_KV_STORE]
            query = {INPUT_NAME: input_name}
            records = kvstore.data.query(query=query)
            for record in records:
                query_key = json.dumps({"_key": record['_key']})
                kvstore.data.delete(query_key)
                logger.debug(f"Deleted metadata record with key: {record['_key']}")
        except Exception as e:
            logger.error(f"Error deleting metadata records for input {input_name}: {str(e)}")
            raise

    def handleCreate(self, conf_info):
        try:
            logger.debug("Handling create operation for TISC IP entry.")
            account = str(self.callerArgs.id)
            # username = self.payload.get("username")
            # password = self.payload.get("password")
            # url = self.payload.get("instanceUrl")
            days_till_expiry = self.payload.get("days_till_expiry")
            interval = self.payload.get("interval")
            #session_key = self._input_definition.metadata["session_key"]

            advancedCheckBox = self.payload.get("advanced")
            logger.debug(f"advancedCheckBox value={advancedCheckBox}")

            incoming_filters = ""
            if(advancedCheckBox=="0"):
                incoming_filters = self.payload.get("filters")
                if(incoming_filters==""):
                    raise ValueError("Invalid Filter: The filter cannot be empty.")
                is_valid, jsonOutput = validate_filter_and_create_json(incoming_filters)
                if not is_valid:
                    logger.debug(f"Invalid filter format: {jsonOutput}")
                    raise ValueError(f"Invalid filter format: {jsonOutput}")
            elif(advancedCheckBox=="1"):
                incoming_filters = self.payload.get("json_filters")
                if(incoming_filters==""):
                    raise ValueError("Invalid Filter: The filter cannot be empty.")
                isValidJSONFilter = validate_filter_for_valid_json(incoming_filters)
                if((not isValidJSONFilter) and len(incoming_filters) > 2):
                    raise ValueError("Invalid JSON: The filter is not a valid JSON.")
                logger.debug(f"validate_filter_for_valid_json result is {isValidJSONFilter}")

            additional_attrs = self.payload.get("additional_attributes")
            is_valid, invalid_attrs = validate_and_get_additional_attribute_field_names(additional_attrs)
            if not is_valid:
                if len(invalid_attrs) == 1:
                    raise ValueError(f"Invalid Additional Attribute: {invalid_attrs[0]} is not valid.")
                else:
                    raise ValueError(f"Invalid Additional Attributes: {', '.join(invalid_attrs)} are not valid.")
            
            logger.debug(f"Handling create operation for TISC IP entry for tiscadmin instance. New UI config ID: {self.callerArgs.id}, Account: {account}, Interval: {interval}, Days till Expiry: {days_till_expiry}, Incoming Filters: {incoming_filters}")

            AdminExternalHandler.handleCreate(self, conf_info)
            logger.debug("Successfully created Instance entry.")
        except Exception as e:
            logger.error(f"Error during handleCreate: {str(e)}")
            raise

    def handleEdit(self, conf_info):
        try:
            logger.debug("Handling edit operation for TISC IP entry.")
            # Validate the API key before editing the config
            input_name = str(self.callerArgs.id)
            advancedCheckBox = self.payload.get("advanced")
            logger.debug(f"advancedCheckBox value={advancedCheckBox}")

            incoming_filters = ""
            if(advancedCheckBox=="0"):
                incoming_filters = self.payload.get("filters")
                if(incoming_filters==""):
                    raise ValueError("Invalid Filter: The filter cannot be empty.")
                is_valid, jsonOutput = validate_filter_and_create_json(incoming_filters)
                if not is_valid:
                    logger.debug(f"Invalid filter format: {jsonOutput}")
                    raise ValueError(f"Invalid filter format: {jsonOutput}")
            elif(advancedCheckBox=="1"):
                incoming_filters = self.payload.get("json_filters")
                if(incoming_filters==""):
                    raise ValueError("Invalid Filter: The filter cannot be empty.")
                isValidJSONFilter = validate_filter_for_valid_json(incoming_filters)
                if((not isValidJSONFilter) and len(incoming_filters) > 2):
                    raise ValueError("Invalid JSON: The filter is not a valid JSON.")
                logger.debug(f"validate_filter_for_valid_json result is {isValidJSONFilter}")

            additional_attrs = self.payload.get("additional_attributes")
            is_valid, invalid_attrs = validate_and_get_additional_attribute_field_names(additional_attrs)
            if not is_valid:
                if len(invalid_attrs) == 1:
                    raise ValueError(f"Invalid Additional Attribute: {invalid_attrs[0]} is not valid.")
                else:
                    raise ValueError(f"Invalid Additional Attributes: {', '.join(invalid_attrs)} are not valid.")
            
            admin_external.AdminExternalHandler.handleEdit(self, conf_info)
            logger.debug("Successfully edited Input entry.")
        except Exception as e:
            logger.error(f"Error during handleEdit: {str(e)}")
            raise
    def handleRemove(self, conf_info):
        try:
            logger.debug("Handling delete operation for TISC IP config")
            input_name = str(self.callerArgs.id)

            # Delete metadata for this input
            self.delete_existing_metadata_records(input_name)

            AdminExternalHandler.handleRemove(self, conf_info)
            logger.debug("Input Removed: Successfully deleted input entry and related metadata.")
        except Exception as e:
            logger.error(f"Error during handleRemove: {str(e)}")
            raise

    def handleList(self, conf_info):
        admin_external.AdminExternalHandler.handleList(self, conf_info)