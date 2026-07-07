# encoding = utf-8

import os
import sys
import time
import datetime
import json
import requests
import time
import logging
import logging.handlers
import splunk
from datetime import date
import datetime
import splunk.entity as entity
import splunk.auth, splunk.search

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''


# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True


def validate_input(helper, definition):
    dummy = definition.parameters.get('dummy', None)

    pass


def collect_events(helper, ew):
    ## Ignoring warnings for unsecure requests ##
    requests.packages.urllib3.disable_warnings()

    ### Other Global Variables ##
    bearer_token = None

    ### Define a logger ###
    logger = logging.getLogger('mulesoft.splunk')
    logger.setLevel(logging.INFO)
    datetime_format = '%Y-%m-%dT%H:%M:%S'
    results_limit = 200

    stanzas = helper.get_input_stanza_names()
    for stanza in stanzas:
        ## Load the mulesoft.conf from local
        try:
            # checkpoint logic
            checkpoint = "MuleSoft" + '_' + stanza + '-' + "last_runtime"
            log_checkpoint = checkpoint
            last_call_time = helper.get_check_point(checkpoint)

            if last_call_time is None:
                last_call_time = datetime.datetime.strptime("2020-01-01T00:00:00", datetime_format)
            else:
                last_call_time = datetime.datetime.strptime(last_call_time, datetime_format)

            ## Check all required variables are loaded
            logger.info('message="current stanza", it is ="%s"', stanza)
            organization_id = helper.get_arg("organization_id", input_stanza_name=stanza)
            logger.info('message="organization ID retrieved", it is ="%s"', organization_id)
            seconds_lookback = int(helper.get_arg("seconds_lookback", input_stanza_name=stanza))
            logger.info('message="seconds look back retrieved", it is ="%s"', seconds_lookback)
            results_limit = int(helper.get_arg("results_limit", input_stanza_name=stanza))
            logger.info('message="results limit retrieved", it is ="%s"', results_limit)
            token_url = helper.get_arg("token_url", input_stanza_name=stanza)
            logger.info('message="token URL retrieved", it is ="%s"', token_url)
            data_url = helper.get_arg("data_url", input_stanza_name=stanza)
            logger.info('message="data URL retrieved", it is ="%s"', data_url)
            index = helper.get_arg("index", input_stanza_name=stanza)
            logger.info('message="index retrieved", it is ="%s"', index)
            try:
                username = helper.get_arg("username", input_stanza_name=stanza)
                password = helper.get_arg("password", input_stanza_name=stanza)

                logger.info('message="username and password retrieved", username="%s", token_url="%s"', username, token_url)


            except NameError:
                try:
                    client_id = helper.get_arg("client_id", input_stanza_name=stanza)
                    client_secret = helper.get_arg("client_secret", input_stanza_name=stanza)
                    grant_type = helper.get_arg("grant_type", input_stanza_name=stanza)
                    username = None
                    logger.info('message="Connected apps data collected", client_id="%s" token_url="%s"', client_id, token_url)
                except Exception as e:
                    logger.exception(
                        'message="username/password OR client_id,client_secret,grant_type not defined.", error="%s"',
                        str(e))
                    exit(1)

        except Exception as e:
            logger.exception('message="exception raised loading ta-mulesoft configurations", error="%s"', str(e))
            exit(1)

        ## Define Proxies ##
        try:
            proxies = {
                "http": http_proxy,
                "https": https_proxy
            }
        except NameError:
            logger.info('message="No proxy defined, continuing without proxy information."')

            # Defining the proxy variable, so as to avoid an exception if not defined above
            try:
                proxies
            except NameError:
                proxies = None

        ## Begin Script
        logger.info('message="Begin Mulesoft scripted input",pwd="%s"', os.getcwd())
        logger.info('message="Crafting Mulesoft bearer token post request.')
        try:
            if username is None:
                tokendata = {'client_id': '%s' % client_id, 'client_secret': '%s' % client_secret,
                             'grant_type': '%s' % grant_type}
            else:
                tokendata = {'username': '%s' % username, 'password': '%s' % password}

            logger.info('message="fetching bearer token", url="%s"', token_url)

            if proxies is None:
                response = requests.post(token_url, data=tokendata, verify=False)
            else:
                response = requests.post(token_url, data=tokendata, proxies=proxies, verify=False)
            logger.info('message="request complete", status_code="%s"', response.status_code)
            try:
                response_json = json.loads(response.text)
                bearer_token = response_json["access_token"];
            except Exception as e:
                logger.info('message="exception raised in deserializing json", error="%s"', str(e))

            if response.status_code != 200:
                raise Exception("Token url returned %s", response.status_code)

            if bearer_token is None:
                raise Exception("Bearer token returned null")


        except Exception as e:
            logger.info('message="exception raised in api call", error="%s"', str(e))
            exit(1)

        logger.info('message="fetching data from mulesoft", url="%s"', data_url)
        try:
            logger.info('message="crafting headers for request"')
            data_headers = {'Authorization': 'bearer %s' % bearer_token, 'Accept': 'application/json',
                            'Content-Type': 'application/json;charset=UTF-8'}
            # Craft our time
            end = datetime.datetime.utcnow()
            startbylookback = end - datetime.timedelta(seconds=seconds_lookback)
            start = startbylookback
            if startbylookback < last_call_time:
                start = last_call_time

            logger.info('message="results limit before making the call", it is ="%s"', results_limit)


            data_data = '{"startDate":"' + str(start) + '", "endDate":"' + str(
                end) + '","organizationId":"' + organization_id + '","limit":' + str(results_limit) + '}'
            data_url = data_url.replace("+organization_id+", organization_id)
            logger.info('message="fetching data", url="%s"', data_url)
            # Defining the proxy variable, so as to avoid an exception if not defined above
            if proxies is None:
                response = requests.post(data_url, data=data_data, headers=data_headers, verify=False)
            else:
                response = requests.post(data_url, data=data_data, headers=data_headers, verify=False, proxies=proxies)
            #print(response.text)
            logger.info('message="data returned",response="%s"', response.text)
            response_json = json.loads(response.text)

            print_json = json.dumps(response_json['data'])
            #print(print_json)
            event = helper.new_event(data=print_json,
                                     time=None,
                                     host=None,
                                     index=index,
                                     source=None,
                                     sourcetype="mulesoft:audit",
                                     done=True,
                                     unbroken=True)
            ew.write_event(event)
            helper.save_check_point(
                checkpoint,
                end.strftime(datetime_format))
            logger.info('message="request complete", status_code="%s"', response.status_code)

        except Exception as e:
            logger.exception('message="exception raised in data call", error="%s"', str(e))
            exit(1)

        logger.info('message="mulesoft api query complete"')