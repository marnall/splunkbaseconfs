import splunk.rest
import ConfigParser
import json
import os.path
import logging
import StringIO

class ConfHandler(splunk.rest.BaseRestHandler):

    def __init__(self, method, requestInfo, responseInfo, sessionKey):
        splunk.rest.BaseRestHandler.__init__(self,
          method, requestInfo, responseInfo, sessionKey)
        self.app_dir = os.path.join(os.environ["SPLUNK_HOME"], 'etc', 'apps')

    def writeJson(self, data):
        self.response.setStatus(200)
        self.response.setHeader('content-type', 'application/json')
        self.response.write(json.dumps(data))

    def handle_GET(self):
        conf_files={}
        for app in os.listdir(self.app_dir):
            try:
                conf_files[app]={}
                for path in ["default","local"]:
                    conf_files[app][path]={}
                    conf_files[app][path]["files"]=[]
                    conf_files[app][path]["contents"]={}
                    if os.path.isdir(os.path.join(self.app_dir,app, path)):
                        for i in os.listdir(os.path.join(self.app_dir, app, path)):
                            if i.endswith('.conf'):
                                conf_files[app][path]["files"].append(i)
                                configuration= ConfigParser.RawConfigParser(allow_no_value=True)
                                configuration.optionxform = str
                                configuration.read(os.path.join(self.app_dir, app, path,i))
                                FileInfo = configuration
                                FileInfo_new = {}
                                if FileInfo != None:
                                    for stanza in FileInfo.sections():
                                        FileInfo_new[stanza] = {}
                                        for key, value in FileInfo.items(stanza):
                                            if value in [None]:
                                                value = ''
                                            FileInfo_new[stanza][key] = value
                                conf_files[app][path]["contents"][i]=FileInfo_new
            except:
                pass
        self.writeJson(conf_files)

    def handle_POST(self):
        config = ConfigParser.RawConfigParser()
        config.optionxform = str
        result=json.loads(self.request["payload"])
        config.read(os.path.join(self.app_dir,result['app_name'],'default',result['file_name']))
        for section in result['details'].keys():
            stanza_flag=config.has_section(section)
            if stanza_flag is False:
                config.add_section(section)
            for prop in result['details'][section]:
                config.set(section, prop, result['details'][section][prop])
        with open(os.path.join(self.app_dir,result['app_name'],'default',result['file_name']), 'w') as FileConfig:
            config.write(FileConfig)
