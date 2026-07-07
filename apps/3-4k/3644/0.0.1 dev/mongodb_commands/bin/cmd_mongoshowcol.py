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
class MongoShowColCommand(GeneratingCommand):
    """ List collections in database specified

    ##Syntax

    .. code-block::
        mongohowcol db=<database>

    ##Description

    List collections in database specified

    ##Example

    List collections in database school

    .. code-block::
        | mongoshowcol db=school

    """

    db = Option(
        doc = '''
        **Syntax:** **db=***<db>*
        **Description:** Name of the db in MongoDB''',
        require=True, validate=validators.Fieldname())


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
        '''Read all collections from database specified'''
        host, port = self.getConfig()
        
        objTime = time.time()

        if host != None and port >0 and port < 65536:
            # host, port
            client = pymongo.MongoClient(host, port)
            
            db = client[self.db]
            
            cur = db.collection_names()
    
            for obj in cur:
                objTime = time.time()
                #self.toStr(obj)
                #str = json.dumps(obj)
                str = {"database": self.db, "collection": obj}
                
                event = {'_time': objTime, 'sourcetype': 'json', 'source': 'mongodb', '_raw': str}
    
                '''
                tipi = ['int', 'str', 'unicode', ]
                for k, v in obj.items():
                    if type(v).__name__ in tipi:
                        event[k] = v
                '''
                yield event
            
            '''
            for i in range(1, self.count + 1):
                text = 'Hello World %d' % i
                yield {'_time': time.time(), 'event_no': i, '_raw': text }
            '''

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
    

dispatch(MongoShowColCommand, sys.argv, sys.stdin, sys.stdout, __name__)
