import ta_intsights_declare     # noqa: F401
import hashlib
import time
import itertools
import random
import json
import os
import sys

from splunklib.binding import HTTPError
from errors import CollectionNotFoundError
from log_manager import setup_logging
import splunk.entity

MASTER_LOOKUP = 'intsights_master_lookup'
MATCHED_LOOKUP = 'intsights_matched_iocs'
LOCK_LOOKUP = 'intsights_lock_lookup'
LOOKUP_METADATA = 'intsights_matched_iocs_metadata'
INTSIGHTS_WHITELIST_CHECKPOINT_LOOKUP = 'intsights_whitelist_checkpointer'

MASTER_ALERTS_LOOKUP = 'intsights_alert_master_lookup'

VULN_MASTER_LOOKUP = 'intsights_vuln_master_lookup'
VULN_MATCHED_LOOKUP = 'intsights_matched_vulnerabilities'
VULN_LOOKUP_METADATA = 'intsights_matched_vuln_metadata'

KVSTORE_CALL_DELAY = 0.3    # in seconds
DEFAULT_MAX_RETRY = 4
DEFAULT_BACKOFF_FACTOR = 30
LOOKUP_LOCK_TIMEOUT = 300     # in seconds
MAX_WAIT_TIME_FOR_LOCK_RELEASE = 5      # in seconds

MIN_KVSTORE_WRITE_LIMIT = 500

logger_name = os.path.splitext(os.path.basename(__file__))[0]
logger = setup_logging(logger_name)


def is_iterator_empty(iterable):
    """Return None if iterator is empty else return iterator as is."""
    try:
        first = next(iterable)
        if first is None:
            return None
        return itertools.chain([first], iterable)
    except StopIteration:
        return None


def chunk(iterable, chunk_size):
    """Split iterable into chunks of given size."""
    for i in range(0, len(iterable), chunk_size):
        yield iterable[i:i + chunk_size]


class ManagementPortProvider:
    """Provides Splunk Management Port to custom validator."""

    def __init__(self, caller_logger=None, session_key=None):
        """Save Management Port in class instance."""
        self.logger = caller_logger or logger
        self.management_port = None
        try:
            self.management_port = splunk.entity.getEntity('/server', 'settings',
                                                           namespace=ta_intsights_declare.ta_name,
                                                           sessionKey=session_key, owner='-')["mgmtHostPort"]
        except Exception as e:
            self.logger.error("Error generated while retrieving the management port: ERROR: {}".format(str(e)))
            sys.exit(1)


class SessionKeyProvider:
    """Provides Splunk session key to custom validator."""

    def __init__(self, caller_logger=None):
        """Save session key in class instance."""
        self.logger = caller_logger or logger
        self.session_key = None
        try:
            self.session_key = sys.stdin.readline().strip()
        except Exception as e:
            self.logger.error(str(e))


