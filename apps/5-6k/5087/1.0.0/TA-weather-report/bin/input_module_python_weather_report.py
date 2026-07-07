# encoding = utf-8
import sys
import json
import datetime


def validate_input(x, y):
    pass

def collect_events(helper, ew):
    api_url = 'https://api.openweathermap.org/data/2.5/weather'
    method = 'GET'
    global_account = helper.get_arg('global_account')
    opt_api_key = global_account['api_key']
    opt_zip_code = helper.get_arg('zip_code')
    opt_units = helper.get_arg('units')
    opt_sourcetype = helper.get_arg('opt_sourcetype')
    parameters = {
        'appid': opt_api_key,
        'units': opt_units,
        'zip': opt_zip_code
    }

    response = helper.send_http_request(
        api_url, 
        method, 
        parameters=parameters, 
        payload=None,
        headers=None, 
        cookies=None, 
        verify=True, 
        cert=None,
        timeout=None, 
        use_proxy=True
    )

    r_status = response.status_code

    if r_status != 200:
        error_string = 'ERROR: Status code: ' + str(r_status)
        sys.stdout.write(error_string)
        response.raise_for_status()

    r_json = response.json()
    r_json['data_timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    event = helper.new_event(
        json.dumps(r_json), 
        time=None, 
        host=None, 
        index=None, 
        source=None, 
        sourcetype=opt_sourcetype, 
        done=True, 
        unbroken=True
    )

    ew.write_event(event) 