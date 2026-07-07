import json

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    org_id = helper.get_global_setting('organization_id')
    api_token = helper.get_global_setting('api_token')
    opt_limit = helper.get_arg('limit')
    opt_duration = helper.get_arg('duration')

    helper.set_log_level("info")
    helper.log_info("input type :- " + helper.get_input_type())
    stanza_name = helper.get_input_stanza_names()
    helper.log_info("stanza name:- " + stanza_name)
    source_type = helper.get_sourcetype()
    helper.log_info("source type:- " + source_type)

    try :
        mist_url = 'https://api.mist.com/api/v1/orgs/'

        mistsys_url = mist_url + org_id + '/logs'
        param = {'limit': opt_limit,'duration':opt_duration}
        next1 = getEvents(helper, ew,  param, api_token, mistsys_url)
        while (not (next1 is None)):
            next1 = getnextEvents(helper, ew, next1, api_token)

    except Exception, err :
        helper.log_error(str(err))

def getEvents(helper, ew,  param, apitoken, mistsys_url):

    response = helper.send_http_request(mistsys_url, "GET", parameters=param,
                                        payload=None,
                                        headers={
                                            'Content-Type': 'application/json',
                                            'Authorization': 'Token %s' % apitoken
                                        },
                                        cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=False)
    r_text = response.text
    jsonObject = json.loads(r_text)
    results = jsonObject.get('results',[])
    for result in results:
        writeEvents(helper, ew, result)

    return jsonObject.get('next', None)
    
    
def getnextEvents(helper, ew, next1, api_token):
    try :
        response = helper.send_http_request('https://api.mist.com/'+ next1, "GET",  headers={
                                            'Content-Type': 'application/json',
                                            'Authorization': 'Token %s' % api_token
                                        },
                                        cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=False )
        r_text = response.text
        jsonObject = json.loads(r_text)
        results = jsonObject.get('results', [])
        for result in results:
            writeEvents(helper, ew, result)

        return jsonObject.get('next', None)
    except Exception , err :
        helper.log_error(err)


def writeEvents(helper, ew, result) :
    id_1 = result.get('id',None)
    timestamp = result.get('timestamp', None)
    message=result.get('message','').replace("\"","").replace("\\","")
    key = str(id_1) + '_' + str(timestamp)
    result['message'] = message
    if helper.get_check_point(key) is None:
        event = helper.new_event(json.dumps(result), time=timestamp, index=helper.get_output_index(),
                                 sourcetype=helper.get_sourcetype(), done=True,
                                 unbroken=True)
        ew.write_event(event)
        helper.save_check_point(key, 0)

