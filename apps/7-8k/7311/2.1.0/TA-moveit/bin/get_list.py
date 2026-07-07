import os
import sys

def GetList(helper,server_address,asset_type,token):

    helper.log_debug(f'initiating {asset_type} list retrieve')

    url = f'{server_address}/api/v1/{asset_type}'

    head = {'Content-Type': 'application/x-www-form-urlencoded','Authorization': bytes(f'Bearer {token}', encoding='utf-8')}

    response = helper.send_http_request(url,method="GET",parameters=None,payload=None,headers=head,cookies=None,verify=False,cert=None,timeout=30,use_proxy=None)

    r_status = response.status_code

    if r_status == 200:
        try:
            asset_list = response.json()['items']
            helper.log_debug(f'{asset_type} list retrieve from items block - success')
        except:
            # handle responces where the set of objects are not inside items
            asset_list = response.json()
            helper.log_debug(f'{asset_type} list retrieve from plain response - success')
        # some responses does not come as a list. if not convert them to a list
        check_list = isinstance(asset_list,list)
        if check_list:
            return asset_list
        else:            
            rearranged_list = []
            rearranged_list.append(asset_list)
            return rearranged_list


    elif r_status == 401 or r_status == 403:
        helper.log_error(f'invalid token for {asset_type}.')
        helper.log_debug(r_status)
        helper.log_debug(response.json())
        raise ValueError(r_status)

    elif r_status == 422:
        helper.log_error(f'invalid input for {asset_type}.')
        helper.log_debug(r_status)
        helper.log_debug(response.json())
        raise ValueError(r_status)

    else:
        helper.log_error(f'unable to fetch {asset_type} list.')
        helper.log_debug(r_status)
        helper.log_debug(response.json())
        raise ValueError(r_status)