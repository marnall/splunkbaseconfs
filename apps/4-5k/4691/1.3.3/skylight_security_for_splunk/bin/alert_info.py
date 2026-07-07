from splunk.persistconn.application import PersistentServerConnectionApplication
import operator
import httplib
import socket
import datetime
import re
import json
import urllib
import os
import hashlib
import requests
import subprocess
import sys
import time

class AlertHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)
        self.splunk_url = "https://localhost:8089/servicesNS/nobody/search/search/jobs/export?output_mode=raw"
        self.headers = lambda token : {
            'Authorization': 'Splunk %s' % token,
            'Content-Type': 'application/json'
        }

    def handle(self, args):
        payload = json.loads(args)
        query = payload['query'][0]
        query.remove('action')
        query = str(query[0])

        if query == 'changeStatus' or query == 'changeOwner' or query == 'changeComment':
            return self.change_alert_info(args, query)
        elif query == 'getUsers':
            return self.getUsers(args)
        elif query == 'change_all_alerts_status':
            return self.change_all_alerts_status(args)
        else:
            query += "Bad action"
            return {"payload": query, "status": 402}

    def edit_alert(self, ids, field, value, token):
        def alert_info(alert_id, token):
            data = {
            'search': 'search index=pvx_alerts id="%s"' % alert_id
            }
            search_result = requests.post(self.splunk_url, verify=False, headers=self.headers(token), data=data)

            latest_event = search_result.text.split("\n")
            if len(latest_event) > 1:
                times = []
                for idx, event in enumerate(latest_event):
                    alert = re.findall(r"(?P<field>[\w\_]+)=(?:\")?(?P<value>[\w\. \,\/\(\)\;\-\'\[\]]+)(?:\")?(?:\,)?\s", event)
                    
                    for fields in alert:
                        if fields[0] == "edit_time":
                            value = fields[1][:-1]
                            times.append([int(value), idx])

                latest_event = latest_event[max(times)[1]]

            alert = re.findall(r"(?P<field>[\w\_]+)=(?:\")?(?P<value>[\w\. \,\/\(\)\;\-\'\[\]]+)(?:\")?(?:\,)?\s", latest_event+"\n")
            alert.append(("_time", search_result.text.split(", ")[0]))
            remove_fields = ["info_min_time", "info_max_time", "info_search_time", "orig_host"]
            for idx, a in enumerate(alert):
                if a[0] in remove_fields:
                    del alert[idx]

            return alert

        def get_unix_time(dtime):
            pm = " +"
            if " -" in dtime:
                pm = " -"
            timestamp = time.mktime(datetime.datetime.strptime(dtime.split(pm)[0], "%m/%d/%Y %H:%M:%S").timetuple())
            return timestamp

        for alert_id in ids:
            info = alert_info(alert_id, token)
            search_array = ["| makeresults | eval _time = {} | eval edit_time = {}".format(get_unix_time(info[-1][1]), int(time.time()))]            
            search_table = []
            for i in info:
                if i[0] == "edit_time" or i[0] == "_time": continue
                if i[0] == field:
                    search_array.append("| eval {} = \"{}\"".format(field, value))
                elif i[0] == "Destination":
                    if type(i[1]) == list:
                        destination_list = i[1]

                        if len(destination_list) > 1:
                            search_array.append("| eval Destination = \"{}\" | makemv Destination".format(" ".join(destination_list)))
                    else:
                        search_array.append("| eval Destination = \"{}\"".format(i[1]))
                else:
                    loc_value = i[1]
                    if "," in loc_value[-1]:
                        loc_value = loc_value[:-1]
                    search_array.append("| eval {} = \"{}\"".format(i[0], loc_value))

                search_table.append(i[0])

            table = "| table _time, edit_time, {}".format(", ".join(search_table))
            
            data = {
                "search": "{} {} | collect index=pvx_alerts".format(" ".join(search_array), table)
            }

            r = requests.post(self.splunk_url, verify=False, headers=self.headers(token), data=data)
        return  {"payload": "Done", "status": 201}

    def change_all_alerts_status(self, args):
        payload = json.loads(args)
        token = payload["session"]["authtoken"]
        
        data = str(payload["payload"])
        alerts = json.loads(data)
        
        return self.edit_alert(alerts["id"], "status", alerts["status"], token)

    def change_alert_info(self, args, action):
        payload = json.loads(args)
        token = payload["session"]["authtoken"]

        data = str(payload["payload"])
        alert_new_info = json.loads(data)

        if action == 'changeStatus':
            return self.edit_alert([alert_new_info["id"]], "status", alert_new_info["status"], token)
        elif action == 'changeOwner':
            return self.edit_alert([alert_new_info["id"]], "owner", alert_new_info["owner"], token)
        elif action == 'changeComment':
            return self.edit_alert([alert_new_info["id"]], "comment", alert_new_info["comment"], token)

    def getUsers(self, args):
        payload = json.loads(args)
        token = payload["session"]["authtoken"]
        url = "https://localhost:8089/servicesNS/admin/search/authentication/users?output_mode=json"
        try:
            r = requests.get(url, verify=False, headers=self.headers(token))
            entries = json.loads(r.text)
            user_list = []
            for entry in entries["entry"]:
                user_list.append(entry['name'])
            return {"payload": user_list, "status": 200}
        except Exception as e:
            return {"payload": str(e), "status": 402}
