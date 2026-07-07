#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import http.client
import json
import logging
import threading
import traceback
from urllib import response

from citrix_netscaler_utility import make_request


_LOGGER = logging.getLogger("ta_citrix_netscaler")


def _convert_to_modinput_format(
    content, resource_name, api_endpoint, url, index, host, input_name
):
    """
    response format:
        {
        "errorcode": 0, "message": "Done", api_endpoint:[{}, {}]
        }
    """
    try:
        jobj = json.loads(content)
    except Exception:
        return ""

    if jobj.get("errorcode", 0) != 0:
        return ""

    api_split = api_endpoint.split("/")
    api_type = api_split[0]
    api_name = api_split[1]

    if not jobj.get(api_name):
        return ""

    evt_fmt = (
        '<event stanza="{0}"><source>{1}</source><sourcetype>{2}</sourcetype>'
        "<host>{3}</host><index>{4}</index>"
        "<data><![CDATA[ {5} ]]></data></event>"
    )

    records = []
    rec = jobj[api_name]
    if isinstance(rec, dict):
        rec["nitro_api_endpoint"] = api_endpoint
        records.append('{}="{}"'.format(k, v) for k, v in sorted(rec.items()))
    elif isinstance(rec, list):
        for r in rec:
            assert isinstance(r, dict)
            r["nitro_api_endpoint"] = api_endpoint
            records.append('{}="{}"'.format(k, v) for k, v in sorted(r.items()))

    host = url
    sourcetype = "citrix:netscaler:nitro"
    source = "{}:{}".format(api_type, api_name)

    results = (
        evt_fmt.format(input_name, source, sourcetype, host, index, rec)
        for rec in (",".join(r) for r in records)
    )
    return "".join(results)


class CitrixNetscaler:
    def __init__(self, config):
        """
        @config: dict like object, should have url, username,
                 password, proxy_url, proxy_port, proxy_username,
                 proxy_password, checkpoint_dir, api_version,
                 api_endpoint, resource_name
        """

        self._config = config

        assert "api_endpoint" in config and config["api_endpoint"]

        self._full_url = self._get_full_url(config)
        content_type = "application/vnd.com.citrix.netscaler.{}+json".format(
            config["api_endpoint"]
        )

        self._headers = {
            "Content-Type": content_type,
            "X-NITRO-USER": config["username"],
            "X-NITRO-PASS": config["password"],
        }
        self._lock = threading.Lock()

        from ta_util2 import data_loader as dl

        self._loader = dl.GlobalDataLoader.get_data_loader(None, None, None)

    def _get_full_url(self, config):
        """
        1) URL to get statistics of a feature must have the format:
           http://<NSIP>/nitro/v1/stat/<feature_name>.
        2) URL to get the statistics of a resource must have the format:
           http://<NSIP>/nitro/v1/stat/<resource_type>/<resource_name>
        3) URL to get the configuration of a feature must have the format:
           http://<NSIP>/nitro/v1/config/<feature_name>
        """

        # FIXME pagination ?
        api_version = config.get("api_version", "v1")
        url = config["url"].rstrip("/")

        # Append http_scheme to host provided
        http_scheme = config.get("http_scheme").strip().lower()
        _LOGGER.debug("Found %s value for http_scheme parameter", http_scheme)
        url = "{}://{}".format(http_scheme, url)

        if config.get("resource_name"):
            # for specific resource
            full_url = "{}/nitro/{}/{}/{}".format(
                url, api_version, config["api_endpoint"], config["resource_name"]
            )
        else:
            full_url = "{}/nitro/{}/{}".format(url, api_version, config["api_endpoint"])
        return full_url

    def collect_data(self):
        if self._lock.locked():
            _LOGGER.info("Last request for %s has not been done yet", self._full_url)
            return None

        with self._lock:
            res = self._do_collect()
        return res

    def _do_collect(self):
        """
        @return: objs
        """

        results = []
        response = self._do_request()
        content = response.content
        if content is not None:
            params = (
                content,
                self._config.get("resource_name"),
                self._config["api_endpoint"],
                self._config["url"],
                self._config.get("index", "main"),
                self._config["host"],
                self._config["name"],
            )
            content = self._loader.run_computing_job(
                _convert_to_modinput_format, params
            )
            results.append(content)
        return results

    def _do_request(self):
        _LOGGER.debug("start %s", self._full_url)

        response = None
        for _ in range(2):
            try:
                response = make_request(
                    self._full_url, "GET", self._config, _LOGGER, headers=self._headers
                )
            except Exception:
                _LOGGER.error(
                    "Failed to connect %s, reason=%s",
                    self._full_url,
                    traceback.format_exc(),
                )
            else:
                if response.status_code not in (200, 201):
                    _LOGGER.error(
                        "Failed to connect %s, reason=%s, %s",
                        self._full_url,
                        response.reason,
                        response.content,
                    )
                else:
                    break

        _LOGGER.debug("Closing request to %s", self._full_url)

        return response
