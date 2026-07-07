from falconpy import APIHarnessV2
import time
import random

import crowdstrike_constants as const
from Status_Code_Errors_Splunk import status_code_errors
from Post_to_Splunk import Post_to_Splunk


def _command_with_retry(falcon, command, log_label, helper, **kwargs):
    """Execute a FalconPy command with rate-limit retry and token expiry handling."""
    reauth_attempted = False
    for attempt in range(const.rate_limit_retries + 1):
        response = falcon.command(command, **kwargs)
        status_code = response.get('status_code', 0) if isinstance(response, dict) else 0

        if status_code == 401 and not reauth_attempted:
            reauth_attempted = True
            helper.log_warning(f'{log_label} Token expired (401) on {command}, attempting re-authentication')
            try:
                falcon.authenticate()
                if falcon.authenticated():
                    helper.log_info(f'{log_label} Re-authentication successful, retrying {command}')
                    continue
                else:
                    helper.log_error(f'{log_label} Re-authentication failed for {command} — HTTP {falcon.token_status}: {falcon.token_fail_reason}')
            except Exception as e:
                helper.log_error(f'{log_label} Re-authentication exception during {command}: {type(e).__name__}: {e}')
            return response

        if status_code == 429 or status_code >= 500:
            if attempt < const.rate_limit_retries:
                wait = const.rate_limit_backoff * (2 ** attempt) + random.uniform(0, 1)
                helper.log_warning(f'{log_label} Retryable error ({status_code}) on {command}, retrying in {wait:.1f}s (attempt {attempt + 1}/{const.rate_limit_retries})')
                time.sleep(wait)
                continue

        if attempt > 0 and 200 <= status_code <= 299:
            helper.log_info(f'{log_label} {command} succeeded after {attempt} retries')

        return response

    helper.log_error(f'{log_label} All {const.rate_limit_retries} retries exhausted for {command}, status {status_code}')
    return response


class Get_CS_Indicators():

    def get_CS_indicators(**kwargs):

        indicator_filter    = kwargs['indicator_filter']
        sort                = kwargs['sort']
        offset              = kwargs['offset']
        limit               = kwargs['limit']
        proxy               = kwargs['proxy']
        user_agent          = kwargs['user_agent']
        base_url            = kwargs['base_url']
        timeout             = kwargs['timeout']
        api_endpoint        = kwargs['api_endpoint']
        log_label           = kwargs['log_label']
        include_deleted     = kwargs['deleted']
        helper              = kwargs['helper']
        client_id           = kwargs['clientid']
        client_secret       = kwargs['secret']

        total_indicators_count = 0
        falcon = APIHarnessV2(client_id=client_id, client_secret=client_secret, base_url=base_url, proxy=proxy, user_agent=user_agent, timeout=timeout)

        try:
            falcon.authenticate()
        except Exception as e:
            helper.log_error(f'{log_label} Authentication request failed: {type(e).__name__}: {e}')
            raise RuntimeError(f'Authentication request failed: {e}') from e

        if not falcon.authenticated():
            status = falcon.token_status
            reason = falcon.token_fail_reason
            if status is None:
                helper.log_error(
                    f'{log_label} Authentication failed — no response from CrowdStrike API. '
                    f'Verify network connectivity, proxy settings, DNS resolution, and firewall rules for {base_url}'
                )
                raise RuntimeError(f'Authentication failed — no response from CrowdStrike API ({base_url})')
            else:
                helper.log_error(
                    f'{log_label} Authentication failed — HTTP {status}: {reason}. '
                    f'Verify client_id, client_secret, API scopes (indicators:read), and cloud environment ({base_url})'
                )
                raise RuntimeError(f'Authentication failed — HTTP {status}: {reason}')

        helper.log_info(f'{log_label} Authentication successful')

        try:
            response = _command_with_retry(falcon, "QueryIntelIndicatorEntities", log_label, helper, offset=offset, limit=limit, filter=indicator_filter, sort=sort, include_deleted=include_deleted)
            status_code_errors(response, api_endpoint, log_label, helper)

            indicators = response.get('body', {}).get('resources', [])

            if len(indicators) > 0:
                total_indicators_count = len(indicators)
                helper.log_debug(f'{log_label} Number of indicators = {total_indicators_count}')
            else:
                helper.log_info(f'{log_label} No indicators match the current requirement.')
                return 0

            helper.log_debug(f'{log_label} Total indicator count currently is: {total_indicators_count}')

            meta = response.get('body', {}).get('meta', {}).get('pagination', {})
            overall_total = int(meta.get('total', 0))

            # Send first set of indicators to splunk
            kwargs['indicator_data'] = indicators
            Post_to_Splunk.post_to_Splunk(**kwargs)

            while total_indicators_count < overall_total:
                next_filter = "_marker:>'" + indicators[-1]['_marker'] + "'"
                next_sort = '_marker|asc'

                response_2 = _command_with_retry(falcon, "QueryIntelIndicatorEntities", log_label, helper, filter=next_filter, limit=limit, sort=next_sort, include_deleted=include_deleted)
                status_code_errors(response_2, api_endpoint, log_label, helper)

                indicators = response_2.get('body', {}).get('resources', [])
                if not indicators:
                    helper.log_warning(f'{log_label} Pagination returned empty page, stopping')
                    break

                total_indicators_count = total_indicators_count + len(indicators)
                helper.log_debug(f'{log_label} Current total indicator count is: {total_indicators_count}')
                kwargs['indicator_data'] = indicators
                Post_to_Splunk.post_to_Splunk(**kwargs)

            helper.log_debug(f'{log_label} Total indicator count is: {total_indicators_count}')
            helper.log_debug(f'{log_label} Total reported by API: {overall_total}')

            return total_indicators_count
        finally:
            falcon.logout()
