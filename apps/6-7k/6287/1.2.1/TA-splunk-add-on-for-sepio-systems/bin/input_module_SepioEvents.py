# encoding = utf-8



#version 1.0.1



import os



import sys



import time



import datetime



import requests



import json



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



def validate_input(helper, definition):



    pass







def collect_events(helper, ew):



    



    hac1url = helper.get_global_setting('host')
    if hac1url.endswith('/'):
        hac1url = hac1url[:-1]
    #if hac1url

    token = helper.get_global_setting('token')



    #fetch_time = int(helper.get_arg('fetch_time'))



    include_http_messages =  helper.get_global_setting('include_http_messages')



    #if insecure is checked then it supports https and http



    #if insecure is not checked then it supports https only



    if include_http_messages == '1' or str(include_http_messages) == 'True':



        secure =  False



    else:



        secure = True



    #max_alerts = helper.get_arg('max_alerts')



    min_severity = helper.get_arg('min_severity')



    #bearer = helper.get_check_point(str("Bearer"))



    #if bearer is None:



    #   bearer = login(helper, hac1url, secure)



    myheaders = {"Authorization": "Bearer " + token}



    PageSize = 10000



    args = {



        'PageSize':PageSize,



        'MinimumSeverity':min_severity



    }



    previousId = helper.get_check_point(str("previousId"))



    if  previousId is None:



        previousDate = helper.get_check_point(str("previousDate"))



        if  previousDate is None:



            previousDate = datetime.datetime.now()



            helper.save_check_point("previousDate", str(previousDate))



        currentDate = datetime.datetime.now()



        args["FromDate"] = previousDate



        args["ToDate"] = currentDate    



    else:



        args["FromEventId"] = previousId



    response = helper.send_http_request(hac1url+'/prime/webui/events/GetEventsIntegration', 'GET', parameters=args, payload=None,headers=myheaders, cookies=None, verify=secure, 



        cert=None,timeout=None, use_proxy=True)



    #if response.status_code == 401:



    #    bearer = login(helper, hac1url,secure)



    #    myheaders = {"Authorization": "Bearer " + bearer}



    #    response = helper.send_http_request(hac1url+'/prime/webui/events/GetEventsIntegration', 'GET', parameters=args, payload=None,headers=myheaders, cookies=None, verify=secure, 



    #    cert=None,timeout=None, use_proxy=True)

    data =  response.json()

    for item in data["data"]:

        state = helper.get_check_point(str(item["eventID"]))



        if state is None:



            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(item), time= item["creationTime"])



            ew.write_event(event)



            helper.save_check_point(str(item["eventID"]), str(item["eventID"]))



    if len(data["data"]):



        helper.save_check_point("previousId", data["data"][0]["eventID"] + 1) 















#def login(helper, hac1url,secure):



#    username = helper.get_global_setting('username')



#    password = helper.get_global_setting('password')



#    ploads = {'Username':username,'Password':password}



#    response = helper.send_http_request(hac1url+"/prime/webui/Auth/signin", 'POST', parameters=None, payload=ploads,headers=None, cookies=None, verify=secure, cert=None,timeout=None, use_proxy=True)



#    bearer = str(response.json()["token"])



#    helper.save_check_point("Bearer", bearer)



#    return bearer	