class CollectionManager(object):
    """Abstract the KVStore Collection related transactions."""

    def __init__(self, service, collection_name, caller_logger=None,
                 max_retry=DEFAULT_MAX_RETRY, backoff_factor=DEFAULT_BACKOFF_FACTOR):
        """Initialize the object."""
        self.logger = caller_logger or logger
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
                raise CollectionNotFoundError(self.collection)
            self._collection = self.service.kvstore[self.collection_name]
        return self._collection

    @property
    def kvstore_write_limit(self):
        """Return kvstore write limit defined in limits.conf file."""
        if self._kvstore_write_limit is None:
            try:
                self._kvstore_write_limit = int(self.service.confs['limits']['kvstore'].content.get(
                    'max_documents_per_batch_save', MIN_KVSTORE_WRITE_LIMIT))
            except Exception:
                self._kvstore_write_limit = MIN_KVSTORE_WRITE_LIMIT
        return self._kvstore_write_limit

    # Decorator
    def retry(method):
        """Retry mechanism to avoid temporary errors."""
        def wrapper(self, *args, **kwargs):
            retry_count = 0
            while True:
                try:
                    response = method(self, *args, **kwargs)
                    break
                except Exception as ex:
                    if retry_count >= self.max_retry:
                        raise ex

                    retry_count += 1
                    if retry_count == 1:
                        self.logger.warning('Method="{}()" Args="{}" Kwargs="{}" Collection="{}" Error="{}"'.format(
                            method.__name__, args, kwargs, self.collection_name, ex))

                    # Exponential backoff
                    delay = (self.backoff_factor) * (2 ** retry_count - 1)
                    time.sleep(delay)

                    self.logger.info('RetryCount={} RetryAfterSecond={}'.format(retry_count, delay))

            return response
        return wrapper

    @retry
    def fetch(self, **kwargs):
        """Fetch IOCs from KVStore."""
        return self.collection.data.query(**kwargs)

    def get(self, fields=[], query={}):
        """Get all items from kvstore collection using pagination."""
        data = []
        skip = 0
        kwargs = {}

        if query:
            kwargs.update({'query': json.dumps(query, ensure_ascii=False)})
        if fields:
            kwargs.update({'fields': ','.join(fields)})
        kwargs.update({'sort': '_key'})

        while True:
            kwargs['skip'] = skip
            items = self.fetch(**kwargs)

            if len(items) == 0:
                break

            data += items
            skip += len(items)
            time.sleep(KVSTORE_CALL_DELAY)

        return data

    def query_by_id(self, id):
        """Returns items which are requested."""
        try:
            return self.collection.data.query_by_id(id)
        except HTTPError as ex:
            if ex.status == 404:
                return None
            else:
                raise ex

    def upsert(self, items):
        """Update/Insert (Upsert) items into collection."""
        # Save data batch wise in KV Store
        for chunked_items in chunk(items, self.kvstore_write_limit):
            self.collection.data.batch_save(*chunked_items)

    def insert(self, item):
        """Insert item into collection."""
        res = self.collection.data.insert(json.dumps(item, ensure_ascii=False))
        return res.get('_key')

    def delete_by_id(self, id):
        """Return id if item deleted else return None."""
        try:
            return self.collection.data.delete_by_id(id)
        except HTTPError as ex:
            if ex.status == 404:
                return None
            else:
                raise ex

    def delete_batch(self, query):
        """Delete the IOC based on query."""
        query = json.dumps(query, ensure_ascii=False)
        self.collection.data.delete(query)


class IOCsManager(object):
    """Handle all IOCs related transactions."""

    def __init__(self, service, caller_logger=None,
                 backoff_factor=DEFAULT_BACKOFF_FACTOR, max_retry=DEFAULT_MAX_RETRY):
        """Initialize the object."""
        self.backoff_factor = backoff_factor
        self.max_retry = max_retry
        self.logger = caller_logger or logger
        self.service = service
        self._matched_iocs = None
        self._all_iocs = None
        self._intsights_whitelist_checkpoint = None

    @property
    def matched_iocs(self):
        """Set matched_iocs as propery."""
        if self._matched_iocs is None:
            self._matched_iocs = CollectionManager(
                self.service, MATCHED_LOOKUP, self.logger, self.max_retry, self.backoff_factor)
        return self._matched_iocs

    @property
    def all_iocs(self):
        """Set matched_iocs as propery."""
        if self._all_iocs is None:
            self._all_iocs = CollectionManager(
                self.service, MASTER_LOOKUP, self.logger, self.max_retry, self.backoff_factor)
        return self._all_iocs

    @property
    def intsights_whitelist_checkpoint(self):
        """Set this as property."""
        if self._intsights_whitelist_checkpoint is None:
            self._intsights_whitelist_checkpoint = CollectionManager(
                self.service, INTSIGHTS_WHITELIST_CHECKPOINT_LOOKUP, self.logger, self.max_retry, self.backoff_factor)
        return self._intsights_whitelist_checkpoint

    @classmethod
    def add_key_field(cls, iocs):
        """Add _key field to IOCs."""
        for ioc in iocs:
            md5_hash = hashlib.md5(ioc['value'].encode()).hexdigest()
            ioc.update({'_key': md5_hash})
        return iocs

    def get_all_iocs_by_type(self, types, fields=[]):
        """Get all IOCs of particular type from lookup."""
        query = {"$or": [{"type": type_} for type_ in types]} if types else {}
        return self.all_iocs.get(query=query, fields=fields)

    def get_matched_iocs(self, fields=[]):
        """Get matched IOCs from lookup."""
        return self.matched_iocs.get(fields=fields)

    def update_matched_iocs(self, iocs):
        """Update iocs into matched IOC lookup."""
        iocs = self.add_key_field(iocs)
        self.matched_iocs.upsert(iocs)

    def delete_from_lookups(self, query):
        """Delete whitelist iocs from lookups."""
        self.all_iocs.delete_batch(query)
        self.matched_iocs.delete_batch(query)

    def delete_from_master_lookup(self, query):
        """Delete data from master lookup."""
        self.all_iocs.delete_batch(query)

    def delete_from_matched_lookup(self, query):
        """Delete data from matched lookup."""
        self.matched_iocs.delete_batch(query)

    def get_intsights_whitelist_checkpoint(self, id):
        """Fetching the checkpoint for whitelisted iocs."""
        return self.intsights_whitelist_checkpoint.query_by_id(id)

    def update_whitelist_checkpoint(self, data):
        """Updating whitelist checkpoint."""
        self.intsights_whitelist_checkpoint.upsert(data)


