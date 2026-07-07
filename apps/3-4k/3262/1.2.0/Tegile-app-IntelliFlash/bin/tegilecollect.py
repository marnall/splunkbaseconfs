# Splunk input script for Tegile IntelliFlash
# Tegile Systems, Inc. All Rights Reserved. - July 29, 2016
# This script uses Tegile's IntelliFlash API to obtain data for ingestion by Splunk
# This script reads a list csv list of <controller IP>,<auth token> from SPLUNK_HOME/etc/apps/Tegile-app-IntelliFlash/local/arrays.csv, and polls each controller in the list
#  arrays.csv is created by running SPLUNK_HOME/etc/apps/Tegile-app-IntelliFlash/bin/cfg_ctrlr_lst.py
# For each controller polled, this script prints the data to the standard output, along with event separator text, and a time stamp
# This script is called by Splunkd per the configuration in the app's inputs.conf
#


import splunk.entity as entity
import os.path # required for dynamic file path creation
import os # required for dynamic file path creation
import socket #required for error trapping of api calls to controllers
import sys # required for appending python modules packaged with this app
import httplib2 # required for interaction with controller API
import json # rrequired for interaction with controller API
import time # required for creating event timestamps
import csv # required for parsing of the list of controllers
import base64

TegAppPth=os.path.join(os.environ.get('SPLUNK_HOME'),'etc','apps','Tegile-app-IntelliFlash') # build the app path from SPLUNK_HOME to support arbitrary Splunk inst dirs
CntrlrLstFlPth=os.path.join(TegAppPth,'local', 'arrays.csv') # Build the path to the list of controllers to be polled

def EvntBrk(): #define a function to create event breaks with timestamps in the output
    tmstmp=time.strftime("%Y-%m-%d %H:%M:%S") #get the time in year-month-day hour:minute:second format
    evtbrk='TegEvtBrkMrkr' #this string is used to separate events and is referenced in LINEBREKER in props.conf
    print(evtbrk) #print the event separator
    print (tmstmp) #print the time stamp
