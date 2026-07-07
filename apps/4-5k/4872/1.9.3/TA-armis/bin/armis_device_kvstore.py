import json
import traceback
import datetime

import ta_armis_declare
import splunk.clilib.cli_common
import splunklib.client as client
import splunk.rest as rest
from armis_exceptions import ApplicationCheckpointException

APP_NAME = ta_armis_declare.ta_name

class ApplicationCheckpoint(object):
    """This class provides a KVStore client for inserting devices records."""

    def __init__(self, helper, logger, input_name):
        """
        ApplicationCheckpoint class init method.
        """
        self.mgmt_port = splunk.clilib.cli_common.getMgmtUri().split(":")[-1]
        self.session_key = helper.context_meta['session_key']
        self.collection_name = "armis_device_collection"
        self.helper = helper
        self.logger = logger
        self.input_name = input_name
        try:
            self.kvstore_status = self._get_kvstore_status()
            service = client.connect(
                port=self.mgmt_port, token=self.session_key, app=APP_NAME)
            if self.collection_name in service.kvstore:
                self.collection = service.kvstore[self.collection_name]
            else:
                self.logger.error(
                    "input_name={} | message=collection_does_not_exist | Collection {} does not exist. Please define one in collections.conf."
                    .format(self.input_name, self.collection_name)
                )
                raise Exception
        except Exception:
            raise ApplicationCheckpointException(traceback.format_exc())

    def _groom(self, data):
        """
        Method to groom data before sending it to lookup.

        :param data: response in json format
        :returns: list of response(s) to be stored in the lookup
        {
            "_key": id,
            "ipAddress": ipAddress
            "macAddress": macAddress.
        }
        """
        dict_array = []
        temp_dict = {}
        try:
            for each in data:
                temp_dict["_key"] = each["id"]
                temp_dict["ipAddress"] = each["ipAddress"]
                temp_dict["macAddress"] = each["macAddress"]
                dict_array.append(temp_dict)
                temp_dict = {}
        except Exception:
            self.logger.error("input_name={} | message=data_grooming_error | An excpetion occurred while grooming data for lookup {}"
            .format(self.input_type, traceback.format_exc())
            )
        return dict_array

    def _get_kvstore_status(self):
        """Get kv store status."""
        _, content = rest.simpleRequest("/services/kvstore/status",
                                        sessionKey=self.session_key,
                                        method="GET",
                                        getargs={"output_mode": "json"},
                                        raiseAllErrors=True)
        data = json.loads(content)["entry"]
        return data[0]["content"]["current"].get("status")

    def _chunk_data(self, data, chunk_size=1000):
        """
        Method for chunking data for kvstore insertion.

        :param data: data dictionary to be chunked.
        :param chunk_size:
        :yields chunks:
        """
        for i in range(0, len(data), chunk_size):
            yield data[i:i + chunk_size]

    def kvstore_insert(self, devices):
        """
        Method to insert devices into the corresponding kvstore collection.

        :param devices: Dict of response.
        """
        groomed_data = self._groom(devices)
        chunked_data = (list(self._chunk_data(groomed_data)))
        inserted_ids = []
        for chunk in chunked_data:
            inserted_ids.extend(self.collection.data.batch_save(*chunk))
        self.logger.debug("input_name={} | message=inserted_device_to_lookup | Inserted {} device ids to lookup successfully."
            .format(self.input_name, len(inserted_ids))
        )

    def kvstore_delete(self):
        """
        Method to remove responses from lookup.
        """
        try:
            self.collection.data.delete()
        except Exception:
            self.logger.error("input_name={} | message=failed_to_clear_lookup | Failed to clear records from lookup.\n{}"
                .format(self.input_name, traceback.format_exc())
            )

    def query_kv_store(self):
        """
        Method to query responses present in the lookup.
        """
        items = []
        if self.kvstore_status != "ready":
            return None
        else:
            kwargs = {}
            try:
                items = self.collection.data.query(**kwargs)
                self.logger.info("input_name={} | message=found_data_from_lookup | Found {} devices from lookup successfully."
                    .format(self.input_name, len(items))
                )
            except Exception:
                self.logger.error("input_name={} | message=querying_kvstore_error | An exception occurred while querying KVStore: {}"
                    .format(self.input_name, traceback.format_exc())
                )
            return items