class AlertsManager(object):
    """Handle all Alerts related transactions."""

    def __init__(self, service, caller_logger=None,
                 backoff_factor=DEFAULT_BACKOFF_FACTOR, max_retry=DEFAULT_MAX_RETRY):
        """Initialize the object."""
        self.backoff_factor = backoff_factor
        self.max_retry = max_retry
        self.logger = caller_logger or logger
        self.service = service
        self._all_alerts = None

    @property
    def all_alerts(self):
        """Set all_alerts as propery."""
        if self._all_alerts is None:
            self._all_alerts = CollectionManager(
                self.service, MASTER_ALERTS_LOOKUP, self.logger, self.max_retry, self.backoff_factor)
        return self._all_alerts

    def delete_from_master_lookup(self, query):
        """Delete data from master lookup."""
        self.all_alerts.delete_batch(query)


class CollectionLock(object):
    """Provide custom locking functionality for KVStore collection."""

    def __init__(self, service, collection_name, caller_logger=None):
        """Initialize the object."""
        self.logger = caller_logger or logger
        self.collection_name = collection_name
        self.lock_lookup = CollectionManager(service, LOCK_LOOKUP, self.logger)
        self.lock = {'collection': self.collection_name}
        self.query = {'collection': self.collection_name}
        self.key = ''

    def acquire(self):
        """
        Acquire lock.

        To avoid race condition while locking from multiple processes,
        we will always recheck if anyone has locked meanwhile we do, and if found so,
        we will delete our lock and will retry locking.
        """
        while True:
            try:
                locks = self.lock_lookup.get(query=self.query)

                """
                Remove if any timed out lock exists and
                wait for other locks release if exists
                """
                still_locked = False
                for lock in locks:
                    lock_time = float(lock['lockTime'])
                    if (time.time() - lock_time) > LOOKUP_LOCK_TIMEOUT:
                        self.lock_lookup.delete_by_id(lock['_key'])
                    else:
                        still_locked = True

                if still_locked:
                    time.sleep(random.randint(1, MAX_WAIT_TIME_FOR_LOCK_RELEASE))
                    continue
            except Exception:
                pass

            self.lock['lockTime'] = time.time()
            self.key = self.lock_lookup.insert(self.lock)

            # Check if meanwhile anyone acquired lock
            locks = self.lock_lookup.get(query=self.query)

            if len(locks) == 1:
                return
            else:
                # Retry if any older lock exists
                locked = True
                for lock in locks:
                    if lock['_key'] == self.key:
                        continue
                    if float(lock['lockTime']) < self.lock['lockTime']:
                        self.release()
                        locked = False
                        break
                if locked:
                    return
                else:
                    continue

    def release(self):
        """Release lock."""
        self.lock_lookup.delete_by_id(self.key)