def PollCntrlr(Cntrlr,Token):
    try:
        auth = Token # Token is the Base64 encoded concatenation of username:password and is read from Controllers.txt
        headerMap = {'content-type':'application/json','Authorization' : 'Basic '+ auth}
        method = "GET"
        urlListPools = "https://"+Cntrlr+"/zebi/api/v1/listPools"
        urlListGroups = "https://"+Cntrlr+"/zebi/api/v1/listGroups"
        urlListUsers = "https://"+Cntrlr+"/zebi/api/v1/listUsers"
        urlListISCSIInitGrps = "https://"+Cntrlr+"/zebi/api/v1/listISCSIInitiatorGroups"
        urlListISCSITrgtGrps = "https://"+Cntrlr+"/zebi/api/v1/listISCSITargetGroups"
        urlListFCInitGrps = "https://"+Cntrlr+"/zebi/api/v1/listFCInitiatorGroups"
        urlListFCTrgtGrps = "https://"+Cntrlr+"/zebi/api/v1/listFCTargetGroups"
        urlListProjects = "https://"+Cntrlr+"/zebi/api/v1/listProjects"
        urlListVolumes = "https://"+Cntrlr+"/zebi/api/v1/listVolumes"
        urlListShares = "https://"+Cntrlr+"/zebi/api/v1/listShares"
        urlListSnapshots = "https://"+Cntrlr+"/zebi/api/v1/listSnapshots"
        resp, content = h.request(urlListPools, method, headers=headerMap) #call the API to get a list of pool dictionaries
        PoolDictList = json.loads(content) # convert the list of dictionaries from json format
        resp, content = h.request(urlListGroups, method, headers=headerMap) #call the API to get a list of group dictionaries
        GroupDictList=json.loads(content) # convert the list of dictionaries from json format
        resp, content = h.request(urlListUsers, method, headers=headerMap) #call the API to get a list of user dictionaries
        UserDictList=json.loads(content) # convert the list of dictionaries from json format
        resp, content = h.request(urlListISCSIInitGrps, method, headers=headerMap) #call the API to get a list of iSCSI initiator groups
        ISCSIInitGrpsList=json.loads(content) # convert the list of from json format
        resp, content = h.request(urlListISCSITrgtGrps, method, headers=headerMap) #call the API to get a list of iSCSI target groups
        ISCSITrgtGrpsList=json.loads(content) # convert the list from json format
        resp, content = h.request(urlListFCInitGrps, method, headers=headerMap) #call the API to get a list of FC initiator groups
        FCInitGrpsList=json.loads(content) # convert the list of from json format
        resp, content = h.request(urlListFCTrgtGrps, method, headers=headerMap) #call the API to get a list of FC target groups
        FCTrgtGrpsList=json.loads(content) # convert the list from json format
        for PoolDict in PoolDictList:
            EvntBrk()
            print ('controller',Cntrlr,'Pool info:',PoolDict)        
        for GroupDict in GroupDictList:
            EvntBrk()
            print ('controller',Cntrlr,'Group info:',GroupDict)
        for UserDict in UserDictList:
            EvntBrk()
            print ('controller',Cntrlr,'User info:',UserDict)
        for ISCSIInitGrp in ISCSIInitGrpsList:
            ISCSIInitGrpOffset=ISCSIInitGrpsList.index(ISCSIInitGrp)
            EvntBrk()
            print ('ISCSIInitGrp',ISCSIInitGrpOffset,'on controller',Cntrlr,'is:',ISCSIInitGrp)
        for ISCSITrgtGrp in ISCSITrgtGrpsList:
            ISCSITrgtGrpOffset=ISCSITrgtGrpsList.index(ISCSITrgtGrp)
            EvntBrk()
            print ('ISCSITrgtGrp',ISCSITrgtGrpOffset,'on controller',Cntrlr,'is:',ISCSITrgtGrp)
        for FCInitGrp in FCInitGrpsList:
            FCInitGrpOffset=FCInitGrpsList.index(FCInitGrp)
            EvntBrk()
            print ('FCInitGrp',FCInitGrpOffset,'on controller',Cntrlr,'is:',FCInitGrp)
        for FCTrgtGrp in FCTrgtGrpsList:
            FCTrgtGrpOffset=FCTrgtGrpsList.index(FCTrgtGrp)
            EvntBrk()
            print ('FCTrgtGrp',FCTrgtGrpOffset,'on controller',Cntrlr,'is:',FCTrgtGrp)
        def CallIFAPI(ParamList,url):
            method = "POST"
            Param_json=json.dumps(ParamList)
            resp, content=h.request(url,method,Param_json,headers=headerMap)
            return json.loads(content)

        for PoolDict in PoolDictList: # iterate list of pool dictionaries
            PoolName=PoolDict["name"] #get the pool name from the pool dict using the name key
            ParamList=[] #initialize the API parameter list
            ParamList.append(PoolName) #add the pool name to the parameter list
            ParamList.append(True) #add "True" to the param list (indicates local controller)
            ProjectDictList=(CallIFAPI(ParamList,urlListProjects)) #call the API and get a list of project dictionaries
            for Project in ProjectDictList: #iterate the list of project dictionaries
                ProjectName=Project["name"] #get the project name
                ParamList=[] #initialize the API parameter list
                ParamList.append(PoolName) #add the pool name to the parameter list
                ParamList.append(ProjectName) #add the projet name to param list
                ParamList.append(True) #add "True" to the param list (indicates local controller)
                VolumeDictList=(CallIFAPI(ParamList,urlListVolumes)) #call the API to get a list of volume dictionaries for this project
                ShareDictList=(CallIFAPI(ParamList,urlListShares)) #call the API to get a list of share dictionaries for this project
                for ShareDict in ShareDictList: #iterate the list of share dictionaries
                    EvntBrk() #create an event break in the output
                    print ('controller',Cntrlr,'Pool=',PoolName,'Project=',ProjectName,'Share info: ',ShareDict) #print info for the current share
                for VolumeDict in VolumeDictList: #iterate the list of volume dictionaries
                    EvntBrk() #create an event break in the output
                    print ('controller',Cntrlr,'Pool=',PoolName,'Project=',ProjectName,'Volume Info:  ',VolumeDict) #print info for each volume    
                    VolumeName=VolumeDict["name"] #get the volume name
                    VolumeDatasetPath=VolumeDict["datasetPath"] #get the volume dataset path
                    ParamList=[] #initialize the parameter list
                    ParamList.append(VolumeDatasetPath) #add the volume dataset path the the parameter list
                    ParamList.append('') #add and empty string to the parameter list, so the API will return all snapshots
                    SnapshotList=(CallIFAPI(ParamList,urlListSnapshots)) #call the API and get a list of snapshots for the current volume
                    SnapshotCnt=len(SnapshotList) #get a count of the snapshots
                    EvntBrk() #create an event break in the output
                    print ('Snapshot count: ',SnapshotCnt,'for volume',VolumeName,'of project',ProjectName,'in pool',PoolName,'on controller',Cntrlr)
                    for Snapshot in SnapshotList: #iterate the list of snapshots
                        SnapshotOffset=SnapshotList.index(Snapshot) #get the snapshot number
                        EvntBrk() #create an event break in the output
                        print ('Snapshot Name:',Snapshot,'is snapshot number:',SnapshotOffset,'of volume',VolumeName,'of project',ProjectName,'in pool',PoolName,'on controller',Cntrlr) #print snapshot info
    except socket.error as socket_err: # write error msg and troubleshooting suggestions to the tegilearray index if we cannot access the controller API
       EvntBrk()
       print ('Couldn not access array',CntrlrIP)
       print(socket_err)
    # End function:  PollCntrlr
    

