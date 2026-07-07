import json
import requests
import logging
import uuid
from splunk_attack_detective import Splunk_AD as splunk_ad
import threading
import queue
import time

class SOCPrime_AD_api():
    def __init__(self, parallel_jobs_threshold, app_name, app_version):
        self.base_url = ''
        self.proxy_server = ''
        self.api_token = ''
        self.input_name = ''
        self.parallel_jobs_threshold = parallel_jobs_threshold
        self.conf = ''
        self.task_queue = queue.Queue(maxsize=self.parallel_jobs_threshold * 2)
        self.app_name = app_name
        self.app_version = app_version
        self.trace_id = self.generate_trace_id()
        logging.info(f'Generated trace ID for session: {self.trace_id}')

    def generate_trace_id(self) -> str:
        """Generates a unique trace ID for request tracing.

        Returns:
            str: Unique trace ID
        """
        return str(uuid.uuid4())

    def get_headers(self):
        """Returns standard headers with trace ID for all API requests.
        
        Returns:
            dict: Headers dictionary with API key, version, user agent and trace ID
        """
        return {
            "X-Api-Key": self.api_token,
            "X-API-Version": "v2",
            'User-Agent': f'{self.app_name}/{self.app_version}',
            'X-Trace-ID': self.trace_id
        }

    def start_processing_tasks(self):
        logging.info(f'Concurrent job limit set to: {self.parallel_jobs_threshold}. Input name: {self.input_name}. Trace ID: {self.trace_id}')
        fetch_thread = threading.Thread(target=self.attack_detective_get_tasks)
        fetch_thread.start()

        processor_threads = []

        for _ in range(self.parallel_jobs_threshold):
            processor_thread = threading.Thread(target=self.process_task)
            processor_threads.append(processor_thread)
            processor_thread.start()

        fetch_thread.join()

        for _ in range(self.parallel_jobs_threshold):
            self.task_queue.put(None)
            
        for processor_thread in processor_threads:
            processor_thread.join()

    def attack_detective_get_tasks(self):
        url_prefix = '/tasks/'
        iteration_number = 0
        max_retries = 5
        retry_count = 0
        base_retry_delay = 10
        
        while retry_count < max_retries:
            iteration_number += 1
            try:
                response = requests.get(
                    url=f'{self.base_url}{url_prefix}',
                    headers=self.get_headers(),
                    proxies=self.proxy_server,
                    verify=True
                )

                if response.status_code == 202:
                    # Task is being processed but no content is ready yet
                    logging.info(f'Task is being processed, no content ready yet. Input name: {self.input_name}. Iteration number: {iteration_number}. Response code: {response.status_code}. Trace ID: {self.trace_id}')
                    logging.info('event_message = {}'.format(json.dumps(
                                             {"type": "connection_to_ad",
                                             "action": "Processing",
                                             "input_name": self.input_name,
                                             "trace_id": self.trace_id,
                                             "message": "Task is being processed, no content ready yet"})))
                    retry_delay = base_retry_delay * 2  # Wait longer for processing
                    time.sleep(retry_delay)
                    continue

                elif response.status_code == 423:
                    # Task is currently paused
                    logging.info(f'Task is currently paused. Please resume from Attack Detective user interface. Input name: {self.input_name}. Iteration number: {iteration_number}. Response code: {response.status_code}. Trace ID: {self.trace_id}')
                    logging.info('event_message = {}'.format(json.dumps(
                                             {"type": "connection_to_ad",
                                             "action": "Paused",
                                             "input_name": self.input_name,
                                             "trace_id": self.trace_id,
                                             "message": "Task is paused, please resume from Attack Detective UI"})))
                    retry_delay = base_retry_delay * 6  # Wait longer for manual resume
                    time.sleep(retry_delay)
                    continue

                elif response.status_code == 404:
                    # No scan/audit has been created yet
                    logging.info(f'No scan/audit has been created yet. Please create a scan/audit from Attack Detective user interface. Input name: {self.input_name}. Iteration number: {iteration_number}. Response code: {response.status_code}. Trace ID: {self.trace_id}')
                    logging.info('event_message = {}'.format(json.dumps(
                                             {"type": "connection_to_ad",
                                             "action": "No_Scan_Available",
                                             "input_name": self.input_name,
                                             "trace_id": self.trace_id,
                                             "message": "No scan/audit created, please create from Attack Detective UI"})))
                    retry_delay = base_retry_delay * 4
                    time.sleep(retry_delay)
                    continue

                elif response.status_code == 429:
                    # Rate limit exceeded
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        try:
                            retry_delay = int(retry_after)
                        except ValueError:
                            retry_delay = base_retry_delay * 6
                    else:
                        retry_delay = base_retry_delay * 6
                    
                    logging.warning(f'Rate limit exceeded. Waiting {retry_delay} seconds before retry. Input name: {self.input_name}. Iteration number: {iteration_number}. Response code: {response.status_code}. Trace ID: {self.trace_id}')
                    logging.warning('event_message = {}'.format(json.dumps(
                                             {"type": "connection_to_ad",
                                             "action": "Rate_Limited",
                                             "input_name": self.input_name,
                                             "trace_id": self.trace_id,
                                             "retry_after": retry_delay})))
                    time.sleep(retry_delay)
                    continue

                elif response.status_code == 425:
                    # Legacy status code - no more queries to execute
                    logging.info(f'No more queries to execute (legacy status). Input name: {self.input_name}. Iteration number: {iteration_number}. Response code: {response.status_code}. Response text: {response.text}. Trace ID: {self.trace_id}')
                    logging.info('event_message = {}'.format(json.dumps(
                                             {"type": "connection_to_ad",
                                             "action": "Success",
                                             "input_name": self.input_name,
                                             "trace_id": self.trace_id})))
                    break

                elif response.ok:
                    # Successful response with queries
                    response_json = response.json()
                    queries = response_json.get('queries')
                    scan_id = response_json.get('scan_id', None)
                    queries_count = len(queries)
                    logging.info(f'{queries_count} queries retrieved successfully from Attack Detective. Iteration number: {iteration_number}. Scan ID: {scan_id}. Trace ID: {self.trace_id}')
                    logging.info('event_message = {}'.format(json.dumps(
                                             {"type": "connection_to_ad",
                                             "action": "Success",
                                             "input_name": self.input_name,
                                             "trace_id": self.trace_id})))
                    
                    for query in queries:
                        query['scan_id'] = scan_id
                        self.task_queue.put(query)
                        logging.info(f'Query {query["id"]} added to queue. Queue size: {self.task_queue.qsize()}. Trace ID: {self.trace_id}')
                        logging.debug(f'Query ID: {query["id"]}. Query: {query["query"]}. Trace ID: {self.trace_id}')
                        if self.task_queue.full():
                            logging.info(f'Queries queue is full, pausing fetch... Queue size: {self.task_queue.qsize()}. Trace ID: {self.trace_id}')
                            while self.task_queue.full():
                                time.sleep(1)
                            logging.info(f'Resuming task fetching... Trace ID: {self.trace_id}')
                    retry_count = 0  # Reset retry count on successful response

                else:
                    # Other error status codes
                    logging.error(f'Error, failed to fetch queries. Input name: {self.input_name}. Iteration number: {iteration_number}. Response code: {response.status_code}. Response text: {response.text}. Trace ID: {self.trace_id}')
                    logging.error('event_message = {}'.format(json.dumps(
                                             {"type": "connection_to_ad",
                                             "action": "Failed",
                                             "reason": str(response.text),
                                             "status_code": response.status_code,
                                             "input_name": self.input_name,
                                             "trace_id": self.trace_id})))
                    retry_count += 1
                    retry_delay = base_retry_delay * min(retry_count, 4)  # Exponential backoff with cap
                    time.sleep(retry_delay)

            except requests.exceptions.Timeout as e:
                logging.error(f'Timeout error. Input name: {self.input_name}. Iteration: {iteration_number}. Error: {e}. Trace ID: {self.trace_id}')
                logging.error('event_message = {}'.format(json.dumps(
                                             {"type": "connection_to_ad",
                                             "action": "Failed",
                                             "reason": str(e),
                                             "input_name": self.input_name,
                                             "trace_id": self.trace_id})))
                retry_count += 1
                retry_delay = base_retry_delay * min(retry_count, 4)
                time.sleep(retry_delay)

            except requests.exceptions.ConnectionError as e:
                logging.error(f'Connection error. Input name: {self.input_name}. Iteration: {iteration_number}. Error: {e}. Trace ID: {self.trace_id}')
                logging.error('event_message = {}'.format(json.dumps(
                                             {"type": "connection_to_ad",
                                             "action": "Failed",
                                             "reason": str(e),
                                             "input_name": self.input_name,
                                             "trace_id": self.trace_id})))
                retry_count += 1
                retry_delay = base_retry_delay * min(retry_count, 4)
                time.sleep(retry_delay)

            except Exception as e:
                logging.error(f'Error fetching queries. Input name: {self.input_name}. Iteration: {iteration_number}. Error: {e}. Trace ID: {self.trace_id}')
                logging.error('event_message = {}'.format(json.dumps(
                                             {"type": "connection_to_ad",
                                             "action": "Failed",
                                             "reason": str(e),
                                             "input_name": self.input_name,
                                             "trace_id": self.trace_id})))
                break
        
        if retry_count >= max_retries:
            logging.error(f'Maximum retry attempts ({max_retries}) exceeded. Stopping task fetching. Input name: {self.input_name}. Trace ID: {self.trace_id}')
            logging.error('event_message = {}'.format(json.dumps(
                                         {"type": "connection_to_ad",
                                         "action": "Failed",
                                         "reason": "Maximum retry attempts exceeded",
                                         "input_name": self.input_name,
                                         "trace_id": self.trace_id})))
  
    def process_task(self):
        while True:
            task = self.task_queue.get()
            if task is None:
                break
            query_id = task['id']
            query = task['query']
            kwargs = task['extra']
            scan_id = task['scan_id']
            query_type = task['query_type']
            
            spl = splunk_ad(self.conf, self.input_name)
            logging.info(f'Processing query in Splunk. Query ID: {query_id}. Search parameters: {kwargs}. Scan ID: {scan_id}. Trace ID: {self.trace_id}')
            logging.debug(f'Processing query: {query}. Trace ID: {self.trace_id}')
            created_job, is_error_on_splunk = spl.splunk_create_job(query_id, query, kwargs)
            if is_error_on_splunk is False:
                status = spl.get_job_status(created_job, query_id)
                if status is True:
                    result = spl.splunk_return_results(created_job, query_id, scan_id, query_type)
                else:
                    result = status
                    result['scan_id'] = scan_id
                    result['query_type'] = query_type
            else:
               result = created_job
               result['scan_id'] = scan_id
               result['query_type'] = query_type
            self.post_data(result)     
            logging.info(f'Finished processing query: {task["id"]}. Trace ID: {self.trace_id}')
            logging.debug(f'Finished processing query: {task["query"]}. Trace ID: {self.trace_id}')
            self.task_queue.task_done() 

    def post_data(self, body):
        url_prefix = '/tasks/'
        task_id = body.get('id')
        body = [body]
        max_retries = 5
        retry_count = 0
        base_retry_delay = 5

        while retry_count < max_retries:
            try:
                logging.debug(f'Post body: {body}. Trace ID: {self.trace_id}')
                response = requests.post(
                    url=f'{self.base_url}{url_prefix}', 
                    json=body, 
                    headers=self.get_headers(),
                    proxies=self.proxy_server,
                    verify=True
                )
                
                if response.ok:
                    logging.info(f'Results for task: {task_id} posted successfully to the AD. Trace ID: {self.trace_id}')
                    logging.info('event_message = {}'.format(json.dumps(
                                                {"type": "post_results_to_ad",
                                                "action": "Success",
                                                "input_name": self.input_name,
                                                "task_id": task_id,
                                                "trace_id": self.trace_id})))
                    return

                elif response.status_code == 410:
                    logging.error(f'Received script stop command from Attack Detective Cloud. Exiting script... Trace ID: {self.trace_id}')
                    exit(0)

                elif response.status_code == 429:
                    # Rate limit exceeded for POST requests
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        try:
                            retry_delay = int(retry_after)
                        except ValueError:
                            retry_delay = base_retry_delay * 2
                    else:
                        retry_delay = base_retry_delay * 2
                    
                    logging.warning(f'Rate limit exceeded while posting results for task: {task_id}. Waiting {retry_delay} seconds before retry. Trace ID: {self.trace_id}')
                    logging.warning('event_message = {}'.format(json.dumps(
                                                {"type": "post_results_to_ad",
                                                "action": "Rate_Limited",
                                                "input_name": self.input_name,
                                                "task_id": task_id,
                                                "trace_id": self.trace_id,
                                                "retry_after": retry_delay})))
                    time.sleep(retry_delay)
                    continue

                else:
                    logging.error(f'Error during posting results session. Task: {task_id}. Response code: {response.status_code}. Response text: {response.text}. Trace ID: {self.trace_id}')
                    logging.error('event_message = {}'.format(json.dumps(
                                                {"type": "post_results_to_ad",
                                                "action": "Failed",
                                                "input_name": self.input_name,
                                                "reason": response.text,
                                                "status_code": response.status_code,
                                                "task_id": task_id,
                                                "trace_id": self.trace_id})))
            
            except (requests.ConnectionError, requests.Timeout) as e:
                logging.error(f'Connection or timeout error while posting results for task: {task_id}. Error: {e}. Trace ID: {self.trace_id}')
                logging.error('event_message = {}'.format(json.dumps(
                                                {"type": "post_results_to_ad",
                                                "action": "Failed",
                                                "input_name": self.input_name,
                                                "reason": str(e),
                                                "task_id": task_id,
                                                "trace_id": self.trace_id})))

            except Exception as e:
                logging.error(f'An unexpected error occurred while posting results for task: {task_id}. Error: {e}. Trace ID: {self.trace_id}')
                logging.error('event_message = {}'.format(json.dumps(
                                                {"type": "post_results_to_ad",
                                                "action": "Failed",
                                                "input_name": self.input_name,
                                                "reason": str(e),
                                                "task_id": task_id,
                                                "trace_id": self.trace_id})))

            retry_count += 1
            retry_delay = base_retry_delay * min(retry_count, 4)  # Exponential backoff with cap
            logging.info(f'Retry attempt {retry_count}/{max_retries} for task: {task_id}. Trace ID: {self.trace_id}')
            time.sleep(retry_delay)
        
        logging.error(f'Failed to post results for task: {task_id} after {max_retries} attempts. Trace ID: {self.trace_id}')
