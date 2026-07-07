import time
from Status_Code_Errors_Splunk import Status_Code_Errors


class Get_CS_Details():
    def get_fim_details(ids, falcon, log_label, ta_data, helper, ew):

        api_endpoint = "FV: getChanges"
        max_retries = 3
        helper.log_info(f"{log_label} Querying API endpoint {api_endpoint}")

        details_response = None
        for attempt in range(max_retries):
            try:
                details_response = falcon.command("getChanges", ids=ids)
                break
            except Exception as issue:
                if attempt < max_retries - 1:
                    backoff = min(5 * (2 ** attempt), 120)
                    helper.log_warning(f"{log_label} API call to {api_endpoint} failed (attempt {attempt + 1}/{max_retries}), retrying in {backoff}s. Exception: {issue}")
                    time.sleep(backoff)
                else:
                    helper.log_error(f"{log_label} Unable to contact CrowdStrike API endpoint {api_endpoint} after {max_retries} attempts. Exception: {issue}")
                    helper.log_error(f"{log_label} TA is shutting down.")
                    raise SystemExit()

        status_code = str(details_response['status_code'])

        # Handle rate limiting (429)
        if status_code == '429':
            for attempt in range(max_retries):
                backoff = min(5 * (2 ** attempt), 120)
                helper.log_warning(f"{log_label} Rate limit exceeded on {api_endpoint} (429), retrying in {backoff}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(backoff)
                try:
                    details_response = falcon.command("getChanges", ids=ids)
                    status_code = str(details_response['status_code'])
                    if status_code != '429':
                        break
                except Exception as issue:
                    if attempt < max_retries - 1:
                        helper.log_error(f"{log_label} API call to {api_endpoint} failed during rate limit retry (attempt {attempt + 1}/{max_retries}). Exception: {issue}")
                    else:
                        helper.log_error(f"{log_label} API call to {api_endpoint} failed on final rate limit retry. Exception: {issue}")
                        helper.log_error(f"{log_label} TA is shutting down.")
                        raise SystemExit()
            else:
                helper.log_error(f"{log_label} Rate limit retry exhausted on {api_endpoint} after {max_retries} attempts. TA is shutting down.")
                raise SystemExit()

        if status_code.startswith('2'):
            helper.log_debug(f"{log_label} Successfully queried API endpoint {api_endpoint}")
            details = details_response['body']['resources']
            return details
        else:
            Status_Code_Errors.status_code_errors(details_response, api_endpoint, log_label, helper, ew)
            return []
