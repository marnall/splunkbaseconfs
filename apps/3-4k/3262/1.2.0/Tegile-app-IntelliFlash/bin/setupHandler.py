import splunk.admin as admin
import splunk.entity as en
import os
import base64
import csv
import os.path

'''
Copyright (C) 2005 - 2010 Splunk Inc. All Rights Reserved.
Description:  This skeleton python script handles the parameters in the configuration page.

      handleList method: lists configurable parameters in the configuration page
      corresponds to handleractions = list in restmap.conf

      handleEdit method: controls the parameters and saves the values 
      corresponds to handleractions = edit in restmap.conf

'''

class ConfigApp(admin.MConfigHandler):
  '''
  Set up supported arguments
  '''
  def setup(self):
    if self.requestedAction == admin.ACTION_EDIT:
      for n in ConfigurableArray:
        for arg in ConfigurableFields:
          self.supportedArgs.addOptArg(arg+n)

  '''
  Read the initial values of the parameters from the custom file
      myappsetup.conf, and write them to the setup page. 

  If the app has never been set up,
      uses .../app_name/default/myappsetup.conf. 

  If app has been set up, looks at 
      .../local/myappsetup.conf first, then looks at 
      .../default/myappsetup.conf only if there is no value for a field in
      .../local/myappsetup.conf

  For boolean fields, may need to switch the true/false setting.

  For text fields, if the conf file says None, set to the empty string.
  '''
  def handleList(self, confInfo):
    confDict = self.readConf("myappsetup")
    if None != confDict:
      for stanza, settings in confDict.items():
        for key, val in settings.items():
          confInfo[stanza].append(key, val)
          
  '''
  After user clicks Save on setup page, take updated parameters,
  normalize them, and save them somewhere
  '''
  def handleEdit(self, confInfo):
    name = self.callerArgs.id
    args = self.callerArgs
    
    for n in ConfigurableArray:
      for arg in ConfigurableFields:
        if self.callerArgs.data[arg+n][0] in [None, '']:
          self.callerArgs.data[arg+n][0] = ''  
        
    '''
    Since we are using a conf file to store parameters, 
    write them to the [setupentity] stanza
    in app_name/local/myappsetup.conf  
    '''       
    self.writeConf('myappsetup', 'setupentity', self.callerArgs.data)

    for n in ConfigurableArray:
      if not self.callerArgs.data['name_'+n][0] in [None, '']:
        ArrayDict={}
        ArrayDict['ArrayName']=self.callerArgs.data['name_'+n][0]
        ArrayDict['ArrayDNS']=self.callerArgs.data['dns_'+n][0]
        ArrayDict['IPCntrlrA']=self.callerArgs.data['controllerAIp_'+n][0]
        ArrayDict['IPCntrlrB']=self.callerArgs.data['controllerBIp_'+n][0]
        ArrayDict['Username']='username_'+n
        ArrayDict['Password']='password_'+n
        ArrayDict['AllowInvalidSslCert']=self.callerArgs.data['allowInvalidSslCert_'+n][0]
        NewArrayDictList.append(ArrayDict) # add the dict we just built to the list of controller dictionaries

    # WrtCntrlrsFile:
    CntrlADictList=list()
    CntrlBDictList=list()
    for ArrayDict in NewArrayDictList: #iterate the new list of array dictionaries
        CntrlADict={}
        CntrlADict['ArrayDNS']=ArrayDict['ArrayDNS'] # extract IP for Controller A from the dictionary
        CntrlADict['IP']=ArrayDict['IPCntrlrA'] # extract IP for Controller A from the dictionary
        CntrlADict['Username']=ArrayDict['Username']
        CntrlADict['Password']=ArrayDict['Password']
        CntrlADict['AllowInvalidSslCert']=ArrayDict['AllowInvalidSslCert']
        CntrlADictList.append(CntrlADict)
        CntrlBDict={}
        CntrlBDict['ArrayDNS']=ArrayDict['ArrayDNS'] # extract IP for Controller A from the dictionary
        CntrlBDict['IP']=ArrayDict['IPCntrlrB'] # extract IP for Controller B from the dictionary
        CntrlBDict['Username']=ArrayDict['Username']
        CntrlBDict['Password']=ArrayDict['Password']
        CntrlBDict['AllowInvalidSslCert']=ArrayDict['AllowInvalidSslCert']
        CntrlBDictList.append(CntrlBDict)
    CntrlrLstFlPth=os.path.join(TegAppPth,'local','arrays.csv')
    CntrlrLstFl=open(CntrlrLstFlPth,'wt') # open the Contrllers.txt file for write
    cout=csv.DictWriter(CntrlrLstFl, ['ArrayDNS', 'IP','Username','Password','AllowInvalidSslCert']) #write the list of dictionaries to Controllers.txt
    cout.writerows(CntrlADictList)
    cout.writerows(CntrlBDictList)
    CntrlrLstFl.close() # close the file      

    # WrtLookUpsFile:
    CntrlADictList=list()
    CntrlADict={}
    CntrlADict['IP']="ControllerIP"    # label the IP column in the header row
    CntrlADict['ArrayName']="ArrayName" # label the array name column in the header row
    CntrlADict['ArrayDNS']="ArrayDNS" # label the array name column in the header row
    CntrlADictList.append(CntrlADict) # Add this header dictionary to the controller A dict list, so its written once
    CntrlBDictList=list()
    for ArrayDict in NewArrayDictList: #iterate the new list of controller dictionaries
        CntrlADict={}
        CntrlADict['IP']=ArrayDict['IPCntrlrA'] # extract IP for Controller A from the dictionary
        CntrlADict['ArrayName']=ArrayDict['ArrayName']
        CntrlADict['ArrayDNS']=ArrayDict['ArrayDNS']
        CntrlADictList.append(CntrlADict)
        CntrlBDict={}
        CntrlBDict['IP']=ArrayDict['IPCntrlrB'] # extract IP for Controller B from the dictionary
        CntrlBDict['ArrayName']=ArrayDict['ArrayName']
        CntrlBDict['ArrayDNS']=ArrayDict['ArrayDNS']
        CntrlBDictList.append(CntrlBDict)
    LookUpFlPth=os.path.join(TegAppPth,'lookups','arraylookuplist.csv')
    LookUpFl=open(LookUpFlPth,'wt') # open the lookup master file for write
    coutlist=csv.DictWriter(LookUpFl, ['IP','ArrayName','ArrayDNS'])
    coutlist.writerows(CntrlADictList)
    coutlist.writerows(CntrlBDictList)
    LookUpFl.close() # close the file



TegAppPth=os.path.join(os.environ.get('SPLUNK_HOME'),'etc','apps','Tegile-app-IntelliFlash')
ConfigurableFields=['name_', 'dns_', 'controllerAIp_', 'controllerBIp_', 'username_', 'password_', 'allowInvalidSslCert_']
ConfigurableArray=['1']
NewArrayDictList=list() # Create a new list of array (controller) dictionaries



# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
