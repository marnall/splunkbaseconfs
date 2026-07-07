"""This file is used to define api methods."""
import ta_jupiterone_declare  # noqa F401
import copy
import time
import datetime
import json
import requests
import traceback
import ta_jupiterone_constants as constants
from ta_jupiterone_utils import post_api_expiration_msg, get_thread_count
from ta_jupiterone_log_manager import setup_logging
import threadpool

logger = setup_logging('ta_jupiterone_alerts')


class JupiterOneAlerts(object):
    """Class responsible for all communication with the JupiterOne platform."""

    def __init__(self, helper, ew):
        """
        Initialize object with given parameters.

        :param ew: object of EventWriter class
        :param helper: object of BaseModInput class
        """
        self.jupiterone_account = helper.get_arg('jupiterone_account')
        self.start_datetime = helper.get_arg('start_datetime')
        self.index = helper.get_arg('index')
        self.account_id = self.jupiterone_account["account_id"]
        self.base_url = self.jupiterone_account["base_url"]
        if not self.base_url:
            self.base_url = constants.BASE_URL
        self.api_key = self.jupiterone_account["api_key"]
        self.input_name = helper.get_arg('name')
        self.pull_alert_related_objects = helper.get_arg('pull_alert_related_objects')
        # convert start_datetime to epoch time (in millisecond)
        self.epoch_start_datetime = ((datetime.datetime.utcnow() - datetime.timedelta(days=30)).timestamp()) * 1000 \
            if self.start_datetime is None else (datetime.datetime.strptime(
                self.start_datetime, "%Y-%m-%dT%H:%M:%S.%f").replace(
                tzinfo=datetime.timezone.utc).timestamp()) * 1000
        self.key = self.input_name + "_alerts"
        self.retry_count = copy.deepcopy(constants.RETRY_COUNT)
        self.timeout = constants.TIMEOUT
        self.endpoint_url = self.base_url
        self.helper = helper
        self.ew = ew
        self.entities_count = 0
        self.threads = threadpool.ThreadPool(get_thread_count(self.helper.context_meta['session_key']))
        self.host = self.get_host_name()

    def get_host_name(self):
        """Provide the host detail of J1 Plateform."""
        is_checkpt = self.helper.get_check_point(self.key)
        # check that checkpoint is available or not
        if is_checkpt:
            host = is_checkpt.get('host', None)
        else:
            # get single alert using J1QL to get host from weblink
            response = self.get_alert_data(cursor=None, get_host=True)
            if response and len(response['data']['queryV1']['data']) > 0:
                host = response['data']['queryV1']['data'][0]['properties']['webLink']
                index = host.index("/alerts")  # get next index of last character of host
                host = host[:index][8:]  # remove the https:// from host
            else:
                host = None
        return host

    def get_request_params(self, cursor, get_host, query_variables, rawDataKey):
        """Provide the request parameters to make API call."""
        # headers to pass in REST call
        headers = {
            'Authorization': 'Bearer {}'.format(self.api_key),
            'JupiterOne-Account': self.account_id
        }

        # check that which params need to provide (i.e.for J1QL or listAlertInstance)
        if get_host:
            query = """
            query J1QL(
            $query: String!,
            $variables: JSON,
            $cursor: String
            ) {
            queryV1(
                query: $query,
                variables: $variables,
                cursor: $cursor,
                includeDeleted: true
            ) {
                type
                data
                cursor
            }
            }
            """
            variables = {
                "query": "find jupiterone_rule_alert LIMIT 1"
            }
        elif query_variables:
            query = """
            query ListResults(
                $collectionType: CollectionType!,
                $collectionOwnerId: String!,
                $beginTimestamp: Long!,
                $endTimestamp: Long!,
                $limit: Int,
                $cursor: String,
                $tag: String) {
                listCollectionResults(
                    collectionType: $collectionType
                    collectionOwnerId: $collectionOwnerId
                    beginTimestamp: $beginTimestamp
                    endTimestamp: $endTimestamp
                    limit: $limit
                    cursor: $cursor
                    tag: $tag
                ) {
                    results {
                    accountId
                    timestamp
                    rawDataDescriptors {
                        rawDataKey
                        recordCount
                    }
                    }
                }
                }
            """
            variables = {
                "collectionType": "RULE_EVALUATION",
                "collectionOwnerId": query_variables[0],
                "beginTimestamp": query_variables[1],
                "endTimestamp": query_variables[1]
            }
        elif rawDataKey:
            query = """
            query GetRawDataDownloadUrl($rawDataKey: String!) {
                getRawDataDownloadUrl(rawDataKey: $rawDataKey)
            }
            """
            variables = {
                "rawDataKey": rawDataKey
            }
        else:
            # GraphQL query to get alerts
            query = """
            query ListAlertInstances($alertStatus: AlertStatus, $limit: Int, $cursor: String) {
            listAlertInstances(alertStatus: $alertStatus, limit: $limit, cursor: $cursor) {
                instances {
                id
                accountId
                ruleId
                level
                status
                lastUpdatedOn
                lastEvaluationBeginOn
                lastEvaluationEndOn
                createdOn
                dismissedOn
                lastEvaluationResult {
                    rawDataDescriptors {
                    recordCount
                    }
                }
                questionRuleInstance {
                    name
                    description
                }
                }
                pageInfo {
                endCursor
                hasNextPage
                }
            }
            }
            """
            variables = {
                "limit": constants.PAGE_LIMIT
            }
            # If cursor available for pagination then add into variables
            if cursor:
                variables["cursor"] = cursor

        return headers, query, variables

    def get_checkpoint_time(self):
        """Provide checkpoint time if checkpoint is available."""
        chkpt_start_time = self.helper.get_check_point(self.key)
        cursor = None
        # check that checkpoint is available or not
        if chkpt_start_time:
            cursor = chkpt_start_time.get('cursor', None)
            # check that cursor is null or not in checkpoint
            if cursor:
                # Use lastUpdatedOn with a small buffer to ensure we don't miss alerts
                # Allow processing alerts that are within 1 second of the checkpoint time
                start_time = chkpt_start_time['lastUpdatedOn'] - 1000  # 1 second buffer
            else:
                start_time = chkpt_start_time['lastUpdatedOn'] - 1000  # 1 second buffer
            logger.info("JupiterOne Info: Get updatedOn epoch time = {} and cursor = {} "
                        "from checkpoint for input: {}.".format(start_time, cursor, self.input_name))
        else:
            # if checkpoint is not available then first time use the start_datetime field
            start_time = int(self.epoch_start_datetime)
            logger.info("JupiterOne Info: Get updatedOn epoch time = {} and cursor = {} "
                        "from start_datetime field for input: {}.".format(start_time, cursor, self.input_name))
        return start_time, cursor

    def get_alert_data(self, cursor, get_host=False, query_variables=None, rawDataKey=None):
        """Execute query against graphql endpoint to get alert data."""
        headers, query, variables = self.get_request_params(cursor, get_host, query_variables, rawDataKey)
        try:
            response = self.helper.send_http_request(self.endpoint_url, "POST", headers=headers,
                                                     payload={"query": query, "variables": variables},
                                                     timeout=self.timeout, use_proxy=True)
            if response.status_code == 200:
                if response.text:
                    content = json.loads(response.text)
                    # check that still any error come after getting 200 response
                    if 'errors' in content:
                        errors = content['errors']
                        # check specific error related to Rate limit exceeded
                        if len(errors) == 1 and '429' in errors[0]['message']:
                            logger.error(
                                "JupiterOne Error: Error occurred while fetching alert data. API rate limit exceeded."
                                " Input: {}, Status code: 200 and Error: {}".format(self.input_name, errors))
                            logger.debug(
                                "JupiterOne Debug: Started retry mechanism as API rate limit exceeded"
                                " for input: {}.".format(self.input_name))
                            # retry mechanism
                            if self.retry_count == constants.RETRY_COUNT:
                                while self.retry_count > 0:
                                    logger.debug(
                                        "JupiterOne Debug: Started retry mechanism and retry count is {} "
                                        "for input: {}.".format(
                                            (constants.RETRY_COUNT - self.retry_count) + 1, self.input_name)
                                    )
                                    time.sleep(10)
                                    self.retry_count -= 1
                                    res = self.get_alert_data(cursor, get_host, query_variables, rawDataKey)
                                    if res:
                                        break
                                self.retry_count = copy.deepcopy(constants.RETRY_COUNT)
                                return res
                        else:
                            logger.error(
                                "JupiterOne Error: Error occurred while fetching alert data."
                                " Input: {}, Status code: 200 and Error: {}".format(self.input_name, errors))
                    else:
                        return response.json()
                else:
                    logger.error(
                        "JupiterOne Error: Error occurred while fetching alert data. "
                        "Input: {}, Status code: 200 and Error: Received empty response.".format(self.input_name))
            elif response.status_code == 400:
                logger.error(
                    "JupiterOne Error: Error occurred while fetching alert data. Error in GraphQL payload."
                    " Input: {}, Status code: 400 and Response: {}".format(self.input_name, response.text))
            elif response.status_code == 401:
                logger.error(
                    "JupiterOne Error: Error occurred while fetching alert data. "
                    "Input: {}, Status code: 401 and Response: {}".format(self.input_name, response.text))
                logger.debug("JupiterOne Debug: Please verify that API key token is expired or not"
                             " for account: {}.".format(self.jupiterone_account["name"]))
                # post the api expiration message
                post_api_expiration_msg(self.helper.context_meta['session_key'], self.jupiterone_account["name"])
            elif response.status_code == 429 or response.status_code in [500, 600]:
                logger.error("JupiterOne Error: Error occurred while fetching alert data."
                             " Input: {}, Status code: {} and "
                             "Response: {}".format(self.input_name, response.status_code, response.text))
                # retry mechanism
                if self.retry_count == constants.RETRY_COUNT:
                    while self.retry_count > 0:
                        logger.debug(
                            "JupiterOne Debug: Started retry mechanism and retry count is {} "
                            "for input: {}.".format((constants.RETRY_COUNT - self.retry_count) + 1, self.input_name)
                        )
                        time.sleep(10)
                        self.retry_count -= 1
                        res = self.get_alert_data(cursor, get_host, query_variables, rawDataKey)
                        if res:
                            break
                    self.retry_count = copy.deepcopy(constants.RETRY_COUNT)
                    return res
            else:
                logger.error("JupiterOne Error: Error occurred while fetching alert data. "
                             " Input: {}, Status code: {} and "
                             "Response: {}".format(self.input_name, response.status_code, response.text))
        except (requests.HTTPError, requests.exceptions.ConnectionError) as e:
            logger.error(
                "JupiterOne Error: HTTPError or ConnectionError occurred while fetching alert data."
                " Input: {}, Error: {}".format(self.input_name, str(e)))
            logger.debug(
                "JupiterOne Debug: HTTPError or ConnectionError occurred while fetching alert data."
                " Input: {}, Error trace: {}".format(self.input_name, traceback.format_exc()))
        except Exception as e:
            logger.error(
                "JupiterOne Error: Exception occurred while fetching alert data."
                " Input: {}, Error: {}".format(self.input_name, str(e)))
            logger.debug(
                "JupiterOne Debug: Unexpected error occured. "
                "Input: {}, Error trace: {}".format(self.input_name, traceback.format_exc()))
        return None

    def get_final_raw_data(self, result_url):
        """Execute the result_url to get final result."""
        try:
            resp = self.helper.send_http_request(result_url, "GET", timeout=self.timeout, use_proxy=True)
            if resp.status_code == 200:
                return resp.json()
            else:
                logger.error("JupiterOne Error: Error occurred while fetching alert entities. "
                             " Input: {}, Status code: {} and "
                             "Response: {}".format(self.input_name, resp.status_code, resp.text))
        except Exception as e:
            logger.error(
                "JupiterOne Error: Exception occurred while fetching alert entities."
                " Input: {}, Error: {}".format(self.input_name, str(e)))
            logger.debug(
                "JupiterOne Debug: Unexpected error occured. "
                "Input: {}, Error trace: {}".format(self.input_name, traceback.format_exc()))
        return None

    def get_alert_related_entities(self, ruleId, lastEvaluationEndOn, id, lastupdatedon):
        """Logic to collect alert related entities will be start from here."""
        logger.info("JupiterOne Info: Started collection of entities related to alert having "
                 "id = {} for input: {}.".format(id, self.input_name))
    
        entities_count = 0  # Initialize to prevent undefined variable error
    
        try:
            # The issue is that we need to get the rawDataKey from the alert's lastEvaluationResult
            # but we don't have access to the alert data in this method
            # We need to modify the calling method to pass the alert data or extract the rawDataKey earlier
            
            logger.debug("JupiterOne Debug: Need to implement new approach - extract rawDataKey from alert data for input: {}.".format(
                self.input_name))
            
            # For now, let's try a different approach - use the ruleId to query for evaluation results
            # But first, let me check if we can get the rawDataKey from the alert data that was already fetched
            
            logger.warning("JupiterOne Warning: Current approach cannot access alert data. Need to modify architecture for input: {}.".format(
                self.input_name))
            
            # TODO: The solution is to modify the write_events method to:
            # 1. Extract rawDataKey from alert.lastEvaluationResult.rawDataDescriptors[0].rawDataKey
            # 2. Pass this rawDataKey to get_alert_related_entities
            # 3. Or call get_alert_related_entities with the alert data
            
            return entities_count
            
        except Exception as e:
            logger.error("JupiterOne Error: Unexpected error while processing alert related entities for "
                        "alert id = {} for input: {}. Error: {}".format(id, self.input_name, str(e)))
            logger.debug("JupiterOne Debug: Full error trace for alert {}: {}".format(id, traceback.format_exc()))
            return 0

    def get_alert_related_entities_from_rule(self, ruleId, lastEvaluationEndOn, id, lastupdatedon):
        """Fetch entities from all queries configured in the alert rule using proper JupiterOne API methods."""
        logger.info("JupiterOne Info: Started collection of entities for alert {} from rule {} for input: {}.".format(
            id, ruleId, self.input_name))
        
        try:
            # Step 1: Get the latest evaluation results for this rule
            evaluations = self.get_rule_evaluation_results(ruleId)
            if not evaluations:
                logger.warning("JupiterOne Warning: No evaluation results found for rule {} in alert {} for input: {}.".format(
                    ruleId, id, self.input_name))
                return 0
            
            # Step 2: Extract rawDataKey values from the most recent evaluation (first in the list)
            raw_data_keys = []
            latest_evaluation = evaluations[0]  # Get only the first (most recent) evaluation
            if latest_evaluation.get('rawDataDescriptors'):
                for descriptor in latest_evaluation['rawDataDescriptors']:
                    if descriptor.get('rawDataKey'):
                        raw_data_keys.append(descriptor['rawDataKey'])
            
            if not raw_data_keys:
                logger.warning("JupiterOne Warning: No rawDataKeys found in evaluation results for rule {} in alert {} for input: {}.".format(
                    ruleId, id, self.input_name))
                return 0
            
            logger.info("JupiterOne Info: Found {} rawDataKeys {} for rule {} in alert {} for input: {}.".format(
                len(raw_data_keys), raw_data_keys, ruleId, id, self.input_name))
            
            # Step 3: Collect entities from each rawDataKey
            return self.get_alert_related_entities_from_raw_data_keys(raw_data_keys, id, lastupdatedon)
            
        except Exception as e:
            logger.error("JupiterOne Error: Unexpected error while fetching rule evaluation results for "
                        "alert id = {} for input: {}. Error: {}".format(id, self.input_name, str(e)))
            logger.debug("JupiterOne Debug: Full error trace for alert {}: {}".format(id, traceback.format_exc()))
            return 0

    def get_rule_evaluation_results(self, ruleId):
        """Get the latest evaluation results for a rule using listCollectionResults GraphQL query."""
        try:
            # GraphQL query to get collection results for the rule
            query = """
            query ListCollectionResults($collectionType: CollectionType!, $collectionOwnerId: String!, $beginTimestamp: Long!, $endTimestamp: Long!, $limit: Int!) {
                listCollectionResults(
                    collectionType: $collectionType
                    collectionOwnerId: $collectionOwnerId
                    beginTimestamp: $beginTimestamp
                    endTimestamp: $endTimestamp
                    limit: $limit
                ) {
                    results {
                        accountId
                        timestamp
                        rawDataDescriptors {
                            rawDataKey
                            recordCount
                        }
                    }
                }
            }
            """
            
            # Get current timestamp for endTimestamp
            import time
            current_timestamp = int(time.time() * 1000)  # Convert to milliseconds
            
            variables = {
                "collectionType": "RULE_EVALUATION",
                "collectionOwnerId": ruleId,
                "beginTimestamp": 0,
                "endTimestamp": current_timestamp,
                "limit": 1  # Only fetch the latest evaluation
            }
            
            headers = {
                'Authorization': 'Bearer {}'.format(self.api_key),
                'JupiterOne-Account': self.account_id
            }
            
            response = requests.post(
                self.endpoint_url,
                headers=headers,
                json={"query": query, "variables": variables},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and data['data'] and data['data'].get('listCollectionResults'):
                    results = data['data']['listCollectionResults']['results']
                    logger.info("JupiterOne Info: Successfully fetched {} evaluation results for rule {} for input: {}.".format(
                        len(results), ruleId, self.input_name))
                    return results
                else:
                    logger.warning("JupiterOne Warning: No evaluation results found for rule {} for input: {}.".format(
                        ruleId, self.input_name))
                    return []
            else:
                logger.error("JupiterOne Error: Failed to fetch evaluation results for rule {}. Status: {}, Response: {}".format(
                    ruleId, response.status_code, response.text))
                return []
                
        except Exception as e:
            logger.error("JupiterOne Error: Exception occurred while fetching evaluation results for rule {} for input: {}. Error: {}.".format(
                ruleId, self.input_name, str(e)))
            logger.debug("JupiterOne Debug: Full error trace for rule {}: {}".format(ruleId, traceback.format_exc()))
            return []

    def get_alert_related_entities_from_raw_data_keys(self, raw_data_keys, id, lastupdatedon):
        """Collect entities from multiple rawDataKeys using proper JupiterOne API flow."""
        logger.info("JupiterOne Info: Started collection of entities from {} rawDataKeys for alert {} for input: {}.".format(
            len(raw_data_keys), id, self.input_name))
    
        total_entities_count = 0
        successful_queries = 0
        failed_queries = 0
    
        try:
            # Process each rawDataKey to collect entities
            for raw_data_key in raw_data_keys:
                try:
                    logger.debug("JupiterOne Debug: Processing rawDataKey {} for alert {} for input: {}.".format(
                        raw_data_key, id, self.input_name))
                    
                    # Step 1: Get download URL for this rawDataKey
                    response = self.get_alert_data(cursor=None, rawDataKey=raw_data_key)
                    if not response or not response.get('data'):
                        logger.warning("JupiterOne Warning: No data returned from get_alert_data with rawDataKey {} "
                                    "for alert id = {} for input: {}.".format(raw_data_key, id, self.input_name))
                        failed_queries += 1
                        continue
                    
                    download_url = response['data'].get('getRawDataDownloadUrl')
                    if not download_url:
                        logger.warning("JupiterOne Warning: No download URL found for rawDataKey {} "
                                    "in alert id = {} for input: {}.".format(raw_data_key, id, self.input_name))
                        failed_queries += 1
                        continue
                    
                    logger.debug("JupiterOne Debug: Successfully obtained download URL for rawDataKey {} in alert {} for input: {}.".format(
                        raw_data_key, id, self.input_name))
                    
                    # Step 2: Download the actual entity data
                    resp = self.get_final_raw_data(download_url)
                    if not resp or not resp.get('data'):
                        logger.warning("JupiterOne Warning: No final raw data returned for rawDataKey {} "
                                    "in alert id = {} for input: {}.".format(raw_data_key, id, self.input_name))
                        failed_queries += 1
                        continue
                    
                    # Step 3: Write the entities to Splunk
                    entities_count = self.write_entities(resp, id, lastupdatedon)
                    total_entities_count += entities_count
                    successful_queries += 1
                    
                    logger.info("JupiterOne Info: Successfully collected {} entities for rawDataKey {} in alert {} for input: {}.".format(
                        entities_count, raw_data_key, id, self.input_name))
                    
                except Exception as e:
                    logger.error("JupiterOne Error: Error processing rawDataKey {} for alert {} for input: {}. Error: {}.".format(
                        raw_data_key, id, self.input_name, str(e)))
                    logger.debug("JupiterOne Debug: Full error trace for rawDataKey {} in alert {}: {}".format(
                        raw_data_key, id, traceback.format_exc()))
                    failed_queries += 1
                    continue
            
            # Log summary of results
            logger.info("JupiterOne Info: Completed entity collection for alert {} for input: {}. "
                        "Successful queries: {}, Failed queries: {}, Total entities: {}.".format(
                            id, self.input_name, successful_queries, failed_queries, total_entities_count))
            
        except Exception as e:
            logger.error("JupiterOne Error: Unexpected error while processing entities from rawDataKeys for "
                        "alert id = {} for input: {}. Error: {}".format(id, self.input_name, str(e)))
            logger.debug("JupiterOne Debug: Full error trace for alert {}: {}".format(id, traceback.format_exc()))
            return 0
        
        return total_entities_count

    def write_entities(self, response, id, lastupdatedon):
        """Ingest the alert related entities in specified index."""
        # iterate through all events of response
        for event in response['data']:
            event['alert_id'] = id
            event['alert_lastUpdatedOn'] = lastupdatedon
            new_event = self.helper.new_event(json.dumps(event), index=self.index, host=self.host,
                                              source="JupiterOne", sourcetype="jupiterone:alerts:entities")
            self.ew.write_event(new_event)
        self.entities_count += response['total']
        return response['total']

    def write_events(self, response, start_time):
        """Ingest the alert data in specified index."""
        # get lastUpdatedOn time from checkpoint
        updatedon_time = self.helper.get_check_point(self.key)['lastUpdatedOn'] \
            if self.helper.get_check_point(self.key) else int(self.epoch_start_datetime)
        event_count = 0
        cursor = response['data']['listAlertInstances']['pageInfo']['endCursor']

        # iterate through all events of response
        total_alerts = len(response['data']['listAlertInstances']['instances'])
        logger.debug("JupiterOne Debug: Processing {} alerts with start_time threshold: {} for input: {}.".format(
            total_alerts, start_time, self.input_name))
        
        processed_alerts = 0
        for event in response['data']['listAlertInstances']['instances']:
            # write the events which have lastUpdatedOn greater than or equal to start_time(i.e.checkpoint time)
            logger.debug("JupiterOne Debug: Alert {} has lastUpdatedOn: {} vs threshold: {} for input: {}.".format(
                event['id'], event['lastUpdatedOn'], start_time, self.input_name))
            if event['lastUpdatedOn'] >= start_time:
                new_event = self.helper.new_event(json.dumps(event), index=self.index, host=self.host,
                                                  source="JupiterOne", sourcetype="jupiterone:alerts")
                self.ew.write_event(new_event)
                event_count += 1
                processed_alerts += 1
                
                # Log detailed information about the processed alert
                logger.info("JupiterOne Info: Processing alert {} with status: '{}', ruleId: '{}' for input: {}.".format(
                    event['id'], event.get('status', 'MISSING'), event.get('ruleId', 'MISSING'), self.input_name))
                
                # fetch the active alert related entities using threading mechanism if checkbox is checked
                if int(self.pull_alert_related_objects) and event['status'] == "ACTIVE":
                    if event.get('ruleId'):
                        logger.info("JupiterOne Info: Fetching query names for rule {} to collect entities for alert {} for input: {}.".format(
                            event['ruleId'], event['id'], self.input_name))
                        
                        # Add entity collection task - the method will fetch query names from the rule
                        self.threads.add_task(self.get_alert_related_entities_from_rule,
                                              event['ruleId'],
                                              event['lastEvaluationEndOn'],
                                              event['id'],
                                              event['lastUpdatedOn'])
                    else:
                        logger.warning("JupiterOne Warning: No ruleId found for alert {} for input: {}.".format(
                            event['id'], self.input_name))
                else:
                    logger.warning("JupiterOne Warning: Skipping entity collection for alert {} - pull_alert_related_objects: {}, status: '{}' for input: {}.".format(
                        event['id'], self.pull_alert_related_objects, event.get('status', 'MISSING'), self.input_name))
                
                # update the existing checkpoint time if event have greater lastUpdatedOn time
                if event['lastUpdatedOn'] > updatedon_time:
                    updatedon_time = event['lastUpdatedOn']

        # Log processing summary
        logger.info("JupiterOne Info: Processed {}/{} alerts for input: {} (threshold: {}).".format(
            processed_alerts, total_alerts, self.input_name, start_time))
        logger.info("JupiterOne Info: Entity collection setting: pull_alert_related_objects = {} for input: {}.".format(
            self.pull_alert_related_objects, self.input_name))
        
        # Wait for entity collection tasks to complete if any were added
        if int(self.pull_alert_related_objects):
            tasks_in_queue = self.threads.tasks.qsize()
            logger.info("JupiterOne Info: Waiting for {} entity collection tasks to complete for input: {}.".format(
                tasks_in_queue, self.input_name))
            if tasks_in_queue == 0:
                logger.warning("JupiterOne Warning: No entity collection tasks were added. This may indicate an issue with alert filtering or status. Check debug logs for details.")
            self.threads.wait_completion()
            logger.info("JupiterOne Info: Entity collection completed. Total entities collected: {} for input: {}.".format(
                self.entities_count, self.input_name))
       
        # dict to save in checkpoint
        checkpt_dict = {
            'lastUpdatedOn': updatedon_time,
            'cursor': cursor,
            'last_checkpoint_time': start_time - 1,
            'host': self.host
        }
        
        # save the checkpoint
        try:
            self.helper.save_check_point(self.key, checkpt_dict)
            logger.info("JupiterOne Info: Saved the checkpoint dict = {} "
                        "for key = {} and"
                        " input: {}.".format(checkpt_dict, self.key, self.input_name))
        except Exception as e:
            logger.error(
                "JupiterOne Error: Exception occurred while saving checkpoint."
                " Input: {}, Error: {}".format(self.input_name, str(e)))
            logger.debug(
                "JupiterOne Debug: Exception occurred while saving checkpoint."
                " Input: {}, Error trace: {}".format(self.input_name, traceback.format_exc()))
        return event_count, cursor