# access the credentials in /servicesNS/nobody/app_name/admin/passwords
def getCredentials(sessionKey, usernameField, passwordField):
  myapp = 'Tegile-app-IntelliFlash'
  try:
     # list all credentials
     entities = entity.getEntities(['admin', 'passwords'], namespace=myapp,
                                   owner='nobody', sessionKey=sessionKey)
  except Exception, e:
     raise Exception("Could not get %s credentials from splunk. Error: %s"
                     % (myapp, str(e)))
  # return first set of credentials
  for i, c in entities.items():
    return (c['username'], c['clear_password'])

  raise Exception("No credentials have been found")  


# read session key sent from splunkd
sessionKey = sys.stdin.readline().strip()
if len(sessionKey) == 0:
  sys.stderr.write("Did not receive a session key from splunkd. " +
                   "Please enable passAuth in inputs.conf for this " +
                   "script\n")
  exit(2)


try:
    with open(CntrlrLstFlPth,'rt') as CntrlrLstFl:
        CntrlrDictList=csv.DictReader(CntrlrLstFl, fieldnames=['ArrayDNS', 'CntrlrIP','Username','Password','AllowInvalidSslCert'])
        for CntrlrDict in CntrlrDictList:
            username, password = getCredentials(sessionKey, CntrlrDict['Username'], CntrlrDict['Password'])
            h = httplib2.Http(disable_ssl_certificate_validation=bool(CntrlrDict['AllowInvalidSslCert']))
            CntrlrIP=CntrlrDict['CntrlrIP']
            CntrlrToken=base64.encodestring(username+":"+password)
            PollCntrlr(CntrlrIP,CntrlrToken)
except IOError as IOerr: # write error msg and troubleshooting suggestions to the tegilearray index if we cannot open the controllers list
    EvntBrk()
    print ('Could not open Tegile-app-IntelliFlash/local/arrays.csv.  Create this file by running Tegile-App-IntelliFlash/bin/cfg_array_lst.py')
    print (IOerr)



#end of script
