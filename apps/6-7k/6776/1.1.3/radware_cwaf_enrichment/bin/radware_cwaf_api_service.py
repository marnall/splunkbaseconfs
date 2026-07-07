#!/usr/bin/env python
#
# Radware Cloud WAF API Services
# This module contains the classes that implement the API services for Radware Cloud WAF access.
#
# Dimiter Todorov - 2023

import http.client
import json
import logging
import os
import re
import sys
import traceback
import urllib.parse
import urllib.request
from base64 import b64encode


# Parent class for Radware API services
# This class is not intended to be used directly - use one of the child classes instead.
class RadwareService:
    radware_auth_endpoint = "/api/v1/authn",
    radware_token_endpoint = "/oauth2/aus7ky2d5wXwflK5N1t7/v1/authorize",

    def __init__(self, credential, settings, radware_api_host="https://portal.radwarecloud.com",
                 radware_auth_endpoint="https://radware-public.okta.com", logger=None) -> None:
        self.credential = credential

        self.radware_user = credential.get("username")
        self.radware_password = credential.get("password")

        self.radware_api_host = radware_api_host
        self.radware_auth_endpoint = radware_auth_endpoint
        self.radware_tenant_id = None
        # Facility info - prepended to log lines
        facility = os.path.basename(__file__)
        facility = os.path.splitext(facility)[0]
        if logger:
            self.app_logger = logger
        else:
            temp_logger = logging.getLogger(facility)
            temp_logger.propagate = False
            temp_logger.setLevel("DEBUG")
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s %(levelname)s ' + facility + ' - %(message)s')
            handler.setFormatter(formatter)
            temp_logger.addHandler(handler)
            self.app_logger = temp_logger

    def get_tenant_id(self):
        raise NotImplementedError

    def login(self):
        raise NotImplementedError

    def get_applications(self):
        raise NotImplementedError


def get_boolean_for_value(value):
    if value in [True, False]:
        return value

    elif str(value).strip().lower() in ["true", "1"]:
        return True

    elif str(value).strip().lower() in ["false", "0"]:
        return False


