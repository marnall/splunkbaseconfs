import os, shutil, configparser, sys
from utils import log  
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
from splunk.clilib.bundle_paths import make_splunkhome_path
import splunk.appserver.mrsparkle.lib.util as splunk_lib_util
import socket

ds_app_path = splunk_lib_util.make_splunkhome_path(['etc', 'deployment-apps'])
final_app_path = splunk_lib_util.make_splunkhome_path(['etc', 'apps', 'getdiag', 'data', 'getdiag_addon'])
conf_file_create_path = splunk_lib_util.make_splunkhome_path(['etc', 'apps', 'getdiag','data', 'getdiag_addon' ,'local', 'diag.conf'])


def get_private_ip():
    try:
        # Check if the file exists
        if os.path.exists(conf_file_create_path):
            # Parse the file as an INI file
            config = configparser.ConfigParser()
            config.read(conf_file_create_path)

            # Fetch the targetUri value
            if "general" in config and "targetUri" in config["general"]:
                target_uri = config["general"]["targetUri"]
                return target_uri

        # Create a socket to connect to a non-routable address (used to determine the primary IP)
        hostname = socket.gethostname()
        private_ip = socket.gethostbyname(hostname)
        private_ip=str(private_ip)+":8089"
        return private_ip
    except Exception as e:
        return f"<IP>:<PORT>"
 
@Configuration()
class Getdiaginfo(GeneratingCommand):
    url = Option(require=False)

    def generate(self):

        log("INFO", "Executing setupdiag custom command", file_name="getdiaginfo")

        try:
            if self.url:
                # Ensure directories exist
                os.makedirs(os.path.dirname(final_app_path), exist_ok=True)
                os.makedirs(os.path.dirname(conf_file_create_path), exist_ok=True)

                # Create diag.conf file
                with open(conf_file_create_path, 'w') as conf_file:
                    conf_file.write(f"[general]\n")
                    conf_file.write(f"targetUri={self.url}\n")
                    log("INFO", f"Successfully created diag.conf", file_name="getdiaginfo")

                # Copy final_app_path to ds_app_path
                target_path = os.path.join(ds_app_path, 'getdiag_addon')
                if os.path.exists(target_path):
                    shutil.rmtree(target_path)  # Remove existing directory before copying
                shutil.copytree(final_app_path, target_path)
                log("INFO", f"Copied getdiag_addon to deployment-apps", file_name="getdiaginfo")

                # Return success result to JavaScript
                result = {"status": "success", "message": "Deployment server IP updated successfully."}
                yield result
            else:
                private_ip=get_private_ip()
                result = {"status": "success", "private_ip": private_ip}
                yield result

        except Exception as e:
            # Handle errors and return error result to JavaScript
            log("ERROR", f"Error during setupdiag execution: {str(e)}", file_name="getdiaginfo")
            result = {"status": "error", "message": f"An error occurred: {str(e)}"}
            yield result


dispatch(Getdiaginfo, sys.argv, sys.stdin, sys.stdout, __name__)
