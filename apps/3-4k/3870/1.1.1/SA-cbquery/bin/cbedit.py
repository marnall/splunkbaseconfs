#!/usr/bin/env python

import sys
import os
import re
import logging, logging.handlers

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators, environment
from splunk import setupSplunkLogger

@Configuration(type='reporting')
class GenerateCbEdit(GeneratingCommand):

    product = Option(
        require=True,
        doc='''**Syntax:** **product=***<string>*
        **Description:** Options are defense, protection or response''',
        ) 	
    model = Option(
        require=True,
        doc='''**Syntax:** **model=***<string>*
        **Description:** Such as Computer''',
        ) 	
    query = Option(
        require=True,
        doc='''**Syntax:** **model=***<string>*
        **Description:** Such as "where('deleted:False')"''',
        ) 	
    target = Option(
        require=True,
        doc='''**Syntax:** **target=***<field>*
        **Description:** field name to change value, enclose in quotes, note that not all fields support update and user requires permissions''',
        ) 	
    value = Option(
        require=True,
        doc='''**Syntax:** **value=***string*
        **Description:** value to change to, enclose in quotes, note that not all fields support update and user requires permissions''',
        ) 	
    ticket = Option(
        require=False,
        doc='''**Syntax:** **ticket=***string*
        **Description:** ticket number to get logged in the audit''',
        ) 	

    #http://dev.splunk.com/view/logging/SP-CAAAFCN
    def setup_logging(self):
        logger = logging.getLogger('splunk.foo')
        SPLUNK_HOME = os.environ['SPLUNK_HOME']

        LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
        LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
        LOGGING_STANZA_NAME = 'python'
        LOGGING_FILE_NAME = "cbedit.log"
        BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
        LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s - %(message)s"
        splunk_log_handler = logging.handlers.RotatingFileHandler(
            os.path.join(
                SPLUNK_HOME,
                BASE_LOG_PATH,
                LOGGING_FILE_NAME
            ), mode='a')
        splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
        logger.addHandler(splunk_log_handler)
        setupSplunkLogger(
            logger,
            LOGGING_DEFAULT_CONFIG_FILE,
            LOGGING_LOCAL_CONFIG_FILE,
            LOGGING_STANZA_NAME
        )
        return logger

    def generate(self):

        logger = self.setup_logging()
        product = self.product
        if product == 'protection' or product == 'Protection':
            from cbapi.protection.models import ApprovalRequest, BaseModel, Certificate, Computer, Connector, CreatableModelMixin, DriftReport, DriftReportContents, EnforcementLevel, Event, FileAnalysis, FileCatalog, FileInstance, FileInstanceDeleted, FileInstanceGroup, FileRule, FileUpload, GrantedUserPolicyPermission, InternalEvent, LooseVersion, MeteredExecution, MutableBaseModel, MutableModel, NewBaseModel, Notification, Notifier, PendingAnalysis, Policy, Publisher, PublisherCertificate, ScriptRule, ServerConfig, ServerPerformance, StringIO, TrustedDirectory, TrustedUser, Updater, User, UserGroup, ZipFile
            from cbapi.protection.rest_api import CbEnterpriseProtectionAPI
            p=CbEnterpriseProtectionAPI()
        elif product == 'response' or product == 'Response':
            from cbapi.response.models import ActionTypes, Alert, AlertQuery, ApiError, ArrayQuery, BannedHash, BaseModel, Binary, CbChildProcEvent, CbCrossProcEvent, CbEvent, CbFileModEvent, CbModLoadEvent, CbNetConnEvent, CbRegModEvent, CreatableModelMixin, Feed, FeedAction, IngressFilter, InvalidHashError, InvalidObjectError, Investigation, LooseVersion, MutableBaseModel, NewBaseModel, ObjectNotFoundError, PaginatedQuery, Process, ProcessQuery, ProcessV1Parser, ProcessV2Parser, ProcessV3Parser, ProcessV4Parser, Query, Sensor, SensorGroup, SensorPaginatedQuery, SensorQuery, ServerError, SimpleQuery, Site, StoragePartition, StoragePartitionQuery, StringIO, TaggedEvent, TaggedModel, Team, ThreatReport, ThreatReportQuery, ThrottleRule, TimeoutError, User, Watchlist, WatchlistAction, WatchlistEnabledQuery, ZipFile
            from cbapi.response import CbResponseAPI
            p=CbResponseAPI()
        elif product == 'defense' or product == 'Defense':
            from cbapi.psc.defense.models import CreatableModelMixin, DefenseMutableModel, Device, Event, MutableBaseModel, NewBaseModel, Policy, ServerError
            from cbapi.defense import CbDefenseAPI
            p=CbDefenseAPI()
        query_object = self.model
        query = self.query
        target = self.target
        value = self.value
        ticket = self.ticket
        
        command = 'p.select('+query_object+').'+query
        e = eval(command)

        #collect logged in user's name
        owner = self._metadata.searchinfo.username
        
        for i in e:
            row = {}
            row['name'] = i.name
            row[target+'_prev_value'] = getattr(i, target)
            setattr(i, target, value)
            i.save()
            row[target+'_new_value'] = getattr(i, target)
            audit_dict = {}
            audit_dict['user'] = owner
            audit_dict['target_changed'] = target
            audit_dict['src_host'] = str(i.name)
            audit_dict['prev_value'] = str(row[target+'_prev_value'])
            audit_dict['new_value'] = str(row[target+'_new_value'])
            log_message = 'user=' + owner + ' target_changed=' + target + ' src_host=' + str(i.name) + ' prev_value=' + str(row[target+'_prev_value']) +' new_value='+ str(row[target+'_new_value'])
            if ticket:
                audit_dict['ticket'] = ticket
                log_message += ' ticket=' + ticket
            row['audit'] = audit_dict
            logger.info(log_message)

            yield row
        

dispatch(GenerateCbEdit, sys.argv, sys.stdin, sys.stdout, __name__)
