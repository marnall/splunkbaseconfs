import time

from falconpy import APIHarnessV2

import crowdstrike_constants as const
from Status_Code_Errors_Splunk import Status_Code_Errors
from CS_FileVantage_Get_Details import Get_CS_Details
from Send_to_Splunk import Post_to_Splunk


class Get_CS_IDs():

    def query_for_ids(api_config, query_params, checkpoint, stanza_checkpoint, log_label, ta_data, helper, ew, total_results=None):

        if total_results is None:
            total_results = []

        api_endpoint = "FV: highVolumeQueryChanges"
        max_retries = 3

        # Unpack query params
        cs_filter = query_params['filter']
        limit = query_params['limit']
        sort = query_params['sort']

        # Authenticate
        helper.log_info(f"{log_label} Initializing API connection")
        falcon = APIHarnessV2(client_id=api_config['client_id'], client_secret=api_config['client_secret'], user_agent=api_config['user_agent'], base_url=api_config['base_url'], proxy=api_config['proxy'], timeout=const.timeout)

        falcon.authenticate()
        if not falcon.authenticated():
            token_status = falcon.token_status
            if token_status is None:
                helper.log_error(f"{log_label} Authentication failed - unable to contact CrowdStrike API. Check network connectivity, proxy settings, and base URL.")
            elif token_status == 401:
                helper.log_error(f"{log_label} Authentication failed - invalid credentials (401). Verify Client ID and Secret are correct.")
            elif token_status == 403:
                helper.log_error(f"{log_label} Authentication failed - insufficient API scopes (403). Verify API client has 'Falcon FileVantage: Read' scope.")
            else:
                helper.log_error(f"{log_label} Authentication failed with status {token_status}. Check credentials and network connectivity.")
            helper.log_error(f"{log_label} TA is shutting down.")
            raise SystemExit()

        helper.log_debug(f"{log_label} Successfully authenticated to CrowdStrike API")

        # Iterative pagination loop
        pagination_after = None
        is_first_page = True

        while True:
            # Build API call with or without pagination marker
            if pagination_after:
                helper.log_info(f"{log_label} Pagination ID call")
            else:
                helper.log_info(f"{log_label} Standard ID call")

            # API call with retry logic
            fim_ids = None
            for attempt in range(max_retries):
                try:
                    if pagination_after:
                        fim_ids = falcon.command("highVolumeQueryChanges", limit=limit, sort=sort, filter=cs_filter, after=pagination_after)
                    else:
                        fim_ids = falcon.command("highVolumeQueryChanges", limit=limit, sort=sort, filter=cs_filter)
                    break
                except Exception as issue:
                    if attempt < max_retries - 1:
                        backoff = min(5 * (2 ** attempt), 120)
                        helper.log_warning(f"{log_label} API call failed (attempt {attempt + 1}/{max_retries}), retrying in {backoff}s. Exception: {issue}")
                        time.sleep(backoff)
                    else:
                        helper.log_error(f"{log_label} Unable to contact the CrowdStrike API after {max_retries} attempts. Exception: {issue}")
                        helper.log_error(f"{log_label} TA is shutting down.")
                        raise SystemExit()

            status_code = str(fim_ids['status_code'])
            helper.log_debug(f"{log_label} Successfully queried API endpoint {api_endpoint} - Status: {status_code}")

            # Handle rate limiting (429)
            if status_code == '429':
                for attempt in range(max_retries):
                    backoff = min(5 * (2 ** attempt), 120)
                    helper.log_warning(f"{log_label} Rate limit exceeded (429), retrying in {backoff}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(backoff)
                    try:
                        if pagination_after:
                            fim_ids = falcon.command("highVolumeQueryChanges", limit=limit, sort=sort, filter=cs_filter, after=pagination_after)
                        else:
                            fim_ids = falcon.command("highVolumeQueryChanges", limit=limit, sort=sort, filter=cs_filter)
                        status_code = str(fim_ids['status_code'])
                        if status_code != '429':
                            break
                    except Exception as issue:
                        if attempt < max_retries - 1:
                            helper.log_error(f"{log_label} API call failed during rate limit retry (attempt {attempt + 1}/{max_retries}). Exception: {issue}")
                        else:
                            helper.log_error(f"{log_label} API call failed on final rate limit retry attempt. Exception: {issue}")
                            helper.log_error(f"{log_label} TA is shutting down.")
                            raise SystemExit()
                else:
                    helper.log_error(f"{log_label} Rate limit retry exhausted after {max_retries} attempts. TA is shutting down.")
                    raise SystemExit()

            # Process successful response
            if status_code.startswith('2'):
                id_collections = []
                fim_body = fim_ids['body']
                collected_ids = fim_body['resources']
                num_ids = len(collected_ids)
                total_matching = fim_body['meta']['pagination']['total']

                if is_first_page:
                    helper.log_info(f"{log_label} Total events matching query = {total_matching}")
                    is_first_page = False
                else:
                    helper.log_info(f"{log_label} Total events for this pagination call = {total_matching}")

                if 0 < num_ids <= const.detail_batch_size:
                    helper.log_info(f"{log_label} Single detail call required")
                    results = Get_CS_Details.get_fim_details(collected_ids, falcon, log_label, ta_data, helper, ew)
                    total_results.extend(results)
                    checkpoint = Post_to_Splunk.send_to_splunk(results, checkpoint, stanza_checkpoint, log_label, ta_data, helper, ew)

                elif num_ids > const.detail_batch_size:
                    helper.log_info(f"{log_label} Multiple detail calls required")
                    while num_ids > 0:
                        helper.log_debug(f"{log_label} Creating ID groups")
                        id_collections.append(list(collected_ids[-const.detail_batch_size:]))
                        del collected_ids[-const.detail_batch_size:]
                        num_ids = len(collected_ids)
                    helper.log_debug(f"{log_label} Number of ID collection groups = {len(id_collections)}")

                    while len(id_collections) != 0:
                        id_group = id_collections.pop(-1)
                        helper.log_info(f"{log_label} Getting details for ID group")
                        helper.log_info(f"{log_label} Number of ID groups remaining = {len(id_collections)}")
                        results = Get_CS_Details.get_fim_details(id_group, falcon, log_label, ta_data, helper, ew)
                        total_results.extend(results)
                        checkpoint = Post_to_Splunk.send_to_splunk(results, checkpoint, stanza_checkpoint, log_label, ta_data, helper, ew)

                else:
                    helper.log_info(f"{log_label} There was no FileVantage data available matching the request")
                    return

                # Check for additional pages
                pagination_obj = fim_body.get('meta', {}).get('pagination') or {}
                pagination_after = pagination_obj.get('after')
                if not pagination_after:
                    break
                helper.log_info(f"{log_label} Additional pages available, continuing pagination")

            else:
                Status_Code_Errors.status_code_errors(fim_ids, api_endpoint, log_label, helper, ew)
                return

        # Collection complete
        helper.log_info(f"{log_label} Collection has completed")
        helper.log_info(f"{log_label} Total number of events collected = {len(total_results)}")
        helper.log_debug(f"{log_label} Total number of matching events reported by API = {total_matching}")
        num_check = len(total_results) == int(total_matching)
        helper.log_debug(f"{log_label} Validate that the number processed matches the total number returned - {num_check}")
        helper.log_info(f"{log_label} TA has completed collection and is shutting down")
        return
