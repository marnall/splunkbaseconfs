
#python imports
import sys
import json
import time
from datetime import datetime
from datetime import timezone
import os
import re

#Splunk Imports
import import_declare_test
from splunklib import modularinput as smi
from splunktaucclib.modinput_wrapper import base_modinput  as base_mi

#File Imports
bin_dir  = os.path.dirname(os.path.abspath(__file__))
app_name = os.path.basename(os.path.dirname(os.getcwd()))

#FalconPy and CrowdStrike Imports
from falconpy import APIHarnessV2, __version__ as falconpy_version
import ScheduledReports_Get_Reports as get_Reports
import Scheduled_Reports_Get_Executions as get_Exec
import Send_to_Splunk as splunk_push
import CrowdStrike_Constants as const
import CSV_Convert as convt_csv
import TA_Data as create_ta_data

def _parse_timestamp(ts_string):
    """Parse ISO 8601 timestamp, tolerant of fractional seconds and Z suffix.

    Python 3.9's fromisoformat() only accepts 0, 3, or 6 fractional digits.
    CrowdStrike API returns variable precision (5, 6, or 9 digits).
    This normalizes all fractional seconds to exactly 6 digits (microseconds).
    """
    clean = ts_string.replace('Z', '+00:00') if ts_string.endswith('Z') else ts_string
    # Normalize fractional seconds to exactly 6 digits (pad short, truncate long)
    clean = re.sub(r'\.(\d{1,6})\d*', lambda m: '.' + m.group(1).ljust(6, '0'), clean)
    return datetime.fromisoformat(clean)

