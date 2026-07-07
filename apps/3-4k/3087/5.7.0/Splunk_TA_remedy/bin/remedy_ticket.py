#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""

* isort ignores:
- isort: skip = Should not be sorted.
* flake8 ignores:
- noqa: F401 -> Def = module imported but unused
    Reason for ignoring = This is necessary as it contains adding a path to sys.path
"""

import splunk_ta_remedy_declare  # isort: skip # noqa: F401

import argparse
import csv
import gzip
import json
import os
import os.path as op
import re
import ssl
import sys
import time

import remedy_config as conf
import remedy_consts as c
import remedy_incident_service as ris
import solnlib.credentials as cred
import splunk.clilib.cli_common as scc
import splunk.Intersplunk as sI
import splunktaucclib.rest_handler.credentials as ucc_cred
import wsdl_crawler as wc
from logger_manager import get_logger
from solnlib import conf_manager, utils
from splunktaucclib.rest_handler.endpoint import MultipleModel

try:
    from splunk.clilib.bundle_paths import make_splunkhome_path
except ImportError:
    from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        sI.parseError("{0}. {1}".format(message, self.format_usage()))


class ICaseDictReader(csv.DictReader):
    @property
    def fieldnames(self):
        return [
            field.strip().lower() for field in super(ICaseDictReader, self).fieldnames
        ]


class RemedyTicket:
    def __init__(self):
        try:
            self._do_init()
        except Exception as e:
            self.logger.exception("Failed to init RemedyTicket, reason=")
            self._handle_error(str(e))

    def _do_init(self):
        self.logger = get_logger(self._get_log_file(), set_invocation_id=True)
        self.server_uri = scc.getMgmtUri()
        self.session_key = self._get_session_key()
        self.app_name = c.APP_NAME

        remedy_conf = conf.RemedyConfig(self.server_uri, self.session_key)
        stanzas = remedy_conf.get_stanzas()
        self.remedy_account = stanzas.get(c.REMEDY_ACCOUNT)
        self.http_scheme = self.remedy_account.get(c.HTTP_SCHEME).strip()
        self.disable_ssl_certificate_validation = utils.is_true(
            self.remedy_account.get(c.DISABLE_SSL_CERTIFICATE_VALIDATION).strip()
        )
        self.certificate_path = self.remedy_account.get(c.CERTIFICATE_PATH)
        if self.certificate_path is not None:
            self.certificate_path = self.certificate_path.strip()

        self.proxy_settings = stanzas.get(c.PROXY_STANZA)
        if c.PROXY_ENABLED not in self.proxy_settings or not utils.is_true(
            self.proxy_settings[c.PROXY_ENABLED]
        ):
            self.proxy_settings = {}

        if not self.remedy_account.get(c.URL):
            raise Exception("Remedy Web Service has not been setup.")

        self.checkpoint_dir = make_splunkhome_path(
            ["etc", "apps", "Splunk_TA_remedy", "local", "wsdl"]
        )

        if self.remedy_account is None:
            raise Exception("Failed to get stanza {}.".format(c.REMEDY_ACCOUNT))
        if not self.remedy_account[c.USER]:
            raise Exception("Remedy Account has not been setup.")

        self.remedy_ws = stanzas.get(c.REMEDY_WS)

        if self.remedy_ws is None:
            raise Exception("Failed to get stanza {}.".format(c.REMEDY_WS))
        wsdl_urls_args = (c.CREATE_WSDL_URL, c.MODIFY_WSDL_URL, c.QUERY_WSDL_URL)
        schema_url = (
            self.remedy_account.get(c.HTTP_SCHEME).strip()
            + "://"
            + self.remedy_account.get(c.URL).strip()
        )
        if any((not self.remedy_ws[k] for k in wsdl_urls_args)) or any(
            schema_url not in self.remedy_ws[k] for k in wsdl_urls_args
        ):
            self.validate_and_create_url()
            remedy_conf = conf.RemedyConfig(self.server_uri, self.session_key)
            stanzas = remedy_conf.get_stanzas()
            self.remedy_ws = stanzas.get(c.REMEDY_WS)

        wsdl_file_path_args = (
            c.CREATE_WSDL_FILE_PATH,
            c.MODIFY_WSDL_FILE_PATH,
            c.QUERY_WSDL_FILE_PATH,
        )
        need_crawl = self._is_need_crawl(wsdl_file_path_args)
        if need_crawl:
            self._crawl_wsdl(remedy_conf)
        self.create_incident_fields = stanzas.get(c.CREATE_INCIDENT)
        if self.create_incident_fields is None:
            raise Exception("Failed to get stanza {}.".format(c.CREATE_INCIDENT))
        self.update_incident_fields = stanzas.get(c.UPDATE_INCIDENT)
        if self.update_incident_fields is None:
            raise Exception("Failed to get stanza {}.".format(c.UPDATE_INCIDENT))
        self.meta_configs = {
            c.SERVER_URI: self.server_uri,
            c.SESSION_KEY: self.session_key,
            c.CHECKPOINT_DIR: self.checkpoint_dir,
        }

        self.remedy_incident_service = ris.RemedyIncidentService(
            self.remedy_account.get(c.USER),
            self.remedy_account.get(c.PASSWORD),
            self.http_scheme,
            self.disable_ssl_certificate_validation,
            self.certificate_path,
            self.proxy_settings,
        )

    def _is_need_crawl(self, wsdl_file_path_args):
        for i in wsdl_file_path_args:
            file_path = self.remedy_ws[i]
            if file_path is None:
                return True
            if not op.exists(file_path):
                return True
            wsdl_file_mtime = op.getmtime(file_path)
            splunk_home = os.environ[c.SPLUNK_HOME]
            remedy_conf_file = op.join(
                splunk_home,
                "etc",
                "apps",
                c.SPLUNK_TA_REMEDY,
                "local",
                c.REMEDY_CONF + ".conf",
            )
            remedy_conf_mtime = op.getmtime(remedy_conf_file)
            if wsdl_file_mtime < remedy_conf_mtime:
                return True
        return False

    @classmethod
    def _get_session_key(cls):
        """
        When called as custom search script, splunkd feeds the following
        to the script as a single line
        'authString:<auth><userId>admin</userId><username>admin</username>\
            <authToken>31619c06960f6deaa49c769c9c68ffb6</authToken></auth>'

        When called as an alert callback script, splunkd feeds the following
        to the script as a single line
        """
        import urllib.parse

        session_key = sys.stdin.readline()
        m = re.search("authToken>(.+)</authToken", session_key)
        if m:
            session_key = m.group(1)
        else:
            session_key = session_key.replace("sessionKey=", "").strip()
        session_key = urllib.parse.unquote(session_key)

        return session_key

    def handle(self):
        try:
            self._do_handle()
        except ssl.SSLError:
            self.logger.error(
                "SSLError occurred. If you are using self signed certificate "
                "and your certificate is at /etc/ssl/ca-bundle.crt, "
                "please refer the troubleshooting section in add-on documentation."
            )
        except Exception as e:
            self.logger.exception("Failed to handle a ticket, reason=")
            self._handle_error(str(e))

    def _do_handle(self):
        self.logger.info("Start of Remedy script")
        self._prepare()
        results = []
        for event in self._get_events():
            if event is None:
                self.logger.info("The event is None.")
                break
            result = self._handle_event(event)
            if result:
                result["_time"] = time.time()
                results.append(result)
        sI.outputResults(results)
        self.logger.info("End of Remedy script")

    def _handle_event(self, event):
        wsdl_file_path, service_name, event = self._prepare_data(event)
        if not wsdl_file_path:
            raise Exception("No WSDL File Path")
        if not service_name:
            raise Exception("No Service Name")
        if not event:
            raise Exception("No Event")
        resp = self.remedy_incident_service.execute(wsdl_file_path, service_name, event)

        self.logger.info(
            "Execute %s successfully, the response is %s.", service_name, resp
        )
        return self._get_result(resp)

    def _prepare(self):
        pass

    def _get_events(self):
        """
        Return events that need to be handled
        """
        raise NotImplementedError("Derive class shall implement this method.")

    @classmethod
    def _get_log_file(cls):
        """
        Return the log file name
        """
        return c.TICKET

    def _prepare_data(self, event):
        return event

    @classmethod
    def _handle_error(cls, msg):
        if msg:
            sI.parseError(msg)
        else:
            sI.parseError("Failed to handle ticket.")

    def _get_resp_record(self, content):
        pass

    def _get_result(self, resp):
        """
        Return a dict object
        """
        raise NotImplementedError("Derived class shall overrides this")

    def _crawl_wsdl(self, remedy_conf):
        if not op.exists(self.checkpoint_dir):
            os.makedirs(self.checkpoint_dir)
        wsdl_infos = (
            (self.remedy_ws.get(c.CREATE_WSDL_URL), c.CREATE_WSDL_FILE_PATH),
            (self.remedy_ws.get(c.MODIFY_WSDL_URL), c.MODIFY_WSDL_FILE_PATH),
            (self.remedy_ws.get(c.QUERY_WSDL_URL), c.QUERY_WSDL_FILE_PATH),
        )

        wsdl_infos_dict = {}
        remedy_ws_stanza = {}

        for wsdl_url, wsdl_file_path_arg in wsdl_infos:
            filename = wsdl_url[wsdl_url.rfind("/") + 1 :]  # noqa: E203
            file_path = op.join(self.checkpoint_dir, filename + ".xml")
            self.remedy_ws[wsdl_file_path_arg] = file_path
            remedy_ws_stanza[wsdl_file_path_arg] = file_path
            wsdl_infos_dict[wsdl_url] = file_path
            self.logger.info("Crawl WSDL file from {}.".format(wsdl_url))

        remedy_conf.update_stanza(c.REMEDY_CONF, c.REMEDY_WS, remedy_ws_stanza)
        username = self.remedy_account.get(c.USER)
        password = self.remedy_account.get(c.PASSWORD)
        wsdl_crawler = wc.WSDLCrawler(
            username,
            password,
            self.http_scheme,
            self.disable_ssl_certificate_validation,
            self.certificate_path,
            self.proxy_settings,
        )
        wsdl_crawler.crawl_files(wsdl_infos_dict)

    def validate_and_create_url(self):
        cong_mgr = conf_manager.ConfManager(
            self.session_key,
            self.app_name,
            realm="__REST_CREDENTIAL__#{}#configs/conf-splunk_ta_remedy_settings".format(
                self.app_name
            ),
        )
        remedy_conf = cong_mgr.get_conf(c.REMEDY_CONF, True)
        remedy_account = remedy_conf.get(c.REMEDY_ACCOUNT)
        remedy_ws_staza = {}

        if "://" in remedy_account.get(c.URL):
            msg = "Enter URL without protocol"
            self.logger.error(msg)
            raise Exception(msg)
        else:
            self.logger.info("Correct URL Format Entered")

        keys = (c.CREATE_WSDL_URL, c.MODIFY_WSDL_URL)
        remedy_ws_staza[c.CREATE_WSDL_URL] = (
            remedy_account.get(c.HTTP_SCHEME)
            + "://"
            + remedy_account.get(c.URL).strip(" /")
            + "/arsys/WSDL/public/"
            + remedy_account.get(c.SERVER_NAME).strip()
            + "/HPD_IncidentInterface_Create_WS"
        )
        remedy_ws_staza[c.MODIFY_WSDL_URL] = (
            remedy_account.get(c.HTTP_SCHEME)
            + "://"
            + remedy_account.get(c.URL).strip(" /")
            + "/arsys/WSDL/public/"
            + remedy_account.get(c.SERVER_NAME).strip()
            + "/HPD_IncidentInterface_WS"
        )
        remedy_ws_staza[c.QUERY_WSDL_URL] = remedy_ws_staza.get(c.MODIFY_WSDL_URL)

        username = remedy_account.get(c.USER)
        password = remedy_account.get(c.PASSWORD)

        if password:
            endpoint = MultipleModel(c.REMEDY_CONF, models=[])
            self.realm = ucc_cred.RestCredentialsContext(
                endpoint, self.app_name
            ).realm()
            cred_mgr = cred.CredentialManager(
                self.session_key, self.app_name, realm=self.realm
            )
            password = cred_mgr.get_password(c.REMEDY_ACCOUNT)
            password = json.loads(password)[c.PASSWORD]

        wsdl_crawler = wc.WSDLCrawler(
            username,
            password,
            self.http_scheme,
            self.disable_ssl_certificate_validation,
            self.certificate_path,
            self.proxy_settings,
        )

        try:
            for key in keys:
                url = remedy_ws_staza.get(key)
                wsdl_crawler.validate_wsdl_url(url)
        except Exception as e:
            self.logger.exception("%s, reason=" % str(e))
            raise Exception(e)

        remedy_ws_staza[c.CREATE_WSDL_FILE_PATH] = ""
        remedy_ws_staza[c.MODIFY_WSDL_FILE_PATH] = ""
        remedy_ws_staza[c.QUERY_WSDL_FILE_PATH] = ""

        remedy_conf.update(c.REMEDY_WS, remedy_ws_staza)
        remedy_conf.reload()


def read_alert_results(alert_file, logger):
    logger.info("Reading alert file %s", alert_file)
    if not op.exists(alert_file):
        logger.warn("Alert result file %s doesn't exist", alert_file)
        yield None

    with gzip.open(alert_file, "rb") as f:
        for event in ICaseDictReader(f, delimiter=","):
            yield event
