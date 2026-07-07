import sys
import os.path as op
import traceback
import urllib
import json
import logging
from splunktalib.rest import build_http_connection
from splunktalib.common import log
from splunktalib.common.util import is_true

sys.path.insert(0, op.join(op.dirname(op.abspath(__file__)), "splunktalib"))

_LOGGER = log.Logs().get_logger("ta_okta", level=logging.DEBUG)


class OktaRestClient(object):
    """
    Okta REST client to send requests
    """
    def __init__(self, config):
        """
        @config: dict contains url, token, proxy_enabled,
                 proxy_url, proxy_port, proxy_username, proxy_password,
                 date_start, page_size, proxy_type, proxy_rdns, custom_cmd_enabled,
                 okta_server_url, okta_server_token
        """
        self.config = config

    def _build_http_connection(self):
        """
        Build connection based on rest.py
        """

        enabled = is_true(self.config.get("proxy_enabled", ""))
        if not enabled:
            if self.config.get("proxy_url"):
                del self.config['proxy_url']
            if self.config.get("proxy_port"):
                del self.config['proxy_port']
        return build_http_connection(self.config, timeout=60)

    def validate(self):
        return True

    def _get_headers(self, token='token'):
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "SSWS {}".format(self.config.get(token)),
        }

    def request(self, endpoint, params=None, themethod="GET", theurl='url', thetoken='token'):
        """
        Send REST requests
        """
        # print self.config

        http = self._build_http_connection()
        
        url = self.config.get(theurl)

        rest_uri = "{}{}".format(url, endpoint)
        if params:
            url_params = urllib.urlencode(params)
            rest_uri = "{}?{}".format(rest_uri, url_params)
        def rebuild_http(i):
            if i == 0:
                _LOGGER.info("Rebuild http connection for %s", rest_uri)
                return self._build_http_connection()
            return None
        _LOGGER.info("start %s", rest_uri)
        resp_content = None
        resp_error = None
        resp_headers = None
        for i in range(2):
            try:
                headers = self._get_headers(thetoken)
                _LOGGER.info("Send request: %s", rest_uri)
                resp_headers, content = http.request(rest_uri, method=themethod,
                                      headers=headers)
                _LOGGER.info("Response status: %i", resp_headers.status)
                if resp_headers.status not in (200, 201, 204):
                    msg = self._log_api_error(resp_headers, content, rest_uri)
                    http = rebuild_http(i)
                    resp_error = msg
                else:
                    resp_content = json.loads(content) if content else {}
                    break
            except Exception as ex:
                _LOGGER.error("Failed to connect %s, reason=%s",
                              rest_uri, traceback.format_exc())
                resp_error = ex.message
                http = rebuild_http(i)

        _LOGGER.info("end %s", rest_uri)

        return {
            "content": resp_content,
            "headers": resp_headers,
            "error": resp_error,
        }


    def _log_api_error(self, response, content, rest_uri):
        """
        Throw errors from Okta server
        """
        try:
            res = json.loads(content)
        except Exception:
            msg = "Failed to connect {0}, code={1}, reason={2}".format(rest_uri, response.status, response.reason)
            _LOGGER.error(msg)
            return msg

        msg = "Failed to connect {0}, code={1}, reason={2}".format(rest_uri, res.get("errorCode"),json.dumps(
            res.get("errorSummary")))
        _LOGGER.error(msg)
        return msg