class ModInputCROWDSTRIKE_SCHEDULED_SEARCH(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputCROWDSTRIKE_SCHEDULED_SEARCH, self).__init__(app_name, "crowdstrike_scheduled_search_json", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        scheme = smi.Scheme('crowdstrike_scheduled_search_json')
        scheme.description = 'CrowdStrike Scheduled Search'
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                'name',
                title='Name',
                description='Name',
                required_on_create=True
            )
        )

        scheme.add_argument(smi.Argument("search_name", title="Scheduled Search Name",
                                         description="Enter the full name of the scheduled search from the Falcon UI",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("cloud", title="Select Cloud Environment",
                                         description="Select the appropriate cloud environment for the Falcon Instance",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("credentials", title="API Credential",
                                         description="This is an OAuth2 based API credential with a Scheduled Reports read\' scope",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("collection_option", title="Collection Options",
                                    description="Allows for historic or standard search retrieval",
                                    required_on_create=False,
                                    required_on_edit=False))

        return scheme

    def validate_input(self, definition):
        ta_interval = definition.parameters.get('interval')

        try:
            interval_value = int(ta_interval)
        except (TypeError, ValueError):
            raise ValueError('Interval must be a valid integer.')

        if interval_value < 300:
            raise ValueError('Inputs cannot run at intervals less than 5 minutes (300 seconds). ')

    def get_app_name(self):
        return "TA-crowdstrike-scheduled-search"

    def collect_events(helper, ew):
        #API call limit
        limit = const.limit

        #collect the TA version from the manifest file
        basepath = os.path.dirname(__file__)
        filepath = os.path.abspath(os.path.join(basepath, "..", "app.manifest"))

        with open(filepath, 'r') as manifest:
            manifest_file = json.load(manifest)
            version = manifest_file['info']['id']['version']

        #get stanza name and create the general logging label with version
        stanza_name = helper.get_input_stanza_names()
        log_label = f'CrowdStrike Scheduled Searches TA {version} {stanza_name} :'

        #create user agent string for API calls
        user_agent = f'Splunk_TA_Scheduled_Search_v{version}'

        #get and set logging level
        loglevel = helper.get_log_level()
        helper.set_log_level(loglevel)
        helper.log_info(f'{log_label} Config - Logging level is currently set to: {loglevel}')
        helper.log_info(f'{log_label} Config - FalconPy SDK version: {falconpy_version}')

        #get configuration variables
        credentials = helper.get_arg('credentials')
        if not credentials:
            helper.log_error(f'{log_label} No credentials found - verify the credential account is configured')
            return
        clientid = credentials.get('username')
        secret = credentials.get('password')
        if not clientid or not secret:
            helper.log_error(f'{log_label} Credentials missing username or password - verify the credential account configuration')
            return
        data_index  = helper.get_arg('index')
        search_name = helper.get_arg('search_name')

        #CrowdStrike Cloud selection and baseURL assignment
        api_endpoint = helper.get_arg('cloud')
        helper.log_info(f'{log_label} Config - Cloud environment selected is: {api_endpoint}')

        cloud_map = {
            'us_commercial': const.us_commercial_base,
            'govcloud': const.govcloud_base,
            'govcloud2': const.govcloud2_base,
            'eucloud': const.eucloud_base,
            'us_commercial2': const.us_commercial2_base,
        }
        base_url = cloud_map.get(api_endpoint)
        if base_url is None:
            helper.log_error(f'{log_label} Unsupported cloud environment: {api_endpoint}')
            raise ValueError(f'Unsupported cloud environment: {api_endpoint}')

        collection_option = helper.get_arg('collection_option')
        helper.log_info(f'{log_label} Config - Collection Option = {collection_option}')

        #get proxy setting configuration
        proxy = helper.get_proxy()

        #configure proper proxy syntax for use with FalconPy SDK calls
        if proxy:
            helper.log_info(f'{log_label} Config - Proxy is Set')
            proxy_type = proxy['proxy_type']
            proxy_url = proxy['proxy_url']
            proxy_port = proxy['proxy_port']
            proxy_username = proxy['proxy_username']
            proxy_password = proxy['proxy_password']
            if proxy['proxy_username']:
                helper.log_info(f'{log_label} Config - Proxy is configured with authentication.')
                proxy_string = f'{proxy_type}://{proxy_username}:{proxy_password}@{proxy_url}:{proxy_port}'
                redacted_proxy = f'{proxy_type}://{proxy_username}:***@{proxy_url}:{proxy_port}'
                helper.log_debug(f'{log_label} Proxy configured: {redacted_proxy}')

            else:
                helper.log_info(f'{log_label} Config - Proxy is configured without authentication')
                proxy_string = f'{proxy_type}://{proxy_url}:{proxy_port}'
                helper.log_debug(f'{log_label} Proxy configured: {proxy_string}')

            if proxy_type == 'https':
                proxy_settings = {proxy_type:proxy_string}

            elif proxy_type == 'http':
                proxy_settings = {'http':proxy_string, 'https':proxy_string}

            else:
                helper.log_error(f'{log_label} Config - Unsupported proxy type: {proxy_type}')
                return

        else:
            helper.log_info(f'{log_label} Config - Proxy is not set.')
            proxy_settings = proxy

        #CrowdStrike Authentication - FalconPy UberClass
        falcon = APIHarnessV2(client_id=clientid,client_secret=secret, base_url=base_url, proxy=proxy_settings, user_agent=user_agent, timeout=const.timeout, ssl_verify=True)

        #Forces the authentication process to determine success
        try:
            auth_response = falcon.authenticate()
            auth_result = falcon.authenticated()
            helper.log_info(f'{log_label} Authentication result: authenticated={auth_result}')
            if not auth_result:
                status = falcon.token_status
                reason = falcon.token_fail_reason
                if status is None:
                    helper.log_error(f'{log_label} Authentication failed — no response from CrowdStrike API. Verify network connectivity, proxy settings, DNS resolution, and firewall rules for {api_endpoint}')
                elif isinstance(auth_response, dict):
                    auth_errors = auth_response.get('body', {}).get('errors', [])
                    auth_error_msg = auth_errors[0].get('message', 'No error message') if auth_errors else 'No error message'
                    helper.log_error(f'{log_label} Authentication failed — HTTP {status}: {auth_error_msg}. Verify client_id, client_secret, API scopes (scheduled-reports:read), and cloud environment ({api_endpoint})')
                else:
                    helper.log_error(f'{log_label} Authentication failed — HTTP {status}: {reason}. Verify client_id, client_secret, API scopes (scheduled-reports:read), and cloud environment ({api_endpoint})')
                return
        except Exception as e:
            helper.log_error(f'{log_label} Authentication exception: {type(e).__name__}: {e}')
            return

        #create checkpoint ID
        helper.log_debug(f'{log_label} Checking for or creating a Checkpoint record.')
        stanza_checkpoint = f'report_finish_{stanza_name}'

        #Check for checkpoint data
        try:
            updated_timestamp = helper.get_check_point(stanza_checkpoint)
            if updated_timestamp is None:
                raise KeyError('No checkpoint exists')
            checkpoint= updated_timestamp['report_finish']
            helper.log_info(f'{log_label} Checkpoint data retrieved: {checkpoint}')
        except KeyError:
            helper.log_info(f'{log_label} No checkpoint data was found for this input.')
            checkpoint = '2021-01-01T01:01:01Z'
            helper.log_info(f'{log_label} placeholder checkpoint will be used: {checkpoint}')
        except Exception as e:
            helper.log_error(f'{log_label} Checkpoint data is corrupted: {e} — to recover, search: index=_internal sourcetype=tacrowdstrikescheduledsearch:log "Checkpoint was recorded as" "{stanza_name}" | head 1, then reset the checkpoint via the KV store or delete and recreate the input.')
            raise RuntimeError(f'Checkpoint corruption detected for {stanza_checkpoint}: {e}')

        #safeguard incase timestamp is saved in datetime format
        if 'T' not in checkpoint:
            try:
                checkpoint = _parse_timestamp(checkpoint).strftime('%Y-%m-%dT%H:%M:%SZ')
            except (ValueError, TypeError) as e:
                helper.log_error(f'{log_label} Checkpoint "{checkpoint}" could not be parsed: {e}, using placeholder — this may trigger full historical re-collection')
                checkpoint = '2021-01-01T01:01:01Z'

        #dictionary to hold TA section data and collection timestamp
        current_dateTime = datetime.now(timezone.utc)
        data_collection_timestamp = current_dateTime.strftime('%Y-%m-%dT%H:%M:%SZ')
        ta_data_sets    ={}
        ta_data = {
                "Cloud_environment": api_endpoint,
                "TA_version":version,
                "Collection_option":collection_option,
                "Search_name":search_name,
                "Input_name":stanza_name,
                "Collection_time":data_collection_timestamp
                }


        #list of execution ids to collect data on and dictionary to track non-processed executions
        collection_ids  = []
        status_count    = {}

        #call to get the ID associated with the Scheduled Report name
        try:
            report_ids = get_Reports.getIDS(falcon, search_name, limit, log_label, helper)
            #collect the details about the Scheduled Report ID
            report_details = get_Reports.getReports(falcon, report_ids, log_label, helper)
        except RuntimeError as e:
            helper.log_error(f'{log_label} Report collection failed: {e}')
            return

        #create the reports section for the TA_Data section - holds select information from the Scheduled Report details
        ta_data['Report_Data'] = report_details

        #check if the report is active
        if "next_execution_on" not in ta_data['Report_Data']:
            helper.log_warning(f'{log_label} The {search_name} report does not have a next execution scheduled, ensure that it is enabled or not expiring. Current status shows: {ta_data["Report_Data"]["status"]}')

        #collects the execution IDs associated with the report ID
        try:
            exec_ids = get_Exec.getExecutions(falcon, report_ids, checkpoint, limit, collection_option, log_label, helper)
        except RuntimeError as e:
            helper.log_error(f'{log_label} Failed to collect execution IDs: {e}')
            return

        #collects the execution IDs associated with the report ID
        if len(exec_ids) > 0:
            helper.log_info(f'{log_label} The number of executions identified for report {search_name} was: {len(exec_ids)}')
        else:
            helper.log_info(f'{log_label} There were no execution IDs matching the current collection criteria for report {search_name}, the TA will now shutdown')
            return

        if collection_option == 'standard':
            helper.log_info(f'{log_label} Attempting to collect the last execution for report {search_name} - {exec_ids[0]}')
            exec_ids = [exec_ids[0]]

        #collect the execution details for the IDs
        try:
            exec_details = get_Exec.getExecDetails(falcon, exec_ids, log_label, helper)
        except RuntimeError as e:
            helper.log_error(f'{log_label} Failed to collect execution details: {e}')
            return

        #create the ta_data section for specific excutions
        collection_ids, ta_data_sets = create_ta_data.create_TA_Data(ta_data, ta_data_sets, collection_ids, status_count, exec_details, log_label, helper)

        #check to ensure that there are execuation ids that require data collection
        if len(collection_ids) > 0:
            helper.log_info(f'{log_label} The number of search executions for report {search_name} that need to be collected and reviewed is: {len(collection_ids)}')
        else:
            helper.log_info(f'{log_label} No search executions with results were found for report {search_name} - the TA will now shutdown')
            return

        #CrowdStike envornmental keys to remove
        cs_keys = [ 'eventtype', 'host', 'index', 'source', 'sourcetype','splunk_server']

        #for each execution ID get the report, append the TA data section and send to Splunk
        current_checkpoint = checkpoint
        total_events = 0

        for ex_id in collection_ids:
            try:
                helper.log_info(f'{log_label} Processing execution {ex_id}')
                #calls to get the binary file download
                reportFile_data = get_Exec.getReportFile(falcon, ex_id, log_label, helper)

                #skip executions that returned no report data
                if isinstance(reportFile_data, bytes) and len(reportFile_data) == 0:
                    helper.log_warning(f'{log_label} Execution {ex_id} returned empty report data, skipping')
                    continue

                #Identify CSV formated reports and convert to JSON
                data_format = ta_data_sets[ex_id].get('Report_Data', {}).get('report_params', {}).get('format', 'json')
                helper.log_info(f'{log_label} Format detected as: {data_format}')
                if data_format == 'csv':
                    helper.log_warning(f'{log_label} CSV formatted search results detected. The TA will attempt to convert to JSON, but for the best/most consistent results the report format should be changed to JSON at your earliest convenience.')
                    reportFile_data = convt_csv.csv_convert(log_label,reportFile_data, helper)
                else:
                    #guard against unexpected bytes return for non-CSV formats
                    if isinstance(reportFile_data, bytes):
                        try:
                            reportFile_data = json.loads(reportFile_data)
                        except (json.JSONDecodeError, UnicodeDecodeError) as e:
                            helper.log_error(f'{log_label} Failed to parse bytes response as JSON for execution {ex_id}: {e}')
                            continue
                        if isinstance(reportFile_data, dict):
                            reportFile_data = reportFile_data.get('resources', reportFile_data.get('results', []))
                            if not reportFile_data:
                                helper.log_warning(f'{log_label} Execution {ex_id}: JSON response was a dict with no extractable event list, skipping')
                                continue
                        if not isinstance(reportFile_data, list):
                            helper.log_error(f'{log_label} Execution {ex_id}: unexpected JSON structure — expected list, got {type(reportFile_data).__name__}, skipping')
                            continue

                # Guard against empty report data (list path)
                if not reportFile_data:
                    helper.log_warning(f'{log_label} Execution {ex_id} returned empty report data, skipping')
                    continue

                #remove CS Splunk specific fields and add ta_data section to events
                exec_report_finish = ta_data_sets[ex_id].get('Execution_Data', {}).get('result_metadata', {}).get('report_finish')
                if not exec_report_finish:
                    helper.log_warning(f'{log_label} Execution {ex_id} missing report_finish timestamp in execution data, skipping')
                    continue

                for report in reportFile_data:

                    for key in cs_keys:
                        if key in report:
                            del report[key]
                    report['ta_data'] = ta_data_sets[ex_id]

                #determine if this execution's timestamp would advance the checkpoint
                exec_checkpoint = exec_report_finish
                helper.log_debug(f'{log_label} Execution {ex_id} timestamp: {exec_checkpoint}, current checkpoint: {checkpoint}')

                #validate timestamps before pushing data
                try:
                    checkpoint_compare = _parse_timestamp(checkpoint)
                    exec_compare = _parse_timestamp(exec_checkpoint)
                except (ValueError, TypeError) as e:
                    helper.log_error(f'{log_label} Execution {ex_id}: timestamp parse error — cannot process this execution')
                    helper.log_error(f'{log_label} Checkpoint value: "{checkpoint}", execution report_finish: "{exec_checkpoint}", error: {e}')
                    helper.log_error(f'{log_label} To skip this execution, create a new input with a start time after the problematic timestamp: "{exec_report_finish}"')
                    helper.log_error(f'{log_label} Last successful checkpoint: {current_checkpoint}')
                    raise RuntimeError(f'Timestamp parse failure for execution {ex_id}')

                #send to Splunk forwarder
                helper.log_debug(f'{log_label} Preparing to send Data from report {search_name}, execution {ex_id} to the Splunk API')
                completed = splunk_push.send_to_splunk(search_name, reportFile_data, log_label, data_index, data_format, helper, ew)
                if completed:
                    total_events += len(reportFile_data)
                    helper.log_info(f'{log_label} Data from report {search_name}, execution {ex_id} has been pushed to Splunk API')
                else:
                    helper.log_error(f'{log_label} Failed to send data from execution {ex_id} to Splunk')
                    helper.log_error(f'{log_label} Please verify Splunk is running and the index "{data_index}" is accessible')
                    helper.log_error(f'{log_label} Last successful checkpoint: {current_checkpoint} — data collection will resume from this point on next run')
                    raise RuntimeError(f'Splunk push failed for execution {ex_id}')

                #advance checkpoint if this execution is newer
                if exec_compare > checkpoint_compare:
                    old_checkpoint = checkpoint
                    checkpoint = exec_checkpoint
                    helper.log_info(f'{log_label} {ex_id}: Checkpoint advanced from {old_checkpoint} to {checkpoint}')
                else:
                    helper.log_info(f'{log_label} {ex_id}: Checkpoint unchanged at {checkpoint} (execution timestamp {exec_checkpoint} is not newer)')

                #Save Checkpoint Data
                if _parse_timestamp(current_checkpoint) < _parse_timestamp(checkpoint):
                    helper.log_info(f'{log_label} Attempting to save checkpoint data for report {search_name} execution {ex_id} to Splunk KV store')
                    checkpoint_key='report_finish'
                    checkpoint_save={checkpoint_key:str(checkpoint)}
                    checkpoint_saved = False
                    for save_attempt in range(3):
                        try:
                            helper.save_check_point(stanza_checkpoint, checkpoint_save)
                            helper.log_info(f'{log_label} {ex_id} Checkpoint was recorded as {checkpoint_save}')
                            checkpoint_saved = True
                            current_checkpoint = checkpoint
                            break
                        except Exception as e:
                            wait = 2 * (save_attempt + 1)
                            helper.log_warning(f'{log_label} Checkpoint save attempt {save_attempt + 1}/3 failed: {e}, retrying in {wait}s')
                            time.sleep(wait)
                    if not checkpoint_saved:
                        helper.log_error(f'{log_label} Unable to record last update checkpoint data after 3 attempts')
                        helper.log_error(f'{log_label} Please correct the issue, the TA will now exit to try and prevent duplicate event ingestion.')
                        raise RuntimeError(f'Checkpoint save failed for {stanza_checkpoint}')
                else:
                    helper.log_info(f'{log_label} {ex_id}: Checkpoint not advanced, retaining {current_checkpoint}')

            except RuntimeError as e:
                helper.log_error(f'{log_label} Fatal error processing execution {ex_id}: {e}')
                helper.log_error(f'{log_label} Stopping collection to prevent duplicate event ingestion.')
                return
            except (TypeError, KeyError, ValueError) as e:
                helper.log_error(f'{log_label} Unexpected error processing execution {ex_id}: {type(e).__name__}: {e}, skipping to next execution')
                continue

        helper.log_info(f'{log_label} Collection complete — {total_events} total events from {len(collection_ids)} executions for report {search_name}')
        if total_events == 0 and len(collection_ids) > 0:
            helper.log_error(f'{log_label} All {len(collection_ids)} executions were fetched but none produced deliverable data — checkpoint remains at {current_checkpoint}. Investigate execution data quality for report {search_name}.')

    def get_account_fields(self):
        account_fields = []
        return account_fields

    def get_checkbox_fields(self):
        checkbox_fields = []
        return checkbox_fields

    def get_global_checkbox_fields(self):
        if self.global_checkbox_fields is None:
            checkbox_name_file = os.path.join(bin_dir, 'global_checkbox_param.json')
            try:
                if os.path.isfile(checkbox_name_file):
                    with open(checkbox_name_file, 'r') as fp:
                        self.global_checkbox_fields = json.load(fp)
                else:
                    self.global_checkbox_fields = []
            except Exception as e:
                self.log_error(f'Get exception when loading global checkbox parameter names. {e}')
                self.global_checkbox_fields = []
        return self.global_checkbox_fields


if __name__ == '__main__':
    exit_code = ModInputCROWDSTRIKE_SCHEDULED_SEARCH().run(sys.argv)
    sys.exit(exit_code)
