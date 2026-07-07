import os
import sys
import json
import time
import hashlib

import requests
from threatq_const import VERIFY_SSL_KVSTORE
import splunk.rest
from threatq_utils import get_encoded_str
from splunklib.searchcommands import (
    Configuration,
    GeneratingCommand,
    Option,
    dispatch,
    validators,
)
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE,"threatqappforsplunk","aob_py3"))
from solnlib.splunkenv import get_splunkd_uri
import logger_manager as log

logger = log.setup_logging("ta_threatquotient_add_on_threatqoutputlookup")
app_name = __file__.split(os.sep)[-3]


class ThreatIntelKVHandler(object):
    """Threat Intel KV handler class."""

    @staticmethod
    def query(query, session_key, collection, delete=False):
        """Issue as query on threat lookup.

        Args:
            query (dict): key-value pair to search lookup
            session_key (str): Splunk session key
            collection (str): name of the threat lookup
            delete (bool, optional): When set to True deletes the returned
                                     records. Defaults to False.

        Returns:
            tuple: A tuple with response and content
                dict: a dict of HTTP status information
                str: the body content
        """
        method = "GET"

        if delete and query:
            method = "DELETE"

        query = json.dumps(query)
        uri = get_splunkd_uri() + "/services/data/threat_intel/item/{collection}" "?item={query}".format(
            collection=collection, query=query
        )
        headers = {
            "Authorization" : "Splunk {}".format(session_key),
            "Content-Type" : "application/json"
        }
        content = requests.request(
            method,
            uri,
            headers=headers,
            verify=VERIFY_SSL_KVSTORE,
        )
        return content, "_"

    @staticmethod
    def batch_create(records, session_key, collection, include_ts=False, time_field=None):
        """Batch post all the records to threat lookup.

        Args:
            records (list): list of records to post
            session_key (str): Splunk session key
            collection (str): threat lookup name
            include_ts (bool, optional): When set to True adds current time in
                                         the time field for each record.
                                         Defaults to False.
            time_field (str, optional): field name to use to post time with
                                        records. Defaults to _time.

        Returns:
            tuple: A tuple with response and content
                dict: a dict of HTTP status information
                str: the body content
        """
        uri = get_splunkd_uri() + "/services/data/threat_intel/item/{collection}".format(collection=collection)
        if not isinstance(records, list):
            records = [records]

        if not time_field:
            time_field = "_time"

        # Make insert time consistent for this batch of records.
        curr = time.time()

        if include_ts:
            for record in records:
                record[time_field] = curr

        
        headers = {
            "Authorization" : "Splunk {}".format(session_key),
            "Content-Type" : "application/x-www-form-urlencoded"
        }
        content = requests.request(
            "POST",
            uri,
            headers=headers,
            data={"item": json.dumps(records)},
            verify=VERIFY_SSL_KVSTORE,
        )
        return content, "_"


def json_result_reader(iterable, raw_search=False):
    """Export job's json type result's wrapper method for ."""
    for i in iterable:
        # this try except makes sure if splunk sends some crappy string at the
        # end of stream it will continue. This was observed at the end of the
        # iterator always.
        try:
            record = json.loads(i)
        except Exception:
            continue
        if record.get("lastrow") and not record.get("result"):
            return
        yield record["result"]["_raw"] if raw_search else record["result"]


def transform_to_hashset(records, hashfield=None):
    """Convert a list of dicts to single set with keys being identifier for each dict in the list.

    Use this to boost performance for if conditions to
    filter out the records.

    Args:
        records (list): list of dicts
        hashfield (str, optional): field to use for generating key hash.
                                   Defaults to using non processed value of
                                   _key.

    Returns:
        dict: dict with hashfield's hash as keys
    """
    hashset = set()
    for record in records:
        if hashfield:
            hashset.add(
                hashlib.sha1(get_encoded_str(record[hashfield] + "threatq_indicator")).hexdigest()
            )
        else:
            hashset.add(record["_key"])
    return hashset


def update_checkpoint(checkpoint, collection, key_id, latest_time):
    """Update the checkpoint with latest time."""
    logger.info("Updating the checkpoint of {} : {}".format(key_id, latest_time))
    if checkpoint:
        collection.data.update(key_id, json.dumps({"last_run_time": latest_time}))
    else:
        collection.data.insert(json.dumps({"_key": key_id, "last_run_time": latest_time}))


