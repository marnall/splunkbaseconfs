#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import logging
import urllib.parse
import urllib.request

import remedy_consts as c
from remedy_connection_helper import get_suds_client


class RemedyIncidentService:
    def __init__(
        self,
        username,
        password,
        http_scheme,
        disable_ssl_certificate_validation,
        certificate_path,
        proxy_settings,
    ):
        logging.getLogger("suds.client").setLevel(logging.CRITICAL)
        self.username = username
        self.password = password
        self.http_scheme = http_scheme
        self.disable_ssl_certificate_validation = disable_ssl_certificate_validation
        self.certificate_path = certificate_path
        self.proxy_settings = proxy_settings

    def execute(self, wsdl_file_path, operation_name, args):
        wsdl_url = urllib.parse.urljoin(
            str("file:"), str(urllib.request.pathname2url(wsdl_file_path))
        )
        # jscpd:ignore-start
        client = get_suds_client(
            wsdl_url,
            self.username,
            self.password,
            self.http_scheme,
            self.disable_ssl_certificate_validation,
            self.certificate_path,
            self.proxy_settings,
        )
        # jscpd:ignore-end
        operation = getattr(client.service, operation_name)
        resp = operation(**args)
        return resp

    def get(self, wsdl_file_path, incident_num):
        wsdl_url = urllib.parse.urljoin(
            str("file:"), str(urllib.request.pathname2url(wsdl_file_path))
        )
        client = get_suds_client(
            wsdl_url,
            self.username,
            self.password,
            self.http_scheme,
            self.disable_ssl_certificate_validation,
            self.certificate_path,
            self.proxy_settings,
        )
        result = client.service.HelpDesk_Query_Service(Incident_Number=incident_num)
        result_data = dict()
        for k, v in result.__dict__.items():
            if k.startswith("__") or k.startswith("_"):
                continue
            if v is not None:
                result_data[k] = v
        result_data[c.INCIDENT_NUMBER] = incident_num
        return result_data

    def getIncidents(self, wsdl_url, args):
        client = get_suds_client(
            wsdl_url,
            self.username,
            self.password,
            self.http_scheme,
            self.disable_ssl_certificate_validation,
            self.certificate_path,
            self.proxy_settings,
        )
        result = client.service.GetEvents(**args)
        result_data_set = []
        for r in result:
            result_data = dict()
            for k, v in r.__dict__.items():
                if k.startswith("__") or k.startswith("_"):
                    continue
                if v is not None:
                    result_data[k] = str(v)
            result_data_set.append(result_data)
        return result_data_set

    def incident_operate(self, wsdl_url, args):
        client = get_suds_client(
            wsdl_url,
            self.username,
            self.password,
            self.http_scheme,
            self.disable_ssl_certificate_validation,
            self.certificate_path,
            self.proxy_settings,
        )
        result = client.service.Process_Event(**args)
        result_data = {}
        for k, v in result.__dict__.items():
            if k.startswith("__") or k.startswith("_"):
                continue
            if v is not None:
                result_data[k] = str(v)
        return result_data
