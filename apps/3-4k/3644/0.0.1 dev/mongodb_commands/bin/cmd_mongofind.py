#!/usr/bin/env python

import ast
import ConfigParser
import json
import os
import pprint
import pymongo
import sys
import time

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


@Configuration(streaming=True, local=True)
class MongoFindCommand(GeneratingCommand):
    """ Read documents from database and collection specified

    ##Syntax

    .. code-block::
        countmatches fieldname=<field> pattern=<regular_expression> <field-list>

    ##Description

    Read documents from database and collection specified and filter data 

    ##Example

    Count the number of words in the `text` of each tweet in tweets.csv and store the result in `word_count`.

    .. code-block::
        | inputlookup tweets | countmatches fieldname=word_count pattern="\\w+" text

    """

    db = Option(
        doc = '''
        **Syntax:** **db=***<db>*
        **Description:** Name of the db in MongoDB''',
        require=True, validate=validators.Fieldname())
    
    collection = Option(require=True, validate=validators.Fieldname())
    time = Option(require=False, validate=validators.Fieldname())


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
        '''Read documents from database and collection specified'''
        error = None
        
        host, port = self.getConfig()
        
        objTime = time.time()

        if host != None and port >0 and port < 65536:
            # host, port
            client = pymongo.MongoClient(host, port)
            
            #client.database_names()
            
            db = client[self.db]
            
            #db.collection_names()
            
            collection = db[self.collection]
    
            f = ''
            for fieldname in self.fieldnames:
                f += fieldname + ' '
            try:
                df = ast.literal_eval(f)
            except:
                df = {}
                error = 'errore'
            
            cur = collection.find(df)
            for obj in cur:
                obj['time'] = self.time
                objTime = time.time()
                if self.time in obj:
                    try:
                        objTime = time.mktime(obj[self.time].timetuple())
                    except:
                        pass
                self.toStr(obj)
                str = json.dumps(obj)
                
                event = {'_time': objTime, 'sourcetype': 'json', 'source': 'mongodb', '_raw': str}
    
                mongotype = ['int', 'float', 'bool', 'time', 'str', 'unicode', ]
                for k, v in obj.items():
                    if type(v).__name__ in mongotype:
                        event[k] = v
    
                event['fieldname'] = f
    
                if error:
                    event['error'] = error
                
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
    

dispatch(MongoFindCommand, sys.argv, sys.stdin, sys.stdout, __name__)
