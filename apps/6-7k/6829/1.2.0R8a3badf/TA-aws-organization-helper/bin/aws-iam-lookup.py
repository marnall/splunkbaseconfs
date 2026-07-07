#!/usr/bin/env python
# coding=utf-8
"""
aws-iam-lookup.py
Pulls in tags from iam users on AWS
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from distutils.ccompiler import new_compiler
import import_declare_test
__author__ = "Will Searle"
__version__ = "1.0.0"
__status__ = "PRODUCTION"

import import_declare_test
from aws_helper import aws_session, get_config_secret, APP_NAME, NAMESPACE
import logging
import os, sys

from splunktalib.credentials import CredentialManager as CredMgr
from splunklib.six.moves.urllib.parse import urlsplit

from botocore.exceptions import ClientError

import boto3
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

import json


filehandler = logging.FileHandler(os.environ['SPLUNK_HOME'] + f"/var/log/splunk/{APP_NAME}_aws-iam-lookup.log", 'a')
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
class StreamIAMLookup(StreamingCommand):

    def stream(self, records):

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
            self.logger.setLevel(logginglevel)

        except Exception as e:
            self.logger.warning("Failed to retrieve the logging level from application level configuration with exception=\"{}\"")
            logging.setLevel(loglevel)
        try:
            app_settings = get_config_secret(self, "additional_parameters")
            aws_access_key = app_settings["aws_access_key"]
            aws_secret_key = app_settings["aws_secret_key"]
            iam_role_arn = app_settings["iam_role_arn"]
            if aws_secret_key != None and aws_access_key != None:
                self.logger.debug("Creating session with aws_access_key")
                boto_session = boto3.session.Session(aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key)
            else:
                self.logger.debug("Creating session without aws_access_key")
                boto_session = None

            try:
                assumed_session = aws_session(self, session=boto_session, role_arn=iam_role_arn, session_name='organisation_lambda')

            except(Exception) as e:
                self.logger.error("Could not assume session")
                self.logger.error(e)
            client = assumed_session.client('iam')
            for record in records:
                if 'username' in record:
                    self.logger.info("Lookup sponsor for username={}".format(record['username']))
                    try:
                        tags = client.list_user_tags(UserName=record['username'])
                        self.logger.info(tags['Tags'])
                        for tag in tags['Tags']:
                            record[tag['Key']] = tag['Value']
                    except Exception as e:
                        self.logger.warning("Tags not found for username={}".format(record['username']))
                yield record
        except:
            self.logger.warning("Failed...")
            yield []

dispatch(StreamIAMLookup, sys.argv, sys.stdin, sys.stdout, __name__)
