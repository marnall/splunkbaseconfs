#/usr/bin/python
# -*- coding: utf-8 -*-
import csv,sys,os.path,traceback,re
from multiprocessing import Pool
import multiprocessing
import time

import json
#check python 2 or 3
if sys.version_info >= (3, 0):
    import urllib,configparser
    from urllib.error import URLError
    from urllib.request import urlopen
else:
    import urllib2 as urllib
    import ConfigParser as configparser
    from urllib2 import URLError
    from urllib2 import urlopen

inifile = configparser.SafeConfigParser()
inifile.read("./config.ini")

docodoco_key_1 = inifile.get("docodoco","key1")
docodoco_key_2 = inifile.get("docodoco","key2")
process_count = inifile.getint("process","count")


def reqDocodoco(target_ip):
    docodoco_format = "json"
    url = "http://api.docodoco.jp/v5/search?key1={k1}&key2={k2}&format={df}&ipadr={tip}".format(k1=docodoco_key_1,k2=docodoco_key_2,df=docodoco_format,tip=str(target_ip))

    try:
        response =  urlopen(url).read()
        response = json.loads(response)

        if("IP" in response):
            response["status"] = "success"
        else:
            response["IP"] = target_ip
            response["status"] = "error"

        return response

    except URLError as e:
        e_response = {"IP":target_ip ,"status":"error"}
        return e_response


def reqDocodocoW(ip_list):
    pool = Pool(processes=process_count)
    return pool.map(reqDocodoco,ip_list)


def checkDict(value):
    check_dict = False
    if isinstance(value, dict):
        check_dict = True
    return check_dict


def checkThirdPartyData(dict_in,target):
    res = ""
    end = False
    for key, value in dict_in.items():
        if end:
            break 
        elif checkDict(value):
           if ((target in value) & (checkDict(value.get(target)) is False)):
                end = True
                res = value.get(target)
           else:
               res = checkThirdPartyData(value,target)

    return res

def getThirdPartyData(dict_in,target,t_name):
    res = ""  
    if((t_name in dict_in)):
        v = dict_in.get(t_name)
        if((target in v) &  (checkDict(v.get(target)) is False)):
            res = v.get(target)
        else:
            res = checkThirdPartyData(v,target)

    return res

def getWeatherData(dict_in,target,wtype):
    res = ""
    if(wtype == "WeatherA"):
       res = dict_in['Area'][target]

    if(wtype == "WeatherP"):
        res = dict_in['Point'][target]

    return res

def main():
    r = csv.reader(sys.stdin)
    w = csv.writer(sys.stdout)
    header = []
    ip_list = []
    first = True
    tip_idx = -1

    for row in r:
        if first:
            header = row
            tip_idx = header.index("ipaddr")
	
            w.writerow(header)
            first = False
            continue

        tip = row[tip_idx]
        ip_list.append(tip)

    docodoco_results = reqDocodocoW(ip_list)


    for result in docodoco_results:
        return_data = []
        req_error = False
        req_staus = result.get("status")

        if (req_staus == "error"):
            req_error = True
        
        for  header_name in header:
            if(header_name == "ipaddr"):
                return_data.append(result.get('IP'))
            elif req_error:
                 return_data.append("request failed")    
            elif ('@' in header_name):
                target = header_name.split('@')[0]
                t_name = header_name.split('@')[1]

                #if((result.has_key("Weather")) and ( t_name == "WeatherA" or t_name == "WeatherP")):
                if(("Weather" in result) and ( t_name == "WeatherA" or t_name == "WeatherP")):
                    return_data.append(getWeatherData(result['Weather'],target,t_name))
                else:
                    return_data.append(getThirdPartyData(result,target,t_name))

            elif((header_name in result) & (checkDict(result.get(header_name)) is False)):
                return_data.append(result.get(header_name))
            else:
                return_data.append(checkThirdPartyData(result,header_name)) 
        w.writerow(return_data)

if __name__ == '__main__':
    main()
