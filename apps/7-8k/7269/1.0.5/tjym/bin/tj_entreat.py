#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project:
@File   :tj_entreat.py
@Author :Imocence
@Date   :2023/11/1
"""
import base64
import hashlib
import hmac
import json
import platform
import subprocess
import time
import uuid

import requests

try:
    from urllib import urlencode
    from urlparse import urlparse
except:
    requests.packages.urllib3.disable_warnings()
    from urllib.parse import urlencode, urlparse

content_md5 = "Content-MD5"
content_length = "Content-Length"
content_type = "Content-Type"

lf = '\n'


class Entreat(object):
    SYSTEM_HEADERS = (
        X_CA_SIGNATURE, X_CA_SIGNATURE_HEADERS, X_CA_TIMESTAMP, X_CA_NONCE, X_CA_KEY, X_CA_STAGE
    ) = (
        'X-Ca-Signature', 'X-Ca-Signature-Headers', 'X-Ca-Timestamp', 'X-Ca-Nonce', 'X-Ca-Key', 'X-Ca-Stage'
    )

    HTTP_HEADERS = (
        HTTP_HEADER_ACCEPT, HTTP_HEADER_CONTENT_MD5,
        HTTP_HEADER_CONTENT_TYPE, HTTP_HEADER_USER_AGENT, HTTP_HEADER_DATE
    ) = (
        'Accept', 'Content-MD5',
        'Content-Type', 'User-Agent', 'Date'
    )

    BODY_TYPE = (
        FORM, STREAM
    ) = (
        'FORM', 'STREAM'
    )

    HTTP_PROTOCOL = (HTTP, HTTPS) = ('http', 'https')
    HTTP_METHOD = (
        GET, POST, PUT, DELETE, HEADER
    ) = (
        'GET', 'POST', 'PUT', 'DELETE', 'HEADER'
    )
    CONTENT_TYPE = (
        CONTENT_TYPE_FORM, CONTENT_TYPE_STREAM,
        CONTENT_TYPE_JSON, CONTENT_TYPE_XML, CONTENT_TYPE_TEXT
    ) = (
        'application/x-www-form-urlencoded', 'application/octet-stream',
        'application/json', 'application/xml', 'application/text'
    )

    def __init__(self, url=None, method=GET, headers={}, content_type=None, body=None, time_out=30000, sign_body=True):
        self._url = url
        self._method = method
        self._headers = headers
        self._content_type = content_type or self.CONTENT_TYPE_FORM
        self._body = body
        self._time_out = time_out
        try:
            self._app_key = base64.decodestring('MjQ2MzQ1NzI='.encode('ascii')).encode("utf-8")
            self._app_secret = base64.decodestring('ODEyZDA3OGZlODE0M2U1Mjk1OTlmOWQ2Njg5YTYwNDY='.encode('ascii'))
        except:
            self._app_key = base64.b64decode('MjQ2MzQ1NzI='.encode('ascii')).decode("utf-8")
            self._app_secret = base64.b64decode('ODEyZDA3OGZlODE0M2U1Mjk1OTlmOWQ2Njg5YTYwNDY='.encode('ascii'))

        self._sign_body = sign_body
        self.cert = None
        self._connection = None
        self._post_data = None
        self.__proxies = {
            "http": 'http://127.0.0.1:1081',
            "https": 'http://127.0.0.1:1081',
        }
        pass

    def _set_method(self, method):
        self._method = method

    def _set_cert(self, cert_file, key_file):
        self.cert = (cert_file, key_file)

    def execute(self):
        try:
            if self._content_type == self.CONTENT_TYPE_FORM and self._body:
                _params = urlencode(self._body)
            elif self._content_type == self.CONTENT_TYPE_JSON and self._body:
                _params = json.dumps(self._body)
            else:
                _params = self._body
            # Determine the request method
            if self.cert:
                resp = requests.request(self._method, self._url, data=_params, headers=self._sort_head(), verify=True,
                                        cert=self.cert)
            else:
                resp = requests.request(self._method, self._url, data=_params, headers=self._sort_head(), verify=False)
            # result message
            return resp.status_code, resp.content.decode('utf-8'), resp.headers
        except Exception as e:
            return None, str(e.message), None
        finally:
            self._close_connection()

    def del_execute(self, url):
        try:
            response = requests.delete(url, headers=self._sort_head())
            if response.status_code == 200:
                print("HTTP Event Collector 配置删除成功！")
            else:
                print("删除 HTTP Event Collector 配置时出现问题：{}".format(response.text))
        except requests.exceptions.RequestException as e:
            print("请求异常: {e}".format(e))

    def _sort_head(self):
        headers = self._headers
        if self.HTTP_HEADER_ACCEPT in headers and headers[self.HTTP_HEADER_ACCEPT]:
            headers[self.HTTP_HEADER_ACCEPT] = headers[self.HTTP_HEADER_ACCEPT]
        else:
            headers[self.HTTP_HEADER_ACCEPT] = self.CONTENT_TYPE_JSON

        if self._content_type:
            headers[self.HTTP_HEADER_CONTENT_TYPE] = self._content_type
        else:
            headers[self.HTTP_HEADER_CONTENT_TYPE] = self.CONTENT_TYPE_JSON

        if self.HTTP_HEADER_USER_AGENT in headers and headers[self.HTTP_HEADER_USER_AGENT]:
            headers[self.HTTP_HEADER_USER_AGENT] = headers[self.HTTP_HEADER_USER_AGENT]
        else:
            headers[self.HTTP_HEADER_USER_AGENT] = 'demo/aliyun/java'

        if headers.get(self.X_CA_STAGE):
            headers[self.X_CA_STAGE] = headers.get(self.X_CA_STAGE)

        headers[self.X_CA_KEY] = self._app_key
        headers[self.X_CA_NONCE] = str(uuid.uuid4())
        headers[self.X_CA_TIMESTAMP] = self.get_timestamp()
        if self.POST == self._method and self.CONTENT_TYPE_STREAM == self._content_type:
            headers[self.HTTP_HEADER_CONTENT_MD5] = self.get_md5_base64_str(self._body)
            str_to_sign = self.__sort_sign_str(uri=self._url, method=self._method, headers=headers)
        else:
            str_to_sign = self.__sort_sign_str(uri=self._url, method=self._method, headers=headers, body=self._body)
        headers[self.X_CA_SIGNATURE] = self.sha_hmac256_sign(str_to_sign, self._app_secret)

        return headers

    def __sort_sign_str(self, uri=None, method=None, headers=None, body=None):
        """
        :param uri: 请求路径
        :param method: 请求方式
        :param headers: 请求头信息
        :param body: 请求消息体
        :return: 构建验签字符串
        """
        string_to_sign = [method, lf]

        if self.HTTP_HEADER_ACCEPT in headers and headers[self.HTTP_HEADER_ACCEPT]:
            string_to_sign.append(headers[self.HTTP_HEADER_ACCEPT])

        string_to_sign.append(lf)
        if self.HTTP_HEADER_CONTENT_MD5 in headers and headers[self.HTTP_HEADER_CONTENT_MD5]:
            string_to_sign.append(headers[self.HTTP_HEADER_CONTENT_MD5])

        string_to_sign.append(lf)
        if self.HTTP_HEADER_CONTENT_TYPE in headers and headers[self.HTTP_HEADER_CONTENT_TYPE]:
            string_to_sign.append(headers[self.HTTP_HEADER_CONTENT_TYPE])

        string_to_sign.append(lf)
        if self.HTTP_HEADER_DATE in headers and headers[self.HTTP_HEADER_DATE]:
            string_to_sign.append(headers[self.HTTP_HEADER_DATE])

        string_to_sign.append(lf)
        string_to_sign.append(self._build_resource(uri=urlparse(uri).path, body=body, sign_with_body=self._sign_body))
        return ''.join(string_to_sign)

    def _close_connection(self):
        try:
            if self._connection is not None:
                self._connection.close()
        except Exception as e:
            pass

    def get_md5_base64_str(self, content):
        """
        :param content: 加密参数
        :return: 获取BASE64加密MD5值
        """
        return base64.encodestring(self.get_md5(content)).strip()

    @staticmethod
    def _build_resource(uri, body={}, sign_with_body=True):
        if '?' in uri:
            uri, query_str = uri.split('?', 1)
            if not body:
                body = {}
            query_str_params = [param.split('=') for param in query_str.split('&')]
            for key, value in query_str_params:
                body.setdefault(key, value)

        resource = [uri]
        if body and sign_with_body:
            resource.append("?")
            param_list = sorted(body.keys())
            for i, key in enumerate(param_list):
                if i > 0:
                    resource.append("&")
                resource.append("{}={}".format(key, body[key]))

        return "".join(resource)

    @classmethod
    def _format_header(cls, headers={}):
        """
        :param headers: 头信息集合
        :return: 参与header验证头信息
        """
        header_list = [k for k in headers.keys() if k.startswith("X-Ca-")]
        temp_headers = ["{}: {}{}".format(k, str(headers[k]), lf) for k in header_list]
        headers[cls.X_CA_SIGNATURE_HEADERS] = ','.join(header_list)
        return ''.join(temp_headers)

    @staticmethod
    def sha_hmac256_sign(content, secret):
        """
        :param content: 加密参数
        :param secret: 密钥
        :return: 生成使用SHA-256哈希算法和HMAC（散列消息认证码）的签名
        """
        h = hmac.new(secret, content.encode("utf-8"), hashlib.sha256)
        return base64.encodestring(h.digest()).decode().strip()

    @staticmethod
    def get_md5(content):
        """
        :param content: 加密参数
        :return: 获取MD5值
        """
        m = hashlib.md5()
        m.update(str(content))
        return m.digest()

    @staticmethod
    def convert_utf8(input_string):
        if isinstance(input_string, str):
            input_string = input_string.encode('utf-8')
        return input_string

    @staticmethod
    def get_timestamp():
        return str(int(time.time() * 1000))

    @staticmethod
    def get_spl_timestamp(time_str, format_str="%Y-%m-%dT%H:%M:%SZ"):
        return int(time.mktime(time.strptime(time_str, format_str)))

    @staticmethod
    def get_time_format(time_str, format_str="%Y-%m-%d %H:%M:%S"):
        return time.strftime(format_str, time.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ"))

    @staticmethod
    def get_spl_time(time_str, time_zone="+08:00"):
        try:
            if "Windows" not in platform.system():
                result = subprocess.run("date -d '{}' +%z".format(time_str), shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    time_zone = result.stdout.strip()
                    if ":" not in time_zone:
                        time_zone = "{}:{}".format(time_zone[:-2], time_zone[-2:])
        except:
            pass
        return Entreat.get_time_format(time_str, "%Y-%m-%dT%H:%M:%S.%f%z")[:-3] + time_zone


if __name__ == '__main__':
    data = {"token": "1", "page": '2'}
    _code, _body, _heads = Entreat(url="https://api.tj-un.com/v1/iocs", body=data, method='POST').execute()
    if _code == 200:
        j = json.loads(_body)
        print(json.dumps(j, indent=4))
