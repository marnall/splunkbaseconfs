import datetime



#Remove lines for debugging if not needed.

# import os

# import sys

# sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))

# import splunk_debug as dbg

# dbg.enable_debugging(timeout=25)

#End of debugging code



from cyera_utils import validate_input, get_jwt, get_checkpoint, save_checkpoint, process_and_send_data, handle_request, DEFAULT_DAYS_TO_LOOK_BACK



# encoding = utf-8



'''

    IMPORTANT

    Edit only the validate_input and collect_events functions.

    Do not edit any other part in this file.

    This file is generated only once when creating the modular input.

'''



'''

# For advanced users, if you want to create single instance mod input, uncomment this method.

def use_single_instance_mode():

    return True

'''



def get_audit_logs(helper, token, limit=200, created_from=None):

    """Fetch audit logs with specific logic."""

    url = 'https://auth.cyera.io/audits/resources/audits/v2'

    all_data = []

    offset = 0



    while True:

        params = {

            'count': limit,

            'offset': offset,

            'created_from': created_from

        }

        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

        

        helper.log_info(f"Requesting audit logs with params: {params}")

        

        data, _ = handle_request(helper, url, headers, params, {"count": 300, "seconds": 300})

        if data is None:

            save_checkpoint(helper, "audit_logs_last_run", datetime.datetime.now().isoformat())

            return all_data



        items = data.get('data', [])

        if not items:

            save_checkpoint(helper, "audit_logs_last_run", datetime.datetime.now().isoformat())

            break



        all_data.extend(items)

        offset += limit



    save_checkpoint(helper, "audit_logs_last_run", datetime.datetime.now().isoformat())

    return all_data



def collect_events(helper, ew):

    """Set up session, authenticate, and fetch audit logs."""

    try:

        helper.session_key = helper.context_meta['session_key']



        # First, try to get the account from the input configuration

        cyera_account = helper.get_arg('cyera_account')

        

        if cyera_account:

            # Input-specific account

            helper.log_debug("Using input-specific account")

            account_name = cyera_account.get('name')

            client_id = cyera_account.get('username')

            secret = cyera_account.get('password')

        else:

            # Try to get the global account

            account = helper.get_arg('account')

            helper.log_debug(f"Using global account: {account}")

            

            if not account:

                helper.log_error("Neither input-specific nor global account is set. Please configure the account in the input parameters or add-on setup.")

                return

            

            try:

                account_details = helper.get_user_credential_by_id(account)

                account_name = account

                client_id = account_details.get('username')

                secret = account_details.get('password')

            except Exception as e:

                helper.log_error(f"Error retrieving account details: {str(e)}")

                return



        if not account_name or not client_id or not secret:

            helper.log_error("Account name, client ID, or secret is missing in the account details.")

            return



        helper.log_debug(f"Successfully retrieved account details. Account name: {account_name}, Client ID: {client_id}")



        token = get_jwt(helper, client_id, secret)

        if not token:

            helper.log_error("Failed to authenticate with API.")

            return



        # Retrieve days_to_look_back from global additional parameters

        days_to_look_back = helper.get_global_setting('days_to_look_back')

        helper.log_debug(f"Retrieved days_to_look_back from global settings: {days_to_look_back}")



        if not days_to_look_back:

            helper.log_warning("The 'days_to_look_back' setting is not set in global additional parameters. Using default value of 365 days.")

            days_to_look_back = DEFAULT_DAYS_TO_LOOK_BACK

        else:

            try:

                days_to_look_back = int(days_to_look_back)

            except ValueError:

                helper.log_error(f"Invalid value for 'days_to_look_back': {days_to_look_back}. Using default value of 365 days.")

                days_to_look_back = DEFAULT_DAYS_TO_LOOK_BACK



        helper.log_info(f"Using days_to_look_back: {days_to_look_back}")



        last_run_timestamp = get_checkpoint(helper, "audit_logs_last_run")

        

        if not last_run_timestamp:

            created_from = (datetime.datetime.now() - datetime.timedelta(days=days_to_look_back)).isoformat()

        else:

            created_from = last_run_timestamp



        helper.log_info(f"Fetching audit logs from: {created_from}")



        data = get_audit_logs(helper, token, limit=200, created_from=created_from)

        process_and_send_data(helper, ew, data, "cyera:audit")



        if data:

            new_checkpoint = datetime.datetime.now().isoformat()

            save_checkpoint(helper, "audit_logs_last_run", new_checkpoint)

            helper.log_info(f"Checkpoint saved for audit_logs_last_run: {new_checkpoint}")

        else:

            helper.log_info("No audit log data retrieved, checkpoint not updated.")



    except Exception as e:

        helper.log_error(f"Error in collect_events: {str(e)}")

        raise



def main(helper, ew):

    """Main entry point for the module."""

    collect_events(helper, ew)
