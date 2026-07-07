import splunk.admin as admin
import splunk.entity as entity
import os
import copy
import getpass
import platform
from datetime import datetime
# import your required python modules

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
  __var=None
 
  def setup(self):
    if self.requestedAction == admin.ACTION_EDIT:
      for arg in ['license_key','download_interval','opt_in','startdate','riskscore', 'uid', 'pwd']:
        self.supportedArgs.addOptArg(arg)
  
  '''
  Read the initial values of the parameters from the custom file
      mediatrustsetup.conf, and write them to the setup page. 

  If the app has never been set up,
      uses .../app_name/default/mediatrustsetup.conf. 

  If app has been set up, looks at 
      .../local/mediatrustsetup.conf first, then looks at 
  .../default/mediatrustsetup.conf only if there is no value for a field in
      .../local/mediatrustsetup.conf

  For boolean fields, may need to switch the true/false setting.

  For text fields, if the conf file says None, set to the empty string.
  '''

  def handleList(self, confInfo):
    confDict = self.readConf("mediatrustsetup")
    confInput = self.readConf("inputs")
    SPLUNK_HOME=os.environ.get('SPLUNK_HOME')
    directory=os.path.join(SPLUNK_HOME,'var','log','TA-themediatrust')
    log_file=os.path.join(SPLUNK_HOME,'var','log','splunk','threat_feed.log')
    if not os.path.exists(directory):
        os.makedirs(directory)
    fi = open(log_file,'a')
    license_key=''
    if None != confDict:
      for stanza, settings in confDict.items():
        for key, val in settings.items():
	  if key in ['license_key','startdate','riskscore']:
		fi.write(str(datetime.now())+' '+getpass.getuser()+' DEBUG stanza:'+stanza+'\n')
		if val in [None, '']:
            	   val = ''
		fi.write(str(datetime.now())+' '+getpass.getuser()+' DEBUG writing this key:'+str(key)+':'+str(val)+':\n')
	        license_key=val
	        confInfo[stanza].append(key, val)
    if None != confInput:
      for stanza, settings in confInput.items():
	if platform.system()!='Windows' and stanza=='script://$SPLUNK_HOME/etc/apps/TA-themediatrust/bin/report_metrics.py':
		fi.write(str(datetime.now())+' '+getpass.getuser()+' DEBUG stanza is report_metrics\n')
		fi.write(str(datetime.now())+' '+getpass.getuser()+' DEBUG os.name:'+os.name+'\n')
		fi.write(str(datetime.now())+' '+getpass.getuser()+' DEBUG platform.system():'+platform.system()+'\n')
		for key, val in settings.items():
		  reported_key=''
		  if key in ['disabled']:
		     reported_key='opt_in'
		     if val in [0, 'false']:
			    val=1
		     else:
			    val=0
		     if license_key=='':
			    val=1
		  if reported_key!='':
		     fi.write(str(datetime.now())+' '+getpass.getuser()+' INFO writing this key:'+str(reported_key)+':'+str(val)+':\n')
		     confInfo['setupentity'].append(reported_key, val)
	elif platform.system()!='Windows' and stanza=='script://$SPLUNK_HOME/etc/apps/TA-themediatrust/bin/download_threatfeed.py':
		fi.write(str(datetime.now())+' '+getpass.getuser()+' DEBUG stanza is download_threatfeed\n')
		for key, val in settings.items():
		  reported_key=''
		  if key in ['interval']: 
		     reported_key='download_interval'
		     if val in [None, '']:
			    val = 60
		     else:
			    val=int(val)/int('60')
		     if int(val)<int('60'):
			    val=60 
		  if reported_key!='':
	             fi.write(str(datetime.now())+' '+getpass.getuser()+' INFO writing this key:'+str(reported_key)+':'+str(val)+':\n')
		     confInfo['setupentity'].append(reported_key, str(val))
	elif platform.system()=='Windows' and stanza=='script:\\$SPLUNK_HOME\etc\apps\TA-themediatrust\bin\report_metrics.py':
		fi.write(str(datetime.now())+' '+getpass.getuser()+' DEBUG stanza is report_metrics\n')
		fi.write(str(datetime.now())+' '+getpass.getuser()+' DEBUG os.name:'+os.name+'\n')
		fi.write(str(datetime.now())+' '+getpass.getuser()+' DEBUG platform.system():'+platform.system()+'\n')
		for key, val in settings.items():
		  reported_key=''
		  if key in ['disabled']:
		     reported_key='opt_in'
		     if val in [0, 'false']:
			    val=1
		     else:
			    val=0
		     if license_key=='':
			    val=1
		  if reported_key!='':
		     fi.write(str(datetime.now())+' '+getpass.getuser()+' INFO writing this key:'+str(reported_key)+':'+str(val)+':\n')
		     confInfo['setupentity'].append(reported_key, val)
	elif platform.system()=='Windows' and stanza=='script:\\$SPLUNK_HOME\etc\apps\TA-themediatrust\bin\download_threatfeed.py':
		fi.write(str(datetime.now())+' '+getpass.getuser()+' DEBUG stanza is download_threatfeed\n')
		for key, val in settings.items():
		  reported_key=''
		  if key in ['interval']: 
		     reported_key='download_interval'
		     if val in [None, '']:
			    val = 60
		     else:
			    val=int(val)/int('60')
		     if int(val)<int('60'):
			    val=60 
		  if reported_key!='':
	             fi.write(str(datetime.now())+' '+getpass.getuser()+' INFO writing this key:'+str(reported_key)+':'+str(val)+':\n')
		     confInfo['setupentity'].append(reported_key, str(val))
	

    fi.close()
              
  '''
  After user clicks Save on setup page, take updated parameters,
  normalize them, and save them somewhere
  '''
  def handleEdit(self, confInfo):
    name = self.callerArgs.id
    args = self.callerArgs
    
    SPLUNK_HOME=os.environ.get('SPLUNK_HOME')
    log_file=os.path.join(SPLUNK_HOME,'var','log','splunk','threat_feed.log')
    directory = os.path.dirname(log_file)
    if not os.path.exists(directory):
        os.makedirs(directory)
    fi = open(log_file,'a')
    fi.write(str(datetime.now())+' '+getpass.getuser()+' DEBUG ************We are in handleEdit************\n')
    setupentity=copy.deepcopy(self.callerArgs.data)
    fetchentity=copy.deepcopy(self.callerArgs.data)
    reportentity=copy.deepcopy(self.callerArgs.data)
    enabledentity=copy.deepcopy(self.callerArgs.data)

    if setupentity['license_key'][0] in [None, '']:
      setupentity['license_key'][0] = ''  
    if setupentity['uid'][0] in [None, '']:
      setupentity['uid'][0] = ''
    if setupentity['pwd'][0] in [None, '']:
      setupentity['pwd'][0] = ''

    del setupentity['download_interval']
    del setupentity['opt_in']

    del fetchentity['download_interval']
    del fetchentity['opt_in']
    del fetchentity['license_key']
    del fetchentity['startdate']
    del fetchentity['riskscore']
    del fetchentity['uid']
    del fetchentity['pwd']

    del reportentity['download_interval']
    del reportentity['opt_in']
    del reportentity['license_key']
    del reportentity['startdate']
    del reportentity['riskscore']
    del reportentity['uid']
    del reportentity['pwd']

    del enabledentity['download_interval']
    del enabledentity['opt_in']
    del enabledentity['license_key']
    del enabledentity['startdate']
    del enabledentity['riskscore']
    del enabledentity['uid']
    del enabledentity['pwd']

    fi.write(str(datetime.now())+' '+getpass.getuser()+' DEBUG right before interval handling\n')
    try:
	interval=int(self.callerArgs['download_interval'][0])
    except ValueError:
	fi.write(str(datetime.now())+' '+getpass.getuser()+' DEBUG we had a ValueError with the interval')
	interval=int('60')
    fi.write(str(datetime.now())+' '+getpass.getuser()+' DEBUG interval:'+str(interval)+'\n')
    if int(interval)<int('60'):
	interval=3600
    else:
	interval=int(interval)*int('60')
    fi.write(str(datetime.now())+' '+getpass.getuser()+' DEBUG interval:'+str(interval)+'\n')
    fetchentity['interval'] = interval 
    try:
	startdate=int(self.callerArgs['startdate'][0])
    except ValueError:
	fi.write(str(datetime.now())+' '+getpass.getuser()+' DEBUG we had a ValueError with the startdate')
	startdate=int('2')
    fi.write(str(datetime.now())+' '+getpass.getuser()+' DEBUG startdate:'+str(startdate)+'\n')
    if int(startdate)>int('7'):
	startdate='7'
    setupentity['startdate'][0]=str(startdate)
    fetchentity['disabled']=0
    fetchentity['passAuth']='splunk-system-user'
    enabledentity['disabled']=0
    if self.callerArgs['opt_in']==0:
	reportentity['disabled']=1
    else:
	reportentity['disabled']=0
	self.writeConf('savedsearches', 'Threat Activity By IP - Summary',enabledentity)
	self.writeConf('savedsearches', 'Threat Activity By Domain - Summary',enabledentity)
	self.writeConf('savedsearches', 'Threat Activity Actions By IP - Summary',enabledentity)
	self.writeConf('savedsearches', 'Threat Activity Actions By Domain - Summary',enabledentity)
    reportentity['passAuth']='splunk-system-user'
        

    sessionKey = self.getSessionKey()
    myapp = 'TA-themediatrust'
    try:
        # list all credentials
        entities = entity.getEntities(['admin', 'passwords'], namespace=myapp, owner='nobody', sessionKey=sessionKey)

        for i, c in entities.items():
            fi.write(str(datetime.now()) + ' ' + getpass.getuser() + ' DEBUG username = ' + c['username']+'/'+c['clear_password'] + '\n')
            entity.deleteEntity(['admin', 'passwords'], ":" + c['username'] + ":", namespace=myapp, owner='nobody', sessionKey=sessionKey)

    except Exception, e:
        fi.write(str(datetime.now()) + ' ' + getpass.getuser() + ' DEBUG Could not get %s credentials from splunk. Error = ' + str(e) + '\n')

    apikey = {'name': 'license_key', 'password': setupentity['license_key']}
    apikey_entity = entity.Entity(['admin', 'passwords'], "license_key", namespace=myapp, owner='nobody', contents=apikey)
    entity.setEntity(apikey_entity, sessionKey=sessionKey, strictCreate=False)

    if setupentity['uid'] != '':
      uid_pwd = {'name': setupentity['uid'], 'password': setupentity['pwd']}
      uid_pwd_entity = entity.Entity(['admin', 'passwords'], setupentity['uid'], namespace=myapp, owner='nobody', contents=uid_pwd)
      entity.setEntity(uid_pwd_entity, sessionKey=sessionKey, strictCreate=False)

    del setupentity['license_key']
    del setupentity['uid']
    del setupentity['pwd']

