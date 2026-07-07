import os, sys, requests, urllib, time
from utils import log  
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
from splunk.clilib.bundle_paths import make_splunkhome_path
import splunk.appserver.mrsparkle.lib.util as splunk_lib_util
from splunklib.binding import HTTPError
import splunk.clilib.cli_common as scc

serverclass_conf = splunk_lib_util.make_splunkhome_path(['etc', 'apps', 'getdiag', 'local', 'serverclass.conf'])
splunk_home=splunk_lib_util.make_splunkhome_path(['bin'])

def trigger_reload_deploy_server(self, sc=None):
    
    try:
        log("INFO","Reloading deployment server...",file_name="getdiaginfo")
        splunkd_uri = scc.getMgmtUri()
        session_key = self.service.token
        
        endpoint = splunkd_uri + "/services/deployment/server/config/_reload"
        headers = {"Authorization": f"Splunk {session_key}", "Content-Type": "application/json"}
        
        if not sc:
            body = ''
        else:
            body = urllib.parse.urlencode({"serverclass": sc})
        update_response = requests.post(endpoint, headers=headers, data=body, verify=False)
 
        if update_response.status_code == 200:
            log("INFO", "Deployment server reloaded Successfully", file_name="getdiaginfo")
            return True
        else:
            log("ERROR", f"Failed to reload deployment server. Status: {update_response.status_code}, Response: {update_response.text}", file_name="getdiaginfo")
            return False
        
    except HTTPError as e:
        log("ERROR",f"Failed to reload deployment server: {e}",file_name="getdiaginfo")
        return False
        
def create_whitelist(server_list):
    
    try:
        # Prepare the whitelist content to be added
        count = 0
        whitelist_content = ""
        for server in server_list:
            whitelist_content += f'whitelist.{count}={server.strip()}\n'
            count+=1
        
        with open(serverclass_conf, 'w') as f:
            f.write('[serverClass:requestdiag:app:getdiag_addon]\n')
            f.write('restartSplunkWeb = 0\n')
            f.write('restartSplunkd = 1\n')
            f.write('stateOnClient = enabled\n')
            f.write('[serverClass:requestdiag]\n')
            f.write(whitelist_content)
            
        log("INFO",f"whitelist_content: {whitelist_content}",file_name="getdiaginfo")
        return True
    except Exception as e:
        return False

def modify_app():
    temp_file = splunk_lib_util.make_splunkhome_path(['etc', 'deployment-apps','getdiag_addon' ,'bin', 'checkpoint.sh'])
    os.makedirs(os.path.dirname(temp_file), exist_ok=True)
    with open(temp_file, 'w') as f:
        f.write(str(time.time()))
        

@Configuration()
class Getdiaginfo(GeneratingCommand):
    server_list = Option(require=False)

    def generate(self):

        log("INFO", "Executing requestdiag custom command", file_name="getdiaginfo")

        try:
            if self.server_list:
                # Ensure directories exist
                os.makedirs(os.path.dirname(serverclass_conf), exist_ok=True)
                
                server_list = self.server_list.split(',')
                log("INFO",f"server_list: {server_list}",file_name="getdiaginfo")
                
                whitelist_status=create_whitelist(server_list)
                modify_app()
                reload_status=trigger_reload_deploy_server(self,"requestdiag")
                
                if  reload_status and whitelist_status:
                    # Return success result to JavaScript
                    result = {"status": "success", "message": "Diag requested successfully. It will be available soon..!!"}
                    yield result
            else:
                result = {"status": "ERROR", "message": "Please provide commas seperated server name"}
                yield result

        except Exception as e:
            # Handle errors and return error result to JavaScript
            log("ERROR", f"Error during requestdiag execution: {str(e)}", file_name="getdiaginfo")
            result = {"status": "error", "message": f"An error occurred: {str(e)}"}
            yield result


dispatch(Getdiaginfo, sys.argv, sys.stdin, sys.stdout, __name__)
