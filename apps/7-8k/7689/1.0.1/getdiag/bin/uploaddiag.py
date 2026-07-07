import os
import json
from splunk.persistconn.application import PersistentServerConnectionApplication
from splunk.clilib.bundle_paths import make_splunkhome_path
import splunk.appserver.mrsparkle.lib.util as splunk_lib_util
import sys, os
sys.path.append(os.path.dirname(__file__))
from utils import log
import getdiag_import
import sys
import pexpect
import traceback

def run_diag(password, splunk_home, upload_file, case_number, upload_user, upload_description):
    command = f"{splunk_home}/bin/splunk diag --upload-file {upload_file} --case-number {case_number} --upload-user {upload_user}  --upload-description {upload_description}"

    if sys.platform.startswith("win"):
        # For Windows
        return "Not Supported on Windows based Deployment Server"
        # subprocess.run(["powershell", "-Command", f"$password = '{password}'"])
        # subprocess.run(command, shell=True)
    else:
        try:
            child = pexpect.spawn(command)
            child.expect("password:")
            child.sendline(password)
            child.expect(pexpect.EOF)
            output1=child.before.decode()
            log('INFO',"Output:", file_name="upload_diag")
            log('INFO',output1, file_name="upload_diag")
            if "success" in output1:
                return "True"
            else:
                return output1
            # print(child.before.decode())  # Decode the bytes to string

        except pexpect.exceptions.EOF:
            log('INFO',"Unexpected end of file. Command failed.", file_name="upload_diag")
            # print("Unexpected end of file. Command failed.")
            log('INFO',traceback.print_exc(), file_name="upload_diag")
            traceback.print_exc()  # Print full stack trace
            return "False"
        except pexpect.exceptions.TIMEOUT:
            log('INFO',"Timeout occurred. No password prompt received.", file_name="upload_diag")
            # print("Timeout occurred. No password prompt received.")
            # traceback.print_exc()  # Print full stack trace
            log('INFO',traceback.print_exc(), file_name="upload_diag")
            return "False"
        except Exception as e:
            log('INFO',f"An error occurred: {e}", file_name="upload_diag")
            # print(f"An error occurred: {e}")
            # traceback.print_exc()  # Print full stack trace
            log('INFO',traceback.print_exc(), file_name="upload_diag")
            return "False"
        return "True"


class UploadDiag(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(UploadDiag, self).__init__()
        log('INFO', 'UploadDiag endpoint initialized.', file_name="upload_diag")
        log('INFO', f'{sys.path}', file_name="upload_diag")

    def handle(self, in_string):
        try:
            request_info = json.loads(in_string)

            # Extract the payload (escaped JSON string)
            raw_payload = request_info.get("payload")
            if not raw_payload:
                raise ValueError("Missing payload in request.")

            # Decode the payload (from escaped JSON string to dictionary)
            try:
                payload = json.loads(raw_payload)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in payload: {str(e)}")

            # Extract parameters
            filename = payload.get("filename")
            case_number = str(payload.get("case_number"))
            upload_user = payload.get("upload_user")
            password = payload.get("password")
            upload_description = payload.get("upload_description", "Uploaded via custom endpoint.")

            splunk_home = os.environ.get("SPLUNK_HOME")        

            filepath = self.get_diag_file_path(filename)
            log('INFO', f"File path : {filepath}", file_name="upload_diag")

            log('INFO', f"run_diag()", file_name="upload_diag")
            response = run_diag(password, splunk_home, filepath, case_number, upload_user, upload_description)
            if response=="True":
                log('INFO', f"Success: {response}", file_name="upload_diag")
                return {'payload': {"Success": "File uploaded successfully."}, 'status': 200}
            else:
                log('Error', f"Error: {response}", file_name="upload_diag")
                return {'payload': response, 'status': 400}
        
        except Exception as e:
            log('ERROR', f"Error processing request: {str(e)}", file_name="upload_diag")
            return {'payload': {"error": str(e)}, 'status': 500}

    def get_diag_file_path(self, filename):
        """
        Get the full path of the diag file.
        """
        APP_NAME = 'getdiag'  # Replace with your app's actual name
        diag_dir = os.path.join(os.environ.get("SPLUNK_HOME"), "etc", "apps", APP_NAME, "appserver", "static", "diag")
        return os.path.join(diag_dir, filename)
