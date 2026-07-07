import json
import splunklib
import splunklib.client as client
import splunklib.results as splunk_sdk_results
import logging
import re
from time import sleep
import time

class Splunk_AD():
    
    def __init__(self, conf, input_name):

        self.input_name = input_name
        self.conf = conf
        self.splunk_host = conf.get('host')
        self.splunk_port = conf.get('port')
        
        try:
            self.service = client.connect(**self.conf)
            logging.info('event_message = {}'.format(json.dumps(
                                             {"type": "connection_to_splunk",
                                             "action": "Success",
                                             "dst": self.splunk_host,
                                             "dport": self.splunk_port})))
        except Exception as err:
            message = f'Unable to establish a connection to Splunk. Error message: {err}'
            logging.error(message)
            logging.error('event_message = {}'.format(json.dumps(
                                             {"type": "connection_to_splunk",
                                             "action": "Failed",
                                             "dst": self.splunk_host,
                                             "dport": self.splunk_port,
                                             "reason": str(err)})))
            raise ValueError(message)


    def splunk_create_job(self, query_id, searchquery_normal, kwargs_normalsearch):
        try:
            job = self.service.jobs.create(searchquery_normal, **kwargs_normalsearch)
            job_sid = job.sid
            logging.info('event_message = {}'.format(json.dumps(
                                             {"type": "create_job_in_splunk",
                                             "action": "Success",
                                             "dst": self.splunk_host,
                                             "dport": self.splunk_port,
                                             "task_id": query_id,
                                             "input_name": self.input_name})))
            logging.info({'job_sid': job_sid, 'query_id': query_id })
            return job, False
        
        except Exception as err:
            message = f'Failed to create a job for the query. Error message: {err}, {query_id}'
            logging.error(message)
            logging.error('event_message = {}'.format(json.dumps(
                                             {"type": "create_job_in_splunk",
                                             "action": "Failed",
                                             "dst": self.splunk_host,
                                             "dport": self.splunk_port,
                                             "task_id": query_id,
                                             "input_name": self.input_name})))
            return {"id":query_id, "is_error": True, "execution_time": 0, "result": json.dumps({"status_code": "-", "reason": str(err)})}, True
    

    def get_job_status(self,job,query_id):
        max_hours = 9
        max_duration = max_hours * 3600
        start_time = time.time() 
        while True:
            elapsed_time = time.time() - start_time
            logging.info(f'The search query is still in progress in Splunk. Job ID: {job.sid}. Query ID: {query_id} Processing...: {float(job["doneProgress"]) * 100}%')
            if job['isDone'] == '1':
                logging.info(f'Search completed in Splunk. Job ID: {job.sid}. Query ID: {query_id}. Process: 100%')
                return True
            if elapsed_time > max_duration:
                logging.error(f'Time limit exceeded. Job ID: {job.sid} terminated after {max_hours} hours. Query ID: {query_id}')
                logging.error('event_message = {}'.format(json.dumps(
                                                {"type": "search_done_in_splunk",
                                                "action": "Failed",
                                                "dst": self.splunk_host,
                                                "dport": self.splunk_port,
                                                "task_id": query_id,
                                                "reason": "Time limit exceeded. Job terminated."})))
                job.cancel()
                return {"id":query_id, "is_error": True, "execution_time": 0, "result": json.dumps({"status_code": "-", "reason": "Time limit exceeded. Job terminated."})}
            sleep(1)
            job.refresh()

        
    def splunk_return_results(self, job, query_id,scan_id,query_type):
        kwargs_normalsearch = {"exec_mode": "normal", "count" : 0}
        try:
            reader = splunk_sdk_results.ResultsReader(job.results(**kwargs_normalsearch))
            res = [
                    result for result in reader if isinstance(result, dict)
                    ]
            logging.info(f'The search query has been successfully completed in Splunk. Query ID: {query_id}. Results count: {len(res)}')
            logging.info('event_message = {}'.format(json.dumps(
                                                {"type": "search_done_in_splunk",
                                                "action": "Success",
                                                "dst": self.splunk_host,
                                                "dport": self.splunk_port,
                                                "task_id": query_id})))
            return {"scan_id":scan_id,"query_type":query_type, "id":query_id, "is_error": False, "execution_time": round(float(job.runDuration), 2), "result": json.dumps(res) }
        except splunklib.binding.HTTPError as err:
            logging.error(f'The search query was not completed in Splunk. Query ID: {query_id}. Reason: {str(err)}')
            logging.error('event_message = {}'.format(json.dumps(
                                                {"type": "search_done_in_splunk",
                                                "action": "Failed",
                                                "dst": self.splunk_host,
                                                "dport": self.splunk_port,
                                                "task_id": query_id,
                                                "reason": str(err)})))
            return {"scan_id":scan_id,"query_type":query_type, "id":query_id, "is_error": True, "execution_time": 0, "result": json.dumps({"status_code": err.status, "reason": str(err)}) }
        except Exception as err:
            logging.error(f'The search query was not completed in Splunk. Query ID: {query_id}. Reason: {str(err)}')
            logging.error('event_message = {}'.format(json.dumps(
                                                {"type": "search_done_in_splunk",
                                                "action": "Failed",
                                                "dst": self.splunk_host,
                                                "dport": self.splunk_port,
                                                "task_id": query_id,
                                                "reason": str(err)})))
            return {"scan_id":scan_id,"query_type":query_type, "id":query_id, "is_error": True, "execution_time": 0, "result": json.dumps({"status_code": "-", "reason": str(err)}) }
