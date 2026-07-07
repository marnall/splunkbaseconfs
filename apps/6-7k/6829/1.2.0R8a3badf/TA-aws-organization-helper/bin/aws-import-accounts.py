#!/usr/bin/env python
# coding=utf-8
"""
import-aws-accounts.py
Pulls in AWS Organisation Accounts
"""

__author__ = "Will Searle"
__version__ = "1.0.0"
__status__ = "PRODUCTION"

import import_declare_test
from aws_helper import aws_session, get_config_secret, APP_NAME, NAMESPACE

import os, sys
import boto3
import logging

from botocore.exceptions import ClientError
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators

filehandler = logging.FileHandler(os.environ['SPLUNK_HOME'] + f"/var/log/splunk/{APP_NAME}_aws-import-accounts.log", 'a')
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

@Configuration()
class GenerateAccountList(GeneratingCommand):

    def generate(self):

        # set loglevel
        loglevel = 'INFO'
        #self.logger = logging.getLogger('aws-import-accounts')
        # If fails, don't break
        try:
            conf_file = f"{NAMESPACE}_settings"
            self.logger.warning(conf_file)
            confs = self.service.confs[str(conf_file)]
            for stanza in confs:
                if stanza.name == 'logging':
                    for stanzakey, stanzavalue in stanza.content.items():
                        if stanzakey == "loglevel":
                            loglevel = stanzavalue
            logginglevel = logging.getLevelName(loglevel)
            log.setLevel(logginglevel)

        except Exception as e:
            logging.warning("Failed to retrieve the logging level from application level configuration with exception=\"{}\"")
            log.setLevel(loglevel)
        try:
            app_settings = get_config_secret(self, "additional_parameters")
            aws_access_key = app_settings["aws_access_key"]
            aws_secret_key = app_settings["aws_secret_key"]
            root_org_role_arn = app_settings["root_org_role_arn"]
            if aws_secret_key != None and aws_access_key != None:
                self.logger.info("Creating session with aws_access_key")
                boto_session = boto3.session.Session(aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key)
            else:
                boto_session = None

            try:
                assumed_session = aws_session(self, session=boto_session, role_arn=root_org_role_arn, session_name='organisation_lambda')
            except(Exception) as e:
                self.logger.error("Could not assume session")
                self.logger.error(e)

            client = assumed_session.client('organizations')
            events = []
            ou_roots = client.list_roots()
            try:
                ou_root = ou_roots['Roots'][0]['Id']
            except:
                self.logger.warning("Could not retrieve root OU")
                exit(1)
            ou_paginator = client.get_paginator('list_organizational_units_for_parent')
            for org_unit in ou_paginator.paginate(ParentId=ou_root):
                for ou in org_unit["OrganizationalUnits"]:
                    acct_paginator = client.get_paginator('list_accounts_for_parent')
                    accounts = acct_paginator.paginate(ParentId=ou["Id"])
                    for account_page in accounts:
                        for account in account_page["Accounts"]:
                            try:
                                tags = client.list_tags_for_resource(ResourceId="{}".format(account['Id']))
                                for tag in tags['Tags']:
                                    account[tag['Key']] = tag['Value']
                            except ClientError as e:
                                self.logger.warning("Failed to get tags")
                                self.logger.warning(e)
                            yield account
        except:
            self.logger.warning("Failed...")
            yield []

dispatch(GenerateAccountList, sys.argv, sys.stdin, sys.stdout, __name__)