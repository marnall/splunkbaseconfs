
# encoding = utf-8

def process_event(helper, *args, **kwargs):

    helper.log_info("Alert action sms_eagle started.")

    # TODO: Implement your alert action logic here
    import requests
    import time
    import json

    url = helper.get_global_setting("smseagle_instance_url")
    api_key = helper.get_global_setting("api_key")
    api_version = helper.get_global_setting("api_version")
    username = helper.get_global_setting("username")
    password = helper.get_global_setting("password")
    validate_certs = not bool(helper.get_global_setting("skip_certificate_validation"))
    
    message = helper.get_param("message")
    helper.log_info("message is {}".format(message))

    phone_number = helper.get_param("phone_number")
    helper.log_info("recipient number/phonebook(s) is/are {}".format(phone_number))

    recipient_type = helper.get_param("receiver_type")
    helper.log_info("recipient type is {}".format(recipient_type))

    highpriority = helper.get_param("highpriority")
    helper.log_info("high priority is " + str(highpriority))

    unicode = helper.get_param("unicode")
    helper.log_info("unicode is " + str(unicode))

    flash = helper.get_param("flash")
    helper.log_info("flash is " + str(flash))

    date = helper.get_param("date")
    helper.log_info("date is {}".format(date))

    # Replace placeholders in the message
    message = message.replace("{NAME}", phone_number)\
            .replace("{ALERTNAME}", helper.settings["search_name"])\
            .replace("{SERVERNAME}", helper.settings["server_uri"])\
            .replace("{TIMESTAMP}", time.strftime('%F %T %Z'))
        
    helper.log_info("updated message is {}".format(message))

    if api_version == "v2":
        if unicode == "1":
            PARAMS['encoding'] = "unicode"

        flash = int(flash)
        
        PARAMS = {
            'text': message,
            'priority': int(highpriority),
            'flash': bool(flash)
        }

        phone_number = phone_number.split(",")

        if recipient_type == 'receiver_phone_number':
            PARAMS['to'] = phone_number
        elif recipient_type == 'receiver_phonebook_group':
            PARAMS['groups'] = [int(group_number) for group_number in phone_number]
        else:
            raise Exception("Invalid value of Recipient Type.")

        if date:
            PARAMS["date"] = date

        PARAMS = json.dumps(PARAMS)
        eagleurl = f"https://{url}/api/v2/messages/sms"

        helper.log_info("SMSEagle URL is {}".format(eagleurl))
        helper.log_info("SMSEagle Params are {}".format(PARAMS))

        if api_key:
            HEADERS = {
                'access-token': api_key
            }
            helper.log_info("API Key is used in authentication.")
        else:
            helper.log_error("API Key is not provided.")

        try:
            get_request = requests.request("POST",eagleurl, data=PARAMS, headers=HEADERS, verify=bool(validate_certs), timeout=10)
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

    else:
        PARAMS = {
                'message': message,
                'highpriority': highpriority,
                'unicode': unicode,
                'flash': flash
            }

        recipient_type = helper.get_param("receiver_type")
        if recipient_type == 'receiver_phone_number':
            eagleurl = f"https://{url}/http_api/send_sms"
            PARAMS['to'] = phone_number
        elif recipient_type == 'receiver_phonebook_group':
            eagleurl = f"https://{url}/http_api/send_togroup"
            PARAMS['groupname'] = phone_number
        else:
            raise Exception("Invalid value of Recipient Type.")
        helper.log_info("SMSEagle URL is {}".format(eagleurl))

        if api_key:
            PARAMS["access_token"] = api_key
            helper.log_info("Access Key is used in authentication.")
        elif username and password:
            PARAMS["login"] = username
            PARAMS["pass"] = password
            helper.log_info("Username is {} is used in authentication.".format(username))
        else:
            raise Exception("Error in configuration of Access Key or Username and Password.")
        
        if date:
            PARAMS["date"] = date
        
        try:
            get_request = requests.get(url=eagleurl, params=PARAMS, verify=bool(validate_certs), timeout=10)
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