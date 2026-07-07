"""sendbetterpdf - a splunk email command to send reports as PDF with more formating options """
from __future__ import print_function
import sys
import os
import json
import six.moves.urllib.request
import six.moves.urllib.error
import six.moves.urllib.parse
import csv
import gzip
import smtplib
import email

# from email.MIMEMultipart import MIMEMultipart
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# from email.MIMEBase import MIMEBase
from email.mime.base import MIMEBase

# from email import Encoders
from email.encoders import encode_base64

import socket
import string
import random
import time
from collections import defaultdict
import logging as logger

import re

# import xlwt
import copy
import datetime
from splunk.util import normalizeBoolean
import splunk
from splunk import rest
from splunk import entity
import requests

# might fix the error - see https://stackoverflow.com/questions/11536764/how-to-fix-attempted-relative-import-in-non-package-even-with-init-py
os.sys.path.append(os.path.dirname(os.path.abspath(".")))

# load own libs from ../lib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

## Create a unique identifier for this invocation
NOWTIME = time.time()
SALT = random.randint(0, 100000)
INVOCATION_ID = str(NOWTIME) + ":" + str(SALT)
INVOCATION_TYPE = "action"

######################################################
######################################################
# Helper functions from a canonical splunk script plus
# own extensions.
#


def unquote(val):
    """unquote strings."""
    if val is not None and len(val) > 1 and val.startswith('"') and val.endswith('"'):
        return val[1:-1]
    return val


def toBool(strVal):
    """string to bool."""
    if strVal is None:
        return False

    lStrVal = strVal.lower()
    if lStrVal in ('true', 't', '1', 'yes', 'y'):
        return True
    return False


def intToBool(Val):
    """int to bool."""
    if Val == 0:
        return False
    if Val == 1:
        return True


def getarg(argvals, name, defaultVal=None):
    """Get arguments and pass unquoted arguments back."""
    return unquote(argvals.get(name, defaultVal))


def request(method, url, data, headers):
    """Helper function to fetch JSON data from the given URL."""
    req = six.moves.urllib.request.Request(url, data, headers)
    req.get_method = lambda: method
    res = six.moves.urllib.request.urlopen(req)
    return json.loads(res.read())


def getCredentials(sessionKey, namespace):
    """Get credentials for api call."""
    try:
        ent = entity.getEntity(
            "admin/alert_actions",
            "email",
            namespace=namespace,
            owner="nobody",
            sessionKey=sessionKey,
        )
        if "auth_username" in ent and "clear_password" in ent:
            encrypted_password = ent["clear_password"]
            splunkhome = os.environ.get("SPLUNK_HOME")
            if splunkhome is None:
                logger.error(
                    "getCredentials - unable to retrieve credentials; SPLUNK_HOME not set"
                )
                return None
            # if splunk home has white spaces in path
            splunkhome = '"' + splunkhome + '"'
            if sys.platform == "win32":
                encr_passwd_env = (
                    '"set "ENCRYPTED_PASSWORD=' + encrypted_password + '" '
                )
                commandparams = [
                    "cmd",
                    "/C",
                    encr_passwd_env,
                    "&&",
                    os.path.join(splunkhome, "bin", "splunk"),
                    "show-decrypted",
                    "--value",
                    '"""',
                ]
            else:
                encr_passwd_env = "ENCRYPTED_PASSWORD='" + encrypted_password + "'"
                commandparams = [
                    encr_passwd_env,
                    os.path.join(splunkhome, "bin", "splunk"),
                    "show-decrypted",
                    "--value",
                    "''",
                ]
            command = " ".join(commandparams)
            stream = os.popen(command)
            clear_password = stream.read()
            # the decrypted password is appended with a '\n'
            if len(clear_password) >= 1:
                clear_password = clear_password[:-1]
            return ent["auth_username"], clear_password
    except Exception as e:
        logger.error(
            f"Could not get email credentials from splunk, using no credentials. Error: {str(e)}"
        )

    return "", ""


###############################################################################
#
# Function:   getEmailAlertActions
#
# Descrition: This function calls the Splunk REST API to get the various alert
#             email configuration settings needed to send SMTP messages in the
#             way that Splunk does
#
# Arguments:
#    argvals  - hash of various arguments passed into the search.
#    payload  - hash of various Splunk configuration settings.
#
###############################################################################


