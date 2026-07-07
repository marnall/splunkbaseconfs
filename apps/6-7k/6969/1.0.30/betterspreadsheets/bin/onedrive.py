#!/usr/bin/env python
#Dominique Vocat, 2023 for kauswagan.io

from __future__ import absolute_import, division, print_function, unicode_literals
import random
import csv
import os,sys
import time
import json
import logging
import logging.handlers
import requests
import datetime
import splunk.entity as entity

splunkhome = os.environ['SPLUNK_HOME']#load own libs from ../lib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
import splunklib.client as client
from solnlib import credentials

appcontext = "TA-onedrive-test"

def setup_logger(level):
     logger = logging.getLogger('onedrive')
     logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
     logger.setLevel(level)
     file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/'+appcontext+'.log', maxBytes=25000000, backupCount=5)
     formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
     file_handler.setFormatter(formatter)
     logger.addHandler(file_handler)
     return logger

def get_onedrive_settings(session_key):
    ent = entity.getEntity(['configs', 'conf-onedrive'],'Splunk OneDrive AlertAction', sessionKey=session_key, namespace="-", owner="-")
    if 'clientid' in ent and 'tenantid' in ent and 'domain' in ent:
        logger.info(ent)
        print( ent, file=sys.stderr )
        clientid = ent["clientid"]
        tenantid = ent["tenantid"]
        domain = ent["domain"]
    return ent

def get_onedrive_session(clientid,tenantid,domain,password):
    data = {'grant_type':"client_credentials", 
        'resource':"https://graph.microsoft.com", 
        'client_id':clientid, 
        'client_secret':password} 
    URL = "https://login.windows.net/"+domain+"/oauth2/token?api-version=1.0"
    r = requests.post(url = URL, data = data) 
    j = json.loads(r.text)
    TOKEN = j["access_token"]
    headers={'Authorization': "Bearer " + TOKEN}
    print( headers, file=sys.stderr )
    return headers

def get_stored_password(session_key, appcontext, realm, whichpassword):
        """
        Retrieve stored password, use https://splunkbase.splunk.com/app/4013 to create/update
        """
        cm = credentials.CredentialManager(session_key, appcontext, realm=realm) #retrieve realm is vrops
        pwd = cm.get_password(whichpassword)
        return pwd

def get_info_for_current_user(session_key, user):
    resp = entity.getEntity(['authentication', 'users'],user, sessionKey=session_key, namespace="-", owner="-")
    print( resp, file=sys.stderr )
    return resp

def get_info_for_principal(session_key, principal, session):
    r = requests.get("https://graph.microsoft.com/v1.0/users/" + principal, headers=session)
    userlist=json.loads(r.text)
    print( "principal=" + userlist["userPrincipalName"] + " id=" + userlist["id"], file=sys.stderr )
    userinfo = {"principal": userlist["userPrincipalName"], "id": userlist["id"]}
    return userinfo

logger = setup_logger(logging.INFO)

@Configuration(type="reporting")
class onedrive(GeneratingCommand):
    """
    Handle parameter passing, lazy way 'round is show user how to pass which combination via searchbnf.conf
    """
    get = Option(require=True)
    limit = Option(require=False, default="10000") #10k is good enough for post and still works without paging, please allow me to be lazy
    item = Option(require=False)

    def generate(self):
        print( self._metadata.searchinfo, file=sys.stderr )
        if not self.records:
            self.records = [] # empty result set as we are a generating command

            # Retrieve stored password, use https://splunkbase.splunk.com/app/4013 to create/update
            pwd = get_stored_password(self._metadata.searchinfo.session_key, "-", "onedrive_alert", 'Splunk OneDrive AlertAction')

            # get tenant etc from config
            config = get_onedrive_settings(self._metadata.searchinfo.session_key)            

            # Perform authentication, get the token for the session and update headers for further calls
            session = get_onedrive_session(config["clientid"],config["tenantid"],config["domain"],pwd)

            # collect user info
            user = get_info_for_current_user(self._metadata.searchinfo.session_key, self._metadata.searchinfo.username)

            # Depending on the desired api do different calls and handle the passing of the json or parts of the json required.
            if self.get=="folders":
                # list just the folders for the user
                r = requests.get("https://graph.microsoft.com/v1.0/users/" + user["email"] + "/drive/root/children", headers=session)
                filelist=json.loads(r.text)
                for item in filelist["value"]:
                    if "folder" in item:
                        #PUT /drives/{drive-id}/items/{parent-id}:/{filename}:/content
                        print("https://graph.microsoft.com/v1.0/drives/"+item["parentReference"]["driveId"]+"/items/"+ item["id"] + ","+item["name"] + " (" + item["webUrl"] + ")", file=sys.stderr )
                        record = {"url": "https://graph.microsoft.com/v1.0/drives/"+item["parentReference"]["driveId"]+"/items/"+ item["id"], "label": item["name"], "weburl": item["webUrl"] }
                        self.records.append(record)
                        parentfolder = item["name"]

                        # list subfolders
                        #GET /drives/{drive-id}/items/{item-id}/children
                        suburl = "https://graph.microsoft.com/v1.0/drives/"+item["parentReference"]["driveId"]+"/items/"+ item["id"]+"/children"
                        r = requests.get(suburl, headers=session)
                        print(r.text , file=sys.stderr )
                        subfolderlist=json.loads(r.text)
                        for item in subfolderlist["value"]:
                            if "folder" in item:
                                #PUT /drives/{drive-id}/items/{parent-id}:/{filename}:/content
                                print("https://graph.microsoft.com/v1.0/drives/"+item["parentReference"]["driveId"]+"/items/"+ item["id"] + ","+item["name"] + " (" + item["webUrl"] + ")", file=sys.stderr )
                                self.records.append( {"url": "https://graph.microsoft.com/v1.0/drives/"+item["parentReference"]["driveId"]+"/items/"+ item["id"], "label": parentfolder+"\\"+item["name"], "weburl": item["webUrl"]} )

            elif self.get=="drives":
                userinfo = get_info_for_principal(self._metadata.searchinfo.session_key, user["email"], session)                
                r = requests.get("https://graph.microsoft.com/v1.0/users/"+userinfo["id"]+"/drives", headers=session)
                drivelist=json.loads(r.text)
                print(r.text, file=sys.stderr )
                for item in drivelist["value"]:
                    #print(item)
                    if "id" in item:
                        self.records.append(item)


            elif self.get=="driveitems":
                print("https://graph.microsoft.com/v1.0/drive/items/"+self.item, file=sys.stderr )
                r = requests.get("https://graph.microsoft.com/v1.0/drive/items/"+self.item, headers=session)
                driveitemlist=json.loads(r.text)
                print(r.text, file=sys.stderr )
                for item in driveitemlist["value"]:
                    #print(item)
                    if "id" in item:
                        self.records.append(item)            

            elif self.get=="sites":              
                r = requests.get("https://graph.microsoft.com/v1.0/sites", headers=session)
                drivelist=json.loads(r.text)
                print(r.text, file=sys.stderr )
                for item in drivelist["value"]:
                    #print(item)
                    if "id" in item:
                        self.records.append(item)

            else:
                #not handled error, generate error results
                print("not implemented value for api= ", file=sys.stderr )
                raise ValueError("not implemented or misspelled value for parameter api: {}\nCurrently can handle resources,resourceKinds,stats,resource and properties".format(self.api))

        for record in self.records:
            yield record

    def __init__(self):
        super(onedrive, self).__init__()
        self.records = None

dispatch(onedrive, sys.argv, sys.stdin, sys.stdout, __name__)