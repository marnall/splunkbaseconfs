# encoding = utf-8



import os



import sys



import time



import datetime



import uuid



import json







"""



    IMPORTANT



    Edit only the validate_input and collect_events functions.



    Do not edit any other part in this file.



    This file is generated only once when creating the modular input.



"""



"""



# For advanced users, if you want to create single instance mod input, uncomment this method.



def use_single_instance_mode():



    return True



"""











def validate_input(helper, definition):



    """Implement your own validation logic to validate the input stanza configurations"""



    # This example accesses the modular input variable



    api_base_url = definition.parameters.get("api_base_url", None)



    api_token = definition.parameters.get("authentication_token", None)



    interval = definition.parameters.get("interval", None)



    if int(interval) < 300:



        raise Exception("The interval must be at least 300.")



        return False



        



    return True



    # if api_base_url.lower().startswith("https://"):



    #     url = api_base_url + "/v1/siem/security_events"



    # else:



    #     url = "https://" + api_base_url + "/v1/siem/security_events"



    # traceid = str(uuid.uuid4())



    # headers = {



    #     "Authorization": "Bearer " + api_token,



    #     "traceid": traceid,



    # }



    # try:



    #     proxy_settings = helper.get_proxy()



    #     helper.log_info("test proxy_settings:{0}".format(proxy_settings))



    #     if not proxy_settings:



    #         use_proxy = False



    #     else:



    #         use_proxy = True



    # except:



    #     helper.log_info("cannot get proxy")



    #     use_proxy = False



    # else:



    #     use_proxy = False  #  no proxy for current helper



    # helper.log_info("test connect request traceid:" + traceid)



    # # The following examples send rest requests to some endpoint.



    # params = {"queryfrom": 0}



    # try:



    #     response = helper.send_http_request(



    #         url,



    #         "GET",



    #         parameters=params,



    #         payload=None,



    #         headers=headers,



    #         cookies=None,



    #         verify=True,



    #         cert=None,



    #         timeout=None,



    #         use_proxy=use_proxy,



    #     )



    # except Exception as errr:



    #     helper.log_error("exception:{errr}")



    #     raise Exception(



    #         "test connect request happened unexpected exception, retry later"



    #     )



    # else:



    #     r_status = response.status_code



    #     if r_status != 200:



    #         # check the response status, if the status is not sucessful, raise requests.HTTPError



    #         helper.log_error(



    #             "error in this request, error code:{0},traceid:{1}. exit".format(



    #                 r_status, traceid



    #             )



    #         )



    #         raise Exception(



    #             "test connect request failed, please check api path and token and retry"



    #         )



    #         # return False



    #     else:



    #         helper.log_info("success, test connect request traceid:" + traceid)



    #         return True











def get_check_point_key(stanza_name, source_name, service, event):



    return (



        stanza_name



        + "_"



        + source_name



        + "_"



        + service



        + "_"



        + event



        + "_LastSuccessTime"



    )











def get_last_success_time(helper, key, time_format):



    now = datetime.datetime.utcnow()



    start = helper.get_check_point(key)  # time_format string



    if not start:



        helper.log_info("no start time,use now - 30 minutes")



        start = (now - datetime.timedelta(minutes=30)).strftime(time_format)



        helper.save_check_point(key, start)



        helper.log_info("first start time:" + start)



    helper.log_info("checkpoint " + key + ":" + start)



    return start











