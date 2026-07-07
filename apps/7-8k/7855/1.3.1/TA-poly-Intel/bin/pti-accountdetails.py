import sys
import time
#sys.path.append(r"polyswarmsdk")
from splunklib.searchcommands import Configuration
from splunklib.searchcommands import dispatch
from splunklib.searchcommands import GeneratingCommand
import log
import environment
from polyswarm_api.api import *
from polyswarm_api import * 

logger = log.get_logger(__file__)

#@Configuration(type='reporting', streaming=False)
@Configuration()
class polytest(GeneratingCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ps_env = None
    
    def generate(self):
        self.ps_env = environment.psEnv(self._metadata.searchinfo.session_key)
        try:
            self.ps_env.api_key
            global_api_key=self.ps_env.api_key
        except Exception as error:
            datacheck=[{'_time':time.time(),'Your Current Set API KEY':'Not Found ','Status':'API Key NOT Found','teamname':'N/A','userid':'N/A','accounttype':'N/A','name':'N/A','_raw':'NO API Key Found'}]
            yield from datacheck
            logger.error('%s',error)
            return
        try:
            community_name='default'
            polyapi = PolyswarmAPI(key=global_api_key,community=community_name)
        except Exception as error:
            datacheck=[{'_time':time.time(),'Your Current Set API KEY':global_api_key,'Status':'Key Found But Error in Setting up PolySwarm Connection','teamname':'N/A','userid':'N/A','accounttype':'N/A','name':'N/A','_raw':'NO API Key Found'}]
            yield from datacheck
            logger.error('%s',error)
            return
        try:
            apidetails = polyapi.account_whois()
            teamname=apidetails.account_name
            teamid=apidetails.account_number
            userid=apidetails.user_account_number
            accounttype=apidetails.account_type
            rawresult=apidetails.json
            datacheck=[{'_time':time.time(),'Your Current Set API KEY':global_api_key,'Status':'Success - API Key and PolySwarm Connection','teamname':teamname,'userid':userid,'accounttype':accounttype,'team id':teamid,'_raw':rawresult}]
            #yield from datacheck
        except Exception as error:
            datacheck=[{'_time':time.time(),'Your Current Set API KEY':global_api_key,'Status':'Key Found and Set PolySwarm Connection But Got Error in Getting the API Data','teamname':'N/A','userid':'N/A','accounttype':'N/A','name':'N/A','_raw':'NO API Key Found'}]
            yield from datacheck
        try:
            apiusage=polyapi.account_features()
            rawresult=apiusage.json # dups the whole JSON for review
            AccountNumber= apiusage.json['account_number'] #account_number
            AccountPlanName= apiusage.json['account_plan_name'] #account_plan_name
            Tenant= apiusage.json['tenant'] #tenant
            UserAccountNumber= apiusage.json['user_account_number'] #   user_account_number
            datacheck=[{'_time':time.time(),'apikey':global_api_key,'name':AccountNumber,'userid':UserAccountNumber,'teamname':AccountPlanName,'accounttype':AccountPlanName,'_raw':rawresult}]
            yield from datacheck
            for usage in apiusage.json['features']:
                if usage["type"] == "boolean":
                    try:
                        evname= str(usage["name"])+' is part of the '+str(usage["backing_feature"])
                    except:
                        if usage["name"] == "Max Artifact Size for Submission":
                            evname = 'Max File Size Support is'+ str(usage["base_uses"])
                        else:
                            evname = 'Featured Enabled:'+str(usage["name"])
                else:
                    evname= str(usage["name"])+' : Current Remaining '+ str(usage["remaining_uses"])+' out of the Total ' +str(usage["base_uses"])
                datacheck=[{'_time':time.time(),'apikey':global_api_key,'name':evname,'userid':UserAccountNumber,'teamname':AccountPlanName,'accounttype':AccountPlanName,'_raw':evname}]
                yield from datacheck
        except Exception as error:
            #logger.error('%s',error.message)
            datacheck=[{'_time':time.time(),'Your Current Set API KEY':global_api_key,'Status':'Error in Getting Account Features and usages. Please Check your API Key','teamname':'N/A','userid':'N/A','accounttype':'N/A','name':'N/A','_raw':'NO API Key Found'}]
            yield from datacheck
            return

        logger.info('Command polyapitest executed successfully')
        return

dispatch(polytest, sys.argv, sys.stdin, sys.stdout, __name__)