#   Since we are using a conf file to store parameters, write them to the [setupentity] stanza in app_name/local/mediatrustsetup.conf  
    self.writeConf('mediatrustsetup', 'setupentity', setupentity)

    if platform.system()!='Windows':
	    self.writeConf('inputs', 'script://$SPLUNK_HOME/etc/apps/TA-themediatrust/bin/download_threatfeed.py',fetchentity)
	    self.writeConf('inputs', 'script://$SPLUNK_HOME/etc/apps/TA-themediatrust/bin/report_metrics.py',reportentity)
	    self.writeConf('inputs', 'monitor://$SPLUNK_HOME/var/log/splunk',enabledentity)
    else:
	    self.writeConf('inputs', 'script:\\'+ os.path.join('$SPLUNK_HOME','etc','apps','TA-themediatrust','bin','download_threatfeed.py'),fetchentity)
	    self.writeConf('inputs', 'script:\\'+os.path.join('$SPLUNK_HOME','etc','apps','TA-themediatrust','bin','report_metrics.py'),reportentity)
	    self.writeConf('inputs', 'monitor:\\'+os.path.join('$SPLUNK_HOME','var','log','splunk'),enabledentity)
    fi.write(str(datetime.now())+' '+getpass.getuser()+' DEBUG everything written successfully\n')
    fi.close()
      
# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)

