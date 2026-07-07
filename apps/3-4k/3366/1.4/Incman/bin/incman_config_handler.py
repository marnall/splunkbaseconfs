import splunk
import os
import sys
import logging  as logger
import traceback
import splunk.bundle as bundle
import splunk.admin as admin
import splunk.entity as entit
import requests
from suds.xsd.doctor import Import
from suds.xsd.doctor import ImportDoctor
from suds.client import Client


logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s %(message)s',
                   filename=os.path.join(os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk', 'incman_handler.log'),
                   filemode='a')

class ConfigApp(admin.MConfigHandler):

    def setup(self):
        try:
            if self.requestedAction == admin.ACTION_EDIT:
                for arg in ['host', 'user', 'password', 'apiuser', 'apipassword', 'number_cef_field', 'disabled', 'ssl']:
                    self.supportedArgs.addOptArg(arg)
        except:
            logger.error("Excecution Failed: Argument not known in incman_config_handler.setup")
            logger.debug(traceback.format_exc())
            exit(1)
        # Make sure there is a incman entry in the passwords storage
        r = requests.get(
            url=splunk.getLocalServerInfo()+'/servicesNS/nobody/Incman/storage/passwords/%3Aincmanuser%3A?output_mode=json',
            headers={'Authorization': 'Splunk ' + self.getSessionKey()},
            verify=True)

        if r.status_code == 404:
            # No credentials stored yet.  Create a placeholder.
            r = requests.post(
                url=splunk.getLocalServerInfo()+'/servicesNS/nobody/Incman/storage/passwords?output_mode=json',
                data={'name': 'incmanuser', 'password':'placeholder'},
                headers={'Authorization': 'Splunk ' + self.getSessionKey()},
                verify=True)
            r = requests.post(
                url=splunk.getLocalServerInfo()+'/servicesNS/nobody/Incman/storage/passwords?output_mode=json',
                data={'name':'incmanapi', 'password':'placeholder'},
                headers={'Authorization': 'Splunk ' + self.getSessionKey()},
                verify=True)

            if r.status_code < 200 or r.status_code >= 300:
                logger.error("Failed to update Incman password in password store!!")
                r = requests.post(
                    url=splunk.getLocalServerInfo()+'/servicesNS/nobody/Incman/messages',
                    data={"name": "incman",
                          "value": "Couldn't update Incman password in password store!"},
                    headers={'Authorization': 'Splunk ' + self.getSessionKey()},
                    verify=True)
                r.raise_for_status()
        elif r.status_code < 200 or r.status_code >= 300:
            logger.error("Failed to retrieve Incman password from password store!")
            r = requests.post(
                url=splunk.getLocalServerInfo()+'/servicesNS/nobody/Incman/messages',
                data={"name": "incman",
                      "value": "Couldn't retrieve Incman  password from password store!"},
                headers={'Authorization': 'Splunk ' + self.getSessionKey()},
                verify=True)
            r.raise_for_status()
    '''
    Read the initial values of the parameters from the custom file
    myappsetup.conf, and write them to the setup screen.
    If the app has never been set up,
    uses .../<appname>/default/myappsetup.conf.
    If app has been set up, looks at
    .../local/myappsetup.conf first, then looks at
    .../default/myappsetup.conf only if there is no value for a field in
    .../local/myappsetup.conf
    For boolean fields, may need to switch the true/false setting.
    
    For text fields, if the conf file says None, set to the empty string.
    '''

    def handleList(self, confInfo):
        confDict = self.readConf("incman")
        logger.info("Incman list handle " + repr(confDict))
        if None != confDict:
            for stanza, settings in confDict.items():
                for key, val in settings.items():
                    confInfo[stanza].append(key, val)
    '''
    After user clicks Save on setup screen, take updated parameters,
    normalize them, and save them somewhere
    '''
    def handleEdit(self, confInfo):
        logger.info("Incman edit handle")
        name = self.callerArgs.id
        args = self.callerArgs

        # Fix Boolean
        if int(self.callerArgs.data['ssl'][0]) == 1:
            self.callerArgs.data['ssl'][0] = '1'
        else:
            self.callerArgs.data['ssl'][0] = '0'

        host = self.callerArgs.data['host'][0]
        host = host.replace("http://", "")
        host = host.replace("https://", "")
        self.callerArgs.data['host'][0] = host
        ssl = self.callerArgs.data['ssl'][0]
        apiuser = self.callerArgs.data['apiuser'][0]
        apipassword = self.callerArgs.data['apipassword'][0]
        number_cef_field = self.callerArgs.data['number_cef_field'][0]
        username = self.callerArgs.data['user'][0]
        password = self.callerArgs.data['password'][0]

        filename1 = os.path.join(os.environ['SPLUNK_HOME'],
                                 'etc',
                                 'apps',
                                 'Incman',
                                 'default',
                                 'data',
                                 'ui',
                                 'alerts',
                                 'incman.html')
        try:                         
            pfile1 = open(filename1, "w")
            pfile1.seek(0)
            pfile1.truncate()
            template_first = """
            <form class="form-horizontal form-complex">
               <div class="control-group">
                  <splunk-control-group>
                <p>Create new incident for each alert or append splunk event to last one (you have to use a unique 
                    incidentID)</p>
                    <splunk-radio-input name="action.incman.param.create_new" >
                <option value="1">Create new</option>
                <option value="2">Append</option>
                </splunk-radio-input>
               </splunk-control-group>
                  </div><hr>
             <div id="timelaps_div" class="control-group">
               <label class="control-label" for="timeplaps">Threshold (minutes)</label>
               <div class="controls">
                 <p>How many minutes from last incident to append splunk event or create a new one</p>
                 <input type="number" min="0" name="action.incman.param.timelaps" id="timeplaps" />
                 <span class="help-block">Threshold in minutes (set 0 for everytime)</span>
               </div>
              </div><hr>
              <div class="control-group">
               <splunk-control-group help="I.e. If append option is selected this'll be ignored">
               <p>Add DateTime to incident Id </p>
                 <splunk-radio-input name="action.incman.param.add_datetime" >
                    <option value="0">Add datetime</option>
                    <option value="1">Not add Datetime</option>
                </splunk-radio-input>
               </splunk-control-group>
              </div><hr>
              <div class="control-group">
               <label class="control-label" for="incidentid">Incident ID</label>
               <div class="controls">
                 <input type="text"  name="action.incman.param.incidentID" id="incidentid" />
                 <span class="help-block">E.g. $name$ - $trigger_date$ $trigger_time$</span>
               </div>
              </div><hr>
              <div class="control-group">
               <label class="control-label" for="add_info">Additional info</label>
               <div class="controls">
                 <input type="text" name="action.incman.param.additionl_info" id="add_info" />
                 <span class="help-block">E.g. Query: $search$</span>
               </div>
              </div><hr>
              <div class="control-group">
               <label class="control-label" for="select_temp">Template</label>
               <div class="controls">
                 <splunk-search-dropdown name="action.incman.param.template"
                      search=" | inputlookup listtemplate.csv"
                      value-field="id" label-field="name" />
                 <span class="help-block">Choose Incman template</span>
               </div>
              </div> 
             <hr>
              """

            pfile1.write(template_first)
            for numb in range(1, int(number_cef_field)+1):
                html_template = """
                    <div class="control-group">
                         <label class="control-label" for="select_cef_{number}">{number} Cef field</label>
                             <div class="controls">
                                <splunk-search-dropdown name="action.incman.param.cef_field_{number}" 
                                        id="select_cef_{number}select_cef_{number}""
                                        search=" | inputlookup listcef.csv"
                                        value-field="value" label-field="name"/>
                             </div>
                             <div class="controls">
                              <input type="text" placeholder="result field to use"  
                                     name="action.incman.param.cef_value_{number}" id="" />
                                <span class="help-block">E.g. $result.host$ </span>	 
                             </div>
                            </div><hr> """.format(number=str(numb))
                pfile1.write(html_template)

            closing_template = "</form>"
            pfile1.write(closing_template)
            pfile1.close()
        except  Exception, e:
                pfile1.close()
                logger.error("Error opening file :" + str(e))
                logger.debug(traceback.format_exc())
                exit(1)

        filename = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'Incman', 'lookups', 'listtemplate.csv')
        try:
            pfile = open(filename, "w")
            pfile.seek(0)
            pfile.truncate()
            html = "id,name\n"
            pfile.write(html)
            try:
                tns = "https://"+host+"/api/"
                client_url = "https://"+host+"/api/service.php?WSDL"
                imp = Import('http://schemas.xmlsoap.org/soap/encoding/')
                imp.filter.add(tns)
                try:
                    client = Client(client_url, plugins=[ImportDoctor(imp)])
                    token = client.service.auth_request_api(apiuser, apipassword)
                    usertoken = client.service.auth_request_user(token, username, password)
                    list_template = client.service.incident_templates_list(usertoken)
                    for items in list_template:
                        for item in items:
                            for (i, val) in enumerate(item):
                                strin = ""
                                for (j, val2) in enumerate(val):
                                    if val2[0] == "key":
                                        key = str(val2[1])
                                        key1 = key.replace("[", "")
                                        key2 = key1.replace("]", "")
                                        strin = '%s' % (key2)
                                    elif val2[0] == "value":
                                        key = str(val2[1])
                                        key1 = key.replace("[", "")
                                        key2 = key1.replace("]", "")
                                        strin = strin +","+ key2+"\n"
                                        pfile.write(strin)
                                        strin = ""
                except Exception, e:
                    pfile.close()
                    r = requests.post(
                        url=splunk.getLocalServerInfo()+'/servicesNS/nobody/Incman/messages',
                        data={"name":"incman",
                              "value":"Couldn't connect to Incman soap service!"},
                        headers={'Authorization':'Splunk ' + self.getSessionKey()},
                        verify=True)
                    r.raise_for_status()
                    logger.error("Excecution Failed : "+ str(ssl)+" - "+ str(tns))
                    logger.debug(traceback.format_exc())
                    exit(1)

                htmlcloise = ""
                pfile.write(htmlcloise)
                pfile.close()
            except  Exception, e:
                pfile.close()
                logger.error("Excecution Failed :" + str(e))
                logger.debug(traceback.format_exc())
                exit(1)
        except  Exception, e:
                pfile.close()
                logger.error("Error opening file :" + str(e))
                logger.debug(traceback.format_exc())
                exit(1)

        if password:
            r = requests.post(
                url=splunk.getLocalServerInfo()+'/servicesNS/nobody/Incman/storage/passwords/%3Aincmanuser%3A?output_mode=json',
                data={'password': password},
                headers={'Authorization': 'Splunk ' + self.getSessionKey()},
                verify=True)
            r = requests.post(
                url=splunk.getLocalServerInfo()+'/servicesNS/nobody/Incman/storage/passwords/%3Aincmanapi%3A?output_mode=json',
                data={'password': apipassword},
                headers={'Authorization': 'Splunk ' + self.getSessionKey()},
                verify=True)
            if r.status_code < 200 or r.status_code >= 300:
                logger.error("Failed to update Incman password in password store!")
                r = requests.post(
                    url=splunk.getLocalServerInfo()+'/servicesNS/nobody/Incman/messages',
                    data={"name": "incman",
                          "value": "Couldn't update Incman password in password store!"},
                    headers={'Authorization': 'Splunk ' + self.getSessionKey()},
                    verify=True)
                r.raise_for_status()
        # We want to store the password securely, not in the conf file
        self.callerArgs.data['password'][0] = ''
        self.callerArgs.data['apipassword'][0] = ''

        # Fix Nulls
        for key in self.callerArgs.data.keys():
            if self.callerArgs.data[key][0] == None:
                self.callerArgs.data[key][0] = ''

            # Strip trailing and leading whitespace
            self.callerArgs.data[key][0] = self.callerArgs.data[key][0].strip()

        self.writeConf('incman', 'inc_config', self.callerArgs.data)


    # end handleEdit

# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
