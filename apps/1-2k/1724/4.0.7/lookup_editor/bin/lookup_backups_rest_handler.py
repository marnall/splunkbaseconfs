"""
This controller provides helper methods to the front-end views that manage lookup files.
"""

import logging
import json
import csv
import time
import re

from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk import AuthorizationFailed, ResourceNotFound
from splunk.rest import simpleRequest

from lookup_editor import shortcuts

# The default of the csv module is 128KB; upping to 10MB. See SPL-12117 for
# the background on issues surrounding field sizes.
# (this method is new in python 2.5)
csv.field_size_limit(10485760)

def setup_logger(level):
    """
    Setup a logger for the REST handler
    """

    logger = logging.getLogger('splunk.appserver.lookup_backups.rest_handler')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)

    log_file_path = make_splunkhome_path(['var', 'log', 'splunk', 'lookup_backups_rest_handler.log'])
    file_handler = logging.handlers.RotatingFileHandler(log_file_path, maxBytes=25000000,
                                                        backupCount=5)

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p %z %Z')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger

logger = setup_logger(logging.DEBUG)

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lookup_editor import LookupEditor
from lookup_editor import rest_handler
from lookup_editor.settings import NUMBER_VALIDATION_REGEX

class LookupBackupsHandler(rest_handler.RESTHandler):
    """
    This is a REST handler that supports backing up lookup files.

    This is broken out as a separate handler so that this handler can be replayed on other search
    heads via the allowRestReplay setting in restmap.conf.
    """

    def __init__(self, command_line, command_arg):
        super(LookupBackupsHandler, self).__init__(command_line, command_arg, logger)

        self.lookup_editor = LookupEditor(logger)

    def post_backup(self, request_info, lookup_file=None, namespace="lookup_editor",
                    owner=None, file_time=None, action=None, backup=None, **kwargs):
        if action == None:
            """
            Make a backup of the given lookup file.
            """
            if owner == None:
                return self.render_error_json("Unauthorized", 403)
                
            validUser = False
            
            response, content = simpleRequest('/services/admin/users?output_mode=json',
                                sessionKey=request_info.session_key,
                                method='GET')
            
            if response.status == 200:
                # self.logger.info("List of users: %s", json.loads(content))
                res = json.loads(content)
                
                if(owner.lower() == "nobody"):
                    validUser = True
                    
                for i in res["entry"]:
                    if(owner.lower() == i["name"].lower()):
                        validUser = True
                        break
                    
            else:
                self.logger.info("Unauthorized")
                return self.render_error_json("Unauthorized", 403)
                
            if not validUser:
                return self.render_error_json("Unauthorized", 403)
            
            if not (file_time and re.search(NUMBER_VALIDATION_REGEX,file_time)):
                file_time = None

            try:
                # Determine the final path of the file
                resolved_file_path = self.lookup_editor.resolve_lookup_filename(lookup_file,
                                                                                namespace,
                                                                                owner,
                                                                                session_key=request_info.session_key,
                                                                                throw_not_found=True)

                # Backup the file passing the time so that the REST handler will use the same time for
                # all lookups even when the REST call is being replayed in an SHC cluster
                file_path = self.lookup_editor.backup_lookup_file(request_info.session_key,
                                                                lookup_file, namespace,
                                                                resolved_file_path, owner,
                                                                file_time)

                self.logger.info("Created a backup of a lookup file, file_path=%s", file_path)

                # Everything worked, return accordingly
                return {
                    'payload': str(file_path), # Payload of the request.
                    'status': 200 # HTTP status code
                }

            except ResourceNotFound:

                self.logger.warn("Unable to find the lookup to backup")

                return self.render_error_json("Unable to find the lookup to backup", 404)

            except Exception as e:

                self.logger.exception("Exception generated when attempting to backup a lookup file")
                return self.render_error_json("Unable to backup the lookup %s", str(e))
        else:
            return self.post_delete_backup(request_info, lookup_file, namespace, backup, owner, action)
        
    def post_delete_backup(self, request_info, lookup_file=None, namespace=None, backup=None, owner=None, action="delete", **kwargs):
        if action == "delete":
            try:
                # Check for necessary parameters
                if not lookup_file or not namespace or not owner or not backup:
                    self.logger.error("Missing required parameters: lookup_file=%s, namespace=%s, owner=%s, backup=%s", lookup_file, namespace, owner, backup)
                    return {
                        'payload': "Missing required parameters", # Payload of the request.
                        'status': 400 # HTTP status code: Bad Request
                    }

                # Escape the filename
                escaped_filename = shortcuts.escape_filename(lookup_file)

                # Get the backup directory
                backup_directory = self.lookup_editor.get_backup_directory(request_info.session_key, escaped_filename, namespace, owner)
                
                if backup_directory and backup and "/" not in backup:  # Validate backup path
                    backup_file_path = os.path.join(backup_directory, os.path.basename(backup))

                    # Try deleting the backup file
                    if os.path.exists(backup_file_path):
                        os.remove(backup_file_path)
                        self.logger.info("Deleted a backup of a lookup file, file_path=%s", backup_file_path)

                        return {
                            'payload': "Deleted backup",  # Payload of the request.
                            'status': 200  # HTTP status code
                        }
                    else:
                        self.logger.warning("Backup file not found: %s", backup_file_path)
                        return {
                            'payload': "Backup not found",  # Payload of the request.
                            'status': 404  # HTTP status code: Not Found
                        }
                else:
                    self.logger.warning("Invalid backup file or backup directory: %s, %s", backup, backup_directory)
                    return {
                        'payload': "Invalid backup file or backup directory",  # Payload of the request.
                        'status': 400  # HTTP status code: Bad Request
                    }

            except ResourceNotFound:
                self.logger.error("Resource not found during backup deletion")
                return {
                    'payload': "Backup not found",  # Payload of the request.
                    'status': 404  # HTTP status code: Not Found
                }

            except Exception as e:
                self.logger.exception("Error deleting backup: %s", str(e))
                return {
                    'payload': f"Backup not deleted: {str(e)}",  # Payload of the request.
                    'status': 500  # HTTP status code: Internal Server Error
                }

        else:
            # If action is not delete, invoke the method to delete all backups
            return self.post_delete_all_backup(request_info, lookup_file, namespace, owner)

    def post_delete_all_backup(self, request_info, lookup_file=None, namespace=None, owner=None, **kwargs):
        try:
            # Call the lookup editor to delete all backups
            deleted = self.lookup_editor.delete_lookup_backups(request_info.session_key, lookup_file, namespace, owner)
            
            if deleted:
                self.logger.info("Deleted all backups for lookup file: %s, namespace: %s, owner: %s", lookup_file, namespace, owner)
                return {
                    'payload': "Deleted all backups",  # Payload of the request.
                    'status': 200  # HTTP status code: OK
                }
            else:
                self.logger.warning("No backups found to delete for lookup file: %s, namespace: %s, owner: %s", lookup_file, namespace, owner)
                return {
                    'payload': "Backup not found",  # Payload of the request.
                    'status': 404  # HTTP status code: Not Found
                }
        except Exception as e:
            self.logger.exception("Error deleting all backups: %s", str(e))
            return {
                'payload': f"Error deleting all backups: {str(e)}",  # Payload of the request.
                'status': 500  # HTTP status code: Internal Server Error
            }
