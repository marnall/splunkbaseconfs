import timestamp_utils
from opswat_auth import get_auth_token
from helpers import get_start_time_epoch_ms


def get_time(helper, input_name, start_date):
    checkpoint_name = input_name + '_time'.replace(' ', '_')
    checkpoint = helper.get_check_point(checkpoint_name)

    if not checkpoint:
        start_time = get_start_time_epoch_ms(start_date)
        
    else:
        start_time = checkpoint

    end_time = timestamp_utils.get_epoch_ms()
    helper.save_check_point(checkpoint_name, end_time)

    return {
        'start_time': start_time,
        'end_time': end_time
    }


def delete(helper, input_name):
    checkpoint_name = input_name + '_time'.replace(' ', '_')
    helper.delete_check_point(checkpoint_name)
    return


def get_token(account_name, helper, client_key, client_secret, host, auth_endpoint, use_proxy):
    checkpoint_name = '{}_opswat_auth_token'.format(account_name)
    auth_token = helper.get_check_point(checkpoint_name)

    if not auth_token:
        helper.log_info('No auth_token saved, requesting new token')
        auth_token = get_auth_token(
            helper, 
            client_key, 
            client_secret, 
            host, 
            auth_endpoint,
            use_proxy
        )

        if not auth_token:
            helper.log_error('No authentication token for request, input exiting.')
            return

        helper.log_info('Saving new auth_token.')
        helper.save_check_point(checkpoint_name, auth_token)

    else:
        helper.log_info('Using saved auth_token.')

    return auth_token
