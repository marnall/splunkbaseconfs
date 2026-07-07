#!/usr/bin/env python

import sys
import re
from collections import OrderedDict
from datetime import datetime

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators

@Configuration(type='reporting')
class GenerateCbQuery(GeneratingCommand):

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
    fields = Option(
        doc='''**Syntax:** **fields=***<fields>*
        **Description:** comma-seperated list of fields, enclose in quotes''',
        ) 	

    def generate(self):

        product = self.product
        if product == 'protection' or product == 'Protection':
            from cbapi.protection.models import ApprovalRequest, BaseModel, Certificate, Computer, Connector, CreatableModelMixin, DriftReport, DriftReportContents, EnforcementLevel, Event, FileAnalysis, FileCatalog, FileInstance, FileInstanceDeleted, FileInstanceGroup, FileRule, FileUpload, GrantedUserPolicyPermission, InternalEvent, LooseVersion, MeteredExecution, MutableBaseModel, MutableModel, NewBaseModel, Notification, Notifier, PendingAnalysis, Policy, Publisher, PublisherCertificate, ScriptRule, ServerConfig, ServerPerformance, StringIO, TrustedDirectory, TrustedUser, Updater, User, UserGroup, ZipFile
            from cbapi.protection.rest_api import CbEnterpriseProtectionAPI
            p=CbEnterpriseProtectionAPI()
        elif product == 'response' or product == 'Response':
            from cbapi.response.models import ActionTypes, Alert, AlertQuery, ApiError, ArrayQuery, BannedHash, BaseModel, Binary, CbChildProcEvent, CbCrossProcEvent, CbEvent, CbFileModEvent, CbModLoadEvent, CbNetConnEvent, CbRegModEvent, CreatableModelMixin, Feed, FeedAction, IngressFilter, InvalidHashError, InvalidObjectError, Investigation, LooseVersion, MutableBaseModel, NewBaseModel, ObjectNotFoundError, PaginatedQuery, Process, ProcessQuery, ProcessV1Parser, ProcessV2Parser, ProcessV3Parser, ProcessV4Parser, Query, Sensor, SensorGroup, SensorPaginatedQuery, SensorQuery, ServerError, SimpleQuery, Site, StoragePartition, StoragePartitionQuery, StringIO, TaggedEvent, TaggedModel, Team, ThreatReport, ThreatReportQuery, ThrottleRule, TimeoutError, User, Watchlist, WatchlistAction, WatchlistEnabledQuery, ZipFile
            from cbapi.response import CbEnterpriseResponseAPI
            p=CbEnterpriseResponseAPI()
        elif product == 'defense' or product == 'Defense':
            from cbapi.psc.defense.models import CreatableModelMixin, DefenseMutableModel, Device, Event, MutableBaseModel, NewBaseModel, Policy, ServerError
            from cbapi.defense import CbDefenseAPI
            p=CbDefenseAPI()
        query_object = self.model
        query = self.query
        if self.fields:
            headers = self.fields.split(',')
        else:
            headers = False
        
        command = 'p.select('+query_object+').'+query
        q = eval(command)
        
        if not headers:
            headers = []
        for obj in q:
            if len(headers) == 0:
                if 'original_document' in dir(obj):
                    headers = list(obj.original_document.keys())
                else:
                    for attr in dir(obj):
                        if not attr.startswith('_'):
                            headers.append(attr)
            row = {}
            for h in headers:
                row[h] = getattr(obj, h)
                if isinstance(row[h], datetime):
                    row[h] = row[h].strftime('%Y-%m-%d %H:%M:%S')
            sorted_row = OrderedDict(sorted(list(row.items()), key=lambda x: x[0]))
            yield sorted_row
        

dispatch(GenerateCbQuery, sys.argv, sys.stdin, sys.stdout, __name__)
