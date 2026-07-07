
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import re
import base64
import requests
import random
from datetime import datetime

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
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # key = definition.parameters.get('key', None)
    # secret = definition.parameters.get('secret', None)
    # code = definition.parameters.get('code', None)
    pass


eventid = random.randint(0,1000000)
    
def collect_events(helper, ew):
    
    from datetime import datetime
    
    helper.log_info("EVENTID={},STATUS={}".format(eventid,"START"))
    
    createdtd = "is now"
    opt_key = helper.get_arg('client_id')
    opt_secret = helper.get_arg('client_secret')
    opt_code = helper.get_arg('access_code')
    
    opt_analysis = helper.get_arg('audio_analysis')
    opt_features = helper.get_arg('audio_features')
    
    datetime_format = '%Y-%m-%dT%H:%M:%S'
    
    auth = base64.b64encode(str(opt_key) + ':' + str(opt_secret))
    
    # Get Token Value
    checkpoint = auth + '-' + "access_token"
    accessToken = helper.get_check_point(checkpoint)
    
    if accessToken == None:
        accessToken=getTokensFromCode(helper,opt_key,opt_secret,opt_code)
        
        if accessToken=="ERROR":
            helper.log_error("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"ATRETER",accessToken))
            return
    
    
    # Get Checkpoint Value
    checkpoint = auth + '-' + "last_runtime"
    helper.bb_last_runtime = helper.get_check_point(checkpoint)

    # If there's no checkpoint value, set initial value to 2000-01-01
    if helper.bb_last_runtime == None:
        helper.bb_last_runtime = "2000-01-01T00%3A00%3A00"

    # Set Current RunTime
    helper.bb_cur_runtime = datetime.utcnow().strftime(datetime_format)
    helper.bb_cur_runtime = re.sub(":","%3A",str(helper.bb_cur_runtime))
    
    
    returnedJson=callAPI(helper,accessToken,auth,opt_key,opt_secret,opt_code,"me/player/currently-playing")
    
    if returnedJson == None:
        return
    
    if returnedJson == "ERROR":
        helper.log_error("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"MAINRETER",returnedJson))
        return
    
    trackJson =returnedJson.json()
    
    write_parsedRecord = json.dumps(trackJson)
    event = helper.new_event(
        data=write_parsedRecord,
        index=helper.get_output_index(),
        source=helper.get_input_type(),
        sourcetype=helper.get_sourcetype() + ':playing'
        )
    ew.write_event(event)
    
    if 'context' in trackJson and trackJson['context'] != None:
        if 'type' in trackJson['context']:
            if 'href' in trackJson['context']:
                if trackJson['context']['type'] == "playlist":
            
                    url = re.search("(playlists.+)",trackJson['context']['href'])
                    
                    returnedJson=callAPI(helper,accessToken,auth,opt_key,opt_secret,opt_code,url.group(0))
                    
                    if returnedJson == None:
                        return
                    
                    if returnedJson == "ERROR":
                        helper.log_error("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"MAINRETER",returnedJson))
                        return
                    
                    parsedJson =returnedJson.json()
                    
                    write_parsedRecord = json.dumps(parsedJson)
                    event = helper.new_event(
                        data=write_parsedRecord,
                        index=helper.get_output_index(),
                        source=helper.get_input_type(),
                        sourcetype=helper.get_sourcetype() + ':playlist'
                        )
                    ew.write_event(event)
    
    if 'item' in trackJson and trackJson['item'] != None:
        if 'artists' in trackJson['item']:
            for artist in trackJson['item']['artists']:
                url = re.search("(artists.+)",artist['href'])
                    
                returnedJson=callAPI(helper,accessToken,auth,opt_key,opt_secret,opt_code,url.group(0))
                
                if returnedJson == None:
                    return
                
                if returnedJson == "ERROR":
                    helper.log_error("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"MAINRETER",returnedJson))
                    return
                
                parsedJson =returnedJson.json()
                
                write_parsedRecord = json.dumps(parsedJson)
                event = helper.new_event(
                    data=write_parsedRecord,
                    index=helper.get_output_index(),
                    source=helper.get_input_type(),
                    sourcetype=helper.get_sourcetype() + ':artist'
                    )
                ew.write_event(event)
                
        if 'id' in trackJson['item']:
            
            if opt_analysis == True:
                
                checkpoint = "audio_analysis_" + str(trackJson['item']['id'])
                trackId = helper.get_check_point(checkpoint)
                
                if trackId == None:
                    
                    url = "audio-analysis/" + trackJson['item']['id']
                        
                    returnedJson=callAPI(helper,accessToken,auth,opt_key,opt_secret,opt_code,url)
                    
                    if returnedJson == None:
                        return
                    
                    if returnedJson == "ERROR":
                        helper.log_error("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"MAINRETER",returnedJson))
                        return
                    
                    parsedJson =returnedJson.json()
                        
                    if 'sections' in parsedJson:
                        for section in parsedJson['sections']:
                        
                            section['track_id'] = trackJson['item']['id']
                            section['type'] = "section"
                    
                            write_parsedRecord = json.dumps(section)
                            event = helper.new_event(
                                data=write_parsedRecord,
                                index=helper.get_output_index(),
                                source=helper.get_input_type(),
                                sourcetype=helper.get_sourcetype() + ':audio:analysis'
                                )
                            ew.write_event(event)
                            
                    if 'segments' in parsedJson:
                        for section in parsedJson['segments']:
                        
                            section['track_id'] = trackJson['item']['id']
                            section['type'] = "segment"
                    
                            write_parsedRecord = json.dumps(section)
                            event = helper.new_event(
                                data=write_parsedRecord,
                                index=helper.get_output_index(),
                                source=helper.get_input_type(),
                                sourcetype=helper.get_sourcetype() + ':audio:analysis'
                                )
                            ew.write_event(event)
                    
                    if 'bars' in parsedJson:
                        for section in parsedJson['bars']:
                        
                            section['track_id'] = trackJson['item']['id']
                            section['type'] = "bar"
                    
                            write_parsedRecord = json.dumps(section)
                            event = helper.new_event(
                                data=write_parsedRecord,
                                index=helper.get_output_index(),
                                source=helper.get_input_type(),
                                sourcetype=helper.get_sourcetype() + ':audio:analysis'
                                )
                            ew.write_event(event)
                            
                    if 'beats' in parsedJson:
                        for section in parsedJson['beats']:
                        
                            section['track_id'] = trackJson['item']['id']
                            section['type'] = "beat"
                    
                            write_parsedRecord = json.dumps(section)
                            event = helper.new_event(
                                data=write_parsedRecord,
                                index=helper.get_output_index(),
                                source=helper.get_input_type(),
                                sourcetype=helper.get_sourcetype() + ':audio:analysis'
                                )
                            ew.write_event(event)
                            
                    if 'tatums' in parsedJson:
                        for section in parsedJson['tatums']:
                        
                            section['track_id'] = trackJson['item']['id']
                            section['type'] = "tatum"
                    
                            write_parsedRecord = json.dumps(section)
                            event = helper.new_event(
                                data=write_parsedRecord,
                                index=helper.get_output_index(),
                                source=helper.get_input_type(),
                                sourcetype=helper.get_sourcetype() + ':audio:analysis'
                                )
                            ew.write_event(event)
                            
                    helper.save_check_point(
                        checkpoint,
                        str(datetime.utcnow()))
                
            if opt_features == True:
                
                checkpoint = "audio_features_" + str(trackJson['item']['id'])
                trackId = helper.get_check_point(checkpoint)
                
                if trackId == None:
                    url = "audio-features/" + trackJson['item']['id']
                        
                    returnedJson=callAPI(helper,accessToken,auth,opt_key,opt_secret,opt_code,url)
                    
                    if returnedJson == None:
                        return
                    
                    if returnedJson == "ERROR":
                        helper.log_error("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"MAINRETER",returnedJson))
                        return
                    
                    parsedJson =returnedJson.json()
                    
                    write_parsedRecord = json.dumps(parsedJson)
                    event = helper.new_event(
                        data=write_parsedRecord,
                        index=helper.get_output_index(),
                        source=helper.get_input_type(),
                        sourcetype=helper.get_sourcetype() + ':audio:features'
                        )
                    ew.write_event(event)
                    
                    helper.save_check_point(
                        checkpoint,
                        str(datetime.utcnow()))
                        
    helper.save_check_point(
        checkpoint,
        helper.bb_cur_runtime)
    
    helper.log_info("EVENTID={},STATUS={}".format(eventid,"END"))

def callAPI(helper,accessToken,auth,opt_key,opt_secret,opt_code,api_endpoint):
    
    helper.log_debug("EVENTID={},HCVAL={},FUNCTION={},MSG={}".format(eventid,"CAPIST","accessToken","START"))
    
    headers = {'Authorization' : '{}'.format('Bearer ' + str(accessToken))}
    
    url = "https://api.spotify.com/v1/{}".format(str(api_endpoint))
    response = helper.send_http_request(url,"GET", headers=headers)
    
    r_status = response.status_code
    
    if r_status == 401:
        helper.log_debug('EVENTID={},HCVAL={},MSGVAL={}'.format(eventid,"TKREFST",'Refreshing Token'))
        
        accessToken = refreshToken(helper,auth,opt_key,opt_secret,opt_code)
        
        if accessToken == "ERROR":
            helper.log_error('EVENTID={},HCVAL={},MSGVAL={}'.format(eventid,"TKREFER",'Unable to refresh token'))
            return "ERROR"
        
        headers = {'Authorization' : '{}'.format('Bearer ' + str(accessToken))}
        response = requests.get(url = url, headers=headers)
        r_status = response.status_code
        response.raise_for_status()
        
    if r_status != 200:
        helper.log_error("EVENTID={},HCVAL={},MSGVAL={}".format(eventid,"ATRETER",r_status))
        return "ERROR"
    
    return response
    
def getTokensFromCode(helper,opt_key,opt_secret,opt_code):

    helper.log_debug("EVENTID={},HCVAL={},FUNCTION={},MSG={}".format(eventid,"GTFCST","getTokensFromCode","START"))
    url = "https://accounts.spotify.com/api/token"
    auth = base64.b64encode(str(opt_key) + ':' + str(opt_secret))
    
    headers = {'Authorization' : '{}'.format('Basic ' + str(auth)),'Content-Type': 'application/x-www-form-urlencoded','Cache-Control': 'no-cache'}
    
    data = {"grant_type":'authorization_code', 'code': str(opt_code), 'redirect_uri': 'https://convergingdata.com'}
    
    response = requests.post(url = url, headers=headers, data=data)

    # Handle Response
    r_status = response.status_code
    
    if r_status != 200:
        helper.log_error("EVENTID={},HCVAL={},FUNCTION={},CODE={},MSG={}".format(eventid,"GTFCER","getTokensFromCode",str(r_status),response.json()))
        return "ERROR"
    
    response = response.json()
    
    accessToken = response['access_token']
    refreshToken = response['refresh_token']
    
    helper.save_check_point(
        auth  + '-' + "access_token",
        accessToken)
        
    helper.save_check_point(
        auth  + '-' + "refresh_token",
        refreshToken)
        
    helper.log_debug("EVENTID={},HCVAL={},FUNCTION={},MSGVAL={}".format(eventid,"GTFCEN","getTokensFromCode",accessToken))
        
    return accessToken
    
def refreshToken(helper,auth,opt_key,opt_secret,opt_code):        
    
    helper.log_debug("EVENTID={},HCVAL={},FUNCTION={},MSG={}".format(eventid,"RFTST","refreshToken","START"))
    
    checkpoint = auth  + '-' + "refresh_token"
    refresh_token = helper.get_check_point(checkpoint)
    
    url = "https://accounts.spotify.com/api/token"
    auth = base64.b64encode(str(opt_key) + ':' + str(opt_secret))
    headers = {'Authorization' : '{}'.format('Basic ' + str(auth)),'Content-Type': 'application/x-www-form-urlencoded','Cache-Control': 'no-cache'}
    data = {"grant_type":'refresh_token', 'refresh_token': refresh_token}

    response = requests.post(url = url, headers=headers, data=data)

    response = response.json()
    
    helper.log_debug("EVENTID={},HCVAL={},FUNCTION={},MSG={}".format(eventid,"RFTRT","refreshToken",response))
    
    accessToken = response['access_token']
    
    helper.save_check_point(
        auth + '-' + "access_token",
        accessToken)
        
    
    helper.log_debug("EVENTID={},HCVAL={},FUNCTION={},MSG={}".format(eventid,"RFTEN","refreshToken","END"))
    
    return accessToken
    