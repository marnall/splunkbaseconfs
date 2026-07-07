#!/usr/bin/env python
# coding=utf-8
"""
import-aws-accounts.py
Pulls in AWS Organisation Accounts
"""

__author__ = "Will Searle"
__version__ = "1.0.0"
__status__ = "PRODUCTION"

import os, sys
import boto3
import logging
import json

from splunktalib.common import util as scu
from splunktalib.credentials import CredentialManager as CredMgr
from splunklib.six.moves.urllib.parse import urlsplit

APP_NAME = scu.get_appname_from_path(__file__)
NAMESPACE = "ta_aws_organization_helper"

filehandler = logging.FileHandler(os.environ['SPLUNK_HOME'] + f"/var/log/splunk/{APP_NAME}_aws-helper.log", 'a')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(filename)s %(funcName)s %(lineno)d %(message)s')
filehandler.setFormatter(formatter)
log = logging.getLogger()  # root logger - Good to get it only once.
for hdlr in log.handlers[:]:  # remove the existing file handlers
    if isinstance(hdlr,logging.FileHandler):
        log.removeHandler(hdlr)
log.addHandler(filehandler)      # set the new handler
# set the log level to INFO, DEBUG as the default is ERROR
log.setLevel(logging.INFO)

sys.path.append(os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', APP_NAME, 'lib'))

def get_config_secret(self, secretName):
    try:
        searchinfo = self._metadata.searchinfo
    except AttributeError:
        return None

    splunkd_uri = searchinfo.splunkd_uri

    if splunkd_uri is None:
        return None

    self.uri = urlsplit(splunkd_uri, allow_fragments=False)

    cred_mgr = CredMgr(
        f"{self.uri.scheme}://{self.uri.hostname}:{self.uri.port}",
        searchinfo.session_key,
        app=APP_NAME,
        #owner=self._user,
        realm=f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-{NAMESPACE}_settings"
    )
    #TODO: try block here
    cred = cred_mgr.get_clear_password(secretName)[secretName]
    secret_obj = json.loads(list(cred.keys())[0])

    return secret_obj

def aws_session(self, session=None, role_arn=None, session_name='lookup_session'):
    """
    If role_arn is given assumes a role and returns boto3 session
    otherwise return a regular session with the current IAM user/role
    """
    if role_arn:
        if session == None:
            client = boto3.client('sts')
        else:
            client = session.client('sts')
        response = client.assume_role(RoleArn=role_arn, RoleSessionName=session_name)
        creds = response.get("Credentials", None)

        if creds is not None:
            session = boto3.Session(
                aws_access_key_id=creds['AccessKeyId'],
                aws_secret_access_key=creds['SecretAccessKey'],
                aws_session_token=creds['SessionToken'])
        return session
    else:
        return boto3.Session()
