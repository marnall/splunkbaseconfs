# coding=utf-8
# Skuriocliet   .py
# Copyright 2019 Skurio Ltd

import sys
import os
import re
import string
import json
from datetime import date, time, datetime, timedelta, timezone
import requests

class SkurioClient:
    BASE_URL = 'https://api.skurio.com/breachalert/v1/'
    INFO = 1
    WARNING = 2
    ERROR = 3

    @classmethod
    def log_level_description(cls, level):
        if level == cls.INFO:
            return 'INFO'
        elif level == cls.WARNING:
            return 'WARNING'
        elif level == cls.ERROR:
            return 'ERROR'
        else:
            return 'UNKNOWN'

    def __init__(self, api_key, app_key, logger_obj = None, exit_on_error = True):
        self.api_key = api_key
        self.app_key = app_key
        self.folder_regex = None
        self.alert_regex = None
        if logger_obj is None:
            self.logger_obj = self
        else:
            self.logger_obj = logger_obj
        self.exit_on_error = exit_on_error

    def write_ba_log(self, level, str):
        print('{} : {}'.format(self.__class__.log_level_description(level), str))

    def log(self, level, str):
        self.logger_obj.write_ba_log(level, str)

    def build_url(self, resource_path):
        return self.__class__.BASE_URL+resource_path

    def auth_headers(self):
        return {'Authorization': 'Bearer '+self.app_key, 'X-Auth-Skurio-Key': self.api_key}

    def check_api_response(self, r):
        return (r is not None) \
        and ('data' in r) \
        and ('items' in r['data']) \
        and ('totalCount' in r['data']) \
        and ('itemsPerPage' in r['data']) 

    def get_alert(self, alert_id):
        r = requests.get(self.build_url('alerts/'+alert_id),headers=self.auth_headers())
        if (r.status_code == 200):
            r_obj = json.loads(r.text)
            if self.check_api_response(r_obj):
                return r_obj['data']['items']
        else:
            self.log(self.__class__.ERROR, 'Alerts API returned status code {} for alert {}'.format(r.status_code, alert_id))
            if self.exit_on_error:
                sys.exit()
        return None

    def get_alert_page(self, page):
        r = requests.get(self.build_url('alerts?page='+str(page)),headers=self.auth_headers())
        if (r.status_code == 200):
            return(json.loads(r.text))
        else:
            self.log(self.__class__.ERROR, 'Alerts API returned status code {} for alerts page {}'.format(r.status_code, page))
            if self.exit_on_error:
                sys.exit()
        return None

    def get_alerts(self):
        page = 0
        r = self.get_alert_page(page)
        alerts = None
        if self.check_api_response(r):
            alerts = r['data']['items']
            page = page + 1
            while r['data']['totalCount'] > (page * r['data']['itemsPerPage']):
                r2 = self.get_alert_page(page)
                if self.check_api_response(r2):
                    alerts.extend(r2['data']['items'])
                page = page + 1

        return alerts

    def get_result_page(self, alert_id, body, page):
        headers = self.auth_headers()
        headers['content-type'] = 'application/json'
        
        r = requests.post(self.build_url('alerts/'+alert_id+'/results?page='+str(page)), headers=headers,data=json.dumps(body))        
        self.log(self.__class__.INFO, 'Requesting results for alert ID {} for time period {}'.format(alert_id,body))
        if (r.status_code == 200):
            return(json.loads(r.text))
        else:
            self.log(self.__class__.ERROR, 'Results List API returned status code {} for alert {}'.format(r.status_code, alert_id))
            if self.exit_on_error:
                sys.exit()

        return None
            
    def get_results(self, alert_id, start_date, end_date):
        r = None
        start = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end = end_date.strftime('%Y-%m-%d %H:%M:%S')
        body = {"dateFrom": start, "dateTo": end}
        page = 0
        results = None
        r = self.get_result_page(alert_id, body, page)
        if self.check_api_response(r):
            results = r['data']['items']
            self.log(self.__class__.INFO, '{} to {} of {}'.format(page*r['data']['itemsPerPage'], page*r['data']['itemsPerPage']+r['data']['itemsPerPage'], r['data']['totalCount']))
            page = page + 1
            while r['data']['totalCount'] > (page * r['data']['itemsPerPage']):
                r2 = self.get_result_page(alert_id, body, page)
                if self.check_api_response(r2):
                    self.log(self.__class__.INFO, '{} to {} of {}'.format(page*r['data']['itemsPerPage'], page*r['data']['itemsPerPage']+r['data']['itemsPerPage'], r['data']['totalCount']))
                    results.extend(r2['data']['items'])
                page = page + 1

        return results
            
    def get_result_details(self, alert_name, alert_id, result_id):
        url = self.build_url('alerts/'+alert_id+'/results/' + result_id)
        self.log(self.__class__.INFO, 'Getting result details {}'.format(url))
        r = requests.get(url, headers=self.auth_headers())
        if (r.status_code == 200):
            return(json.loads(r.text))
        else:
            self.log(self.__class__.ERROR, 'Result Details API returned status code {} for "{}" ({}), resultId {}'.format(r.status_code, alert_name, alert_id, result_id))
            if self.exit_on_error:
                sys.exit()
        return None