class MatchedIOCsLock(CollectionLock):
    """Matched IOCs locking functionality."""

    def __init__(self, service, caller_logger):
        """Initialize the object."""
        super(MatchedIOCsLock, self).__init__(service, MATCHED_LOOKUP, caller_logger)


def update_last_scan_time(service, last_scan_time, metadata_lookup, matched_lookup):
    """Update last scan time for matched lookup."""
    CollectionManager(service, metadata_lookup).upsert(
        [{'lastScanTime': last_scan_time, '_key': matched_lookup}]
    )


def process_latest_time(latest_time):
    """Handle empty latest time when Time Range is 'All Time'."""
    if not latest_time:
        return time.time()
    else:
        return float(latest_time)


class VulnerabilitiesManager(object):
    """Handle all Vulnerabilities related transactions."""

    def __init__(self, service, caller_logger=None,
                 backoff_factor=DEFAULT_BACKOFF_FACTOR, max_retry=DEFAULT_MAX_RETRY):
        """Initialize the object."""
        self.backoff_factor = backoff_factor
        self.max_retry = max_retry
        self.logger = caller_logger or logger
        self.service = service
        self._matched_vulns = None
        self._all_vulns = None

    @property
    def matched_vulns(self):
        """Set matched_vulns as propery."""
        if self._matched_vulns is None:
            self._matched_vulns = CollectionManager(
                self.service, VULN_MATCHED_LOOKUP, self.logger, self.max_retry, self.backoff_factor)
        return self._matched_vulns

    @property
    def all_vulns(self):
        """Set matched_vulns as propery."""
        if self._all_vulns is None:
            self._all_vulns = CollectionManager(
                self.service, VULN_MASTER_LOOKUP, self.logger, self.max_retry, self.backoff_factor)
        return self._all_vulns

    @classmethod
    def add_key_field(cls, vulns):
        """Add _key field to vulnerabilities."""
        for vuln in vulns:
            md5_hash = hashlib.md5(vuln['cveId'].encode()).hexdigest()
            vuln.update({'_key': md5_hash})
        return vulns

    def get_all_vulns(self, fields=[]):
        """Get all vulnerabilities from lookup."""
        return self.all_vulns.get(fields=fields)

    def get_matched_vulns(self, fields=[]):
        """Get matched vulnerabilities from lookup."""
        return self.matched_vulns.get(fields=fields)

    def get_unmatched_vulns(self, fields=[]):
        """Get unmatched vulnerabilities from lookup."""
        matched_vulns = {ind["cveId"]: True for ind in self.get_matched_vulns(fields=['cveId'])}
        unmatched_vulns = [vuln for vuln in self.get_all_vulns(fields=fields)
                           if not matched_vulns.get(vuln["cveId"], False)]
        return unmatched_vulns

    def update_matched_vulns(self, vulns):
        """Update vulnerabilitiess into matched vulnerabilities lookup."""
        vulns = self.add_key_field(vulns)
        self.matched_vulns.upsert(vulns)

    def delete_from_lookups(self, query):
        """Delete whitelist vulnerabilities from lookups."""
        self.all_vulns.delete_batch(query)
        self.matched_vulns.delete_batch(query)

    def delete_from_master_lookup(self, query):
        """Delete data from master lookup."""
        self.all_vulns.delete_batch(query)

    def delete_from_matched_lookup(self, query):
        """Delete data from matched lookup."""
        self.matched_vulns.delete_batch(query)


class MatchedVulnerabilitiesLock(CollectionLock):
    """Matched vulnerabilities locking functionality."""

    def __init__(self, service, caller_logger):
        """Initialize the object."""
        super(MatchedVulnerabilitiesLock, self).__init__(service, VULN_MATCHED_LOOKUP, caller_logger)
