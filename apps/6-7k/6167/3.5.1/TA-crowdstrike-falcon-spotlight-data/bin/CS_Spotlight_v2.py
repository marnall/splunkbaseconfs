#!/usr/bin/env python

#local imports
import time
import random
from falconpy import SpotlightVulnerabilities
from Send_to_Splunk_v2 import send_to_splunk
from Status_Code_Errors import status_code_errors
import crowdstrike_constants as const

RATE_LIMIT_RETRIES = 3
RATE_LIMIT_BACKOFF = 5

def _call_with_retry(falcon, method_name, log_label, helper, **kwargs):
    """Call a FalconPy Service Class method with rate-limit retry and 401 re-auth."""
    method = getattr(falcon, method_name)
    reauth_attempted = False
    for attempt in range(RATE_LIMIT_RETRIES + 1):
        response = method(**kwargs)
        status_code = response.get('status_code', 0) if isinstance(response, dict) else 0

        # Handle token expiry — attempt re-authentication once
        if status_code == 401 and not reauth_attempted:
            reauth_attempted = True
            helper.log_warning(f'{log_label} Token expired (401) on {method_name}, attempting re-authentication')
            try:
                falcon.login()
                if falcon.authenticated():
                    helper.log_info(f'{log_label} Re-authentication successful, retrying {method_name}')
                    continue
                else:
                    helper.log_error(f'{log_label} Re-authentication failed for {method_name} — HTTP {falcon.token_status}: {falcon.token_fail_reason}')
            except Exception as e:
                helper.log_error(f'{log_label} Re-authentication exception during {method_name}: {type(e).__name__}: {e}')
            return response

        # Handle rate limiting, network errors, and server errors
        if status_code in (429, 0) or status_code >= 500:
            if attempt < RATE_LIMIT_RETRIES:
                wait = RATE_LIMIT_BACKOFF * (2 ** attempt) + random.uniform(0, 1)
                helper.log_warning(f'{log_label} Retryable error ({status_code}) on {method_name}, retrying in {wait:.1f}s (attempt {attempt + 1}/{RATE_LIMIT_RETRIES})')
                time.sleep(wait)
                continue

        if attempt > 0:
            helper.log_info(f'{log_label} {method_name} succeeded after {attempt} retries')

        return response
    return response

