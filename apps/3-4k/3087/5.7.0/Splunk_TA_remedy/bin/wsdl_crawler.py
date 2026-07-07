#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import remedy_consts as c
from remedy_connection_helper import get_urllib2_request


class WSDLCrawler:
    def __init__(
        self,
        username,
        password,
        http_scheme,
        disable_ssl_certificate_validation,
        certificate_path,
        proxy_settings,
    ):
        self.username = username
        self.password = password
        self.http_scheme = http_scheme
        self.disable_ssl_certificate_validation = disable_ssl_certificate_validation
        self.certificate_path = certificate_path
        self.proxy_settings = proxy_settings

    def crawl_file(self, url, file_path):
        resp = get_urllib2_request(
            url,
            self.username,
            self.password,
            self.http_scheme,
            self.disable_ssl_certificate_validation,
            self.certificate_path,
            self.proxy_settings,
        )
        wsdl_content = resp.read()
        wsdl_content = wsdl_content.decode()

        if wsdl_content.startswith(c.URLLIB_PREFIX):
            self._write_file(file_path, wsdl_content)
        else:
            raise Exception("Failed to get wsdl file from {}.".format(url))

    def crawl_files(self, wsdl_infos):
        for url, file_path in wsdl_infos.items():
            self.crawl_file(url, file_path)

    def validate_wsdl_url(self, url):
        resp = get_urllib2_request(
            url,
            self.username,
            self.password,
            self.http_scheme,
            self.disable_ssl_certificate_validation,
            self.certificate_path,
            self.proxy_settings,
        )
        wsdl_content = resp.read()
        wsdl_content = wsdl_content.decode()
        if not wsdl_content.startswith(c.URLLIB_PREFIX):
            raise Exception(
                "Can't get the WSDL file at %s. Check the URL, username or password and try again."
                % url
            )

    def validate_wsdl_urls(self, urls):
        for url in urls:
            self.validate_wsdl_url(url)

    @classmethod
    def _write_file(cls, file_path, content):
        output = open(file_path, "w")
        output.write(content)
