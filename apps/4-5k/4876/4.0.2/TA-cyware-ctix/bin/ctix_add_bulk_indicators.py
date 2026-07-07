"""Add bulk indicators to CTIX Intel Exchange."""

import ta_cyware_ctix_declare  # noqa: F401

import splunk.clilib.cli_common
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
import ta_cyware_ctix.logging_helper as logging_helper
import ta_cyware_ctix.proxy_helper as proxy_helper
import ta_cyware_ctix.ssl_helper as ssl_helper
import ta_cyware_ctix.conf_helper as conf_helper
from ta_cyware_ctix.ctix_exceptions import (
    CTIXAPIError, CTIXConnectionError, CTIXTimeoutError,
    CTIXConfigurationError, CTIXValidationError
)
from ta_cyware_ctix.ctix_connector import CTIXConnector as BaseCTIXConnector
from ta_cyware_ctix.constants import (
    BULK_INDICATOR_BATCH_SIZE, BULK_INDICATOR_MAX_INDICATOR_LENGTH, BULK_INDICATOR_MAX_FETCH_LIMIT, USER_AGENT
)

import json
import sys
import time
import traceback
from ta_cyware_ctix.aob_py3 import requests


logger = logging_helper.get_logger("add_bulk_indicators")
MGMT_PORT = splunk.clilib.cli_common.getMgmtUri().split(":")[-1]