class CS_Spotlight_v2():

    def spotlight_data(self, spotlight_sortby, proxy_settings, clientid, secret, spotlight_base_url, facet, spotlight_filter, limit, user_agent,log_label, ta_data, stanza_checkpoint, current_checkpoint, status_filter, platform_name_filter, cve_severity_filter, cve_exprt_rating_filter, remove_meta, helper, ew):
        #Holds returned data
        facet_settings = ''

        if facet:
            facet_values = facet if isinstance(facet, list) else facet.split('~')
            facet_settings = ','.join(facet_values)
            helper.log_debug(f'{log_label} Facet selections: {facet_values}')

        if 'all' not in status_filter:
            values = status_filter if isinstance(status_filter, list) else status_filter.split('~')
            if len(values) == 1:
                status_f = f" + status:'{values[0]}'"
            else:
                quoted = ','.join(f"'{v}'" for v in values)
                status_f = f" + status:[{quoted}]"
            spotlight_filter = spotlight_filter + status_f
        if 'all' not in platform_name_filter:
            plat_name_f = f" + host_info.platform_name:'{platform_name_filter}'"
            spotlight_filter = spotlight_filter + plat_name_f
        if 'all' not in cve_severity_filter:
            values = cve_severity_filter if isinstance(cve_severity_filter, list) else cve_severity_filter.split('~')
            if len(values) == 1:
                cve_sev_f = f" + cve.severity:'{values[0]}'"
            else:
                quoted = ','.join(f"'{v}'" for v in values)
                cve_sev_f = f" + cve.severity:[{quoted}]"
            spotlight_filter = spotlight_filter + cve_sev_f
        if 'all' not in cve_exprt_rating_filter:
            values = cve_exprt_rating_filter if isinstance(cve_exprt_rating_filter, list) else cve_exprt_rating_filter.split('~')
            if len(values) == 1:
                cve_exprt_rat_f = f" + cve.exprt_rating:'{values[0]}'"
            else:
                quoted = ','.join(f"'{v}'" for v in values)
                cve_exprt_rat_f = f" + cve.exprt_rating:[{quoted}]"
            spotlight_filter = spotlight_filter + cve_exprt_rat_f
        
        helper.log_info(f'{log_label} The filter value for the API call will be: {spotlight_filter}')

        try:
            falcon = SpotlightVulnerabilities(client_id=clientid,
                                  client_secret=secret, base_url=spotlight_base_url, proxy=proxy_settings, user_agent=user_agent, timeout=const.timeout)
        except Exception as e:
            helper.log_error(f'{log_label} Authentication exception: {type(e).__name__}: {e}')
            raise

        if falcon.authenticated():
            helper.log_info(f'{log_label} Authentication successful')
        else:
            auth_status = falcon.token_status
            auth_reason = falcon.token_fail_reason
            if auth_status is None:
                helper.log_error(f'{log_label} Authentication failed — no response from CrowdStrike API. Verify network connectivity, proxy settings, DNS resolution, and firewall rules for {spotlight_base_url}')
                raise RuntimeError(f'{log_label} Authentication failed — no response from CrowdStrike API ({spotlight_base_url})')
            else:
                helper.log_error(f'{log_label} Authentication failed — HTTP {auth_status}: {auth_reason}. Verify client_id, client_secret, API scopes (spotlight-vulnerabilities:read), and cloud environment ({spotlight_base_url})')
                raise RuntimeError(f'{log_label} Authentication failed — HTTP {auth_status}: {auth_reason}')

        api_kwargs = {'filter': spotlight_filter, 'limit': limit, 'sort': spotlight_sortby}
        if facet_settings:
            api_kwargs['facet'] = facet_settings

        try:
            spotlight_response = _call_with_retry(falcon, 'combinedQueryVulnerabilities', log_label, helper, **api_kwargs)
        except Exception as e:
            helper.log_error(f'{log_label} Error contacting the Spotlight API on initial call: {type(e).__name__}: {e}')
            raise

        #evaluate the response from the Spotlight API
        status_code_errors(spotlight_response, 'initial call', log_label, helper)

        #Collect the data and setup to evaluate if pagination is occurring
        try:
            response_data = spotlight_response['body']['resources']
            response_data.sort(key=lambda x: x["updated_timestamp"])
            vulnerability_data = len(response_data)
            meta = spotlight_response['body']['meta']
            pagination = meta['pagination']
            after = pagination.get('after', '')
            total_vul = pagination['total']
        except (KeyError, TypeError) as e:
            helper.log_error(f'{log_label} Unexpected API response structure on initial call: {type(e).__name__}: {e}')
            helper.log_debug(f'{log_label} Response keys: {list(spotlight_response.get("body", {}).keys()) if isinstance(spotlight_response.get("body"), dict) else "no body"}')
            raise RuntimeError(f'{log_label} API returned unexpected response structure') from e
        
        if total_vul == 0:
            helper.log_info(f'{log_label} There is no vulnerability data that currently matches the collection criteria or the most recent data has already been collected')
            return 0, 0

        if vulnerability_data == 0:
            helper.log_warning(f'{log_label} API returned empty resources despite total={total_vul}, halting to prevent infinite loop')
            return 0, total_vul
    
        thread_args = {'helper':helper, 'ew':ew, 'current_checkpoint':current_checkpoint, 'response_data':response_data, 'ta_data':ta_data, 'log_label':log_label, 'stanza_checkpoint':stanza_checkpoint, 'meta':meta, 'remove_meta':remove_meta}

        helper.log_info(f'{log_label} Preparing to send to Splunk and recording checkpoints')
        write_results, checkpoint_results, current_checkpoint = send_to_splunk(**thread_args)

        MAX_PAGES = 5000  # Safety limit: 5000 pages × 4000 records = 20M vulnerabilities
        page_count = 1
        while total_vul > vulnerability_data:
            page_count += 1
            if page_count > MAX_PAGES:
                helper.log_error(f'{log_label} Pagination safety limit reached ({MAX_PAGES} pages, {vulnerability_data} records collected). Halting to prevent runaway loop.')
                break
            helper.log_info(f'{log_label} Pagination page {page_count}: collected {vulnerability_data}/{total_vul} vulnerabilities so far')
            try:
                spotlight_after_response = _call_with_retry(falcon, 'combinedQueryVulnerabilities', log_label, helper, after=after, **api_kwargs)

            except Exception as e:
                helper.log_error(f'{log_label} Error contacting the Spotlight API - pagination: {type(e).__name__}: {e}')
                raise

            #evaluate the pagination request response
            status_code_errors(spotlight_after_response, 'pagination', log_label, helper)

            #Retrieve Spotlight data
            try:
                response_after_data = spotlight_after_response['body']['resources']
                response_after_data.sort(key=lambda x: x["updated_timestamp"])
                if len(response_after_data) == 0:
                    break

                vulnerability_data = vulnerability_data + len(response_after_data)
                meta_pagination = spotlight_after_response['body']['meta']
                after_pagination = meta_pagination['pagination']
                after = after_pagination.get('after', '')
            except (KeyError, TypeError) as e:
                helper.log_error(f'{log_label} Unexpected API response structure on pagination page {page_count}: {type(e).__name__}: {e}')
                helper.log_debug(f'{log_label} Response keys: {list(spotlight_after_response.get("body", {}).keys()) if isinstance(spotlight_after_response.get("body"), dict) else "no body"}')
                raise RuntimeError(f'{log_label} API returned unexpected response structure on pagination') from e
            if not after:
                helper.log_info(f'{log_label} Pagination ended — no after token returned (collected {vulnerability_data}/{total_vul})')
                break
            thread_args['response_data']       = response_after_data
            thread_args['current_checkpoint']  = current_checkpoint
            thread_args['meta']                = meta_pagination
            thread_args['remove_meta']        = remove_meta
            helper.log_info(f'{log_label} Sending to Splunk and recording checkpoints')
            write_results, checkpoint_results, current_checkpoint = send_to_splunk(**thread_args)
            helper.log_debug(f'{log_label} Write results = {write_results}')
            helper.log_debug(f'{log_label} Checkpoint results = {checkpoint_results}')

            helper.log_debug(f'{log_label} Number of vulnerabilities currently = {vulnerability_data}')

        if page_count > 1:
            helper.log_info(f'{log_label} Pagination complete — collected {vulnerability_data} vulnerabilities across {page_count} pages')

        return vulnerability_data, total_vul
