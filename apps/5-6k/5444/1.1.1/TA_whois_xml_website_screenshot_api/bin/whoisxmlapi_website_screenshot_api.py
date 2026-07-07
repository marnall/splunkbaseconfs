#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import sys
import os
import requests
import re

import logging
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators

from splunk.clilib import cli_common as cli
import splunklib.client as client
import splunk


@Configuration(distributed=False)
class WXAWebsiteScreenshotCommand(GeneratingCommand):
    url = Option(require=True)
    credits_type = Option(require=False)
    api_key = Option(require=False)
    image_type = Option(require=False)
    width = Option(require=False)
    height = Option(require=False)
    thumb_width = Option(require=False)
    mode = Option(require=False)
    scroll = Option(require=False)
    full_page = Option(require=False)
    no_js = Option(require=False)
    delay = Option(require=False)
    timeout = Option(require=False)
    scale = Option(require=False)
    retina = Option(require=False)
    ua = Option(require=False)
    mobile = Option(require=False)
    touch_screen = Option(require=False)
    landscape = Option(require=False)
    quality = Option(require=False)
    cookies = Option(require=False)

    __URL_REGEX = re.compile(r"(?:(?:https|http):\/\/)?(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+" +
                             r"[a-z0-9][a-z0-9-]{0,61}[a-z0-9]\/?(?:[\w\d\-.,\/]+)?")

    def generate(self):
        api_config = self._get_application_config("whoisxmlapi_website_screenshot.conf", "whoisxmlapi_website_screenshot")

        session_key = self.metadata.searchinfo.session_key

        try:
            service = client.connect(token=session_key, app="TA_whois_xml_website_screenshot_api")
        except Exception as e:
            self.logger.error("An error occurred connecting to splunkd: " + str(e))
            exit(1)

        if self.api_key and len(self.api_key) > 0:
            api_config['api_key'] = self.api_key
        else:
            for storage_password in service.storage_passwords:
                if storage_password.username == 'admin' and storage_password.realm == 'api_key':
                    api_config['api_key'] = storage_password.clear_password
                    break

        if self.credits_type and len(self.credits_type) > 0:
            api_config['credits_type'] = self.credits_type

        _term = self.url.strip(' \n\r')

        _parameters = {'url': WXAWebsiteScreenshotCommand._validate_term(_term)}

        for k, v in self._get_specified_options().items():
            _parameters[k] = v

        if _parameters['url'] is None and len(_parameters['url']) <= 0:
            self.logger.error('Given search terms are invalid')
            exit(2)

        api_response = ''
        try:
            api_response = self._send_api_request(_parameters, api_config)
        except requests.exceptions.RequestException as e:
            self.logger.error(e)
            exit(3)

        try:
            _ = json.loads(api_response)
            yield {'error': api_response.decode("utf-8")}
            self.logger.error(api_response)
        except:
            pass

        yield {'image': api_response.decode('utf-8')}

    @staticmethod
    def _get_application_config(file, stanza):
        app_dir = os.path.dirname(__file__)
        config_path = os.path.join(app_dir, "../default", file)
        config = cli.readConfFile(config_path)
        local_config_path = os.path.join(app_dir, "../local", file)

        if os.path.exists(local_config_path):
            local_config = cli.readConfFile(local_config_path)
            for name, content in local_config.items():
                if name in config:
                    config[name].update(content)
                else:
                    config[name] = content

        return config[stanza]

    @staticmethod
    def _send_api_request(_search_parameters, _api_config):
        _search_parameters['apiKey'] = _api_config['api_key']
        _search_parameters['credits'] = _api_config['credits_type']
        _search_parameters['imageOutputFormat'] = 'base64'

        response = requests.get(
            _api_config['api_url'],
            params=_search_parameters
        )

        return response.content

    @staticmethod
    def _validate_term(term):
        if WXAWebsiteScreenshotCommand.__URL_REGEX.search(term):
            return term
        return None

    def _get_specified_options(self):
        """

        :return: dictionary
        """
        res = {}
        if self.image_type is not None and self.image_type.lower() in ['jpg', 'png']:
            res['type'] = self.image_type.lower()
        else:
            res['type'] = 'jpg'

        if self.mode is not None and self.mode in ['fast', 'slow']:
            res['mode'] = self.mode

        if self.quality is not None and (40 <= int(self.quality) <= 99) and res['type'] is 'jpg':
            res['quality'] = self.quality

        if self.timeout is not None and (1000 <= int(self.timeout) <= 30000):
            res['timeout'] = self.timeout

        if self.delay is not None and (0 < int(self.delay) <= 10000):
            res['delay'] = self.delay

        if self.full_page is not None and bool(self.full_page) is not False:
            res['fullPage'] = self.full_page

        if self.width is not None and (100 <= int(self.width) <= 3000):
            res['width'] = self.width
        else:
            self.width = 600

        if self.thumb_width is not None and (50 <= int(self.thumb_width) <= self.width):
            res['thumbWidth'] = self.thumb_width

        if self.height is not None and (100 <= int(self.height) <= 3000):
            res['height'] = self.height

        if self.scale is not None and (0.5 <= float(self.scale) <= 4.0):
            res['scale'] = self.scale

        if self.landscape is not None and bool(self.landscape) is True:
            res['landscape'] = self.landscape

        if self.mobile is not None and bool(self.mobile) is True:
            res['mobile'] = self.mobile

        if self.no_js is not None and bool(self.no_js) is True:
            res['noJs'] = self.no_js

        if self.retina is not None and bool(self.retina) is True:
            res['retina'] = self.retina

        if self.scroll is not None and bool(self.scroll) is True:
            res['scroll'] = self.scroll

        if self.touch_screen is not None and bool(self.touch_screen) is True:
            res['touchScreen'] = self.touch_screen

        if self.ua is not None and len(str(self.ua)) is True:
            res['ua'] = self.ua

        if self.cookies is not None and len(str(self.cookies)) > 0:
            res['cookies'] = self.cookies

        return res


dispatch(WXAWebsiteScreenshotCommand, sys.argv, sys.stdin, sys.stdout, None)
