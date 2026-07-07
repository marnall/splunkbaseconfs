#==============================================================================#
# Continuous Automation and Visibility Engine                    Set Solutions #
# Handlers for Setup Configuration                 Engineering and Development #
#==============================================================================#


#------------------------------------------------------------------------------#
# Include Libraries and Configuration                                          #
#------------------------------------------------------------------------------#
#
#-- Library Imports and Global Variables -------------------------------------
import re
import splunk.admin as admin
fields = {"splunkrest":["splunkrest_verify","splunkrest_certauth","splunkrest_clientcrt","splunkrest_clientkey"],
          "enrichrest_opendns":["enrichrest_opendns_verify","enrichrest_opendns_baseurl","enrichrest_opendns_apikey","enrichrest_opendns_certauth","enrichrest_opendns_clientcrt","enrichrest_opendns_clientkey","enrichrest_opendns_retain_bad","enrichrest_opendns_retain_neutral","enrichrest_opendns_retain_good"],
          "enrichrest_virustotal":["enrichrest_virustotal_verify","enrichrest_virustotal_baseurl","enrichrest_virustotal_apikey","enrichrest_virustotal_certauth","enrichrest_virustotal_clientcrt","enrichrest_virustotal_clientkey","enrichrest_virustotal_retain_bad","enrichrest_virustotal_retain_neutral","enrichrest_virustotal_retain_good"],
          "httpsproxy":["httpsproxy_address","httpsproxy_bypass"]}
#-----------------------------------------------------------------------------
#
#------------------------------------------------------------------------------#


#------------------------------------------------------------------------------#
# Configuration Handler                                                        #
#------------------------------------------------------------------------------#
#
#-- Configuration Handler ----------------------------------------------------
class ConfigApp(admin.MConfigHandler):
    #
    # Set up and define the supported configuration arguments
    def setup(self):
        if self.requestedAction != admin.ACTION_EDIT: return False
        for stanza in fields:
            for field in fields[stanza]: self.supportedArgs.addOptArg(field)
    #
    # Read the initial values of the parameters in the CAVE configuration
    def handleList(self,gifnoc):
        config = self.readConf("cavedetective")
        if config == None: return False
        for stanza,settings in config.items():
            for field,value in settings.items(): gifnoc[stanza].append(field,value)
    #
    # Normalize user provided parameters and save to the CAVE configuration
    def handleEdit(self,gifnoc):
        for stanza in fields:
            for field in fields[stanza]:
                if field not in self.callerArgs.data: continue
                elif not isinstance(self.callerArgs.data[field],list): self.callerArgs.data[field] = [str()]
                elif not isinstance(self.callerArgs.data[field][0],(str,int,bool,basestring,unicode)): self.callerArgs.data[field] = [str()]
                if re.match(r'\_verify$',field): self.callerArgs.data[field][0] = "1" if str(self.callerArgs.data[field][0]) == "1" else "0"
                elif re.match(r'\_retain\_((bad)|(neutral)|(good))$',field): self.callerArgs.data[field][0] = "86400" if int(self.callerArgs.data[field][0]) < 86400 else str(self.callerArgs.data[field][0])
                elif re.match(r'\_retain\_((bad)|(neutral)|(good))$',field): self.callerArgs.data[field][0] = "31557600" if int(self.callerArgs.data[field][0]) > 31557600 else str(self.callerArgs.data[field][0])
                else: self.callerArgs.data[field][0] = str(self.callerArgs.data[field][0])
                self.writeConf("cavedetective",stanza,{field:self.callerArgs.data[field]})
#
# Execute the intended class for processing the provided data
admin.init(ConfigApp,admin.CONTEXT_NONE)
#-----------------------------------------------------------------------------
#
#------------------------------------------------------------------------------#