class RadwareCwafService(RadwareService):
    def __init__(self, credential, settings, radware_api_host="https://portal.radwarecloud.com",
                 radware_auth_endpoint="https://radware-public.okta.com", logger=None) -> None:
        super().__init__(credential, settings, radware_api_host, radware_auth_endpoint, logger)

        if get_boolean_for_value(settings['use_proxy']):
            self.credential['use_proxy'] = get_boolean_for_value(settings['use_proxy'])
            self.credential['proxy_host'] = settings['proxy_host']
            self.credential['proxy_port'] = settings['proxy_port']
            if settings.get('proxy_user') and settings.get('proxy_password'):
                self.credential['proxy_user'] = settings['proxy_user']
                self.credential['proxy_password'] = settings['proxy_password']
        else:
            self.credential['use_proxy'] = False

    def login(self):
        self.get_session_token()
        self.get_tenant_id()

    def get_https_connection(self, url):
        headers = {
            'User-Agent': 'SplunkRadwareEnrichment/1.0.1',
            'Accept': 'application/json, text/plain, */*'
        }
        if self.credential['use_proxy']:
            conn = http.client.HTTPSConnection(self.credential['proxy_host'], self.credential['proxy_port'])
            if self.credential.get('proxy_user') and self.credential.get('proxy_password'):
                auth_header = self.credential['proxy_user'] + \
                              ":" + self.credential['proxy_password']
                auth_header = b64encode(auth_header.encode()).decode("ascii")
                headers['Proxy-Authorization'] = "Basic %s", auth_header
            conn.set_tunnel(url, port=443)
        else:
            conn = http.client.HTTPSConnection(url)
        return conn, headers

    def get_session_token(self):
        conn, headers = self.get_https_connection("radware-public.okta.com")
        payload = "{\"username\":\"" + self.credential["username"] + "\",\"password\":\"" + self.credential[
            "password"] + "\",\"options\":{ \"multiOptionalFactorEnroll\": true,\"warnBeforePasswordExpired\": true}}"
        headers['Content-Type'] = "application/json"

        conn.request("POST", "/api/v1/authn", payload, headers)
        res = conn.getresponse()
        if res.status != 200:
            self.app_logger.error("Failed Session with response => %d : %s", (res.status, res.reason))
            raise Exception("Failed Session with response => %d : %s" % (res.status, res.reason))
        else:
            data = res.read()
            response = json.loads(data.decode("utf-8"))
            self.credential["sessionToken"] = response["sessionToken"]
            try:
                conn.request("GET", "/oauth2/aus7ky2d5wXwflK5N1t7/v1/authorize?client_id=M1Bx6MXpRXqsv3M1JKa6" +
                             "&nonce=n-0S6_WzA2M&" +
                             "prompt=none&" +
                             "redirect_uri=https%3A" + "%2F" + "%2F" + "portal-ng.radwarecloud.com" + "%2F" + "&" +
                             "response_mode=form_post&" +
                             "response_type=token&" +
                             "scope=api_scope&" +
                             "sessionToken=" + self.credential["sessionToken"] + "&" +
                             "state=parallel_af0ifjsldkj", "", headers)
                res = conn.getresponse()
                if res.status != 200:
                    self.app_logger.error("Failed Radware Authorization with response => %d : %s", res.status,
                                          res.reason)
                    raise Exception("Failed Radware Authorization with response => %d : %s" % (res.status, res.reason))
                else:
                    data = res.read()
                    result = re.split('([^;]+);?', res.getheader('set-cookie'), re.MULTILINE)
                    for cookie in result:
                        dt = re.search(',\sDT=([^;]+);?', cookie, re.MULTILINE)
                        sid = re.search(',\ssid=([^;]+);?', cookie, re.MULTILINE)
                        proximity = re.search(',(.+=[^;]+);?\sEx', cookie, re.MULTILINE)
                        sessID = re.search(r'JSESSIONID=([^;]+);?', cookie, re.MULTILINE)
                        if proximity:
                            self.credential["proximity"] = proximity.group(1)
                        elif dt:
                            self.credential["DT"] = dt.group(1)
                        elif sid:
                            self.credential["sid"] = sid.group(1)
                        elif sessID:
                            self.credential["JSESSIONID"] = sessID.group(1)
                    self.credential["Bearer"] = \
                        data.decode('unicode_escape').split('name="access_token" value="')[1].split('"')[0]
                    return 0
            except:
                self.app_logger.error("Error occurred on getting the Authorization from Cloud AppSec portal-ng. %s",
                                      traceback.format_exc())
                raise Exception("Failed Radware Authorization with response => %d : %s" % (res.status, res.reason))

    def get_tenant_id(self):
        conn, headers = self.get_https_connection("portal-ng.radwarecloud.com")
        headers['Authorization'] = "Bearer %s" % self.credential["Bearer"]
        try:
            conn.request("GET", "/v1/users/me/summary", headers=headers)
            response = conn.getresponse()
            if response.status != 200:
                self.app_logger.error("Failed TenantID with response => %d : %s", response.status, response.reason)
                exit(2)
            else:
                data = json.loads(response.read().decode("utf8"))
                self.radware_tenant_id = data["tenantEntityId"]
                return data["tenantEntityId"]
        except:
            self.app_logger.error("Error occurred on getting the TenantID from Cloud AppSec portal-ng. %s",
                                  traceback.format_exc())
            raise Exception("Error occurred on getting the TenantID from Cloud AppSec portal-ng. %s",
                            traceback.format_exc())

    def get_applications(self):
        apps = []
        conn, headers = self.get_https_connection("portal-ng.radwarecloud.com")
        headers['Authorization'] = "Bearer %s" % self.credential["Bearer"]
        headers['Requestentityids'] = self.radware_tenant_id
        try:
            last_page = False
            request_payload = {
                'page': 0,
                'size': 10
            }
            while not last_page:
                conn.request("GET", f"/v1/gms/applications?{urllib.parse.urlencode(request_payload)}", headers=headers)
                response = conn.getresponse()
                if response.status != 200:
                    self.app_logger.error("Failed Application with response => %d : %s", response.status,
                                          response.reason)
                    exit(2)
                else:
                    data = json.loads(response.read().decode("utf8"))
                    if data['last']:
                        last_page = True
                    if len(data['content']) > 0:
                        apps = apps + data['content']
                    else:
                        last_page = True
                    request_payload['page'] += 1
            return apps
        except:
            self.app_logger.error("Error occurred on getting the Applications from Cloud AppSec portal-ng. %s",
                                  traceback.format_exc())
            exit(2)
