# Alert action - Send Email
#
import base64
import hashlib
import re
import smtplib
import urllib.parse
from email.mime.base import MIMEBase

from splunk.Intersplunk import decodeMV
import sys
import os
import logging
import csv
import gzip
import json
from email.mime.multipart import MIMEMultipart
from os.path import basename
import io

from Utilities import KennyLoggins
from google_constants import app_name as _package_id
from google_alert_action import GWAlertAction
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from email.utils import formatdate
from email.mime.text import MIMEText

_alert_name = "googleworkspace-alert-action-gmail-send"
# This needs added to apl_logging.conf and README/apl_logging.conf.spec using splapp
sys.path.insert(0, make_splunkhome_path(["etc", "apps", _package_id, "lib"]))
from jinja2 import Environment, BaseLoader

kl = KennyLoggins()
logger = kl.get_logger(app_name=_package_id, file_name=_alert_name, log_level=logging.DEBUG)


class GWAlert(GWAlertAction):
    def __init__(self, settings, action_name):
        try:
            GWAlertAction.__init__(self, settings=settings, action_name=_alert_name,
                                   filename=_alert_name,
                                   stanza="global_{}_configuration".format(_alert_name))
            self.client = None
            self.path = None
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error_msg = "error_message=\"{}\" " \
                        "error_type=\"{}\" " \
                        "error_arguments=\"{}\" " \
                        "error_filename=\"{}\" " \
                        "error_line_number=\"{}\" " \
                        "alert_name=\"{}\" " \
                .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno, _alert_name)
            logger.fatal(error_msg)

    def _get_file_handler(self, form='rb'):
        return gzip.open(self.payload.get("results_file"), form)

    def _setup_service(self):
        self.service = self.build('gmail', 'v1', credentials=self.credential)

    def _convert_mv(self, data):
        fields = data.get("event_fields", [])
        for field in fields:
            self._log.debug(f"field={field}")
            if f'__mv_{field}' in fields:
                self._log.debug(f"action=has_mv_field field={field}")
                if "evts" in data:
                    self._log.debug(f"action=multiple_events")
                    for idx, evt in enumerate(data["evts"]):
                        self._log.debug(f"idx={idx} evt={evt}")
                        if len(evt[f'__mv_{field}']) > 0:
                            self._log.debug(f'action=decoding idx={idx} __mv_{field}="{evt[f"__mv_{field}"]}" data="{data["evts"][idx][field]}"')
                            t = []
                            decodeMV(evt[f'__mv_{field}'], t)
                            data['evts'][idx][field] = t
                else:
                    if len(data['evt'][f'__mv_{field}']) > 0:
                        self._log.debug(
                            f'action=decoding  __mv_{field}="{data["evt"][f"__mv_{field}"]}"  data="{data["evt"][field]}"')
                        t = []
                        decodeMV(data['evt'][f'__mv_{field}'], t)
                        data['evt'][field] = t
        return data

    def main(self):
        try:
            self._log.debug(f"action=start alert_name={_alert_name}")
            # self._log.debug(f"config={self._settings}")
            single_email = self._settings.get("configuration", {}).get("one_email", False)
            use_google = True if self._settings.get("configuration", {}).get("use_google", "1") == "1" else False
            self._log.debug(f"use_google={use_google}")
            self._configuration["credential"] = self._settings.get("configuration", {}).get("credential", None)
            if use_google:
                self.setup_gw("gmail")
                self._setup_service()
            else:
                tmp_settings = f'{urllib.parse.unquote(self.utils.get_credential(self._app_name, self.get_config("credential", None)))}'.split("@@")
                self._config["smtp_settings"] = tmp_settings[1]
            aa_results_file = self.payload.get("results_file")
            with gzip.open(aa_results_file, "rt") as gf:
                matrix = [n for r, n in enumerate(csv.DictReader(gf))]
            self._log.debug(f"action=loaded_results len_results={len(matrix)}")
            field_values = {}
            for m in matrix:
                for k, v in m.items():
                    if k not in field_values:
                        field_values[k] = []
                    field_values[k].append(v)
            event_fields = list(field_values.keys())
            self._log.debug(f"action=loaded_field_values field_keys={json.dumps(list(field_values.keys()))}")
            search_name = self._settings.get("search_name", "adhoc")
            self._log.debug(
                f'action=alert_action_settings search_name="{search_name}" single_email="{single_email}"')

            # Single Email Logic here, need a diagram I think.
            # If single email, then just send boilerplate message body with attached results.
            is_single_email = True if single_email == "1" else False
            template_data = {
                    "savedsearch": search_name,
                    "results_file": basename(aa_results_file),
                    "event_fields": event_fields,
                    "single_email": is_single_email,
                }
            if is_single_email == "1" or is_single_email:
                template_data["evts"] = matrix
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=event_fields)
                writer.writeheader()
                [writer.writerow(evt) for evt in matrix]
                attachments = [{"data": output.getvalue(), "file": aa_results_file, "attachment_name": "results.csv", "mimetype": "text/csv"}]
                self._send_email(use_google, template_data, attachments)
            else:
                for evt in matrix:
                    template_data["evts"] = [evt]
                    output = io.StringIO()
                    writer = csv.DictWriter(output, fieldnames=event_fields)
                    writer.writeheader()
                    writer.writerow(evt)
                    attachments = [{"data": output.getvalue(), "file": aa_results_file, "attachment_name": "results.csv", "mimetype": "text/csv"}]
                    self._send_email(use_google, template_data, attachments)
        except Exception as me:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error_msg = " " \
                        "error_message=\"{}\" " \
                        "error_type=\"{}\" " \
                        "error_arguments=\"{}\" " \
                        "error_filename=\"{}\" " \
                        "error_line_number=\"{}\" " \
                        "alert_name=\"{}\" " \
                .format(str(me), type(me), "{}".format(me), fname, exc_tb.tb_lineno, self._action_name)
            self._log.error(error_msg)

    def _send_email(self, use_google, template_data=None, attachments=None):
        try:
            if attachments is None:
                attachments = []
            if template_data is None:
                template_data = {}
            template_data = self._convert_mv(template_data)
            self._log.debug(f"template_data={json.dumps(template_data)}")
            is_single_email = template_data.get("single_email", True)
            event_fields = template_data.get("event_fields", [])
            if not is_single_email:
                evt = template_data.get("evts")[0]
            else:
                evt = {}
            COMMASPACE = ", "
            body_template = self._settings.get("configuration", {}).get("body_template", "")
            if not is_single_email and "body_template" in event_fields:
                body_template = evt.get("body_template", "No Body Template")
            if len(body_template) == 0:
                body_template= "[{{ savedsearch }}] has sent you a results. Please see attachments."
            env = Environment(loader=BaseLoader).from_string(body_template)
            body = env.render(template_data)
            self._log.debug(f'action=alert_action_settings body_template="{body_template}" len_body_template={len(body_template)} rendered_body="{body}"')
            ## TO:
            recipients = self._settings.get("configuration", {}).get("recipients", "")
            if not is_single_email and "recipients" in event_fields:
                recipients = evt.get("recipients", "")
            ## CC:
            cc = self._settings.get("configuration", {}).get("cc", "")
            if not is_single_email and "cc" in event_fields:
                cc = evt.get("cc", "")
            ## BCC:
            bcc = self._settings.get("configuration", {}).get("bcc", "")
            if not is_single_email and "bcc" in event_fields:
                bcc = evt.get("bcc", "")
            ## Subject:
            subject = self._settings.get("configuration", {}).get("subject", "Unknown Subject")
            if not is_single_email and "subject" in event_fields:
                subject = evt.get("subject", "No Subject")
            env_subject = Environment(loader=BaseLoader).from_string(subject)
            subject = env_subject.render(template_data)
            self._log.debug(f'action=setting_subject is_single_email={is_single_email} subject="{subject}"')
            ## From:
            sender = self._settings.get("configuration", {}).get("sender", "")
            if use_google:
                sender = self._config.get("impersonation_user", None)
                if sender is None:
                    raise ValueError(f'action="impersonation_user_not_defined" alert_name="{_alert_name}"')
            if not use_google and not is_single_email and "sender" in event_fields:
                sender = evt.get("sender", "")
            if len(sender) == 0:
                    raise ValueError(f'action="from_email_not_defined" alert_name="{_alert_name}" ')
            ### BUILD THE MESSAGE
            message = MIMEMultipart("alternative")
            # Required Items
            message["Subject"] = subject
            message["From"] = sender
            message['Date'] = formatdate(localtime=True)
            message["To"] = COMMASPACE.join([t.strip() for t in recipients.split(",")])
            message.attach(MIMEText(body, 'plain'))
            message.attach(MIMEText(body, 'html'))
            # Optional, if provided.
            if len(cc) > 0:
                message["Cc"] = COMMASPACE.join([t.strip() for t in cc.split(",")])
            if len(bcc) > 0:
                message["Bcc"] = COMMASPACE.join([t.strip() for t in bcc.split(",")])
            for attachment in attachments:
                content = attachment.get("data", "")
                attachment_file_name = attachment.get("attachment_name", "")
                mimes = attachment.get("mimetype", "text/csv").split("/")
                part = MIMEBase(mimes[0], mimes[1])
                part.set_payload(content)
                # encoders.encode_base64(part)
                part.add_header("Content-Disposition", "attachment", filename=attachment_file_name)
                self._log.debug(f'action="add_attachments" data="{type(content)}" attachment_filename="{attachment_file_name}" part="{part}"')
                message.attach(part)
            if use_google:
                encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
                create_message = {"raw": encoded_message}
                send_message = self.service.users().messages().send(userId="me", body=create_message).execute()
                self._log.debug(f"action=send_message server=google_smtp_api message_id={send_message.get('id')}")
            else:
                smtp_settings = self._config.get("smtp_settings", None)
                if smtp_settings is None:
                    raise ValueError(f'action="smtp_settings_not_defined" alert_name="{_alert_name}" configuration="{self._config}')
                username = password = server = port = protocol = None
                found_m = ""
                for m in re.finditer('(?P<protocol>smtp[sv]?)://(?:(?P<username>[^:]+):(?P<password>\w+)@)?(?P<server>[^:]+):(?P<port>\d+)', smtp_settings):
                    username = m.group('username')
                    password = m.group('password')
                    server = m.group('server')
                    port = m.group('port')
                    protocol = m.group('protocol')
                    found_m = m
                    self.service = smtplib.SMTP if protocol == 'smtp' else smtplib.SMTP_SSL
                self._log.debug(f"action=smtp_settings username={username} server={server} port={port} protocol={protocol}")
                if server is None:
                    sha_hash = hashlib.sha512()
                    sha_hash.update(password)
                    sha_hash_sk = hashlib.sha512()
                    sha_hash_sk.update(self.session_key)
                    messages = {"username": username, "sha512_password": sha_hash.hexdigest(), "server": server, "port": port, "protocol": protocol,
                                "smtp_settings": smtp_settings, "configuration": self._config, "alert_name": _alert_name,
                                "regex_findings": found_m, "has_sensitive_value": True
                                }
                    self._log.fatal(" ".join([f'{k}="{v}"' for k, v in messages.items()]).replace(self.session_key, sha_hash_sk.hexdigest()))
                    raise ValueError(f'action="smtp_settings_not_defined" alert_name="{_alert_name}"')
                with self.service(server, port) as smtp:
                    if username is not None and password is not None:
                        smtp.login(username, password)
                    try:
                        smtp.send_message(message)
                    except Exception as me:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                        error_msg = f'"error_message="{str(me)}" error_type="{type(me)}" ' \
                                    f'error_arguments="{me}" ' \
                                    f'error_filename="{fname}"'  \
                                    f'"error_line_number="{exc_tb.tb_lineno}" "' \
                                    f'"alert_name="{self._action_name}" "' \
                                    f'username={username} server={server} port={port} protocol={protocol}'
                        self._log.error(error_msg)
                        raise me
                self._log.debug(f'action="smtp_settings" smtp_settings={smtp_settings}')
        except Exception as me:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error_msg = " " \
                        "error_message=\"{}\" " \
                        "error_type=\"{}\" " \
                        "error_arguments=\"{}\" " \
                        "error_filename=\"{}\" " \
                        "error_line_number=\"{}\" " \
                        "alert_name=\"{}\" " \
                .format(str(me), type(me), "{}".format(me), fname, exc_tb.tb_lineno, self._action_name)
            self._log.error(error_msg)

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        logger.fatal("FATAL Unsupported execution mode (expected --execute flag)")
        sys.exit(1)
    try:
        logger.info("instantiating {}".format(_alert_name))
        modaction = GWAlert(sys.stdin.read(), action_name=_alert_name)
        modaction.main()
        sc, evttype = modaction.get_evt_idx("google_workspace")
        logger.info("action=found_eventtype class=alert_action_index alert_action_index=\"{}\"".format(evttype))
        modaction.writeevents(index=evttype,
                              fext='googleworkspace_alert_action_st',
                              sourcetype="google:workspace:alert_action:{}".format(_alert_name),
                              source="google:workspace:alert_action:{}:{}".format(_alert_name,
                                                                                  modaction.payload[
                                                                                      "search_name"].replace(" ",
                                                                                                             "_")))
    except Exception as e:
        try:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error_msg = " " \
                        "error_message=\"{}\" " \
                        "error_type=\"{}\" " \
                        "error_arguments=\"{}\" " \
                        "error_filename=\"{}\" " \
                        "error_line_number=\"{}\" " \
                        "alert_name=\"{}\" " \
                .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno, _alert_name)
            logger.error(error_msg)
        except Exception as e:
            logger.critical(e)
        sys.exit(3)