def collect_events(helper, ew):



    """Implement your data collection logic here """



    # The following examples get the arguments of this input.



    # Note, for single instance mod input, args will be returned as a dict.



    # For multi instance mod input, args will be returned as a single value.



    opt_api_base_url = helper.get_arg("api_base_url")



    opt_api_token = helper.get_arg("authentication_token")



    opt_exchange = helper.get_arg("office365")



    opt_gmail = helper.get_arg("google")



    opt_storage = helper.get_arg("storage")



    opt_crm = helper.get_arg("crm")



    opt_exchange_server = helper.get_arg("exchange_server")



    # In single instance mode, to get arguments of a particular input, use



    # opt_api_base_url = helper.get_arg('api_base_url', stanza_name)



    # opt_api_token = helper.get_arg('api_token', stanza_name)



    # opt_exchange = helper.get_arg('exchange', stanza_name)



    # opt_gmail = helper.get_arg('gmail', stanza_name)



    # helper.log_info(opt_exchange)



    # helper.log_info(opt_gmail)



    # get input type



    input_type = helper.get_input_type()



    helper.log_info(input_type)



    # The following examples get input stanzas.



    # get all detailed input stanzas



    stanza = helper.get_input_stanza()



    # helper.log_info(stanza) # The "stanza" variable contains the API Token value, comment this log



    stanza_name = helper.get_input_stanza_names()



    helper.log_info(stanza_name)



    # get specific input stanza with stanza name



    input_setting = helper.get_input_stanza(stanza_name)



    # helper.log_info(input_setting) # The "input_setting" variable contains the API Token value, comment this log



    source_type = helper.get_sourcetype(stanza_name)



    helper.log_info(source_type)



    interval = helper.get_arg("interval", stanza_name)



    # get all stanza names



    # helper.get_input_stanza_names()



    helper.log_info(interval)



    # The following examples get options from setup page configuration.



    # get the loglevel from the setup page



    log_level = helper.get_log_level()



    # get proxy setting configuration



    proxy_settings = helper.get_proxy()



    helper.log_info("proxy_settings:{0}".format(proxy_settings))



    if not proxy_settings:



        use_proxy = False



    else:



        use_proxy = True



    # get account credentials as dictionary



    # account = helper.get_user_credential_by_username("username")



    # account = helper.get_user_credential_by_id("account id")



    # get global variable configuration



    # global_userdefined_global_var = helper.get_global_setting("userdefined_global_var")



    # The following examples show usage of logging related helper functions.



    # write to the log for this modular input using configured global log level or INFO as default



    # helper.log("log message")



    # write to the log using specified log level



    # helper.log_debug("log message")



    # helper.log_info("log message")



    # helper.log_warning("log message")



    # helper.log_error("log message")



    # helper.log_critical("log message")



    # set the log level for this modular input



    # (log_level can be "debug", "info", "warning", "error" or "critical", case insensitive)



    if log_level:



        helper.set_log_level(log_level)



    if opt_api_base_url.lower().startswith("https://"):



        url = opt_api_base_url + "/v1/siem/security_events"



    else:



        url = "https://" + opt_api_base_url + "/v1/siem/security_events"



    service_list = []



    if opt_exchange == True:



        service_list.append("office365")



    if opt_gmail == True:



        service_list.append("google")



    if opt_storage == True:



        service_list.append("storage")



    if opt_crm == True:



        service_list.append("crm")



    if opt_exchange_server == True:



        service_list.append("exchange_server")



    event_list = ["securityrisk", "virtualanalyzer", "dlp"]



    time_format = "%Y-%m-%dT%H:%M:%S.%fZ"



    source_name = "TrendMicroCloudAppSecurity"



    now = datetime.datetime.utcnow()



    end = now.strftime(time_format)



    toomuch_reqs = False



    for service in service_list:





        if toomuch_reqs:



            break



        for event in event_list:



            url_request = url



            if toomuch_reqs:



                break



            need_records = []



            key = get_check_point_key(stanza_name, source_name, service, event)



            start = get_last_success_time(helper, key, time_format)



            need_next_link_request = True  # first request always true



            next_link = ""



            while need_next_link_request and not toomuch_reqs:



                if not next_link:



                    params = {



                        "event": event,



                        "service": service,



                        "start":  start ,



                        "end":  end ,



                        "limit": 5000,



                        "queryfrom": 1,



                    }



                    #helper.log_info(" url_request:"+url_request)



                else:

                    if next_link.lower().startswith("https://"):
                        url_request = next_link
                    else:
                        url_request = "https://" + next_link
                    # url_request = next_link

                    helper.log_info(" url_request next link:"+next_link)

                    params = {"queryfrom": 1}



                traceid = str(uuid.uuid4())



                headers = {



                    "Authorization": "Bearer " + opt_api_token,



                    "traceid": traceid,



                }



                



                # The following examples send rest requests to some endpoint.



                response = helper.send_http_request(



                    url_request,



                    "GET",



                    parameters=params,



                    payload=None,



                    headers=headers,



                    cookies=None,



                    verify=True,



                    cert=None,



                    timeout=(60,120),



                    use_proxy=use_proxy,



                )



                # get the response headers



                # r_headers = response.headers



                # get the response body as text



                # r_text = response.text



                # get response body as json. If the body text is not a json string, raise a ValueError



                r_json = response.json()



                # get response cookies



                # r_cookies = response.cookies



                # get redirect history



                # historical_responses = response.history



                # get response status code



                r_status = response.status_code
                r_traceid = r_json.get("traceId", traceid)
                traceid = r_traceid
                helper.log_info("request traceid:" + traceid+" url_request:"+url_request)



                if r_status != 200:



                    if r_status == 429:



                        helper.log_warning(



                            "too much requests, error code:{0},traceid:{1}. exit".format(



                                r_status, r_traceid



                            )



                        )



                        # check the response status, if the status is not sucessful, raise requests.HTTPError



                        toomuch_reqs = True



                        continue



                    else:



                        helper.log_error(



                            "error in this request, error code:{0},traceid:{1}. exit".format(



                                r_status, r_traceid



                            )



                        )



                        #response.raise_for_status()



                        return



                # The following examples show usage of check pointing related helper functions.



                # save checkpoint



                # helper.save_check_point(key, state)



                # delete checkpoint



                # helper.delete_check_point(key)



                # get checkpoint



                # state = helper.get_check_point(key)



                security_events = r_json["security_events"]



                if len(security_events) > 0:



                    need_records.extend(security_events)



                next_link = r_json["next_link"]



                if not next_link:



                    need_next_link_request = False



                else:



                    need_next_link_request = True



                    helper.log_info("next link:" + next_link)



            if len(need_records) > 0:



                for item in need_records:



                    # To create a splunk event



                    timestamp = (



                        datetime.datetime.strptime(



                            item["message"]["detection_time"], time_format



                        )



                        - datetime.datetime(1970, 1, 1)



                    ).total_seconds()



                    splunkevent = helper.new_event(



                        json.dumps(item),



                        time=timestamp,



                        host=None,



                        index=None,



                        source=source_name,



                        sourcetype=source_type,



                        done=True,



                        unbroken=True,



                    )



                    # helper.log_info(event)



                    ew.write_event(splunkevent)



                helper.log_info("write {} {} events".format(len(need_records), event))



            # save checkpoint



            helper.save_check_point(key, end)



            helper.log_info("save checkpoint:" + key + ":" + end)



            time.sleep(5)