@Configuration(type="reporting")
class ThreatQOutputLookupCommand(GeneratingCommand):
    """ThreatQ output lookup custom command."""

    lookup = Option(name="lookup", require=True)
    ioc_type = Option(name="ioc_type", require=True, validate=validators.List())
    ioc_field = Option(name="ioc_field", require=True)
    chunk_size = Option(
        name="chunk_size", default=20000, validate=validators.Integer(10000, 50000),
    )

    EXPORT_JOB_URI = "{splunkd_uri}/servicesNS/{user}/{app}/search/v2/jobs/export"

    LOCAL_LOOKUP_TO_KVSTORE_MAP = {
        "email_intel": "email_intel",
        "file_intel": "file_intel",
        "domain_intel": "ip_intel",
        "ip_intel": "ip_intel",
        "registry_intel": "registry_intel",
        "service_intel": "service_intel",
        "certificate_intel": "certificate_intel",
        "http_intel": "http_intel",
        "user_intel": "user_intel",
    }

    def generate(self):
        """Generate method of Generating Command."""
        try:
            # getting old checkpoint
            checkpoint_collection = self.service.kvstore["threatq_checkpointer_lookup"]
            key_id = "{}_{}".format(self.lookup, self.ioc_field)
            checkpoint = checkpoint_collection.data.query(query=json.dumps({"_key": key_id}))

            job_export_url = self.EXPORT_JOB_URI.format(
                splunkd_uri=self.metadata.searchinfo.splunkd_uri, user="nobody", app=app_name,
            )
            latest_time_value = int(self.metadata.searchinfo.latest_time)
            if latest_time_value == 0:
                latest_time_value = int(time.time())
            kwargs_export = {
                "output_mode": "json",
                "count": 0,
                "earliest_time": "0",
                "latest_time": latest_time_value,
                "preview": False,
            }
            index_time = "0"
            if checkpoint:
                kwargs_export["earliest_time"] = checkpoint[0].get("last_run_time")
                index_time = checkpoint[0].get("last_run_time")

            # get all iocs without any filters
            all_iocs_searchquery = (
                '| inputlookup master_lookup | where type="{ioc_type}" '
                '| eval _key=sha1(ioc_value."threatq_indicator"), '
                'description="ThreatQ Indicator", '
                'threat_key="threatq_indicator" '
                "| rename ioc_value as {ioc_field}, score as weight "
                "| table _key, {ioc_field}, weight, description, "
                "threat_key".format(
                    ioc_type='" OR type="'.join(self.ioc_type), ioc_field=self.ioc_field,
                )
            )
            kwargs_export.update({"search": all_iocs_searchquery})
            
            headers = {
                "Authorization" : "Splunk {}".format(self.metadata.searchinfo.session_key),
                "Content-Type" : "application/x-www-form-urlencoded"
            }
            params = {"output_mode": "json"}
            content = requests.request(
                "POST",
                job_export_url,
                headers=headers,
                params=params,
                data=kwargs_export,
                verify=VERIFY_SSL_KVSTORE,
            )
            
            all_records = list(json_result_reader(content.text.splitlines()))
            all_records_hash = transform_to_hashset(json_result_reader(content.text.splitlines()))
            logger.info("Got {} records from the `master_lookup`".format(len(all_records)))

            # exit immediately if theres no updates on indicators found
            if not all_records:
                # check if es is installed by making get request to its lookup
                query = {"threat_key": "threatq_indicator"}
                response, _ = ThreatIntelKVHandler.query(
                    query,
                    self.metadata.searchinfo.session_key,
                    self.LOCAL_LOOKUP_TO_KVSTORE_MAP[self.lookup],
                )
                # endpoint returns 404 error if the collection deosnt exist
                if response.status_code != 404:
                    update_checkpoint(
                        checkpoint, checkpoint_collection, key_id, kwargs_export["latest_time"],
                    )
                return
            constrained_iocs_searchquery = (
                '| inputlookup master_lookup | where {ioc_filter} AND type="{ioc_type}" '
                '| eval _key=sha1(ioc_value."threatq_indicator"), '
                'description="ThreatQ Indicator", '
                'threat_key="threatq_indicator" '
                "| rename ioc_value as {ioc_field}, score as weight "
                "| table _key, {ioc_field}, weight, description, "
                "threat_key".format(
                    ioc_filter="".join("index_time>={}".format(index_time))
                    if checkpoint
                    else "(isnull(index_time) OR index_time>=0)",
                    ioc_type='" OR type="'.join(self.ioc_type),
                    ioc_field=self.ioc_field,
                )
            )

            kwargs_export.update({"search": constrained_iocs_searchquery})
            content = requests.request(
                "POST",
                job_export_url,
                headers=headers,
                params=params,
                data=kwargs_export,
                verify=VERIFY_SSL_KVSTORE,
            )
            constrained_results_set = transform_to_hashset(json_result_reader(content.text.splitlines()))
            logger.info(
                "Got {} filtered records from the `master_lookup`".format(
                    len(constrained_results_set)
                )
            )

            # get all iocs from ES KVStore
            es_iocs_searchquery = (
                "| inputlookup {lookup} | where "
                'threat_key="threatq_indicator" AND disabled="0" AND isnotnull({ioc_field})'.format(
                    lookup=self.LOCAL_LOOKUP_TO_KVSTORE_MAP[self.lookup], ioc_field=self.ioc_field
                )
            )
            kwargs_export.update({"search": es_iocs_searchquery})
            content = requests.request(
                "POST",
                job_export_url,
                headers=headers,
                params=params,
                data=kwargs_export,
                verify=VERIFY_SSL_KVSTORE,
            )
            threat_intel_results_set = transform_to_hashset(
                json_result_reader(content.text.splitlines())
            )
            threatq_intel_results = list(json_result_reader(content.text.splitlines()))
            logger.info(
                "Got {} threatq ingested records from the ES lookup".format(
                    len(threat_intel_results_set)
                )
            )

            delete_ioc_set = threat_intel_results_set - all_records_hash

            for i in range(0, len(threatq_intel_results), self.chunk_size):
                if len(threatq_intel_results) < i + self.chunk_size:
                    records = threatq_intel_results[i:]
                else:
                    records = threatq_intel_results[i: i + self.chunk_size]
                records2delete = []
                for record in records:
                    if record["_key"] in delete_ioc_set:
                        kv_pairs = {"disabled": True}
                        record.update(kv_pairs)
                        records2delete.append(record)

                        yield record
                logger.info("Deleting {} entries.".format(len(records2delete)))
                for i in range(4):
                    try:
                        response, _ = ThreatIntelKVHandler.batch_create(
                            records2delete,
                            self.metadata.searchinfo.session_key,
                            self.LOCAL_LOOKUP_TO_KVSTORE_MAP[self.lookup],
                        )
                    except Exception:
                        if i == 3:
                            logger.info(
                                "Failed delete due to kvstore limits. "
                                "Please change the chunk_size to lower value "
                                "to fix this. Exiting."
                            )
                            raise
                        else:
                            logger.info(
                                "Failed delete. Retrying in 5 seconds... "
                                "Attempt({})".format(i + 1)
                            )
                        time.sleep(5)
                    else:
                        break

            for i in range(0, len(all_records), self.chunk_size):
                if len(all_records) < i + self.chunk_size:
                    records = all_records[i:]
                else:
                    records = all_records[i: i + self.chunk_size]
                records2update = []
                for record in records:
                    if record["_key"] in constrained_results_set:
                        kv_pairs = {"disabled": False}
                        record.update(kv_pairs)
                        records2update.append(record)
                    yield record
                logger.info("Updating {} entries.".format(len(records2update)))
                for i in range(4):
                    try:
                        response, _ = ThreatIntelKVHandler.batch_create(
                            records2update,
                            self.metadata.searchinfo.session_key,
                            self.LOCAL_LOOKUP_TO_KVSTORE_MAP[self.lookup],
                        )
                    except Exception:
                        if i == 3:
                            logger.info(
                                "Failed updating due to kvstore limits. "
                                "Please change the chunk_size to lower value "
                                "to fix this. Exiting."
                            )
                            raise
                        else:
                            logger.info(
                                "Failed updating. Retrying in 5 seconds... "
                                "Attempt({})".format(i + 1)
                            )
                        time.sleep(5)
                    else:
                        break
            update_checkpoint(
                checkpoint, checkpoint_collection, key_id, kwargs_export["latest_time"],
            )
        except Exception as e:
            logger.error("ThreatQ 'threatqoutputlookup' command error: %s" % str(e))
            raise


dispatch(ThreatQOutputLookupCommand, sys.argv, sys.stdin, sys.stdout, __name__)
