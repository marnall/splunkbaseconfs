# encoding = utf-8
from __future__ import print_function, absolute_import

def ip_validator(ip_obj):
    import ipaddress
    try:
        ip_val = ipaddress.ip_address(ip_obj)
        return True
    except Exception as error:
        return False

def cummulative_validator(hostname):
    import re
    if len(hostname) > 255:
        return False
    if hostname[-1] == ".":
        hostname = hostname[:-1]
    allowed = re.compile("(?!-)[&#@+=:/A-Z\s\w\d-]{1,100}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))

def date_validator(date_obj):
    flag = 0
    date_list = []
    date_obj = date_obj.split(' ')[0]
    if '/' in date_obj:
        date_list = date_obj.split('/')
    elif '-' in date_obj:
        date_list = date_obj.split('-')
    for i in date_list:
        if cummulative_validator(i):
            continue
        else:
            flag = 1
            break
    if flag == 1:
        return False
    else:
        return True

def sha_validator(sha_obj):
    if len(sha_obj)==16 and cummulative_validator(sha_obj):
        return True
    else:
        return False

def escapes(data):
    # if data.startswith('http'):
    #     data = data.replace("&", "&amp;").replace(">", "&gt;").replace("<", "&lt;").replace('"',"&quot;").replace("'",'&apos')
    # else:
    #     data = data.replace("&", "&amp;").replace(">", "&gt;").replace("<", "&lt;").replace('"',"&quot;").replace("'",'&apos').replace("/","&#x2F")
    return data

def json_sanitizer(json_obj):
    _obj = {}
    _list = []
    if isinstance(json_obj,dict):
        # for key,value in json_obj.items():
        for key,value in list(json_obj.items()):
            key = escapes(key)
            if isinstance(value,dict):
                value = json_sanitizer(value)
            elif isinstance(value,list):
                value = json_sanitizer(value)
            else:
                value = escapes(str(value))
            _obj[key] = value
    elif isinstance(json_obj,list):
        for ele in json_obj:
            _list.append(json_sanitizer(ele))
        _obj=_list
    else:
        _obj = escapes(str(json_obj))
    return _obj