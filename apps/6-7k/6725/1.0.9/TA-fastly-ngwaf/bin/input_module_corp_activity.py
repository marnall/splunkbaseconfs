# encoding = utf-8

import os

import sys

import time

import datetime

import requests

import calendar

#import random

import json

from datetime import datetime, timedelta



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



# Initial setup

#api_host = 'https://dashboard.signalsciences.net'

#email = os.environ.get('SIGSCI_EMAIL')

#password = os.environ.get('SIGSCI_PASSWORD')

#corp_name = 'testcorp'

#site_name = 'www.example.com'





def validate_input(helper, definition):

    #"""Implement your own validation logic to validate the input stanza configurations"""

    # This example accesses the modular input variable



    email = definition.parameters.get('email_address', None)

    api_token = definition.parameters.get('api_token', None)

    corp_name = definition.parameters.get('corp_name', None)

    site_name = definition.parameters.get('site_name', None)

    # delta_minutes_ = definition.parameters.get('delta_minutes_', None)

    delta_minutes_ = definition.parameters.get('delta_minutes_', None)    

    pass



def collect_events(helper, ew):

    api_host = 'https://dashboard.signalsciences.net'

    email = helper.get_global_setting('email_address')#os.environ.get('SIGSCI_EMAIL')

    api_token = helper.get_global_setting('api_token')

    corp_name = helper.get_global_setting('corp_name')

    site_name = helper.get_arg('site_name')#get_arg('site_name') #'www.example.com'

    

    headers = {

        'Content-type': 'application/json',

        'x-api-user': email,

        'x-api-token': api_token,

    }

    

    #param='from%3A-6h'

    url = api_host + ('/api/v0/corps/%s/activity?limit=1000&page=1' % (corp_name))

    # The following examples send rest requests to some endpoint.

    

    

    

    method="GET"

    headers=headers

    use_proxy=False

    cookies=None

    

    def getResponse(url,method,headers,cookies,use_proxy):

        response = helper.send_http_request(url, method="GET", parameters=None, payload=None,

                                            headers=headers, cookies=cookies, verify=True, cert=None,

                                            timeout=None, use_proxy=use_proxy)

        helper.log_info("in getResponse")

        return(response)

        

        

    def CheckResponse(response):

        if response is not None:

            # get the response headers

            r_headers = response.headers

            # get the response body as text

            r_text = response.text

            # get response body as json. If the body text is not a json string, raise a ValueError

            r_json = response.json()

            # get response cookies

            r_cookies = response.cookies

            # get redirect history

            historical_responses = response.history

            # get response status code

            r_status = response.status_code

            # check the response status, if the status is not sucessful, raise requests.HTTPError

            if r_status != 200:

                response.raise_for_status()

            else:

                indexResponse(r_json)



    def indexResponse(r_json):

        finalresult=[]

        for data in r_json["data"]:

            state=helper.get_check_point(str(data["id"]))

            if state is None:

                finalresult.append(data)

                helper.save_check_point(str(data["id"]),"indexed")

            #helper.delete_check_point(data["id"])

    

        if len(finalresult)>0:

            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(finalresult))

            ew.write_event(event)

        

        if r_json.get("next") is None:

            next_url_exist=False

        else:

            next_url_exist=True



            while next_url_exist:

                newurl=r_json["next"]["uri"]

                response=getResponse(newurl,method,headers,cookies,use_proxy)

                CheckResponse(response)

                



    #def main():

    #    fetchNextdata(url)

    response=getResponse(url,method,headers,cookies,use_proxy)

    CheckResponse(response)

