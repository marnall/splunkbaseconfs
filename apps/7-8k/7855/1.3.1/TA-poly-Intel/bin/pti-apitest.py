import sys,time
#sys.path.append(r"polyswarmsdk")
from splunklib.searchcommands import Configuration
from splunklib.searchcommands import dispatch
from splunklib.searchcommands import GeneratingCommand
import log
import environment
from polyswarm_api.api import *

logger = log.get_logger(__file__)

@Configuration(type='reporting', streaming=False)
class polytest(GeneratingCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ps_env = None
    
    def generate(self):
        self.ps_env = environment.psEnv(self._metadata.searchinfo.session_key)
        datacheck = []
        try:
            self.ps_env.api_key
            global_api_key=self.ps_env.api_key
            yield from datacheck

        except Exception as error:
            datacheck=[{'_time':time.time(),'Your Current Set API KEY':'Not Found ','Status':'API Key NOT Found','teamname':'N/A','userid':'N/A','accounttype':'N/A','name':'N/A','_raw':'NO API Key Found'}]
            yield from datacheck
            logger.error('%s',error)
            return
        try:
            community_name='default'
            polyapi = PolyswarmAPI(key=global_api_key,community=community_name)
        except Exception as error:
            if global_api_key == "invaild":
                datacheck=[{'_time':time.time(),'Your Current Set API KEY':'Not Found ','Status':'API Key NOT Found','teamname':'N/A','userid':'N/A','accounttype':'N/A','name':'N/A','_raw':'NO API Key Found'}]
            else:
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
            yield from datacheck
            return
        except Exception as error:
            if global_api_key == "invalid":
                datacheck=[{'_time':time.time(),'Your Current Set API KEY':'Not Found ','Status':'API Key NOT Found','teamname':'N/A','userid':'N/A','accounttype':'N/A','name':'N/A','_raw':'NO API Key Found'}]
            else: 
                datacheck=[{'_time':time.time(),'Your Current Set API KEY':global_api_key,'Status':'Got Error in Getting the API Data','teamname':'N/A','userid':'N/A','accounttype':'N/A','name':'N/A','_raw':'NO API Key Found'}]
            yield from datacheck
            return
        return
        logger.info('Command polyapitest executed successfully')

dispatch(polytest, sys.argv, sys.stdin, sys.stdout, __name__)

