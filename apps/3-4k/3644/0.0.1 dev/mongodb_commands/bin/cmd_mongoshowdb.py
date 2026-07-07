#!/usr/bin/env python

import ConfigParser
import json
import os
import pprint
import pymongo
import sys
import time

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


@Configuration(streaming=True, local=True)
class MongoShowDbCommand(GeneratingCommand):
    """ List databases on MongoDB instance

    ##Syntax

    .. code-block::
        mongoshowdb

    ##Description

    List databases on MongoDB instance

    ##Example

    List all databases define in MongoDb instance configured

    .. code-block::
        | mongodbshowdb

    """


    def getConfig(self):
        '''Read mongodb configuration'''
        host = None
        port = 0
        
        conf_file = os.path.join(os.getcwd(), '..', 'default', 'mongodb.conf')
        config = ConfigParser.ConfigParser()
        config.read(conf_file)
        sections = config.sections()
        if 'mongodb' in sections:
            try:
                host = config.get('mongodb', 'host')
            except:
                pass
            try:
                port = int(config.get('mongodb', 'port'))
            except:
                pass

        conf_file = os.path.join(os.getcwd(), '..', 'local', 'mongodb.conf')
        config = ConfigParser.ConfigParser()
        config.read(conf_file)
        sections = config.sections()
        if 'mongodb' in sections:
            try:
                host = config.get('mongodb', 'host')
            except:
                pass
            try:
                port = int(config.get('mongodb', 'port'))
            except:
                pass

        return (host, port)


    def generate(self):
        '''Read databases list from MongoDb'''
        host, port = self.getConfig()
        
        objTime = time.time()

        if host != None and port >0 and port < 65536:
            client = pymongo.MongoClient(host, port)
            
            cur = client.database_names()
            
            for obj in cur:
                str = {"database": obj}
                
                event = {'_time': objTime, 'sourcetype': 'json', 'source': 'mongodb', '_raw': str}
    
                yield event

    def toStr(self, iterObj):
        '''Convert bson objects in string'''
        if type(iterObj).__name__ == 'dict':
            for k, v in iterObj.items():
                if type(v).__name__ == 'ObjectId':
                    iterObj[k] = str(v)
                elif type(v).__name__ == 'list':
                    self.toStr(v)
                elif type(v).__name__ == 'datetime':
                    iterObj[k] = unicode(v)
    

dispatch(MongoShowDbCommand, sys.argv, sys.stdin, sys.stdout, __name__)