class CTIXConnector(BaseCTIXConnector):
    """CTIX connector for add bulk indicators operations."""

    def _filter_indicators(self, ioc_values):
        """Filter out indicators exceeding max length."""
        filtered_ioc_values = []
        skipped_count = 0

        for ioc in ioc_values:
            ioc_str = str(ioc)
            if len(ioc_str) > BULK_INDICATOR_MAX_INDICATOR_LENGTH:
                skipped_count += 1
                logger.warning(
                    f"Skipping indicator (length: {len(ioc_str)} > {BULK_INDICATOR_MAX_INDICATOR_LENGTH} chars): "
                    f"{ioc_str[:100]}..." if len(ioc_str) > 100 else ioc_str
                )
            else:
                filtered_ioc_values.append(ioc)

        if skipped_count > 0:
            logger.info(
                f"Skipped {skipped_count} indicator(s) exceeding "
                f"{BULK_INDICATOR_MAX_INDICATOR_LENGTH} characters"
            )

        return filtered_ioc_values, skipped_count

    def _build_batch_payload(self, batch, source_name, tlp, confidence, tags, description, collection_name):
        """Build payload for a batch of indicators."""
        return {
            "ioc_values": batch,
            "metadata": {
                "tlp": tlp,
                "confidence": int(confidence),
                "tags": tags,
                "description": description
            },
            "source": {
                "source_name": source_name
            },
            "collection": {
                "collection_name": collection_name
            }
        }

    def _process_batch_response(self, response, batch_num, aggregated_result):
        """Process batch response and update aggregated results."""
        if response.ok:
            try:
                batch_result = response.json()
                aggregated_result["batches_processed"] += 1
                aggregated_result["created"] += batch_result.get("created", 0)
                aggregated_result["updated"] += batch_result.get("updated", 0)
                aggregated_result["already_exists"] += batch_result.get("already_exists", 0)
                aggregated_result["failed"] += batch_result.get("failed", 0)

                logger.info(
                    f"Batch {batch_num + 1} completed."
                )
            except json.JSONDecodeError:
                logger.warning(f"Batch {batch_num + 1} returned non-JSON response")
                aggregated_result["batches_processed"] += 1
        else:
            raise CTIXAPIError(
                f"Cyware API Error (Batch {batch_num + 1}) - "
                f"Status Code: {response.status_code}, Message: {response.text}"
            )

    def add_indicators_bulk(self, ioc_values, source_name, tlp, confidence, tags, description, collection_name):
        """
        Add indicators in bulk using CTIX bulk-lookup-and-create API.

        Handles pagination by splitting into batches of 1000 IOCs per call.

        Args:
            ioc_values: List of indicator values
            source_name: Name of the source
            tlp: TLP marking (CLEAR, GREEN, AMBER, AMBER_STRICT, RED)
            confidence: Confidence score (0-100)
            tags: List of tag strings
            description: Description for indicators
            collection_name: Collection name for grouping

        Returns:
            dict: Aggregated API response with totals
        """
        logger.info("Add bulk indicators action started")
        logger.info(f"Processing {len(ioc_values)} indicators from source: {source_name}")

        try:
            filtered_ioc_values, skipped_count = self._filter_indicators(ioc_values)
            total_iocs_original = len(ioc_values)
            total_iocs = len(filtered_ioc_values)

            if total_iocs == 0:
                logger.warning("No valid indicators to process after filtering")
                return {
                    "total_iocs_original": total_iocs_original,
                    "total_iocs": 0,
                    "skipped": skipped_count,
                    "batches_processed": 0,
                    "created": 0,
                    "updated": 0,
                    "already_exists": 0,
                    "failed": 0
                }

            # Initialize aggregated results
            aggregated_result = {
                "total_iocs_original": total_iocs_original,
                "total_iocs": total_iocs,
                "skipped": skipped_count,
                "batches_processed": 0,
                "created": 0,
                "updated": 0,
                "already_exists": 0,
                "failed": 0
            }

            # Split IOCs into batches of 1000
            logger.info(f"Starting batch processing with {BULK_INDICATOR_BATCH_SIZE} indicators per batch")
            for batch_num in range(0, total_iocs, BULK_INDICATOR_BATCH_SIZE):
                batch = filtered_ioc_values[batch_num:batch_num + BULK_INDICATOR_BATCH_SIZE]
                batch_size = len(batch)

                logger.info(
                    f"Processing batch {batch_num//BULK_INDICATOR_BATCH_SIZE + 1} "
                    f"with {batch_size} IOCs (total: {total_iocs})"
                )

                url = f"{self.api_url}/ingestion/threat-data/bulk-lookup-and-create/"
                auth_params = self.auth()
                auth_params["enrichment"] = "true"
                auth_params["create"] = "true"

                headers = {
                    'Content-Type': 'application/json',
                    'User-Agent': USER_AGENT,
                }

                payload = self._build_batch_payload(
                    batch, source_name, tlp, confidence, tags, description, collection_name
                )

                batch_number = batch_num//BULK_INDICATOR_BATCH_SIZE + 1

                proxy_config = proxy_helper.get_proxy_config(self.session_key, logger)
                ssl_verify = ssl_helper.get_ssl_verify(self.session_key, logger)

                logger.info(f"Calling API for batch {batch_number}")
                logger.debug(f"API URL: {url}")
                logger.debug(f"Batch size: {batch_size}")

                response = requests.post(
                    url=url,
                    params=auth_params,
                    headers=headers,
                    json=payload,
                    proxies=proxy_config,
                    verify=ssl_verify,
                    timeout=180
                )
                self._process_batch_response(response, batch_num//BULK_INDICATOR_BATCH_SIZE, aggregated_result)

                # Log progress for each batch
                total_batches = (total_iocs + BULK_INDICATOR_BATCH_SIZE - 1) // BULK_INDICATOR_BATCH_SIZE
                logger.info(
                    f"Processed batch {batch_number}/{total_batches} "
                    f"({batch_number/total_batches*100:.1f}% complete)"
                )

            logger.info(f"All batches processed. Total: {aggregated_result['batches_processed']}")
            logger.info("Returning aggregated results to UI")
            return aggregated_result

        except requests.exceptions.Timeout as e:
            raise CTIXTimeoutError("Request to CTIX API timed out after 180 seconds") from e
        except requests.exceptions.ConnectionError as e:
            raise CTIXConnectionError(f"Could not connect to CTIX API: {str(e)}") from e
        except (CTIXAPIError, CTIXTimeoutError, CTIXConnectionError):
            raise
        except Exception as e:
            logger.error(
                f"Error adding indicators to Intel Exchange: {str(e)}\n{traceback.format_exc()}"
            )
            raise CTIXAPIError(f"Error adding indicators to Intel Exchange: {str(e)}") from e


@Configuration()
class CTIXAddBulkIndicatorsCommand(GeneratingCommand):
    """Splunk custom search command to add bulk indicators to CTIX."""

    source_type = Option(require=False, default="index")
    index_name = Option(require=False, default=None)
    sourcetype = Option(require=False, default=None)
    cim_datamodel_name = Option(require=False, default=None)
    cim_field_name = Option(require=False, default=None)
    datamodel_name = Option(require=False, default=None)
    lookup_name = Option(require=False, default=None)
    field_name = Option(require=False, default=None)
    field_name_custom_datamodel = Option(require=False, default=None)
    source_name = Option(require=False, default="Splunk")
    description = Option(require=False, default="")
    tlp = Option(require=False, default="AMBER")
    confidence_score = Option(require=False, default="100")
    tags = Option(require=False, default="")
    splunk_account = Option(require=True)
    collection_name = Option(require=False, default="Splunk Collection")
    enable_automation = Option(require=False, default=None)
    automation_source_name = Option(require=False, default=None)

    def _build_search_query_index(self, index_name, sourcetype, field_name):
        """Build search query for index."""
        search_query = f"search index={index_name}"
        if sourcetype:
            search_query += f" sourcetype={sourcetype}"
        search_query += f" | dedup {field_name} | table {field_name}"
        return search_query

    def _create_search_job(self, headers, search_query, earliest_time, latest_time):
        """Create a Splunk search job and return the job SID."""
        create_job_url = f"https://localhost:{MGMT_PORT}/services/search/jobs"
        job_data = {
            "search": search_query,
            "earliest_time": earliest_time,
            "latest_time": latest_time,
            "output_mode": "json"
        }

        logger.info("Creating search job...")
        job_response = requests.post(create_job_url, headers=headers, data=job_data, verify=False, timeout=60)

        if job_response.status_code != 201:
            logger.error(f"Failed to create search job: {job_response.status_code} - {job_response.text}")
            raise CTIXAPIError(f"Failed to create search job: {job_response.status_code}")

        job_sid = job_response.json().get("sid")
        logger.info(f"Search job created: {job_sid}")
        return job_sid

    def _wait_for_job_completion(self, headers, job_sid, max_wait_time=600):
        """Wait for search job to complete."""
        job_status_url = f"https://localhost:{MGMT_PORT}/services/search/jobs/{job_sid}"
        wait_interval = 2
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            status_response = requests.get(
                job_status_url,
                headers=headers,
                params={"output_mode": "json"},
                verify=False,
                timeout=30
            )

            if status_response.status_code != 200:
                raise CTIXAPIError(f"Failed to check job status: {status_response.status_code}")

            status_data = status_response.json()
            job_state = status_data.get("entry", [{}])[0].get("content", {}).get("dispatchState")

            if job_state == "DONE":
                result_count = status_data.get("entry", [{}])[0].get("content", {}).get("resultCount", 0)
                logger.info(f"Search job completed. Total results: {result_count}")
                return
            elif job_state == "FAILED":
                raise CTIXAPIError("Search job failed")

            time.sleep(wait_interval)
            elapsed_time += wait_interval

        logger.error(f"Search job timed out after {max_wait_time} seconds")
        raise CTIXAPIError(f"Search job timed out after {max_wait_time} seconds")

    def _fetch_job_results_paginated(self, headers, job_sid):
        """Fetch search job results in 1000-record chunks."""
        all_indicators = []
        offset = 0
        chunk_size = 1000
        results_url = f"https://localhost:{MGMT_PORT}/services/search/jobs/{job_sid}/results"

        while offset < BULK_INDICATOR_MAX_FETCH_LIMIT:
            logger.info(f"Fetching results: offset={offset}, count={chunk_size}")

            results_response = requests.get(
                results_url,
                headers=headers,
                params={
                    "output_mode": "json",
                    "offset": offset,
                    "count": chunk_size
                },
                verify=False,
                timeout=120
            )

            if results_response.status_code != 200:
                logger.error(f"Failed to fetch results: {results_response.status_code}")
                raise CTIXAPIError(f"Failed to fetch results: {results_response.status_code}")

            chunk_data = results_response.json()
            results = chunk_data.get("results", [])

            if not results:
                logger.info("No more results to fetch")
                break

            logger.info(f"Fetched {len(results)} results in this chunk")
            all_indicators.extend(results)
            offset += len(results)

        if offset >= BULK_INDICATOR_MAX_FETCH_LIMIT:
            logger.warning(f"Reached maximum fetch limit of {BULK_INDICATOR_MAX_FETCH_LIMIT} indicators")

        logger.info(f"Total indicators fetched: {len(all_indicators)}")
        return all_indicators

    def _execute_search_paginated(self, session_key, search_query, earliest_time="0", latest_time="now"):
        """Execute Splunk search with pagination to handle large result sets."""
        headers = {"Authorization": f"Splunk {session_key}"}

        try:
            job_sid = self._create_search_job(headers, search_query, earliest_time, latest_time)
            self._wait_for_job_completion(headers, job_sid)
            return self._fetch_job_results_paginated(headers, job_sid)

        except requests.exceptions.Timeout as e:
            logger.error(f"Request timed out: {str(e)}")
            raise CTIXAPIError("Request timed out while fetching data")
        except CTIXAPIError:
            raise
        except Exception as e:
            logger.error(f"Error in paginated search: {str(e)}\n{traceback.format_exc()}")
            raise CTIXAPIError(f"Error executing search: {str(e)}")

    def _execute_search(self, session_key, search_query, earliest_time="0", latest_time="now"):
        """Execute Splunk search and return response."""
        url = f"https://localhost:{MGMT_PORT}/services/search/jobs/export"
        headers = {"Authorization": f"Splunk {session_key}"}
        data = {
            "search": search_query,
            "output_mode": "json",
            "earliest_time": earliest_time,
            "latest_time": latest_time
        }

        try:
            response = requests.post(url, headers=headers, data=data, verify=False, timeout=600)
        except requests.exceptions.Timeout:
            logger.error(
                f"Search timed out after 600 seconds. Query: {search_query[:200]}... "
                "Consider limiting the data using time filters or adding '| head 100000' to your query."
            )
            raise CTIXAPIError(
                "Search timed out after 10 minutes. The datamodel/index may have too much data. "
                "Please narrow your search using time filters or contact your administrator."
            )

        if response.status_code != 200:
            logger.error(f"Search failed: {response.status_code} - {response.text}")
            raise CTIXAPIError(f"Search failed with status {response.status_code}")

        return response

    def _extract_field_value(self, result, field_name):
        """Extract field value from a single result row."""
        # Handle both regular search results and datamodel results
        if "result" in result:
            # Standard search results
            value = result["result"].get(field_name)
        elif field_name in result:
            # Direct field value (e.g., from datamodel queries)
            value = result.get(field_name)
        else:
            return None

        if value and str(value).strip():
            return str(value).strip()
        return None

    def _parse_search_results(self, response_text, field_name):
        """Parse search results and extract field values."""
        indicators = []
        for line in response_text.strip().split("\n"):
            if not line:
                continue

            try:
                result = json.loads(line)
                value = self._extract_field_value(result, field_name)
                if value:
                    indicators.append(value)
            except json.JSONDecodeError:
                continue

        return list(set(indicators))

    def _parse_paginated_results(self, results_list, field_name):
        """Parse paginated search results and extract field values."""
        indicators = []
        for result in results_list:
            value = result.get(field_name)
            if value and str(value).strip():
                indicators.append(str(value).strip())

        return list(set(indicators))

    def _fetch_from_index(self, session_key, index_name, sourcetype, field_name, earliest_time="0"):
        """Fetch indicator values from a Splunk index using REST API."""
        try:
            logger.info(
                f"Fetching from index: {index_name}, sourcetype: {sourcetype}, field: {field_name}, "
                f"earliest_time: {earliest_time}"
            )

            search_query = self._build_search_query_index(index_name, sourcetype, field_name)
            logger.info(f"Index search query: {search_query}")

            results = self._execute_search_paginated(session_key, search_query, earliest_time=earliest_time)
            indicators = self._parse_paginated_results(results, field_name)

            logger.info(f"Fetched {len(indicators)} unique indicators from index")
            return indicators

        except CTIXAPIError:
            raise
        except Exception as e:
            logger.error(
                f"Error fetching from index: {str(e)}\n{traceback.format_exc()}"
            )
            raise CTIXAPIError(f"Error fetching from index: {str(e)}") from e

    def _fetch_from_custom_datamodel(self, session_key, datamodel_name, field_name, earliest_time="0"):
        """Fetch indicator values from custom_datamodel datamodel using REST API."""
        try:
            logger.info(
                f"Fetching from custom_datamodel datamodel: {datamodel_name}, field: {field_name}, "
                f"earliest_time: {earliest_time}"
            )

            # Extract simple field alias from full field path
            # Example: Cisco_Catalyst_Dataset.Cisco_Catalyst_SDWAN_Tunnel_Health.sdwan_tunnel_health_remote_system_ip -> sdwan_tunnel_health_remote_system_ip  # noqa: E501
            field_alias = field_name.split(".")[-1] if "." in field_name else field_name

            # Use tstats for accelerated datamodel queries
            search_query = (
                f"| tstats values({field_name}) AS {field_alias} "
                f"FROM datamodel={datamodel_name} by {field_name} "
                f"| dedup {field_name} | table {field_alias}"
            )
            logger.info(f"custom_datamodel search query: {search_query}")

            results = self._execute_search_paginated(session_key, search_query, earliest_time=earliest_time)
            indicators = self._parse_paginated_results(results, field_alias)

            logger.info(f"Fetched {len(indicators)} unique indicators from custom_datamodel")
            return indicators

        except CTIXAPIError:
            raise
        except Exception as e:
            logger.error(f"Error fetching from custom_datamodel: {str(e)}\n{traceback.format_exc()}")
            raise CTIXAPIError(f"Error fetching from custom_datamodel: {str(e)}") from e

    def _fetch_from_cim(self, session_key, cim_datamodel_name, cim_field_name, earliest_time="0"):
        """Fetch indicator values from CIM datamodel using REST API."""
        try:
            logger.info(
                f"Fetching from CIM datamodel: {cim_datamodel_name}, field: {cim_field_name}, "
                f"earliest_time: {earliest_time}"
            )

            # Use simple datamodel query
            search_query = f"| from datamodel {cim_datamodel_name} | dedup {cim_field_name} | table {cim_field_name}"
            logger.info(f"CIM search query: {search_query}")

            results = self._execute_search_paginated(session_key, search_query, earliest_time=earliest_time)
            indicators = self._parse_paginated_results(results, cim_field_name)

            logger.info(f"Fetched {len(indicators)} unique indicators from CIM")
            return indicators

        except CTIXAPIError:
            raise
        except Exception as e:
            logger.error(
                f"Error fetching from CIM: {str(e)}\n{traceback.format_exc()}"
            )
            raise CTIXAPIError(f"Error fetching from CIM: {str(e)}") from e

    def _get_checkpoint_from_kv_store(self, session_key, automation_source_name):
        """Retrieve checkpoint time from KVStore for incremental collection."""
        try:
            from ta_cyware_ctix.kvstore_helper import KvStoreClient

            kvstore_client = KvStoreClient(session_key=session_key)
            service = kvstore_client._connect_splunk_service()

            collection_name = "ctix_bulk_indicator_sources"
            collection = service.kvstore[collection_name]

            # Query for the source by name
            query = json.dumps({"source_name": automation_source_name})
            results = collection.data.query(query=query)

            if results:
                checkpoint_time = results[0].get("checkpoint_time", 0)
                logger.info(f"Retrieved checkpoint for '{automation_source_name}': {checkpoint_time}")
                return checkpoint_time
            else:
                logger.info(f"No checkpoint found for '{automation_source_name}', starting from beginning")
                return 0

        except Exception as e:
            logger.error(f"Error retrieving checkpoint: {str(e)}\n{traceback.format_exc()}")
            return 0

    def _update_checkpoint_in_kv_store(self, session_key, automation_source_name, new_checkpoint_time):
        """Update checkpoint time in KVStore after successful ingestion."""
        try:
            from ta_cyware_ctix.kvstore_helper import KvStoreClient

            kvstore_client = KvStoreClient(session_key=session_key)
            service = kvstore_client._connect_splunk_service()

            collection_name = "ctix_bulk_indicator_sources"
            collection = service.kvstore[collection_name]

            # Query for the source by name
            query = json.dumps({"source_name": automation_source_name})
            results = collection.data.query(query=query)

            if results:
                key = results[0].get("_key")
                current_time = int(time.time())

                # Get the existing record to preserve all fields
                existing_record = results[0]

                # Update only the checkpoint-related fields
                existing_record["checkpoint_time"] = new_checkpoint_time
                existing_record["last_run"] = current_time
                existing_record["last_status"] = "success"
                existing_record["updated_time"] = current_time

                # Remove _key and _user from the record before updating
                existing_record.pop("_key", None)
                existing_record.pop("_user", None)

                # Update the complete record with all fields
                collection.data.update(key, json.dumps(existing_record))
                logger.info(f"Updated checkpoint for '{automation_source_name}': {new_checkpoint_time}")
                return True
            else:
                logger.warning(f"Source '{automation_source_name}' not found in KVStore for checkpoint update")
                return False

        except Exception as e:
            logger.error(f"Error updating checkpoint: {str(e)}\n{traceback.format_exc()}")
            return False

    def _save_to_kv_store(self, session_key):
        """Save source configuration to KV Store for automated ingestion."""
        try:
            from ta_cyware_ctix.kvstore_helper import KvStoreClient

            # Use the existing KvStoreClient which properly handles hostname resolution
            # This avoids "Address family not supported by protocol" errors
            kvstore_client = KvStoreClient(session_key=session_key)
            service = kvstore_client._connect_splunk_service()

            collection_name = "ctix_bulk_indicator_sources"
            collection = service.kvstore[collection_name]

            current_time = int(time.time())

            # Set field name and datamodel name based on source type
            if self.source_type == "cim":
                field_name = self.cim_field_name
                datamodel_name = self.cim_datamodel_name
            elif self.source_type == "custom_datamodel":
                field_name = self.field_name_custom_datamodel
                datamodel_name = self.datamodel_name
            else:
                field_name = self.field_name
                datamodel_name = self.datamodel_name or ""

            record = {
                "source_name": self.automation_source_name or f"{self.source_name} - Automated",
                "source_type": self.source_type,
                "index_name": self.index_name or None,
                "sourcetype": self.sourcetype or None,
                "datamodel_name": datamodel_name or None,
                "lookup_name": self.lookup_name or None,
                "field_name": field_name or None,
                "source_name_metadata": self.source_name,
                "tlp": self.tlp,
                "confidence": int(self.confidence_score),
                "tags": self.tags or None,
                "description": self.description or None,
                "collection_name": self.collection_name or None,
                "splunk_account": self.splunk_account,
                "status": "active",
                "checkpoint_time": current_time,
                "checkpoint_row": 0,
                "last_run": current_time,
                "last_status": "success",
                "created_time": current_time,
                "updated_time": current_time
            }

            result = collection.data.insert(json.dumps(record))
            logger.info(f"Source saved to KV Store with key: {result['_key']}")

            return {
                "status": "success",
                "message": f"Source configuration saved for automated ingestion (Key: {result['_key']})",
                "key": result["_key"]
            }

        except Exception as e:
            logger.error(
                f"Error saving to KV Store: {str(e)}\n{traceback.format_exc()}"
            )
            return {
                "status": "error",
                "message": f"Failed to save source configuration: {str(e)}"
            }

    def _fetch_from_lookup(self, session_key, lookup_name, field_name):
        """Fetch indicator values from a Splunk lookup using REST API."""
        try:
            logger.info(f"Fetching from lookup: {lookup_name}, field: {field_name}")

            search_query = f"| inputlookup {lookup_name} | dedup {field_name} | table {field_name}"
            logger.info(f"Lookup search query: {search_query}")

            results = self._execute_search_paginated(session_key, search_query)
            indicators = self._parse_paginated_results(results, field_name)

            logger.info(f"Fetched {len(indicators)} unique indicators from lookup")
            return indicators

        except CTIXAPIError:
            raise
        except Exception as e:
            logger.error(
                f"Error fetching from lookup: {str(e)}\n{traceback.format_exc()}"
            )
            raise CTIXAPIError(f"Error fetching from lookup: {str(e)}") from e

    def _fetch_indicators_by_source_type(self, session_key, earliest_time="0"):
        """Fetch indicators based on source type."""
        if self.source_type == "index":
            if not self.index_name:
                raise CTIXValidationError("Index name required for index source")
            return self._fetch_from_index(session_key, self.index_name, self.sourcetype, self.field_name, earliest_time)
        elif self.source_type == "cim":
            if not self.cim_datamodel_name:
                raise CTIXValidationError("CIM datamodel name required for CIM source")
            if not self.cim_field_name:
                raise CTIXValidationError("CIM field name required for CIM source")
            return self._fetch_from_cim(session_key, self.cim_datamodel_name, self.cim_field_name, earliest_time)
        elif self.source_type == "custom_datamodel":
            if not self.datamodel_name:
                raise CTIXValidationError("Datamodel name required for custom_datamodel source")
            return self._fetch_from_custom_datamodel(
                session_key, self.datamodel_name, self.field_name_custom_datamodel, earliest_time
            )
        elif self.source_type == "lookup":
            if not self.lookup_name:
                raise CTIXValidationError("Lookup name required for lookup source")
            return self._fetch_from_lookup(session_key, self.lookup_name, self.field_name)
        else:
            raise CTIXValidationError(f"Invalid source type: {self.source_type}")

    def _build_output_result(self, result, indicators):
        """Build output dictionary from API result."""
        batches_processed = result.get("batches_processed", 0)
        skipped_count = result.get("skipped", 0)
        total_iocs_original = result.get("total_iocs_original", len(indicators))
        total_iocs_processed = result.get("total_iocs", len(indicators))

        message_parts = [f"Processed {total_iocs_processed} indicators in {batches_processed} batch(es)"]
        if skipped_count > 0:
            message_parts.append(f"Skipped {skipped_count} indicator(s) exceeding 1000 characters")

        output = {
            "status": "success",
            "message": ". ".join(message_parts),
            "source_type": self.source_type,
            "field_name": self.field_name,
            "indicators_count_original": total_iocs_original,
            "indicators_count_processed": total_iocs_processed,
            "indicators_skipped": skipped_count,
            "batches_processed": batches_processed,
            "tlp": self.tlp,
            "confidence_score": self.confidence_score,
            "collection_name": self.collection_name,
            "_time": time.time(),
            "_raw": json.dumps(result)
        }

        if self.source_type == "index":
            output["index_name"] = self.index_name
        elif self.source_type == "cim":
            output["cim_datamodel_name"] = self.cim_datamodel_name
            output["cim_field_name"] = self.cim_field_name
        elif self.source_type == "custom_datamodel":
            output["datamodel_name"] = self.datamodel_name
        elif self.source_type == "lookup":
            output["lookup_name"] = self.lookup_name

        if isinstance(result, dict):
            for key in ["created", "updated", "already_exists", "failed", "skipped"]:
                if key in result:
                    output[key] = result[key]

        return output

    def _handle_automation(self, session_key, output):
        """Handle automation if enabled."""
        if self.enable_automation == "true":
            logger.info("Automation enabled - saving source configuration to KV Store")
            automation_result = self._save_to_kv_store(session_key)
            output["automation_status"] = automation_result["status"]
            output["automation_message"] = automation_result["message"]
            if automation_result["status"] == "success":
                output["automation_key"] = automation_result.get("key", "")
        else:
            output["automation_status"] = "disabled"
            output["automation_message"] = "Automation not enabled"

    def generate(self):
        """Execute main command - fetch indicators and send to CTIX."""
        try:
            session_key = self._metadata.searchinfo.session_key

            account_creds = conf_helper.get_account_credentials_for_search_command(
                self.splunk_account, logger, session_key
            )

            api_url = account_creds.get("base_url")
            client_id = account_creds.get("access_id")
            client_secret = account_creds.get("secret_key")

            if not client_id or not client_secret or not api_url:
                raise CTIXConfigurationError("Credentials missing. Please configure account settings.")

            # Get checkpoint for incremental collection (if automation is enabled)
            checkpoint_time = 0
            earliest_time = "0"

            if self.enable_automation == "true" and self.automation_source_name:
                checkpoint_time = self._get_checkpoint_from_kv_store(session_key, self.automation_source_name)
                if checkpoint_time > 0:
                    earliest_time = str(checkpoint_time)
                    logger.info(f"Using checkpoint for incremental collection: {earliest_time}")

            # Fetch indicators (with checkpoint if available)
            indicators = self._fetch_indicators_by_source_type(session_key, earliest_time)

            if not indicators:
                logger.warning("No indicators found")
                yield {
                    "status": "warning",
                    "message": "No indicators found",
                    "source_type": self.source_type,
                    "indicators_count": 0,
                    "_time": time.time()
                }
                return

            logger.info(f"Found {len(indicators)} unique indicators")

            # Prepare tags
            tags_list = []
            if self.tags:
                tags_list = [t.strip() for t in self.tags.split(",") if t.strip()]
            tags_list.append("created_from_splunk")

            description_text = self.description if self.description else f"Indicators from {self.source_type}"

            # Send to CTIX
            logger.info(f"Sending {len(indicators)} indicators to CTIX...")
            connector = CTIXConnector(api_url, client_id, client_secret, session_key)
            result = connector.add_indicators_bulk(
                ioc_values=indicators,
                source_name=self.source_name,
                tlp=self.tlp,
                confidence=self.confidence_score,
                tags=tags_list,
                description=description_text,
                collection_name=self.collection_name
            )

            logger.info("Cyware API response received")

            # Log batch details
            if "batches" in result:
                for i, batch in enumerate(result.get("batches", []), 1):
                    logger.info(
                        f"Batch {i} completed."
                    )

            output = self._build_output_result(result, indicators)
            self._handle_automation(session_key, output)

            # Update checkpoint after successful ingestion
            if self.enable_automation == "true" and self.automation_source_name:
                current_time = int(time.time())
                self._update_checkpoint_in_kv_store(session_key, self.automation_source_name, current_time)
                output["checkpoint_updated"] = current_time

            yield output

        except Exception as err:
            logger.error(
                f"Error in generate: {str(err)}\n{traceback.format_exc()}"
            )
            yield {
                "status": "error",
                "message": str(err),
                "source_type": getattr(self, 'source_type', 'unknown'),
                "indicators_count": 0,
                "_time": time.time()
            }


if __name__ == "__main__":
    dispatch(CTIXAddBulkIndicatorsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