def getEmailAlertActions(argvals, payload):
    """Get the eMail alert action settings."""
    try:
        url_tmpl = (
            "%(server_uri)s/services/configs/conf-alert_actions/email?output_mode=json"
        )
        record_url = url_tmpl % dict(server_uri=payload.get("server_uri"))
        session_key = payload.get("session_key")
        headers = {
            "Authorization": f"Splunk {session_key}",
            "Content-Type": "application/json",
        }

        try:
            record = request("GET", record_url, None, headers)
        except six.moves.urllib.error.HTTPError as e:
            logger.error(
                f'invocation_id={INVOCATION_ID} invocation_type={INVOCATION_TYPE}" msg="Could not get email alert actions from splunk" error="{str(e)}"'
            )
            sys.exit(2)

        argvals["server"] = record["entry"][0]["content"]["mailserver"]
        argvals["sender"] = record["entry"][0]["content"]["from"]
        argvals["use_ssl"] = record["entry"][0]["content"]["use_ssl"]
        argvals["use_tls"] = record["entry"][0]["content"]["use_tls"]
        argvals["reportFileName"] = record["entry"][0]["content"]["reportFileName"]
    except six.moves.urllib.error.HTTPError as e:
        logger.error(
            f'invocation_id="{INVOCATION_ID}" invocation_type="{INVOCATION_TYPE}" msg="Could not get email alert actions from splunk" error="{str(e)}"'
        )
        raise


###############################################################################
#
# Function:   sendemail
#
# Descrition: This function sends a MIME encoded e-mail message using Splunk SMTP
#              Settings.
#
# Arguments:
#    recipient - maps the the field 'email_to' in the event returned by Search.
#    subject - maps to the field 'subject' in the event returned by Search.
#    body - maps the field 'message' in the event returned by Search.
#    argvals - hash of various arguments needed to configure the SMTP connection etc.
#
###############################################################################


