# -*- coding: utf-8 -*-
# @File  : eventingcsc.py.py
# @Date  : 2023/4/12
# @Desc  :
from logging import info
import sys
import os
import re
import requests
from helper import Helper
import json
# from flatten_json import flatten
#from lib.soc_adpter import SOCAdpter
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option
    
#     json_data = {"data":[{"ioc":"zzv.no-ip.info","host":"192.168.91.174","intelligence":[{"judgments":["Malware","C2"],"severity":"high","ban":{"banned":2,"suggestion":"1、及时更新系统/应用程序补丁或版本"},"tags_classes":{"virus_family":["Rebhip","CyberGate"]},"basic_tag":"Backdoor","main_tag":"CyberGate","platform":["all","windows"],"tlp":0,"ports":[],"ioc_type":"domain","confidence_level":"high","is_malicious":"true","source_name":"微步在线-失陷指标","update_time":1650576353000}]}],"response_code":0,"verbose_msg":"成功"}
#     flattened_json = flatten_json(json_data)
#     # dict_generator(data)
#     flatten_json(json_data)
#     print(flattened_json)
@Configuration()
class ThreatbookTip(EventingCommand):
#     """
#     The eventingcsc command filters records from the events stream returning only those for which the status is same
#     as search query.

#     Example:

#     ``index="_internal" | head 4000 | eventingcsc status=200``

#     Returns records having status 200 as mentioned in search query.
#     """
    @staticmethod
    def flatten_json(src_json, prefix=""):
        flattened_dict = {}
        def flatten(json_data, parent_key=''):
            if isinstance(json_data, dict):
                for key, value in json_data.items():
                    new_key = f"{parent_key}.{key}" if parent_key else key
                    flatten(value, parent_key=new_key)
            elif isinstance(json_data, list):
                for index, item in enumerate(json_data):
                    new_key = f"{parent_key}.{index}" if parent_key else str(index)
                    flatten(item, parent_key=new_key)
            else:
                flattened_dict[parent_key] = json_data
        flatten(src_json, prefix)
        return flattened_dict

    def transform(self, records):
        # To connect with Splunk, use the instantiated service object which is created using the server-uri and
        # other meta details and can be accessed as shown below
        # Example:-
        #    service = self.service
        #    info = service.info //access the Splunk Server info

        domain_url = 'http://ip:8090/tip_api/v4/dns'
        ip_url = 'http://ip:8090/tip_api/v4/ip'
        # ip_url = 'http://ip:8090/tip_api/v4/ip'
        # domain_url = 'http://ip:8090/tip_api/v4/dns'
        # ip_url = 'http://ip:8090/tip_api/v4/ip'
        headers = {"Content-Type": "application/json;charset=UTF-8"}
        send = requests.Session()
        for record in records:    
            a = record['threatbook_ioc']
            query = {
                "apikey" : "YOUR-APIKEY",
                "resource" : a
            }
            if re.search(r"\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}", a):
                response = send.get(url = ip_url, headers = headers , params = query)
            else:
                response = send.get(url = domain_url, headers = headers , params = query)
            # print(self.send.json())
            sdata = response.text
            # data = response.json()
            # record.update({"threatbook_data" : sdata})
            data = json.loads(sdata)
            Threatbook_dict = {"ioc" : "", "host" : "", "judgments" : "", "severity" : "", "ban" : "", "cur_ips_ip" : "", "cur_ips_carrier" : "","cur_whois" : "", "tags_classes" : "",  "basic_tag" : "", "main_tag" : "", "ioc_type" : "", "confidence_level" : "", "is_malicious" : "", "source_name" : "", "update_time" : "", "response_code" : "", "verbose_msg" : "" }
            Threatbook_dict["ioc"] = Helper.getv(data, "data.0.ioc")
            Threatbook_dict["host"] = Helper.getv(data, "data.0.host")
            Threatbook_dict["judgments"] = Helper.getv(data, "data.0.intelligence.0.judgments")
            Threatbook_dict["severity"] = Helper.getv(data, "data.0.intelligence.0.severity")
            Threatbook_dict["ban"] = Helper.getv(data, "data.0.intelligence.0.ban")
            Threatbook_dict["tags_classes"] = Helper.getv(data, "data.0.intelligence.0.tags_classes")
            Threatbook_dict["basic_tag"] = Helper.getv(data, "data.0.intelligence.0.basic_tag")
            Threatbook_dict["main_tag"] = Helper.getv(data, "data.0.intelligence.0.main_tag")
            Threatbook_dict["cur_ips_ip"] = Helper.getv(data, "data.0.intelligence.0.cur_ips.0.ip")
            Threatbook_dict["cur_ips_carrier"] = Helper.getv(data, "data.0.intelligence.cur_ips.0.carrier")
            Threatbook_dict["cur_whois"] = Helper.getv(data, "data.0.intelligence.0.cur_whois")
            Threatbook_dict["ioc_type"] = Helper.getv(data, "data.0.intelligence.0.ioc_type")
            Threatbook_dict["confidence_level"] = Helper.getv(data, "data.0.intelligence.0.confidence_level")
            Threatbook_dict["is_malicious"] = Helper.getv(data, "data.0.intelligence.0.is_malicious")
            Threatbook_dict["source_name"] = Helper.getv(data, "data.0.intelligence.0.source_name")
            Threatbook_dict["update_time"] = Helper.getv(data, "data.0.intelligence.0.update_time")
            Threatbook_dict["response_code"] = Helper.getv(data, "response_code")
            Threatbook_dict["verbose_msg"] = Helper.getv(data, "verbose_msg")    
            if data["response_code"] == 0:
                severity = Helper.getv(data, "data.0.intelligence.0.severity")
                if severity == "info":
                    Threatbook_dict["threatbook_white"] = "yes"
                    record.update(Threatbook_dict)
                elif severity in ['low', 'medium', 'high', 'critical']:
                    Threatbook_dict["threatbook_white"] = "no"
                    record.update(Threatbook_dict)
            elif data['response_code'] == 2:
                Threatbook_dict["threatbook_white"] = "yes"
                record.update(Threatbook_dict)

            # if data["response_code"] == 0:
            #     # record.update({"threatbook_data_data" : data["data"][0]})
            #     severity = Helper.getv(data, "data.0.intelligence.0.severity")
            #     if severity == "info":
            #         record.update({"white" : "info"})
            #         record.update({"liuhaoran" : severity})
            #     elif severity in ['low', 'medium', 'high', 'critical']:
            #         flatten_data = ThreatbookTip.flateten_json(data,"threatbook")
            #         record.updat(flatten_data)
            #     else:
            #         record.update({"white" : "No IOC"})

            # elif data['response_code'] == 2:
            #     record.update({"white" : "No IOC"})
            # # # record.update({'threatbook' : flatten_data})
            yield record

dispatch(ThreatbookTip, sys.argv, sys.stdin, sys.stdout, __name__)

            #     if data['data'][0]['intelligence'][0]['severity'] in ['low', 'medium', 'high', 'critical']:
            #         flatten_data = ThreatbookTip.flatten_json(data,"threatbook")
            #         record.update(flatten_data)
            #     else:
            #         record.update({"white" : "No IOC"})

