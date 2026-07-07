# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
import os,subprocess,platform
import binascii
import sys
import ssl
import splunk.rest
import json 
import saUtils
from pymongo import MongoClient
from io import open

#========================================================================
# Method to connect to the database using properties from the specified
# file (scm-feramework.properties for example):
#
def connectToDb (propsFile, dbName='',theSessionKey=''):

    mongo_replicaSet_hosts = ''
    mongo_replicaSet_name = ''
    mongo_host = ''
    mongo_port = 27020
    mongo_db = ''
    mongo_ssl = 'false'
    mongo_auth_db = ''
    mongo_user = ''
    mongo_password = ''
    connectionString = ''
    sessionKey= ''

    # Get mongo properties
    with open(propsFile) as propertyFile:
        for line in propertyFile:
            propname, propval = line.partition("=")[::2]
            if propname.strip() == "mongo.host":
                mongo_host = propval[:-1]
            elif propname.strip() == "mongo.port":
                mongo_port = int (propval[:-1])
            elif propname.strip() == "mongo.db":
                mongo_db = propval[:-1]
            elif propname.strip() == "mongo.auth.db":
                mongo_auth_db = propval[:-1]
            elif propname.strip() == "mongo.user":
                mongo_user = propval[:-1]
            elif propname.strip() == "mongo.replicaSet.hosts":
               mongo_replicaSet_hosts = propval[:-1]
            elif propname.strip() == "mongo.replicaSet.name":
               mongo_replicaSet_name = propval[:-1]
            elif propname.strip() == "mongo.ssl":
               mongo_ssl = propval[:-1]

    if len(dbName) > 0:
        mongo_db = dbName;

    if len(mongo_user) == 0:
        raise Exception ("Missing property: mongo.user in properties file: " + propsFile);

    if len(mongo_host) == 0 and len(mongo_replicaSet_hosts) == 0:
        raise Exception ("Missing property: Must set mongo.host OR mongo.replicaSet.hosts in properties file: " + propsFile);

    if len(mongo_replicaSet_hosts) > 0 and len(mongo_replicaSet_name) == 0:
        raise Exception ("Must set mongo.replicaSet.name when mongo.replicaSet.hosts is defined in properties file: " + propsFile);

    if len(mongo_db) == 0:
        raise Exception ("Missing property: mongo.db in properties file: " + propsFile);

    if len(mongo_auth_db) == 0:
        raise Exception ("Missing property: mongo.auth.db in properties file: " + propsFile);

    if len(mongo_user) == 0:
        raise Exception ("Failed to decrypt mongo_user");

    # Retrieve mongo password from splunk storage

    if len(theSessionKey) == 0:
        settings = saUtils.getSettings(sys.stdin)
        sessionKey = settings['sessionKey']
    else:
        sessionKey = theSessionKey

    passwdEndpoint = "/services/storage/passwords/" + mongo_user + "?output_mode=json"
    #passwdResponse, passwdContent = splunk.rest.simpleRequest (passwdEndpoint, method='GET', sessionKey=settings['sessionKey'], raiseAllErrors=False)
    passwdResponse, passwdContent = splunk.rest.simpleRequest (passwdEndpoint, method='GET', sessionKey=sessionKey, raiseAllErrors=False)
    tmp = json.loads(passwdContent)
    mongo_password = tmp['entry'][0]['content']['clear_password']

    if len(mongo_password) == 0:
        raise Exception ("Failed to retrieve mongo_password");

    doSSL = False;
    if (mongo_ssl == 'true'):
        doSSL = True;

    if len(mongo_replicaSet_hosts) > 0:
        # Connect to replica set, in this case do it using connection string with format:
        # mongodb://user:password@host1:port1,host2:port2:host3:port3/?authSource= + mongo_auth_db + "&replicaSet=scm&ssl=tre"
        connectionString = "mongodb://" + mongo_user + ":" + mongo_password + "@" + mongo_replicaSet_hosts + "/?authSource=" + mongo_auth_db + "&replicaSet=" + mongo_replicaSet_name 
        client = MongoClient (connectionString, ssl=doSSL, ssl_match_hostname=False, ssl_cert_reqs=ssl.CERT_NONE);
        db = client[mongo_db]
    else:
        # Connect to single node mongo instance:
        client = MongoClient (mongo_host, mongo_port, ssl=doSSL, ssl_match_hostname=False, ssl_cert_reqs=ssl.CERT_NONE);
        db = client[mongo_db]
        db.authenticate (mongo_user, mongo_password, source=mongo_auth_db)

    return db
