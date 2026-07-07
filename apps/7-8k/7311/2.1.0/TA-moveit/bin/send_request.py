def SendRequest(helper,report_type,token,report_url,method,payld):

    head = {'Content-Type': 'application/json','Authorization': bytes(f'Bearer {token}', encoding='utf-8')}

    response = helper.send_http_request(report_url,method=method,parameters=None,payload=payld,headers=head,cookies=None,verify=False,cert=None,timeout=30,use_proxy=None) 

    r_status = response.status_code

    if r_status == 200:
        helper.log_debug(r_status)        

    elif r_status == 401 or r_status == 403:
        helper.log_error(f'invalid token. - {report_type}')
        helper.log_debug(r_status)
        helper.log_debug(response.json())
        raise ValueError(r_status)

    elif r_status == 422:
        helper.log_error(f'invalid input. - {report_type}')
        helper.log_debug(r_status)
        helper.log_debug(response.json())
        raise ValueError(r_status)

    else:
        helper.log_error(f'unable to fetch report - {report_type}')
        helper.log_debug(r_status)
        helper.log_debug(response.json())
        raise ValueError(r_status)
    
    return r_status,response