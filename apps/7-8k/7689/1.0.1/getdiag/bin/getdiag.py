import os
import base64
import json
from splunk.clilib.bundle_paths import make_splunkhome_path
import splunk.appserver.mrsparkle.lib.util as splunk_lib_util
from splunk.persistconn.application import PersistentServerConnectionApplication
from utils import log  # Import the log function

class GetDiag(PersistentServerConnectionApplication):  # Change class name from HelloWorld to GetDiag
    def __init__(self, _command_line, _command_arg):
        super(GetDiag, self).__init__()
        log('INFO', 'GetDiag application has started.', file_name="getdiag")  # Update log message

    def handle(self, in_string):
        try:
            # Parse incoming request
            log('INFO', 'Processing request...', file_name="getdiag")
            request_info = json.loads(in_string)
            query_params = request_info.get("query", [])
            payload_data = request_info.get("payload")

            # Initialize parameters
            filename = None
            chunk_number = None
            total_chunks = None
            final_check = False

            # Parse query parameters
            for param in query_params:
                if param[0] == "filename":
                    filename = param[1]
                elif param[0] == "chunk_number":
                    chunk_number = int(param[1])
                elif param[0] == "total_chunks":
                    total_chunks = int(param[1])
                elif param[0] == "final_check":
                    final_check = param[1].lower() == "true"

            log('INFO', f'Received parameters: filename={filename}, chunk_number={chunk_number}, total_chunks={total_chunks}, final_check={final_check}', file_name="getdiag")

            # Perform final check if requested
            if final_check:
                log('INFO', f'Final check for file: {filename}...', file_name="getdiag")
                return self.perform_final_check(filename, total_chunks)

            # Validate parameters for regular chunk handling
            if not filename or chunk_number is None or total_chunks is None:
                log('ERROR', 'Required parameters are missing. Cannot process the request.', file_name="getdiag")
                return {'payload': {"error": "Missing parameters."}, 'status': 400}

            # Decode and append the current chunk to the temp file
            binary_data = base64.b64decode(payload_data)
            temp_file_path = self.append_chunk_to_temp_file(filename, binary_data)

            # Confirm receipt of chunk
            log('INFO', f'Chunk {chunk_number} has been received and saved to temporary file: {temp_file_path}.', file_name="getdiag")
            return {'payload': {"text": f"Chunk {chunk_number} received successfully."}, 'status': 202}

        except Exception as e:
            log('ERROR', f'An error occurred while processing the request: {str(e)}', file_name="getdiag")
            return {'payload': {"error": str(e)}, 'status': 500}

    def append_chunk_to_temp_file(self, filename, binary_data):
        """
        Appends a single chunk of binary data to a temporary file.
        """
        log('INFO', f'Appending data to temporary file: {filename}.tmp', file_name="getdiag")
        diag_dir = self.prepare_diag_directory()
        temp_file_path = os.path.join(diag_dir, f"{filename}.tmp")

        try:
            with open(temp_file_path, 'ab') as temp_file:
                temp_file.write(binary_data)

            log('INFO', f'Chunk successfully appended to {temp_file_path}.', file_name="getdiag")
            return temp_file_path
        except Exception as e:
            log('ERROR', f'Failed to append chunk to temporary file: {str(e)}', file_name="getdiag")
            raise

    def perform_final_check(self, filename, total_chunks):
        """
        Only renames the temp file to the final name if all chunks are received.
        """
        try:
            log('INFO', f'Performing final check for file: {filename}, expected total chunks: {total_chunks}...', file_name="getdiag")
            diag_dir = self.prepare_diag_directory()
            temp_file_path = os.path.join(diag_dir, f"{filename}.tmp")

            # Ensure the temp file exists before renaming
            if not os.path.isfile(temp_file_path):
                log('ERROR', f'Temporary file {temp_file_path} not found. Cannot complete upload.', file_name="getdiag")
                return {'payload': {"error": f"Temp file '{temp_file_path}' not found."}, 'status': 400}

            # Rename the temp file to the final file (without .tmp)
            final_file_path = os.path.join(diag_dir, f"{filename}.tar.gz")
            os.rename(temp_file_path, final_file_path)

            log('INFO', f'File {filename} successfully reassembled and saved as {final_file_path}.', file_name="getdiag")
            return {'payload': {"text": "File uploaded and reassembled successfully!", "file_path": final_file_path}, 'status': 200}

        except Exception as e:
            log('ERROR', f'Error during final check and file renaming for {filename}: {str(e)}', file_name="getdiag")
            return {'payload': {"error": str(e)}, 'status': 500}

    def prepare_diag_directory(self):
        """
        Prepares the diagnostic directory if it doesn't exist.
        """
        APP_NAME = 'getdiag'  # Change the app name to 'getdiag'
        APP_PATH = splunk_lib_util.make_splunkhome_path(["etc", "apps", APP_NAME])
        diag_dir = os.path.join(APP_PATH, 'appserver', 'static', 'diag')
        os.makedirs(diag_dir, exist_ok=True)

        log('INFO', f'Diagnostic directory ready at: {diag_dir}', file_name="getdiag")
        return diag_dir
