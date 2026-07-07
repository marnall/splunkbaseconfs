#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
import traceback
import logging
from io import BytesIO
from defusedxml import ElementTree
from solnlib.modular_input import event_writer
import requests
import ciso_ucs_utils as utils
import base64
from solnlib import log
from splunk_ta_cisco_ucs_constants import TA_NAME

_LOGGER = logging.getLogger(TA_NAME.lower())


def _parse_xml(content):
    try:
        return ElementTree.parse(BytesIO(content.encode()))
    except ElementTree.ParseError:
        return None


def _get_sys_info(parsed_xml):
    sys_info = []
    sys_node = parsed_xml.find(".//topSystem")
    if sys_node is None:
        return sys_info

    for k in ("site", "name", "address"):
        v = sys_node.get(k)
        if k == "name":
            k = "system_name"
        sys_info.append((k, v))
    return ",".join(('{}="{}"'.format(kv[0], kv[1]) for kv in sys_info))


def _parse_and_extract_xml_events(content, class_ids, sourcetype, index, host):
    sourcetype = sourcetype if sourcetype else "cisco:ucs"
    parsed_xml = _parse_xml(content)
    if parsed_xml is None:
        return ""

    sys_info = _get_sys_info(parsed_xml)
    if not sys_info:
        return ""

    ew = event_writer.ClassicEventWriter()
    event_count = {}
    for cid in class_ids:
        cnodes = parsed_xml.findall(".//" + cid)
        if not cnodes:
            continue

        events = [
            ew.create_event(
                data="{},{sys_info}".format(
                    ",".join('{}="{}"'.format(kv[0], kv[1]) for kv in node.items()),
                    sys_info=sys_info,
                ),
                host=host,
                sourcetype=sourcetype,
                source="cisco:ucs:" + cid,
                index=index,
            )
            for node in cnodes
        ]
        ew.write_events(events)
        event_count[cid] = len(events)

    return event_count


class CiscoUcs:
    def __init__(self, config):
        """
        @config: dict like object, should have class_ids, url, username,
                 password, proxy_url, proxy_port, proxy_username,
                 proxy_password, cookie, path, checkpoint_dir
        """

        self._config = config
        if not self._config.get("path"):
            self._config["path"] = "/nuova"
        self._full_url = "https://{}{}".format(
            self._config["url"], self._config["path"]
        )

    def collect_data(self):
        _LOGGER.info(
            "Start collecting data for input {} from {}.".format(
                self._config["name"], self._config["class_ids"]
            )
        )
        try:
            self._connect_to_ucs()
            req = (
                """<configResolveClasses cookie="{}" inHierarchical="false">"""
                """<inIds><Id value="topSystem"/>{}</inIds>"""
                """</configResolveClasses>"""
            )
            class_ids = self._config["class_ids"]
            cids = "".join(('<Id value="{}"/>'.format(cid) for cid in class_ids))
            req = req.format(self._config["cookie"], cids)
            err, content = self._send_request(req, True)
            if not err and content:
                params = (
                    content,
                    self._config["class_ids"],
                    self._config.get("sourcetype"),
                    self._config.get("index", "main"),
                    self._config["url"],
                )
            event_count = _parse_and_extract_xml_events(*params)
            total_event_count = sum(event_count.values())
            _LOGGER.info(
                "Events collected by input {} for each metric - {}".format(
                    self._config["name"], event_count
                )
            )
            log.events_ingested(
                _LOGGER,
                self._config.get("name", "cisco_ucs_unknown"),
                self._config.get("sourcetype"),
                total_event_count,
                self._config.get("index", "main"),
            )
        except Exception:
            raise
        finally:
            self._disconnect_from_ucs()

        _LOGGER.info(
            "End collecting data for input {} from {}.".format(
                self._config["name"], self._config["class_ids"]
            )
        )

    @staticmethod
    def _to_xml(err_content):
        if not err_content[0] and err_content[1]:
            xml = _parse_xml(err_content[1])
            if xml is None:
                log.log_exception(
                    _LOGGER,
                    Exception(err_content[1]),
                    "Failed to parse XML response {}".format(err_content[1]),
                )
                return None
            return xml
        else:
            return None

    def _send_request(self, req, log_begin_end=False):
        resp, content = self._do_request(payload=req, log_begin_end=log_begin_end)
        if resp and resp.status_code in (200, 201):
            return 0, content
        else:
            return 1, None

    def _do_request(self, method="POST", payload=None, log_begin_end=False):
        if log_begin_end:
            _LOGGER.debug("start %s %s", self._full_url, payload)

        credentials = base64.urlsafe_b64encode(
            ("%s:%s" % (self._config["username"], self._config["password"])).encode(
                "UTF-8"
            )
        ).decode("ascii")

        headers = {
            "Content-type": 'text/xml; charset="UTF-8"',
            "Content-length": "{}".format(len(payload)),
            "Authorization": "Basic %s" % credentials,
        }
        resp, content = None, None
        timeout = 180
        for retry_count in range(2):
            try:
                verify_cert = not utils.is_true(
                    self._config.get("disable_ssl_verification", False)
                )
                resp = requests.request(
                    method,
                    self._full_url,
                    headers=headers,
                    data=payload,
                    timeout=timeout,
                    verify=verify_cert,
                )
                if resp.content:
                    content = resp.content.decode()
            except Exception as e:
                if retry_count:
                    log.log_connection_error(
                        _LOGGER, e, "Failed to connect %s", self._full_url
                    )
                else:
                    timeout = 1800
                    _LOGGER.warn(
                        "Failed to connect %s, trying to reconnect...", self._full_url
                    )

            else:
                if resp.status_code not in (200, 201):
                    timeout = 1800
                    log.log_connection_error(
                        _LOGGER,
                        Exception(
                            "Failed to connect {}, reason={}, {}".format(
                                self._full_url, resp.reason, content
                            ),
                        ),
                        "Failed to connect %s",
                        self._full_url,
                    )
                else:
                    break

        if log_begin_end:
            _LOGGER.debug("end %s %s", self._full_url, payload)

        return resp, content

    def _connect_to_ucs(self):
        if self._config.get("cookie"):
            req = """<aaaRefresh inName="{}" inPassword="{}" inCookie="{}"/>""".format(
                self._config["username"],
                self._config["password"],
                self._config.get("cookie"),
            )
            content = self._to_xml(self._send_request(req))
            if content is not None:
                self._config["cookie"] = content.getroot().get("outCookie")
            else:
                self._config["cookie"] = None

        if not self._config.get("cookie"):
            req = """<aaaLogin inName="{}" inPassword="{}"/>""".format(
                self._config["username"], self._config["password"]
            )
            content = self._to_xml(self._send_request(req))
            if content is None:
                raise Exception("Failed to get cookie for %s", self._config["url"])

            cookie = content.getroot().get("outCookie")
            if cookie:
                self._config["cookie"] = cookie
            else:
                # FIXME errcode=572
                msg = "Failed to get cookie for {}, errcode={}, reason={}".format(
                    self._config["url"],
                    content.getroot().get("errorCode"),
                    content.getroot().get("errorDescr"),
                )
                log.log_exception(
                    _LOGGER,
                    Exception(msg),
                    "Failed to get cookie for {}, errcode={}".format(
                        self._config["url"], content.getroot().get("errorCode")
                    ),
                )
                raise Exception(msg)

    def _disconnect_from_ucs(self):
        cookie = self._config.get("cookie")
        if cookie:
            req = """<aaaLogout inCookie="{}"/>""".format(cookie)
            err, _ = self._send_request(req)
            if not err:
                return 0
        return 1
