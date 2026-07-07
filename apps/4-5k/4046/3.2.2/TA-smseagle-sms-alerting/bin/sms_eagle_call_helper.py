
# encoding = utf-8

def process_event(helper, *args, **kwargs):

    helper.log_info("Alert call action sms_eagle started.")

    # TODO: Implement your alert action logic here
    import requests
    import time
    import json


    url = helper.get_global_setting("smseagle_instance_url")
    api_key = helper.get_global_setting("api_key")
    username = helper.get_global_setting("username")
    password = helper.get_global_setting("password")
    validate_certs = not bool(helper.get_global_setting("skip_certificate_validation"))

    if not api_key:
        helper.log_error("API Key is not provided.")
        return 1

    text = helper.get_param("message")
    helper.log_info("message is {}".format(text))

    to = helper.get_param("phone_number")
    helper.log_info("recipient number is {}".format(to))

    priority = helper.get_param("highpriority")
    helper.log_info("high priority is " + str(priority))

    call_type = helper.get_param("call_type")
    helper.log_info("call type is " + str(call_type))

    duration = helper.get_param("call_duration")
    helper.log_info("duration is " + str(duration))

    date = helper.get_param("call_date")
    helper.log_info("date is {}".format(date))


    # Replace placeholders in the message
    # message = message.replace("{NAME}", to)\
    #        .replace("{ALERTNAME}", helper.settings["search_name"])\
    #        .replace("{SERVERNAME}", helper.settings["server_uri"])\
    #        .replace("{TIMESTAMP}", time.strftime('%F %T %Z'))

    #helper.log_info("updated message is {}".format(message))

    ENDPOINTS = {
        'ring': 'calls/ring',
        'tts': 'calls/tts',
        'tts_advanced': 'calls/tts_advanced',
        'wave': 'calls/wave',
    }

    if call_type not in ENDPOINTS:
        helper.log_error("Invalid call type: {}".format(call_type))
        return 1

    to = [number.strip() for number in to.split(",")]

    PARAMS = {
        'to': to,
        'duration': int(duration),
        'priority': int(priority),
    }
    if date:
        PARAMS['date'] = date
    if call_type in ('tts', 'tts_advanced'):
        PARAMS['text'] = text
    if call_type == 'tts_advanced':
        voice_id = helper.get_param("voice_id")
        if not voice_id:
            helper.log_error("voice_id is required for tts_advanced call type")
            return 1
        PARAMS['voice_id'] = int(voice_id)
    if call_type == 'wave':
        wave_id = helper.get_param("wave_id")
        if not wave_id:
            helper.log_error("wave_id is required for wave call type")
            return 1
        PARAMS['wave_id'] = int(wave_id)

    HEADERS = {
        'access-token': api_key,
        'Content-Type': 'application/json'
    }

    PARAMS = json.dumps(PARAMS)

    eagleurl = f"https://{url}/api/v2/{ENDPOINTS[call_type]}"

    helper.log_info("SMSEagle URL is {}".format(eagleurl))
    helper.log_info("SMSEagle Params are {}".format(PARAMS))



    try:
        get_request = requests.request("POST", eagleurl, data=PARAMS, headers=HEADERS, verify=bool(validate_certs), timeout=10)
        get_request.raise_for_status()
        helper.log_info("SMSEagle Response is {}".format(get_request.text))
    except requests.exceptions.HTTPError as e:
        helper.log_error("Http Error: {}".format(e))
    except requests.exceptions.ConnectionError as e:
        helper.log_error("Connection Error")  # stacktrace here might print password in clear text, hence ignoring stacktrace
    except requests.exceptions.Timeout as e:
        helper.log_error("Timeout Error: {}".format(e))
    except requests.exceptions.RequestException as e:
        helper.log_error("RequestException: {}".format(e))
    except Exception as e:
        helper.log_error("Some other unhandled error: {}".format(e))

    helper.log_info("Alert action smseagle completed.")
    return 0
