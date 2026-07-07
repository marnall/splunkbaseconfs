import import_utils
import sys
import json
import hashlib
import urllib.parse
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option
from splunk import rest

import logging
import logger_manager

logger = logger_manager.setup_logging("cmd", logging.INFO)


APP_NAME = "green_alerts_app"
NO_GROUPBY_FIELD = "--NONE--"

KVSTORE_INFO_COLLECTION = "green_alerts_details_collection"
# _key(alert_name), groupby_field_names
KVSTORE_DATA_COLLECTION = "green_alerts_data_collection"
# _key(hash of alert_name & groupby_field_values), alert_name, groupby_field_values, status



def generate_hash(input_string, algorithm='sha256'):
    hash_object = hashlib.new(algorithm)
    hash_object.update(input_string.encode())
    return hash_object.hexdigest()



@Configuration(local=True)
class GreenAlertCommand(StreamingCommand):

    alertname = Option(name="alertname", default=None, require=False)
    statusfield = Option(name="statusfield", default="status", require=False)
    groupbyfields = Option(name="groupbyfields",
                           default=NO_GROUPBY_FIELD, require=False)


    def read_kvstore_lookup_value(self, collection_name, key, raiseNoErrors=False):
        try:
            _, serverContent = rest.simpleRequest(
                f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{collection_name}/{urllib.parse.quote(key)}?output_mode=json",
                method="GET",
                sessionKey=self.session_key,
                raiseAllErrors=True,
            )
            return json.loads(serverContent)
        except Exception as e:
            if raiseNoErrors:
                return None
            raise e


    def write_kvstore_lookup_value(self, collection_name, data=None):
        _, serverContent = rest.simpleRequest(
            f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{collection_name}?output_mode=json",
            jsonargs=json.dumps(data),
            method="POST",
            sessionKey=self.session_key,
            raiseAllErrors=True,
        )
        logger.debug(f"Output write_kvstore_lookup_value: {json.loads(serverContent)}")


    def update_kvstore_lookup_value(self, collection_name, key, data):
        _, serverContent = rest.simpleRequest(
            f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{collection_name}/{urllib.parse.quote(key)}?output_mode=json",
            jsonargs=json.dumps(data),
            method="POST",
            sessionKey=self.session_key,
            raiseAllErrors=True,
        )
        logger.debug(f"Output update_kvstore_lookup_value: {json.loads(serverContent)}")


    def delete_kvstore_lookup_by_query(self, collection_name, query):
        _, serverContent = rest.simpleRequest(
            f"/servicesNS/nobody/{APP_NAME}/storage/collections/data/{collection_name}?output_mode=json",
            postargs={
                "query": query
            },
            method="DELETE",
            sessionKey=self.session_key,
            raiseAllErrors=True,
        )


    def _convert_str_to_dict(self, kvstore_collection_data):
        kvstore_collection_data = kvstore_collection_data if kvstore_collection_data else []
        for alert_info in kvstore_collection_data:
            alert_info["groupby_fields"] = json.loads(
                alert_info["groupby_fields"])
        return kvstore_collection_data


    def _convert_dict_to_str(self, alerts_details):
        for alert_info in alerts_details:
            alert_info["groupby_info"] = json.dumps(alert_info["groupby_info"])
        return alerts_details


    def _groupby_fields_list_to_str(self, groupby_field_names):
        # logger.debug(f"_groupby_fields_list_to_str -> groupby_field_names={groupby_field_names}")
        string_groupby = ",".join(groupby_field_names)
        # logger.debug(f"_groupby_fields_list_to_str -> string_groupby={string_groupby}")
        return string_groupby

    def _groupby_fields_str_to_list(self, groupby_field_names):
        # logger.debug(f"_groupby_fields_str_to_list -> groupby_field_names={groupby_field_names}")
        if not groupby_field_names:
            return []
        lst = sorted([ele.strip() for ele in groupby_field_names.split(",") if ele.strip()])
        # logger.debug(f"_groupby_fields_str_to_list -> lst={lst}")
        return lst


    def write_kvstore_data_value(self, alert_name, hash_value, groupby_field_values, color):
        self.write_kvstore_lookup_value(KVSTORE_DATA_COLLECTION, {
            "_key": hash_value,
            "alert_name": alert_name,
            "groupby_field_values": groupby_field_values,
            "status": color
        })
    
    def update_kvstore_data_value(self, alert_name, hash_value, groupby_field_values, color):
        self.update_kvstore_lookup_value(KVSTORE_DATA_COLLECTION, hash_value, {
            "alert_name": alert_name,
            "groupby_field_values": groupby_field_values,
            "status": color
        })


    def stream(self, records):
        logger.info("Green-alert Command stream()")
        if self.alertname and str(self.alertname) != "None":
            alert_name = self.alertname
        elif self.search_results_info.label:
            alert_name = self.search_results_info.label
        else:
            raise Exception("This can only be executed from alert or specify alertname option to the command.")
        logger.info(f"INPUT - alert_name: {alert_name}")
        logger.info(f"INPUT - groupbyfields: {self.groupbyfields}")
        logger.info(f"INPUT - statusfield: {self.statusfield}")

        if not self.search_results_info or not self.search_results_info.auth_token:
            self.logger.error("Unable to get session key in the custom command.")
            raise Exception("Unable to get session key.")
        self.session_key = self.search_results_info.auth_token

        try:
            groupby_field_names_lst_from_input = self._groupby_fields_str_to_list(self.groupbyfields)
            groupby_field_names_from_input = self._groupby_fields_list_to_str(groupby_field_names_lst_from_input)

            groupby_field_names_from_collection_dict = self.read_kvstore_lookup_value(KVSTORE_INFO_COLLECTION, alert_name, raiseNoErrors=True)
            logger.debug(f"groupby_field_names_from_collection_dict: {groupby_field_names_from_collection_dict}")
            groupby_field_names_lst_from_collection = None
            if groupby_field_names_from_collection_dict:
                groupby_field_names_from_collection = groupby_field_names_from_collection_dict["groupby_field_names"]
                groupby_field_names_lst_from_collection = self._groupby_fields_str_to_list(groupby_field_names_from_collection)

            if not groupby_field_names_from_collection_dict and not groupby_field_names_lst_from_collection:
                logger.warning("Adding the groupby field list to the alert info lookup.")
                self.write_kvstore_lookup_value(KVSTORE_INFO_COLLECTION, {"_key": alert_name, "groupby_field_names": groupby_field_names_from_input})
                groupby_field_names_from_collection = groupby_field_names_from_input
                groupby_field_names_lst_from_collection = groupby_field_names_lst_from_input

            elif groupby_field_names_from_input != groupby_field_names_from_collection:
                logger.warning("Cleaning up the alert status the lookup for the alert as there is change in groupby field list.")
                self.delete_kvstore_lookup_by_query(KVSTORE_DATA_COLLECTION, {"alert_name": alert_name})

                logger.warning("Updating the alert info lookup to update the groupby fields.")
                self.update_kvstore_lookup_value(KVSTORE_INFO_COLLECTION, alert_name, {"groupby_field_names": groupby_field_names_from_input})
                groupby_field_names_from_collection = groupby_field_names_from_input
                groupby_field_names_lst_from_collection = groupby_field_names_lst_from_input
            
            logger.info("Pre-processing completed, evaluating the search result records next.")

            for record in records:
                if self.statusfield in record:
                    logger.debug(f"RECORD - Evaluating the record: {record}")

                    value1 = f"{alert_name}|"
                    groupby_field_values = ""

                    if groupby_field_names_from_input == NO_GROUPBY_FIELD:
                        pass   # No group by field
                    else:
                        for gf in groupby_field_names_lst_from_input:
                            groupby_field_values += record.get(gf, "NONE")
                            groupby_field_values += "|"

                    hash_value = generate_hash(value1+groupby_field_values)

                    last_data_value_from_lookup = self.read_kvstore_lookup_value(KVSTORE_DATA_COLLECTION, hash_value, raiseNoErrors=True)
                    record_status = record[self.statusfield].upper().strip()
                    logger.debug(f"RECORD - last_data_value_from_lookup={last_data_value_from_lookup}, record_status={record_status}")

                    if last_data_value_from_lookup:
                        if last_data_value_from_lookup['status'] == "GREEN":
                            if record_status == "RED":
                                yield record
                                self.update_kvstore_data_value(alert_name, hash_value, groupby_field_values, "RED")
                            elif record_status == "GREEN":
                                pass

                        elif last_data_value_from_lookup['status'] == "RED":
                            if record_status == "RED":
                                yield record
                            elif record_status == "GREEN":
                                yield record
                                self.update_kvstore_data_value(alert_name, hash_value, groupby_field_values, "GREEN")

                    else:
                        if record_status == "RED":
                            yield record
                            self.write_kvstore_data_value(alert_name, hash_value, groupby_field_values, "RED")
                        elif record_status == "GREEN":
                            self.write_kvstore_data_value(alert_name, hash_value, groupby_field_values, "RED")

                else:
                    logger.info(f"This record ({record}) does not have any status field hence ignoring.")

        except Exception as err:
            msg = "Error occurred in GreenAlertCommand: {}".format(err)
            self.write_error(msg)
            logger.exception(msg)


if __name__ == "__main__":
    dispatch(GreenAlertCommand, sys.argv, sys.stdin, sys.stdout, __name__)
