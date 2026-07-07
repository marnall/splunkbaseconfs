import import_declare_test  # noqa: F401

import http
import json
import os
import sys
import time

import splunklib

from log_helper import setup_logging

sys.path.insert(0, os.path.abspath(os.path.join(__file__, "..", "..")))


ALERT_LOOKUP = "dataminr_saved_alerts"

KVSTORE_CALL_DELAY_SEC = 0.1
DEFAULT_MAX_RETRY = 3
DEFAULT_BACKOFF_FACTOR = 5
DEFAULT_KVSTORE_WRITE_LIMIT = 1000
RETRY_STATUS_CODES = set(range(500, 599))

# - Max allowed length of accelerated fields is 999 and ideally all fields used in kvstore query should be accelerated.
# - When putting field with 4 character name (e.g. "_key") into query,
#   it is verified that in worst case (all fields are of 999 char long),
#   max supported values into single call is with 498 (with removal of whitespaces in query's json dump) values,
#   exceeding it, throws the error "HTTP 413 Request Entity Too Large".
# - Followign is the optimum value for allowing few more characters for other URI components
KVSTORE_URL_CHUNKSIZE = 490

sys.path.append(os.path.abspath(os.path.join(__file__, "..")))
logger = setup_logging(os.path.splitext(os.path.basename(__file__))[0].lower())


def chunk(iterable, chunk_size):
    """Split iterable into chunks of given size."""
    for i in range(0, len(iterable), chunk_size):
        yield iterable[i : i + chunk_size]  # noqa: E203


class KVStoreUnavailbleError(Exception):
    """KVStore is not available (503 status code)."""

    pass


class CollectionNotFoundError(Exception):
    """Expected collection not found in KVStore."""

    def __init__(self, collection):
        """Initialize an environment."""
        message = 'Could not found collection named "{}"'.format(collection)
        super(CollectionNotFoundError, self).__init__(message)


class CollectionManager(object):
    """Abstract the KVStore Collection related transactions."""

    def __init__(
        self,
        service,
        collection_name,
        max_retry=DEFAULT_MAX_RETRY,
        backoff_factor=DEFAULT_BACKOFF_FACTOR,
    ):
        """Initialize the object."""
        self.max_retry = max_retry
        self.backoff_factor = backoff_factor
        self.collection_name = collection_name
        self.service = service
        self._kvstore_write_limit = None
        self._collection = None

    @property
    def collection(self):
        """Set collection object as propery."""
        if self._collection is None:
            if self.collection_name not in self.service.kvstore:
                raise CollectionNotFoundError(self.collection_name)
            self._collection = self.service.kvstore[self.collection_name]
        return self._collection

    @property
    def kvstore_write_limit(self):
        """Return kvstore write limit defined in limits.conf file."""
        if self._kvstore_write_limit is None:
            try:
                self._kvstore_write_limit = int(
                    self.service.confs["limits"]["kvstore"].content.get(
                        "max_documents_per_batch_save", DEFAULT_KVSTORE_WRITE_LIMIT
                    )
                )
            except Exception:
                self._kvstore_write_limit = DEFAULT_KVSTORE_WRITE_LIMIT
        return self._kvstore_write_limit

    # Decorator
    def normalize_exc(method):
        """Normalize low level exception to abstract application level excepitons."""

        def wrapper(self, *args, **kwargs):
            try:
                res = method(self, *args, **kwargs)
                return res
            except splunklib.binding.HTTPError as ex:
                if ex.status == http.HTTPStatus.SERVICE_UNAVAILABLE:
                    raise KVStoreUnavailbleError(str(ex))
                raise

        return wrapper

    # Decorator
    def retry(method):
        """Retry mechanism to avoid temporary errors."""

        def wrapper(self, *args, **kwargs):
            retry_count = 0
            response = None
            while True:
                try:
                    response = method(self, *args, **kwargs)
                    break
                except splunklib.binding.HTTPError as ex:
                    if (ex.status not in RETRY_STATUS_CODES) or (retry_count >= self.max_retry):
                        logger.error(
                            "message=kvstore_error | Error from KVStore:"
                            ' method="{}" collection="{}" error="{}"'.format(method.__name__, self.collection_name, ex)
                        )
                        raise

                    retry_count += 1
                    if retry_count == 1:
                        logger.warning(
                            "message=kvstore_retry | Retrying:"
                            ' method="{}" collection="{}" error="{}"'.format(method.__name__, self.collection_name, ex)
                        )

                    # Exponential backoff
                    delay = (self.backoff_factor) * (2 ** (retry_count - 2))
                    time.sleep(delay)

                    logger.info(
                        "message=kvstore_retry_counter | retry_count={} retry_after_seconds={}".format(
                            retry_count, delay
                        )
                    )

            return response

        return wrapper

    @normalize_exc
    @retry
    def query(self, **kwargs):
        """Query indicators from KVStore."""
        res = self.collection.data.query(**kwargs)
        return res

    @normalize_exc
    def get(self, fields=["_user:0"], query={}):
        """Get all items from kvstore collection using pagination."""
        data = []
        skip = 0
        kwargs = {}

        if query:
            # Note: KVStore doesn't support $in operator that MongoDB has
            kwargs.update({"query": json.dumps(query, separators=(",", ":"))})
        if fields:
            kwargs.update({"fields": ",".join(fields)})

        while True:
            kwargs["skip"] = skip
            items = self.query(**kwargs)

            if len(items) == 0:
                break

            logger.debug(
                "message=kvstore_query_call | Fetched the data from kvstore: collection={} count={}".format(
                    self.collection_name, len(items)
                )
            )

            data += items
            skip += len(items)
            time.sleep(KVSTORE_CALL_DELAY_SEC)

        return data

    @normalize_exc
    def upsert(self, items):
        """Update/Insert (Upsert) items into collection."""
        # Save data batch wise in KV Store
        for chunked_items in chunk(items, self.kvstore_write_limit):
            self.collection.data.batch_save(*chunked_items)
            logger.debug(
                "message=kvstore_upsert_call | Upserted the data to kvstore: collection={} count={}".format(
                    self.collection_name, len(chunked_items)
                )
            )
            time.sleep(KVSTORE_CALL_DELAY_SEC)

    @normalize_exc
    def delete_batch(self, query):
        """Delete the events based on query."""
        logger.debug(
            "message=kvstore_delete_batch_call | Delete batch call to kvstore: collection={}".format(
                self.collection_name
            )
        )
        query = json.dumps(query)
        self.collection.data.delete(query)


class BaseManager:
    """Manager all common operations and provide abstraction over underlying KVStore usage."""

    def get_chunked_queries(self, key, values):
        """Generate queries considering max supportd URI size for HTTP request to KVStore."""
        return (
            [{"$or": [{key: value} for value in values_]} for values_ in chunk(list(values), KVSTORE_URL_CHUNKSIZE)]
            if values
            else []
        )


class AlertManager:
    """Manager all indicators related operations and provide abstraction over underlying KVStore usage."""

    def __init__(self, service):
        """Initialize the object."""
        self.alert_lookup = CollectionManager(service, ALERT_LOOKUP)

    # Decorator
    def expect(type_, default):
        """Return default value if expected type is not found in response."""

        def inner(method):
            def wrapper(self, *args, **kwargs):
                res = method(self, *args, **kwargs)
                if not isinstance(res, type_):
                    res = default
                return res

            return wrapper

        return inner

    @expect(type_=list, default=[])
    def upsert_alerts(self, alerts):
        """Upsert Updated indiators."""
        return self.alert_lookup.upsert(alerts)
