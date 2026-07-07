import json

import splunk.rest


class KVStoreClient:
    """Use this client class to retrieve Splunk collections, add items to collections, and
    remove items from collections. This is built on top of the Splunk API via their
    `simpleRequest` tool.

    REST Documentation: https://dev.splunk.com/enterprise/docs/developapps/manageknowledge/kvstore/usetherestapitomanagekv/
    """

    _base_uri = (
        "/servicesNS/nobody/TA-code42-insider-threats-add-on/storage/collections/data"
    )

    def __init__(self, collection_name, session_key):
        self._collection_name = collection_name
        self._session_key = session_key

    def get_collection(self):
        """Return an entire collection from Splunk."""
        uri = f"{self._base_uri}/{self._collection_name}"
        response, content = splunk.rest.simpleRequest(uri, sessionKey=self._session_key)
        return response, json.loads(content)

    def insert_item_into_collection(self, record):
        """Insert a new item into a collection by providing a dictionary representation of the item."""
        uri = f"{self._base_uri}/{self._collection_name}"
        return splunk.rest.simpleRequest(
            uri,
            sessionKey=self._session_key,
            jsonargs=json.dumps(record),
            method="POST",
        )

    def delete_item_from_collection(self, item_key):
        """Delete an item from splunk using the item's unique identifier (`_key`)."""
        uri = f"{self._base_uri}/{self._collection_name}/{item_key}"
        return splunk.rest.simpleRequest(
            uri, sessionKey=self._session_key, method="DELETE"
        )
