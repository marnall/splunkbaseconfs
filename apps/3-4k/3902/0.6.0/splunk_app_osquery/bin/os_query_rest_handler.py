'''
This REST handler provides an interface for managing osquery clients. This provides functionality for:

1. Creating queries
2. Getting a list of the enrolled clients
3. Provinding the interfaces for osquery clients

Note that osquery clients are not expected to talk to this REST endpoint directly. Rather they
communicate to the modular input which in turn communicates with this endpoint.

Here are the functions that are exposed via the REST API that are intended to be used by the
osquery clients:

* enroll_client
* configure_client
* read_distributed_queries
* set_distributed_query_status

Here are the functions that are exposed via the REST API that are not intended to be used by the
osquery clients:

* create_queries
* get_clients
* ping

Below are some helper functions that are not exposed via the REST API:

* checkin_client
* register_job_hash
'''

import os
import time
import sys
import json
import base64
import httplib
import hashlib
import logging
import tempfile
import zipfile

import splunk.util
import splunk.rest as rest

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'splunk_app_osquery', 'bin']))

import SolnCommon.rest_handler
from SolnCommon.rest_handler import route
from SolnCommon.kvstore import KvStoreHandler

class OSQueryRestHandler(SolnCommon.rest_handler.PersistentRestHandler):
    '''
    OSquery REST handler.
    '''
    logger_name = 'osquery_rest_handler'

    DEFAULT_APP = 'splunk_app_osquery'
    DEFAULT_OWNER = 'nobody'

    ENROLLMENT_OPTIONS = {
        'app': DEFAULT_APP,
        'owner': DEFAULT_OWNER,
        'collection': 'osquery_enrollment'
    }

    CHECKIN_OPTIONS = {
        'app': DEFAULT_APP,
        'owner': DEFAULT_OWNER,
        'collection': 'osquery_checkin'
    }

    JOBS_OPTIONS = {
        'app': DEFAULT_APP,
        'owner': DEFAULT_OWNER,
        'collection': 'osquery_jobs'
    }

    JOB_HASHES_OPTIONS = {
        'app': DEFAULT_APP,
        'owner': DEFAULT_OWNER,
        'collection': 'osquery_job_hashes'
    }

    # Below is the list of job statuses that indicates the state of a query
    JOB_STATUS_NEW = 'new'
    JOB_STATUS_IN_PROGRESS = 'in_progress'
    JOB_STATUS_DONE = 'done'
    JOB_STATUS_FAILED = 'failed'

    JOB_STATUSES = [
        JOB_STATUS_NEW,
        JOB_STATUS_IN_PROGRESS,
        JOB_STATUS_DONE,
        JOB_STATUS_FAILED
    ]

    # If true, then multiple queries will be provided to the client in a single distributed_read
    # call. Otherwise, the queries will be broken up into separate queries that will require
    # several distributed_read calls to get all of the jobs. The advantage is that the results
    # will be sent separately and thus results in smaller, easier to parse events.
    COMBINE_QUERIES = False

    def __init__(self, command_line, command_arg):
        super(OSQueryRestHandler, self).__init__(command_line, command_arg)
        self.logger.setLevel(logging.DEBUG)

    @route("/enroll_client", "GET,POST")
    def enroll_client(self, args, params):
        '''
        Perform operations on all items of a kvstore collection.
        /servies/datra/osquery/<collection>/<collection_item_key>
        '''

        client_data = args['form_map'].get('client_data', '{}')

        self.logger.info("data=%r", client_data)

        hostname = json.loads(client_data)['host_identifier']

        self.logger.info('Got enrollment request for client=%s', hostname)

        kvstore = KvStoreHandler()
        record = {
            'client': hostname,
            'client_data': client_data
        }
        try:
            session_key = args['session']['authtoken']
            response, content = kvstore.create(record, hostname, session_key, self.ENROLLMENT_OPTIONS, include_ts=True)
            if response.status == httplib.CREATED:
                self.logger.info('Client %s was successfully enrolled.', hostname)
            elif response.status == httplib.CONFLICT:
                self.logger.info('Client %s is already enrolled.', hostname)
            else:
                self.logger.debug('Response: %s', str(response))
                self.logger.debug('Content: %s', str(content))
                self.logger.error('An unexpected error occurred trying to enroll client %s. HTTP Status: %s', hostname, response.status)
        except Exception:
            self.logger.exception('Exception generated when attempting to enroll the client')
            return self.response({'node_key': hostname}, httplib.INTERNAL_SERVER_ERROR)

        return self.response({'node_key': hostname}, httplib.OK)

    @route("/configure_client", "GET,POST")
    def configure_client(self, args, params):
        '''
        Get the client configuration.
        '''

        node_key = args['form_map'].get('node_key', None)

        self.logger.info('Got configuration request for node=%s', str(node_key))

        # TODO: Get the jobs for the client from the KV store collection
        configuration = {
            "schedule": {
                "interface_addresses": {"query": "select * from interface_addresses", "interval": 3600},
            },
            "node_invalid": False, # Return true to indicate that the client should re-enroll
        }

        # Save each of the queries so that they can be easily recalled later
        if 'schedule' in configuration:
            session_key = args['session']['authtoken']

            for _, entry in configuration['schedule'].items():
                if 'query' in entry:
                    self.register_job_hash(entry['query'], session_key)

        return self.response(configuration, httplib.OK)

    @route("/get_clients", "GET")
    def get_clients(self, args, params):
        '''
        Return a list of the clients that are currently available for dispatching jobs.
        '''
        kvstore = KvStoreHandler()
        session_key = args['session']['authtoken']
        data = []
        enrollment_response, enrollment_content = kvstore.get(None, session_key, self.ENROLLMENT_OPTIONS)
        checkin_response, checkin_content = kvstore.get(None, session_key, self.CHECKIN_OPTIONS)

        if enrollment_response.status == httplib.OK:
            parsed_enrollment_content = json.loads(enrollment_content)

            # Parse the checkin response
            if checkin_response.status == httplib.OK:
                parsed_checkin_content = json.loads(checkin_content)
            else:
                parsed_checkin_content = []

            # Process the enrollment content to add the last active time
            if parsed_enrollment_content:
                for enrollment_record in parsed_enrollment_content:
                    # Get the last time that the client checked in
                    client_last_active = None

                    for client_record in parsed_checkin_content:
                        if 'client' in client_record and client_record['client'] == enrollment_record['client']:
                            client_last_active = client_record['_time']
                            break

                    # Get the hostname (if possible)
                    try:
                        hostname = json.loads(enrollment_record['client_data'])['host_details']['system_info']['hostname']
                    except KeyError:
                        self.logger.info('Unable the parse the client data for client=%s', enrollment_record['client'])
                        hostname = None
                        
                    # Add the record to the list
                    data.append({
                        'client' : enrollment_record['client'],
                        'last_active' : client_last_active,
                        'hostname' : hostname
                    })

                #data = [record['client'] for record in content]
        self.logger.debug("Client List: " + str(data))
        return self.response(data, httplib.OK)

    def md5(self, content):
        '''
        MD5 the given string.
        '''
        m = hashlib.md5()
        m.update(content)
        return m.hexdigest()

    @route("/create_queries", "POST")
    def create_queries(self, args, params):
        '''
        Creates jobs for the given set of clients with the queries provided.
        '''

        session_key = args['session']['authtoken']
        queries = args['form_map'].get('queries', [])
        clients = args['form_map'].get('clients', [])
        query_name = args['form_map'].get('query_name', None)

        if isinstance(queries, basestring):
            queries = [queries]

        if isinstance(clients, basestring):
            clients = [clients]

        self.logger.info('Got request to create queries for clients, client_count=%d, name="%s"', len(clients), query_name)

        # Instantiate some variables that we will use when creating the records
        records = []
        query_ids = []

        if self.COMBINE_QUERIES:
            ## Form queries object
            queries_obj = {}

            for query in queries:
                id_ = self.md5(query) + '_' + self.md5(str(time.time()))
                queries_obj[id_] = query
                query_ids.append(id_)

                # Save the query and the hash so that we can determine what the executed query was
                self.register_job_hash(query, session_key)

            ## Form job records
            records = []
            for client in clients:
                records.append({
                    'client': client,
                    'status': OSQueryRestHandler.JOB_STATUS_NEW,
                    'job': queries_obj
                })

                # Make a log entry for each noting that it was created
                for query_id in query_ids:
                    self.log_distributed_query_status(client, OSQueryRestHandler.JOB_STATUS_NEW, query_id, query_name)

        else:
            for client in clients:
                ## Form job records
                for query in queries:

                    # Save the query and the hash so that we can determine what the executed query was
                    self.register_job_hash(query, session_key)

                    queries_obj = {}
                    id_ = self.md5(query) + '_' + self.md5(str(time.time()))
                    queries_obj[id_] = query

                    query_ids.append(id_)

                    # Make a log entry for each noting that it was created
                    self.log_distributed_query_status(client, OSQueryRestHandler.JOB_STATUS_NEW, id_, query_name)

                    records.append({
                        'client': client,
                        'status': 'new',
                        'job': queries_obj
                    })

        ## Write jobs to KvStore
        kvstore = KvStoreHandler()
        try:
            response, _ = kvstore.batch_create(records, session_key, self.JOBS_OPTIONS, include_ts=True)
            if response.status == httplib.OK:
                self.logger.info("Jobs were successfully created, count=%r", len(records))
            else:
                self.logger.error("Unable to save jobs.")
            self.logger.debug("The following job records were being saved: %s", str(records))

        except Exception:
            self.logger.exception('Exception generated when attempting to creates ad-hoc queries')

        return self.response(query_ids, httplib.OK)

    def log_distributed_query_status(self, client, status, query_id, query_name=None):
        '''
        Log the status of a distibuted query.
        '''

        if query_name is None:
            self.logger.info('Query status updated, status=%s, client=%s, query_id=%s', status,
                             client, query_id)
        else:
            self.logger.info('Query status updated, status=%s, client=%s, query_id=%s, query_name=%s',
                             status, client, query_id, query_name)

    @route("/read_distributed_queries", "GET,POST")
    def read_distributed_queries(self, args, params):
        '''
        Get the ad-hoc queries that the client should run. In osquery terminology, this is referred
        to as a "distributed query".
        '''

        node_key = args['form_map'].get('node_key', None)

        self.logger.info('Got request for distributed queries for node=%s', str(node_key))

        session_key = args['session']['authtoken']

        # Record that the host checked-in
        self.checkin_client(node_key, session_key)

        kvstore = KvStoreHandler()
        data = {}
        try:
            ## 1. Confirm client is enrolled
            response, content = kvstore.get(node_key, session_key, self.ENROLLMENT_OPTIONS)

            # if not enrolled ...
            if not response.status == httplib.OK:
                data['node_invalid'] = True
                self.logger.error("Client is not enrolled.")
                return self.response(data, httplib.OK)

            # client is enrolled
            data['node_invalid'] = False
            parsed_content = json.loads(content)
            client = parsed_content['client']

            ## 2. Get client configurations/jobs
            adv_query = {
                'query': {
                    'client': client,
                    'status': 'new'
                },
                'limit': 1
            }

            response, content = kvstore.adv_query(adv_query, self.JOBS_OPTIONS, session_key)
            if not response.status == httplib.OK:
                self.logger.error("An unknown error occured")
                return self.response(data, httplib.INTERNAL_SERVER_ERROR)

            parsed_content = json.loads(content)
            if not parsed_content:
                self.logger.info("No jobs available for client=%s", client)
                return self.response(data, httplib.OK)

            ## 3. Parse configuration/job for client
            job_record = parsed_content[0]
            data['queries'] = job_record['job']

            self.logger.info("Sending jobs available for client=%s, count=%r", client, len(data['queries']))

            ## 4. Set status for retrieve configuration/job to in_progress
            job_record['status'] = OSQueryRestHandler.JOB_STATUS_IN_PROGRESS
            response, content = kvstore.single_update(job_record, job_record['_key'], session_key, self.JOBS_OPTIONS, include_ts=True)

            # Make a log entry noting that the job has changed status
            for query_id in data['queries'].keys():
                self.log_distributed_query_status(client, OSQueryRestHandler.JOB_STATUS_IN_PROGRESS, query_id)

            # TODO: we should come up with a plan for handling scenarios in which we are unable to update status. seems like it may be a pretty rare edge case though.
            if not response.status == httplib.OK:
                self.logger.warning('Unable to update status for query_id=%s, client=%s', job_record['_key'], job_record['client'])

            # Return the response
            return self.response(data, httplib.OK)

        except Exception:
            self.logger.exception('Exception generated when attempting to get the ad-hoc queries')
            return self.response({}, httplib.INTERNAL_SERVER_ERROR)

    def checkin_client(self, node_key, session_key):
        '''
        Set the state of the ad-hoc queries that the client is supposed to run.
        '''

        self.logger.info('Checking in node=%s', str(node_key))

        kvstore = KvStoreHandler()
        record = {
            'client': node_key
        }

        try:
            response, content = kvstore.single_update(record, node_key, session_key, self.CHECKIN_OPTIONS, include_ts=True)

            self.logger.debug('Response: %s', str(response))
            self.logger.debug('Content: %s', str(content))

            if response.status != httplib.OK and response.status != httplib.CREATED:
                self.logger.debug('Response: %s', str(response))
                self.logger.debug('Content: %s', str(content))
                self.logger.error('An unexpected error occurred trying to check-in client %s. HTTP Status: %s', node_key, response.status)
                return False
            else:
                return True

        except splunk.ResourceNotFound:
            self.logger.info('Creating a new check-in record since existing record not for found for node=%s', str(node_key))

            # If the record wasn't found, then create a new record
            response, content = kvstore.create(record, node_key, session_key, self.CHECKIN_OPTIONS, include_ts=True)
            
            if response.status != httplib.OK and response.status != httplib.CREATED:
                self.logger.debug('Response: %s', str(response))
                self.logger.debug('Content: %s', str(content))
                self.logger.error('An unexpected error occurred trying to check-in client %s. HTTP Status: %s', node_key, response.status)
                return False
            else:
                return True

        except Exception:
            self.logger.exception('Exception generated when attempting to check-in client')
            return False

    def register_job_hash(self, query, session_key):
        '''
        Set the state of the ad-hoc queries that the client is supposed to run.
        '''

        hash_value = self.md5(query)

        kvstore = KvStoreHandler()
        record = {
            'query': query,
            'hash': hash_value
        }

        self.logger.debug('Creating a query hash, hash=%s.', hash_value)

        try:
            response, content = kvstore.create(record, hash_value, session_key, self.JOB_HASHES_OPTIONS, include_ts=False)

            if response.status != httplib.CONFLICT:
                self.logger.info('The query hash already existed, hash=%s. HTTP Status: %s', hash_value, response.status)
                return False
            if response.status != httplib.OK and response.status != httplib.CREATED and response.status != httplib.CONFLICT:
                self.logger.error('An unexpected error occurred trying to save a query, hash=%s. HTTP Status: %s', hash_value, response.status)
                return False
            else:
                self.logger.debug('Successfully created the query hash, hash=%s.', hash_value)
                return True

        except splunk.ResourceNotFound:
            self.logger.debug('Query hash already existed, hash=%s.', hash_value)
            return True

        except Exception:
            self.logger.exception('Exception generated when attempting to save query hash')
            return False

    @route("/ping", "GET")
    def ping(self, args, params):
        '''
        Return a response indicating that the REST handler is online.
        '''

        return {
            'payload': 'Online',
            'status': 200,
            'headers': {
                'Content-Type': 'text/plain'
            },
        }

    @route("/set_distributed_query_status", "POST")
    def set_distributed_query_status(self, args, params):
        '''
        Set the status of the query so that we know if the job was handled.
        '''

        client = args['form_map'].get('node_key', None)
        job = args['form_map'].get('query', None)
        status = args['form_map'].get('status', None)

        self.log_distributed_query_status(client, status, job)

        self.logger.debug('Setting status of job=%s', job)

        session_key = args['session']['authtoken']

        if client is not None and job is not None and status is not None:
            ## 1. Get the existing job to update
            adv_query = {
                'query': {
                    'client': client,
                    'job.' + job: {
                        "$regex": ".*"
                    }
                },
                'limit': 1
            }

            kvstore = KvStoreHandler()

            try:
                response, content = kvstore.adv_query(adv_query, self.JOBS_OPTIONS, session_key)
            except splunk.ResourceNotFound:
                self.logger.warning("Unable to find a job to update with query=%s for client=%s", job, client)
                return self.response({}, httplib.NOT_FOUND)
            except Exception:
                self.logger.exception("Exception generated when attempting to retrieve query=%s for client=%s", job, client)
                return self.response({}, httplib.EXPECTATION_FAILED)

            if not response.status == httplib.OK:
                # not sure what error codes the osquery client accepts, returning a generic internal server error
                self.logger.error("An unknown error occured")
                return self.response({}, httplib.INTERNAL_SERVER_ERROR)

            ## 3. Parse the job
            parsed_content = json.loads(content)
            if not parsed_content:
                self.logger.info("No jobs available for client: %s", client)
                return self.response({}, httplib.NOT_FOUND)

            job_record = parsed_content[0]

            ## 4. Set status
            job_record['status'] = status
            response, content = kvstore.single_update(job_record, job_record['_key'], session_key, self.JOBS_OPTIONS, include_ts=False)

            # TODO: we should come up with a plan for handling scenarios in which we are unable to update status. seems like it may be a pretty rare edge case though.
            if not response.status == httplib.OK:
                self.logger.warning('Unable to update status for job ID %s, and client %s.', job_record['_key'], job_record['client'])

            # Return the response
            return self.response({}, httplib.OK)
        else:
            # Return the response
            return self.response({}, httplib.BAD_REQUEST)
