# File: reversinglabs_ticloud_connector.py
#
# Copyright (c) ReversingLabs Inc 2016-2022
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#

import collections
import hashlib
# Other imports used by this connector
import json

# Phantom imports
import phantom.app as phantom
import phantom.rules as ph_rules
import requests
from phantom.app import ActionResult, BaseConnector
from phantom.vault import Vault
from requests import ConnectionError, HTTPError
from requests.auth import HTTPBasicAuth
# Wheels import
from rl_threat_hunting import cloud, constants, file_report, mwp_metadata_adapter
from rl_threat_hunting.plugins import joe_sandbox

# THIS Connector imports
from reversinglabs_ticloud_consts import *


class ReversinglabsConnector(BaseConnector):

    # The actions supported by this connector
    ACTION_ID_FILE_REPUTATION = 'file_reputation'
    ACTION_ID_ADV_SEARHC = 'adv_search'
    ACTION_ID_RHA1_ANALYTICS = 'file_similarity'
    ACTION_ID_URI_STATISTICS = 'uri_statistics'
    ACTION_ID_CERT_ANALYTICS = 'certificate_analytics'
    ACTION_ID_ADD_JOE_RESULTS = 'add_joe_results'

    def __init__(self):
        super(ReversinglabsConnector, self).__init__()

        self._headers = {'content-type': 'application/octet-stream', 'User-Agent': 'ReversingLabs Phantom TiCloud v2.3'}
        self._auth = None
        self._base_url = TICLOUD_AWS_HOST_NAME
        self._mwp_url = TICLOUD_AWS_HOST_NAME + MAL_PRESENCE_API_URL
        self._xref_url = TICLOUD_AWS_HOST_NAME + XREF_API_URL
        self._search_url = TICLOUD_AWS_HOST_NAME + ADVANCED_SEARCH_API_URL
        self._rha1_url = TICLOUD_AWS_HOST_NAME + RHA1_ANALYTICS_API_URL
        self._cert_analytics_url = TICLOUD_AWS_HOST_NAME + CERTIFICATE_ANALYTICS_URL
        self._verify_cert = True

        self.ACTIONS = {
            phantom.ACTION_ID_TEST_ASSET_CONNECTIVITY: self.action_asset_connectivity,
            self.ACTION_ID_FILE_REPUTATION: self.action_file_reputation,
            self.ACTION_ID_ADV_SEARHC: self.action_advanced_search,
            self.ACTION_ID_RHA1_ANALYTICS: self.action_file_similarity_analytics,
            self.ACTION_ID_URI_STATISTICS: self.action_uri_statistics,
            self.ACTION_ID_CERT_ANALYTICS: self.action_cert_analytics,
            self.ACTION_ID_ADD_JOE_RESULTS: self.action_add_joe_results,
        }

    def initialize(self):
        config = self.get_config()

        self._auth = HTTPBasicAuth(
            phantom.get_req_value(config, phantom.APP_JSON_USERNAME),
            phantom.get_req_value(config, phantom.APP_JSON_PASSWORD),
        )

        if 'url' in config:
            self._base_url = config.get('url').rstrip('/')
            self._mwp_url = '{0}{1}'.format(self._base_url, MAL_PRESENCE_API_URL)
            self._xref_url = '{0}{1}'.format(self._base_url, XREF_API_URL)
            self._search_url = '{0}{1}'.format(self._base_url, ADVANCED_SEARCH_API_URL)
            self._rha1_url = '{0}{1}'.format(self._base_url, RHA1_ANALYTICS_API_URL)
            self._cert_analytics_url = '{0}{1}'.format(self._base_url, CERTIFICATE_ANALYTICS_URL)

        if 'verify_server_cert' in config:
            self._verify_cert = config['verify_server_cert']

        self.debug_print('self.status', self.get_status())

        return phantom.APP_SUCCESS

    def _validate_integer(self, parameter, key, allow_zero=False):
        """ This method is to check if the provided input parameter value
        is a non-zero positive integer and returns the integer value of the parameter itself.
        :param action_result: Action result or BaseConnector object
        :param parameter: input parameter
        :param key: action parameter key
        :param allow_zero: action parameter allowed zero value or not
        :return: integer value of the parameter or None in case of failure
        """

        if parameter is not None:
            try:
                if not float(parameter).is_integer():
                    raise Exception(VALID_INTEGER_MSG.format(key))

                parameter = int(parameter)
            except Exception:
                raise Exception(VALID_INTEGER_MSG.format(key))

            if parameter < 0:
                raise Exception(NON_NEGATIVE_INTEGER_MSG.format(key))

            if not allow_zero and parameter == 0:
                raise Exception(POSITIVE_INTEGER_MSG.format(key))

        return parameter

    def handle_action(self, param):
        action_id = self.get_action_identifier()
        action = self.ACTIONS.get(action_id)
        if not action:
            return

        action_result = self.add_action_result(ActionResult(dict(param)))
        try:
            success_message = action(action_result, param)
        except requests.HTTPError as err:
            return action_result.set_status(phantom.APP_ERROR, 'Request to server failed. {}'.format(err))
        except Exception as err:
            return action_result.set_status(phantom.APP_ERROR, str(err))

        if success_message:
            return action_result.set_status(phantom.APP_SUCCESS, success_message)

        return action_result.set_status(phantom.APP_SUCCESS)

    def action_advanced_search(self, action_result, param):
        hunting_report, vault_id = self._get_threat_hunting_state(param)
        single_search_term = param.get(REVERSINGLABS_JSON_ADVANCED_SEARCH)
        results_per_page = self._validate_integer(param.get("results_per_page"), RESULTS_PER_PAGE_KEY)
        page_number = self._validate_integer(param.get("page_number"), PAGE_NUMBER_KEY)

        if not param.get(REVERSINGLABS_JSON_HUNTING_REPORT) and not single_search_term:
            raise Exception("Parameters 'hunting report vault id' and 'search parameter' not provided. At least one is needed.")

        if hunting_report:
            self._hunting_with_advanced_search(action_result, hunting_report, vault_id, results_per_page, page_number)
        elif single_search_term:
            self._advanced_search_make_single_query(action_result, single_search_term, results_per_page, page_number)
        else:
            raise ApplicationExecutionFailed('Unable to get data from provided input')

    def _hunting_with_advanced_search(self, action_result, hunting_report, vault_id, results_per_page, page_number):
        search_tasks = cloud.get_query_tasks(hunting_report, constants.HuntingCategory.ADVANCED_SEARCH)

        if not search_tasks:
            self._update_threat_hunting_state(action_result, hunting_report, vault_id)
            return

        for task in search_tasks:
            search_term = task['query']['term']

            if 'classification:' in search_term:
                search_function = self._make_search_api_request
            else:
                search_function = self._make_double_search_api_request

            try:
                api_data = search_function(search_term, results_per_page, page_number)  # tu
            except (HTTPError, ConnectionError):
                cloud.mark_tasks_as_failed(hunting_report, task)
                continue

            try:
                cloud.update_hunting_meta(hunting_report, api_data, task)
            except StopIteration:
                break

        hunting_meta_vault_id = self._store_threat_hunting_state(hunting_report)
        self._update_threat_hunting_state(action_result, hunting_report, hunting_meta_vault_id)

    def _make_double_search_api_request(self, task_term, results_per_page, page_number):
        api_data = tuple()
        for search_term in [task_term + ' AND classification:malicious',
                             task_term + ' AND classification:known']:
            response = self._make_search_api_request(search_term, results_per_page, page_number)
            api_data += (response,)
        return api_data

    def _advanced_search_make_single_query(self, action_result, search_term, results_per_page, page_number):
        api_data = self._make_search_api_request(search_term, results_per_page, page_number)
        action_result.add_data(api_data)

    def _make_search_api_request(self, search_term, results_per_page, page_number):
        post_data = {'query': search_term, 'format': 'json', 'page': page_number or 1,
            'records_per_page': results_per_page or MAX_SEARCH_RESULTS}
        response = requests.post(self._search_url,
                                  timeout=10,
                                  data=json.dumps(post_data),
                                  auth=self._auth, headers=self._headers, verify=self._verify_cert)

        if response.ok:
            return response.json()

        response.raise_for_status()

    def action_file_similarity_analytics(self, action_result, param):
        hunting_report, vault_id = self._get_threat_hunting_state(param)
        single_hash_value, rha1_type = self._get_single_file_similarity_parameter(param)

        if not param.get(REVERSINGLABS_JSON_HUNTING_REPORT) and not param.get(phantom.APP_JSON_HASH):
            raise Exception('No parameters provided. At least one is needed.')

        if hunting_report:
            self._hunting_with_file_similarity(action_result, hunting_report, vault_id)
        elif single_hash_value:
            self._file_similarity_make_single_query(action_result, single_hash_value, rha1_type)
        else:
            raise ApplicationExecutionFailed('Unable to get data from provided input')

    def _get_single_file_similarity_parameter(self, parameters):
        sha1_value = parameters.get(phantom.APP_JSON_HASH)
        sample_type = parameters.get(REVERSINGLABS_JSON_SAMPLE_TYPE)

        if not sha1_value and not sample_type:
            return None, None

        if sha1_value and not phantom.is_sha1(sha1_value):
            raise ApplicationExecutionFailed('Provided file hash must be SHA1')

        rha1_type = None
        if sample_type:
            rha1_type = self._get_rha1_type(sample_type)
            if not rha1_type:
                raise ApplicationExecutionFailed(
                    'Invalid file type for RHA1 analytics. Only PE, ELF and MachO files are supported')

        return sha1_value, rha1_type

    @staticmethod
    def _get_rha1_type(sample_type):
        if sample_type.startswith('MachO'):
            return 'macho01'
        if sample_type.startswith('ELF'):
            return 'elf01'
        if sample_type.startswith('PE'):
            return'pe01'

    def _hunting_with_file_similarity(self, action_result, hunting_report, vault_id):
        file_similarity_tasks = cloud.get_query_tasks(hunting_report, constants.HuntingCategory.FILE_SIMILARITY_ANALYTICS)

        if not file_similarity_tasks:
            self._update_threat_hunting_state(action_result, hunting_report, vault_id)
            return

        categorized_file_similarity_tasks = self._categorize_file_similarity_tasks(file_similarity_tasks)

        for rha1_type in categorized_file_similarity_tasks:
            tasks = categorized_file_similarity_tasks[rha1_type]

            for tasks_batch in self.make_batches(tasks, MAX_BULK_HASHES_RHA1):
                terms = [task['query']['term'] for task in tasks_batch]
                hashes = [term.split('/')[1] for term in terms]

                try:
                    api_data = self._make_file_similarity_post_api_request(rha1_type, hashes)
                except (HTTPError, ConnectionError):
                    cloud.mark_tasks_as_failed(hunting_report, *tasks_batch)
                    continue

                cloud.update_hunting_meta(hunting_report, api_data, *tasks_batch)

        hunting_meta_vault_id = self._store_threat_hunting_state(hunting_report)
        self._update_threat_hunting_state(action_result, hunting_report, hunting_meta_vault_id)

    @staticmethod
    def _categorize_file_similarity_tasks(file_similarity_tasks):
        categorized_tasks = collections.defaultdict(list)
        for task in file_similarity_tasks:
            term = task['query']['term']
            rha1_type, _ = term.split('/')
            categorized_tasks[rha1_type].append(task)
        return categorized_tasks

    def _file_similarity_make_single_query(self, action_result, hash_value, rha1_type):
        api_data = self._make_file_similarity_post_api_request(rha1_type, [hash_value])
        action_result.add_data(api_data)

    def _make_file_similarity_post_api_request(self, rha1_type, hashes):
        post_data = {'rl': {'query': {'rha1_type': rha1_type, 'extended': 'true', 'response_format': 'json', 'hashes': hashes}}}
        response = requests.post(self._rha1_url,
                                  timeout=10,
                                  data=json.dumps(post_data),
                                  auth=self._auth, headers=self._headers, verify=self._verify_cert)

        if response.ok or response.status_code == requests.status_codes.codes.NOT_FOUND:
            return response.json()

        response.raise_for_status()

    def action_uri_statistics(self, action_result, param):
        hunting_report, vault_id = self._get_threat_hunting_state(param)
        uri_term = param.get(REVERSINGLABS_JSON_URI)

        if not param.get(REVERSINGLABS_JSON_HUNTING_REPORT) and not uri_term:
            raise Exception('No parameters provided. At least one is needed.')

        if hunting_report:
            self._hunting_with_uri_statistics(action_result, hunting_report, vault_id)
        elif uri_term:
            self._uri_statistics_make_single_query(action_result, uri_term)
        else:
            raise ApplicationExecutionFailed('Unable to get data from provided input')

    def _hunting_with_uri_statistics(self, action_result, hunting_report, vault_id):
        uri_tasks = cloud.get_query_tasks(hunting_report, constants.HuntingCategory.URI_ANALYTICS)

        if not uri_tasks:
            self._update_threat_hunting_state(action_result, hunting_report, vault_id)
            return

        for task in uri_tasks:
            uri_term = task['query']['term']

            try:
                api_data = self._make_uri_statistics_api_request(uri_term)
            except (HTTPError, ConnectionError):
                cloud.mark_tasks_as_failed(hunting_report, task)
                continue

            cloud.update_hunting_meta(hunting_report, api_data, task)

        hunting_meta_vault_id = self._store_threat_hunting_state(hunting_report)
        self._update_threat_hunting_state(action_result, hunting_report, hunting_meta_vault_id)

    def _uri_statistics_make_single_query(self, action_result, uri_term):
        api_data = self._make_uri_statistics_api_request(uri_term)
        action_result.add_data(api_data)

    def _make_uri_statistics_api_request(self, uri_term):
        uri_sha1 = self._generate_sha1_hash(uri_term)
        uri_request_url = '{0}{1}'.format(self._base_url, URI_STATISTICS_API_URL.format(sha1=uri_sha1))
        response = requests.get(uri_request_url, timeout=10, auth=self._auth, headers=self._headers, verify=self._verify_cert)

        if response.ok:
            return response.json()
        elif response.status_code == requests.status_codes.codes.NOT_FOUND:
            return None

        response.raise_for_status()

    def action_cert_analytics(self, action_result, param):
        hunting_report, vault_id = self._get_threat_hunting_state(param)
        thumbprint_value = param.get(REVERSINGLABS_JSON_THUMBPRINT)

        if not param.get(REVERSINGLABS_JSON_HUNTING_REPORT) and not thumbprint_value:
            raise Exception('No parameters provided. At least one is needed.')

        if hunting_report:
            self._hunting_with_certificate_analytics(action_result, hunting_report, vault_id)
        elif thumbprint_value:
            self._cert_analytics_make_single_query(action_result, thumbprint_value)
        else:
            raise ApplicationExecutionFailed('Unable to get data from provided input')

    def _hunting_with_certificate_analytics(self, action_result, hunting_report, vault_id):
        cert_tasks = cloud.get_query_tasks(hunting_report, constants.HuntingCategory.CERTIFICATE_ANALYTICS)

        if not cert_tasks:
            self._update_threat_hunting_state(action_result, hunting_report, vault_id)
            return

        for tasks_bulk in self.make_batches(cert_tasks, MAX_BULK_HASHES_CERT):
            thumbprints = [task['query']['term'] for task in tasks_bulk]

            try:
                api_data = self._make_certificate_analytics_api_request(thumbprints)
            except (HTTPError, ConnectionError):
                cloud.mark_tasks_as_failed(hunting_report, *tasks_bulk)
                continue

            cloud.update_hunting_meta(hunting_report, api_data, *tasks_bulk)

        hunting_meta_vault_id = self._store_threat_hunting_state(hunting_report)
        self._update_threat_hunting_state(action_result, hunting_report, hunting_meta_vault_id)

    def _cert_analytics_make_single_query(self, action_result, thumbprint):
        api_data = self._make_certificate_analytics_api_request([thumbprint])
        action_result.add_data(api_data)

    def _make_certificate_analytics_api_request(self, thumpbrints):
        post_data = {'rl': {'query': {'thumbprints': thumpbrints, 'format': 'json'}}}
        response = requests.post(self._cert_analytics_url,
                                 timeout=10,
                                 data=json.dumps(post_data),
                                 auth=self._auth, headers=self._headers, verify=self._verify_cert)

        if response.ok:
            return response.json()

        response.raise_for_status()

    @staticmethod
    def _determine_valid_hash_type(value):
        if phantom.is_md5(value):
            return 'md5'
        if phantom.is_sha1(value):
            return 'sha1'
        if phantom.is_sha256(value):
            return 'sha256'
        raise ApplicationExecutionFailed('Must be valid MD5, SHA1 or SHA256 hash value')

    def action_asset_connectivity(self, action_result, param):
        # just MWP for now, need to test other APIs, at least one should work.

        sha1_hash = self._generate_random_sha1_hash()
        self.save_progress(REVERSINGLABS_GENERATED_RANDOM_HASH)

        query = {'rl': {'query': {'hash_type': 'sha1', 'hashes': [sha1_hash]}}}
        response = requests.post(self._mwp_url, auth=self._auth, json=query, timeout=10,
                                 headers=self._headers, verify=self._verify_cert)

        if not response.ok:
            status_message = '{0}. {1}. HTTP status_code: {2}, reason: {3}, URL: {4}'.format(
                REVERSINGLABS_ERR_CONNECTIVITY_TEST, REVERSINGLABS_MSG_CHECK_CREDENTIALS,
                response.status_code, response.reason, self._mwp_url
            )
            raise Exception(status_message)

        self.save_progress(REVERSINGLABS_SUCC_CONNECTIVITY_TEST)
        return REVERSINGLABS_SUCC_CONNECTIVITY_TEST

    @classmethod
    def _generate_random_sha1_hash(cls):
        random_string = phantom.get_random_chars(size=10)
        return cls._generate_sha1_hash(random_string)

    @staticmethod
    def _generate_sha1_hash(value):
        sha1 = hashlib.sha1(str(value).encode('utf-8'))
        return sha1.hexdigest()

    def action_file_reputation(self, action_result, param):
        hunting_report, vault_id = self._get_threat_hunting_state(param)
        single_hash_value, hash_type = self._get_single_hash_parameter(param)

        if not param.get(REVERSINGLABS_JSON_HUNTING_REPORT) and not param.get(phantom.APP_JSON_HASH):
            raise Exception('No parameters provided. At least one is needed.')

        if hunting_report:
            self._hunt_with_file_reputation(action_result, hunting_report, vault_id)
        elif single_hash_value:
            self._file_reputation_creates_new_hunting_state(action_result, hash_type, single_hash_value)
        else:
            raise ApplicationExecutionFailed('Unable to get data from provided input')

    def _get_single_hash_parameter(self, parameters):
        hash_value = parameters.get(phantom.APP_JSON_HASH)
        if hash_value:
            hash_type = self._determine_valid_hash_type(hash_value)
            return hash_value, hash_type
        return None, None

    def _hunt_with_file_reputation(self, action_result, hunting_report, vault_id):
        reputation_tasks = cloud.get_query_tasks(hunting_report, constants.HuntingCategory.CLOUD_REPUTATION)

        if not reputation_tasks:
            self._update_threat_hunting_state(action_result, hunting_report, vault_id)
            return

        categorized_file_reputation_tasks = self._categorize_file_reputation_tasks(reputation_tasks)

        for hash_type in categorized_file_reputation_tasks:
            tasks = categorized_file_reputation_tasks[hash_type]

            for tasks_batch in self.make_batches(tasks, MAX_BULK_HASHES_MWP):
                hashes = [task['query']['term'] for task in tasks_batch]

                try:
                    api_data = self._make_file_reputation_api_request(hash_type, hashes)
                except (HTTPError, ConnectionError):
                    cloud.mark_tasks_as_failed(hunting_report, *tasks_batch)
                    continue

                cloud.update_hunting_meta(hunting_report, api_data, *tasks_batch)

        hunting_meta_vault_id = self._store_threat_hunting_state(hunting_report)
        self._update_threat_hunting_state(action_result, hunting_report, hunting_meta_vault_id)

    def _categorize_file_reputation_tasks(self, query_tasks):
        categorized_tasks = {}
        for task in query_tasks:
            hash_value = task['query']['term']
            hash_type = self._determine_valid_hash_type(hash_value)

            category_hashes = categorized_tasks.setdefault(hash_type, [])
            category_hashes.append(task)

        return categorized_tasks

    def _file_reputation_creates_new_hunting_state(self, action_result, hash_type, hash_value):
        api_data = self._make_file_reputation_api_request(hash_type, [hash_value])
        hunting_report = mwp_metadata_adapter.parse_mwp_metadata(api_data)

        hunting_meta_vault_id = self._store_threat_hunting_state(hunting_report)
        self._update_threat_hunting_state(action_result, hunting_report, hunting_meta_vault_id)

    def _make_file_reputation_api_request(self, hash_type, hashes):
        post_data = {'rl': {'query': {'hash_type': hash_type, 'hashes': hashes}}}
        response = requests.post(self._mwp_url,
                                  timeout=10,
                                  data=json.dumps(post_data),
                                  auth=self._auth, headers=self._headers, verify=self._verify_cert)

        if response.ok:
            return response.json()

        response.raise_for_status()

    def action_add_joe_results(self, action_result, param):
        hunting_report, vault_id = self._get_threat_hunting_state(param)
        joe_report_vault_id = param.get(REVERSINGLABS_JSON_JOE_REPORT)

        if not hunting_report and not joe_report_vault_id:
            raise ApplicationExecutionFailed('No parameters provided. At least one is needed.')

        joe_report = None
        if joe_report_vault_id:
            success, msg, files_array = ph_rules.vault_info(vault_id=joe_report_vault_id)
            if not success:
                raise Exception(f'Unable to get Vault item details. Error Details: {msg}')
            file_data = list(files_array)[0]
            with open(file_data['path'], 'rb') as f:
                payload = f.read()
            joe_report = json.loads(payload.decode('utf-8'))

        if hunting_report:
            joe_sandbox.add_dynamic_analysis(hunting_report, joe_report)
            hunting_meta_vault_id = self._store_threat_hunting_state(hunting_report)
            self._update_threat_hunting_state(action_result, hunting_report, hunting_meta_vault_id)

        else:
            action_result.add_data({'joe_report': joe_report})

    def finalize(self):
        total_positives = 0
        for action_result in self.get_action_results():
            action_id = self.get_action_identifier()

            if action_id == self.ACTION_ID_FILE_REPUTATION:
                self._update_summary_for_file_reputation(action_result, total_positives)

    def _update_summary_for_file_reputation(self, action_result, total_positives):
        summary = action_result.get_summary()

        positive_detections = summary.get(REVERSINGLABS_JSON_POSITIVES)
        if positive_detections:
            total_positives += 1
            self.update_summary({REVERSINGLABS_JSON_TOTAL_POSITIVES: total_positives})

    @staticmethod
    def make_batches(data, max_length):
        number_of_batches = range(0, len(data), max_length)
        for start_index in number_of_batches:
            end_index = start_index + max_length
            yield data[start_index:end_index]

    @staticmethod
    def _get_threat_hunting_state(parameters):
        hunting_report_vault_id = parameters.get(REVERSINGLABS_JSON_HUNTING_REPORT)
        if hunting_report_vault_id:
            success, msg, files_array = ph_rules.vault_info(vault_id=hunting_report_vault_id)
            if not success:
                raise Exception(f'Unable to get Vault item details. Error Details: {msg}')
            file_data = list(files_array)[0]
            with open(file_data['path'], 'rb') as f:
                payload = f.read()
            return json.loads(payload.decode('utf-8')), hunting_report_vault_id

        return None, None

    def _store_threat_hunting_state(self, hunting_meta):
        container_id = self.get_container_id()
        vault_file_name = self._create_hunting_report_name()
        dump_path = self._dump_report_in_file(hunting_meta, vault_file_name)
        success, message, vault_id = ph_rules.vault_add(container_id, dump_path, file_name=vault_file_name)

        if success:
            return vault_id
        else:
            raise VaultError('Storing threat hunting report failed: ' + message)

    def _create_hunting_report_name(self):
        product_name = self._get_product_name()
        action_name = self._get_action_name()
        return '{}_{}_hunting_report.json'.format(product_name, action_name)

    def _get_product_name(self):
        app_config = self.get_app_json()
        product_name = app_config['product_name']
        return product_name.replace(' ', '_')

    def _get_action_name(self):
        action_name = self.get_action_name()
        return action_name.replace(' ', '_')

    @staticmethod
    def _dump_report_in_file(hunting_meta, file_name):
        dump_dir = Vault.get_vault_tmp_dir()
        dump_path = '{}/{}'.format(dump_dir, file_name)
        return file_report.write_json(hunting_meta, dump_path)

    @staticmethod
    def _update_threat_hunting_state(action_result, hunting_report, hunting_report_vault_id):
        action_result.add_data(hunting_report)
        action_result.add_data({REVERSINGLABS_JSON_HUNTING_REPORT: hunting_report_vault_id})


class ApplicationExecutionFailed(Exception):
    pass


class VaultError(Exception):
    pass


def test_with_action_json():
    import argparse

    parser = argparse.ArgumentParser('Test arguments')
    parser.add_argument('input_json', help='Input action json file path.')
    parser.add_argument('-p', '--pudb', required=False, action='store_true', help='Use visual python debugger.')
    args = parser.parse_args()

    if args.pudb:
        import pudb
        pudb.set_trace()

    with open(args.input_json) as action_input_json:
        input_data = json.loads(action_input_json.read())

    print(json.dumps(input_data, indent=4))

    connector = ReversinglabsConnector()
    connector.print_progress_message = True

    action_result_text = connector._handle_action(json.dumps(input_data), None)
    try:
        action_result = json.loads(action_result_text)
        print(json.dumps(action_result, indent=4))
    except TypeError:
        print(action_result_text)


if __name__ == '__main__':

    test_with_action_json()