def sendemail(
    recipient, sender, subject, bodyText, argvals, attachment, filename, authToken
):
    """Send the email."""
    print(
        "email sender: "
        + sender
        + " | recipient: "
        + recipient
        + " | subject: "
        + subject
        + " | body: "
        + bodyText,
        file=sys.stderr,
    )
    print(argvals, file=sys.stderr)
    server = getarg(argvals, "server", "localhost")
    use_ssl = intToBool(argvals["use_ssl"])
    use_tls = intToBool(argvals["use_tls"])

    username, password = getCredentials(authToken, "betterpdf")
    print("username then password", file=sys.stderr)
    print(username, file=sys.stderr)
    print(password, file=sys.stderr)
    """
    username  = getarg(argvals, "username"  , username)
    password  = getarg(argvals, "password"  , password)
    """

    # make sure the sender is a valid email address
    if sender.find("@") == -1:
        print("case -1", file=sys.stderr)
        sender = sender + "@" + socket.gethostname()

    if sender.endswith("@"):
        print("case endswith", file=sys.stderr)
        sender = sender + "localhost"

    print(sender, file=sys.stderr)
    # Create multi part mail
    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    part1 = MIMEText(bodyText, "plain", "utf-8")
    msg.attach(part1)

    try:
        part2 = MIMEBase("application", "octet-stream")
        part2.set_payload(attachment)
        encode_base64(part2)
        part2.add_header(
            "Content-Disposition", 'attachment; filename="' + filename + '.pdf"'
        )
        msg.attach(part2)
    except Exception as e:
        print("exception while attaching file occured", file=sys.stderr)
        logger.error(
            f'invocation_id={INVOCATION_ID} invocation_type="{INVOCATION_TYPE}" msg="error attaching file" rcpt="{recipient}" error="{str(e)}"'
        )
        raise

    try:
        # send the mail
        if not use_ssl:
            smtp = secure_smtplib.SecureSMTP(host=server)
        else:
            smtp = secure_smtplib.SecureSMTP_SSL(host=server, sslContext=ctx)

        if use_tls:
            print("use TLS", file=sys.stderr)
            smtp.ehlo()
            smtp.starttls()
        if len(username) > 0 and len(password) > 0:
            print("user username/password logon", file=sys.stderr)
            logger.info("user username/password logon")
            smtp.login(username, password)

        # print >> sys.stderr, msg.as_string()
        print("go go gadget - send email!", file=sys.stderr)
        logger.info("go go gadget - send email!")
        smtp.sendmail(sender, recipient.split(","), msg.as_string())
        smtp.quit()
        return

    except smtplib.SMTPRecipientsRefused as e:
        print(
            "exception while sending email occured - refused recipients",
            file=sys.stderr,
        )
        logger.error("exception while sending email occured - refused recipients")
        print(e.recipients, file=sys.stderr)
        logger.error(e.recipients)
        print(e, file=sys.stderr)
        logger.error(e)
        logger.error(
            f'invocation_id={INVOCATION_ID} invocation_type="{INVOCATION_TYPE}" msg="error attaching file" rcpt="{recipient}" error="{str(e)}"'
        )
        raise
    except (socket.error, smtplib.SMTPException) as e:
        print("exception while sending email occured", file=sys.stderr)
        logger.error("exception while sending email occured")
        print(e, file=sys.stderr)
        logger.error(e)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":

        logger.basicConfig(
            format="%(asctime)s %(levelname)s %(message)s",
            filename=os.path.join(
                os.environ["SPLUNK_HOME"], "var", "log", "splunk", "betterpdf.log"
            ),
            filemode="a+",
            level=logger.INFO,
        )

        argvals = defaultdict(list)
        recipient_list = defaultdict(list)
        event_list = defaultdict(list)
        fields = []
        header_key = {}
        default_format = "table {font-family:Arial;font-size:12px;border: 1px solid black;padding:3px}th {background-color:#4F81BD;color:#fff;border-left: solid 1px #e9e9e9} td {border:solid 1px #e9e9e9}"

        payload = json.loads(sys.stdin.read())
        print("Payload:", file=sys.stderr)
        print(payload, file=sys.stderr)
        logger.info(payload)

        getEmailAlertActions(argvals, payload)

        settings = payload.get("configuration")
        print("Settings we received:", file=sys.stderr)
        print(settings, file=sys.stderr)
        logger.debug(settings)

        print("Arguments we received:", file=sys.stderr)
        print(argvals, file=sys.stderr)
        bodyText = getarg(settings, "body", "")
        subject = getarg(settings, "subject", "")
        sender = getarg(settings, "sender", "")
        recipient = getarg(settings, "recipient", "")
        filename = getarg(settings, "filename", "")
        search_name = getarg(argvals, "search_name", "one")
        smptHost = getarg(argvals, "server", "localhost")
        reportFileName = getarg(argvals, "reportFileName", "")
        # timedateformatstring     = getarg(settings, "timedateformatstring", "dd/mm/yy")
        charttype = getarg(settings, "charttype", "")
        print("charttype we received:", file=sys.stderr)
        print(charttype, file=sys.stderr)
        logger.info("charttype")
        logger.info(charttype)
        arg_sid = getarg(settings, "sid", "")
        title = getarg(settings, "title", reportFileName)

        try:
            if arg_sid != "":
                sid = arg_sid
            else:
                sid = payload["sid"]
            logger.info(sid)
            server_uri = payload["server_uri"]
            authToken = payload["session_key"]
            uri = "/services/betterpdf?job=" + sid + charttype

            url = server_uri + uri
            logger.info(url)

            logger.info("reading ssl settings from the conf via rest")
            print("reading ssl settings from the conf via rest", file=sys.stderr)
            resp = splunk.entity.getEntity(
                ["configs"],
                "conf-server",
                sessionKey=authToken,
                namespace="-",
                owner="-",
            )
            print("one", file=sys.stderr)
            print(resp, file=sys.stderr)
            resp = splunk.entity.getEntity(
                ["configs", "conf-server"],
                "sslConfig",
                sessionKey=authToken,
                namespace="-",
                owner="-",
            )
            print("two", file=sys.stderr)
            print(resp, file=sys.stderr)
            sslconf = {}
            for k, v in resp.items():
                if str(v) == "None":
                    sslconf[str(k)] = ""
                else:
                    sslconf[str(k)] = str(v)
            logger.info("ssl settings: ")
            logger.info(str(sslconf))
            print(str(sslconf), file=sys.stderr)
            caCertFile = os.path.expandvars(sslconf["caCertFile"])
            logger.info(caCertFile)
            print(caCertFile, file=sys.stderr)

            if sslconf["sslVerifyServerName"] == 1:
                verify = caCertFile
            else:
                verify = False

            print(url, file=sys.stderr)

            # """
            r = requests.get(
                url, verify=verify, headers={"Authorization": f"Splunk {authToken}"}
            )
            print(str(r.status_code))
            logger.info(str(r.status_code))
            filecontent = r.content
            #filename = title

        except Exception as e:
            import traceback

            stack = traceback.format_exc()
            print(f"exception: {stack}", file=sys.stderr)
            logger.error(f"exception: {stack}")
            sys.exit(1)

        try:
            # sendemail(recipient, sender, subject, bodyText, argvals, filename)
            print("try to send")
            print(
                "email sender: "
                + sender
                + " | recipient: "
                + recipient
                + " | subject: "
                + subject
                + " | body: "
                + bodyText,
                file=sys.stderr,
            )
            sendemail(
                recipient,
                sender,
                subject,
                bodyText,
                argvals,
                filecontent,
                filename,
                authToken,
            )

        except Exception as e:
            import traceback

            stack = traceback.format_exc()
            print("exception: " + stack, file=sys.stderr)
            logger.error(
                f'invocation_id={INVOCATION_ID} invocation_type="{INVOCATION_TYPE}" msg="some error occured - stack trace follows" {stack}'
            )
            exit()

    else:
        logger.error(
            f'invocation_id="{INVOCATION_ID}" invocation_type="{INVOCATION_TYPE}" msg="Unsupported execution mode (expected --execute flag)"'
        )
        sys.exit(1)
