"""
This controller provides helper methods to the front-end views that manage lookup files.
"""

import logging
import csv
import json
import time
import datetime
import math
import os
import threading
import shutil
import re
import urllib.parse
import signal

from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk import AuthorizationFailed, ResourceNotFound
from splunk.rest import simpleRequest

# The default of the csv module is 128KB; upping to 10MB. See SPL-12117 for
# the background on issues surrounding field sizes.
# (this method is new in python 2.5)
csv.field_size_limit(10485760)

def setup_logger(level):
    """
    Setup a logger for the REST handler
    """

    logger = logging.getLogger('splunk.appserver.lookup_editor.rest_handler')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)

    log_file_path = make_splunkhome_path(['var', 'log', 'splunk', 'lookup_editor_rest_handler.log'])
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

from lookup_editor import lookupfiles
from lookup_editor import LookupEditor
from lookup_editor import shortcuts
from lookup_editor.exceptions import LookupAlreadyExistException, LookupFileTooBigException, PermissionDeniedException, LookupNameInvalidException, NoOwnerException
from lookup_editor import rest_handler
from lookup_editor.settings import NUMBER_VALIDATION_REGEX;

BACKUP_FILE = "backup_details_for_lookups"
class LookupEditorHandler(rest_handler.RESTHandler):
    """
    This is a REST handler that supports editing lookup files. All calls from the user-interface
    should pass through this handler.
    """

    def __init__(self, command_line, command_arg):
        super(LookupEditorHandler, self).__init__(command_line, command_arg, logger)

        self.lookup_editor = LookupEditor(logger)

    def get_lookup_info(self, request_info, lookup_file=None, namespace="lookup_editor", **kwargs):
        """
        Get information about a lookup file (owner, size, etc.)
        """

        return {
            'payload': str(lookup_file), # Payload of the request.
            'status': 200 # HTTP status code
        }
        
    def format_bytes(self, bytes, decimals = 2):
        bytes_int = int(bytes)
        if bytes_int <= 0:
            return "0 Bytes"

        k = 1024
        dm = 0 if decimals < 0 else decimals
        sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
        i = int(math.floor(math.log(bytes_int, k)))
        p = math.pow(k, i)
        s = round(bytes_int / p, dm)
        return "%s %s" % (s, sizes[i])

    def post_lookup_backups(self, request_info, lookup_file=None, namespace=None, owner=None,
                           **kwargs):
        """
        Get a list of the lookup file backups rendered as JSON.
        """
        try:
            self.validate_current_loggedin_user(request_info,owner)

            backups = self.lookup_editor.get_backup_files(request_info.session_key, lookup_file,
                                                        namespace, owner)
            # Make the response
            backups_meta = []

            for backup in backups:
                try:
                    if backup["size"]>0:
                        backups_meta.append(
                            {
                                'time': backup["backup"],
                                'time_readable' : datetime.datetime.fromtimestamp(float(backup["backup"])).strftime('%Y-%m-%d %H:%M:%S'),
                                'size': backup["size"],
                                'size_readable': self.format_bytes(backup["size"], 2)
                            }
                        )
                except ValueError:
                    self.logger.warning("Backup file name is invalid, file_name=%s", backup)

            # Sort the list
            backups_meta = sorted(backups_meta, key=lambda x: float(x['time']), reverse=True)

            return self.render_json(backups_meta)
        
        except (AuthorizationFailed, PermissionDeniedException) as e:
            self.logger.warning("Access to lookup denied")
            return self.render_error_json("You do not have permission to perform this operation", 403)
        except ResourceNotFound:
            self.logger.exception('Unable to find the lookup')
            return self.render_error_json('Unable to find the lookup', 404)
        except:
            self.logger.exception('Lookup file could not be loaded')
            return self.render_error_json('Lookup file could not be loaded', 500)

    def get_lookup_backup_size(self, request_info, lookup_file=None, namespace=None, owner=None,
                           **kwargs):
        """
        Get a total backup size the lookup file.
        """

        backups = self.lookup_editor.get_backup_files(request_info.session_key, lookup_file,
                                                      namespace, owner)
        # Make the response
        total_backup_size = 0
        recent_backup=""
        backup_count = len(backups)

        if backups and backup_count > 0:
            recent_backup = backups[0]["backup"]
            for backup in backups:
                try: 
                    if backup["size"] >0:
                        total_backup_size += backup["size"]
                except ValueError:
                    self.logger.warning("Backup file name is invalid, file_name=%s", backup)
        return [total_backup_size, recent_backup, backup_count]
   
    def post_lookup_data(self, request_info, lookup_file=None, namespace="lookup_editor",
                            owner=None, header_only=False, version=None, lookup_type=None,
                            **kwargs):
        """
        Provides the contents of a lookup file as JSON.
        """
        self.logger.info("Retrieving lookup contents, namespace=%s, lookup=%s, type=%s, owner=%s,"
                         " version=%s", namespace, lookup_file, lookup_type, owner, version)

        if owner == None:
            return self.render_error_json("Unauthorized", 403)
        
        if version and (not re.search(NUMBER_VALIDATION_REGEX,version)):
            return self.render_error_json("Unauthorized", 403)
                
        owner = os.path.basename(owner)
        if lookup_type is None or len(lookup_type) == 0:
            lookup_type = "csv"
            self.logger.warning("No type for the lookup provided when attempting to load a lookup %s file, it will default to CSV",lookup_file)

        if header_only in ["1", "true", 1, True]:
            header_only = True
        else:
            header_only = False

        try:
            if lookup_type == "csv":
                self.validate_current_loggedin_user(request_info,owner)

            # Load the KV store lookup
            if lookup_type == "kv":
                return self.render_json(self.lookup_editor.get_kv_lookup(request_info.session_key,
                                                                         lookup_file, namespace,
                                                                         owner))

            # Load the CSV lookup
            elif lookup_type == "csv":
                with self.lookup_editor.get_lookup(request_info.session_key, lookup_file, namespace,
                                                   owner, version=version,
                                                   throw_exception_if_too_big=True) as csv_file:
                    csv_reader = csv.reader([row.replace('\0',"") for row in csv_file.readlines()])

                    # Convert the content to JSON
                    lookup_contents = []

                    for row in csv_reader:
                        lookup_contents.append(row)

                        # If we are only loading the header, then stop here
                        if header_only:
                            break

                    return self.render_json(lookup_contents)

            else:
                self.logger.warning('Lookup file type is not recognized,' +
                                    ' lookup_type=' + lookup_type)
                return self.render_error_json('Lookup file type is not recognized', 421)

        except IOError:
            self.logger.warning("Unable to find the requested lookup")
            return self.render_error_json("Unable to find the lookup", 404)

        except (AuthorizationFailed, PermissionDeniedException) as e:
            self.logger.warning("Access to lookup denied")
            return self.render_error_json("You do not have permission to perform this operation", 403)

        except LookupFileTooBigException as e:
            self.logger.warning("Lookup file is too large to load")

            data = {
                'message': 'Lookup file is too large to load' +
                           '(file-size must be less than 10 MB to be edited)',
                'file_size' : e.file_size
            }

            return {
                'payload': json.dumps(data),
                'status': 420
            }
        except ResourceNotFound:
            self.logger.exception('Unable to find the lookup')
            return self.render_error_json('Unable to find the lookup', 404)
        except:
            self.logger.exception('Lookup file could not be loaded')
            return self.render_error_json('Lookup file could not be loaded', 500)


    # GET Call to the path  /lookup_edit/lookup_as_file is converted to POST call 
    def post_lookup_as_file(self, request_info, lookup_file=None, namespace="lookup_editor",
                           owner=None, lookup_type='csv', **kwargs):

        self.logger.info("Exporting lookup, namespace=%s, lookup=%s, type=%s, owner=%s", namespace,
                         lookup_file, lookup_type, owner)
        try:

            # If we are getting the CSV, then just pipe the file to the user
            if lookup_type == "csv":
                with self.lookup_editor.get_lookup(request_info.session_key, lookup_file, namespace, owner) as csv_file_handle:
                    csv_data = csv_file_handle.read()

            # If we are getting a KV store lookup, then convert it to a CSV file
            else:
                rows = self.lookup_editor.get_kv_lookup(request_info.session_key, lookup_file, namespace, owner)
                csv_data = shortcuts.convert_array_to_csv(rows)
            return {
                    'payload': csv_data, # Payload of the request.
                    'status': 200, # HTTP status code
                    'headers': {
                    'Content-Type': 'text/csv',
                    'Content-Disposition': lookup_file
                },

                }
        except (IOError, ResourceNotFound):
            return self.render_error_json("Unable to find the lookup", 404)

        except (AuthorizationFailed, PermissionDeniedException):
            return self.render_error_json("You do not have permission to perform this operation", 403)

        except Exception as e:
            self.logger.exception("Export lookup: details=%s", e)
            return self.render_error_json("Something went wrong!")
    
    
    def post_check_backup_availability (self, request_info, lookup_file=None,
                             namespace="lookup_editor", owner=None, **kwargs):
        splunk_home = os.getenv('SPLUNK_HOME')
        if not splunk_home:
            splunk_home='/'
            
        # Get disk space availability
        total, used, free = shutil.disk_usage(splunk_home)
        self.logger.info("Disk space total: %s, used: %s, Free: %s", total, used, free )
        if ((free / total) * 100) <= 10:
             return self.render_error_json("Unable to create backup. Available disk space is at 10%.", 507)
        else:
            lookup_info = self.lookup_editor.get_kv_lookup(request_info.session_key, BACKUP_FILE)

            for i in lookup_info:
                self.logger.info("from KV: %s %s %s", i[4], i[1], i[5])
                if i[4] == lookup_file and i[1] == namespace:
                    if i[3] is not None:
                        if i[2] is not None:
                            if i[2] > i[3]:
                                return self.render_error_json("Unable to create backup. You have reached the backup size limit of " + self.format_bytes(i[3], 0), 500)
            return {
                'payload': 'Backup space available', # Payload of the request.
                'status': 200 # HTTP status code
            }
        
    def validate_current_loggedin_user(self, request_info,owner=None):
        try:
            validUser = False

            if owner is None:
                owner = "nobody"
            else:
                cuser, ccontent = simpleRequest('/services/authentication/current-context?output_mode=json',
                                sessionKey= request_info.session_key,
                                    method='GET')
                context = json.loads(ccontent)
                currentcontext = context["entry"]
                [currentUser] = currentcontext 
                username = currentUser["content"]["username"]

                if(owner.lower() == "nobody"):
                    validUser = True
                if username==owner.lower():
                    validUser = True
                        
                if not validUser:
                    raise PermissionDeniedException("Unauthorized user")
                else:
                    return validUser
        except Exception as e:
            return self.render_error_json("Something went wrong!")

    def post_lookup_contents(self, request_info, contents=None, lookup_file=None,
                             namespace="lookup_editor", owner=None, backup=False, isNew=False, **kwargs):
        """
        Save the JSON contents to the lookup file.
        """

        """
        Return error if Existing Backup size exceeds The set Limit
        """

        try:
            self.validate_current_loggedin_user(request_info,owner)
            if '.csv' not in os.path.splitext(lookup_file)[1]:
                return {
                    'payload': "Invalid file", # Payload of the request.
                    'status': 403 # HTTP status code
                }
            
            if ':exsl' in contents:
                return {
                    'payload': "Invalid content", # Payload of the request.
                    'status': 403 # HTTP status code
                }

            if backup == "true":
                backup = True
                validate = self.post_check_backup_availability(request_info, lookup_file, namespace, owner)
                if validate['status'] != 200:
                    return validate
            else:
                backup = False

                # Backup the lookup file
            if backup :
                data = {
                    'lookup_file' : lookup_file,
                    'namespace' : namespace,
                    'owner' : owner,
                    'file_time' : time.time()
                }

                try:
                    _, _ = simpleRequest('/services/data/lookup_backup/backup',
                                        sessionKey=request_info.session_key,
                                        method='POST', postargs=data)
                except ResourceNotFound:
                    self.logger.info("Existing lookup could not be found for backup")

            file_name = self.lookup_editor.update(contents, lookup_file, namespace, owner,
                                                  request_info.session_key, request_info.user,isNew)

            # Everything worked, return accordingly
            return {
                'payload': str(file_name), # Payload of the request.
                'status': 200 # HTTP status code
            }

        except (AuthorizationFailed, PermissionDeniedException):
            return self.render_error_json("You do not have permission to perform this operation", 403)

        except LookupNameInvalidException:
            return self.render_error_json("Lookup name is invalid", 400)
        
        except LookupAlreadyExistException:
            return self.render_error_json("Lookup already exists", 409)
        
        except NoOwnerException:
            return self.render_error_json("Owner must be provided when updating a lookup file", 400)

        except Exception as e:
            self.logger.exception("Failed to save lookup: details=%s", e)
            return self.render_error_json("Unable to save the lookup")
        
    def post_kvlookup_contents(self, request_info, data=None,
                             namespace="lookup_editor", owner=None, **kwargs):
        """
        Save the JSON contents to the lookup file.
        """
        try:
            self.validate_current_loggedin_user(request_info,owner)
            postdata = {'name' : data}
            response, _data = simpleRequest('/servicesNS/'+owner+'/'+namespace+'/storage/collections/config',
                                        sessionKey=request_info.session_key,
                                        method='POST', postargs=postdata)

            # Everything worked, return accordingly
            self.logger.info("Saved KV lookup contents...%s",str(response))

            return {
                'payload': str(response), # Payload of the request.
                'status': 200 # HTTP status code
            }

        except (AuthorizationFailed, PermissionDeniedException, ResourceNotFound):
            return self.render_error_json("You do not have permission to perform this operation", 403)

        except LookupNameInvalidException:
            return self.render_error_json("Lookup name is invalid", 400)

        except Exception as e:
            self.logger.exception("Failed to save lookup: details=%s", e)
            return self.render_error_json("Unable to save the lookup")

    def post_remove_all_lookup_backups(self, request_info, lookup_file=None, namespace=None, owner=None,
                                **kwargs):
        data = {
                    'lookup_file' : lookup_file,
                    'namespace' : namespace,
                    'owner' : owner,
                    'action':"deleteAll",
                    'backup' : None,
                }
        try:
                response, _data = simpleRequest('/services/data/lookup_backup/backup',
                                        sessionKey=request_info.session_key,
                                        method='POST', postargs=data)
                return {
                            'payload': _data.decode("utf8"), # Payload of the request.
                            'status': response.status # HTTP status code
                        }

        except ResourceNotFound:
                    self.logger.info("Existing lookup could not be found for backup")

    def post_remove_lookup_backup(self, request_info, lookup_file=None, namespace=None, backup=None, owner=None, **kwargs):
        data = {
                    'lookup_file' : lookup_file,
                    'namespace' : namespace,
                    'owner' : owner,
                    'action':"delete",
                    'backup' : backup,
                }
        try:
                response, _data = simpleRequest('/services/data/lookup_backup/backup',
                                        sessionKey=request_info.session_key,
                                        method='POST', postargs=data)
                return {
                            'payload': _data.decode("utf8"), # Payload of the request.
                            'status': response.status # HTTP status code
                        }

        except ResourceNotFound:
                    self.logger.info("Existing lookup could not be found for backup")
    
    def is_supported_lookup(self, lookup_name):
        if lookup_name.endswith(".default"):
            return False
        elif ".ds_store" in lookup_name.lower():
            return False
        elif lookup_name.endswith(".kmz"):
            return False
        else:
            return True

    def fetch_app_lists(self, request_info):
        url = 'apps/local?count=-1&output_mode=json'
        response, data = simpleRequest(url, method="GET", sessionKey=request_info.session_key)
        res = json.loads(data)

        app_list = []

        for app in res["entry"]:
            app_list.append({
                "name": app["name"],
                "label": app["content"]["label"]
            })

        return app_list
    
    def find_app_label_from_name(self, app_list, app_name):
        for app in app_list:
            if app["name"] == app_name:
                return app["label"]

    def run_lookup_metadata_query(self, request_info, lookup_file=None, namespace=None, owner=None,
                                **kwargs):

        def timeout_handler(signum, frame):
            raise TimeoutError("Process is taking way too long.")

        # Start an alarm of 15 minutes
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(900) # 900 seconds = 15 minutes

        """
        This code block will handle the operations for single lookup query
        """
        try:
            if lookup_file is not None:
                try:
                    backup_details = self.get_lookup_backup_size(request_info=request_info, lookup_file=lookup_file, namespace=namespace, owner=owner)
                    if backup_details is not None:
                        backup_size = backup_details[0]
                        backup_count = backup_details[2]

                        return {
                            'payload': {
                                'lookup_file': lookup_file,
                                'backup_count': backup_count,
                                'backup_size': backup_size,
                                'backup_size_readable': self.format_bytes(backup_size),
                            }, # Payload of the request.
                            'status': 200 # HTTP status code
                        }
                    else:
                        return {
                            'payload': {
                                'lookup_file': lookup_file,
                                'backup_count': 0,
                                'backup_size_readable': "0 MB",
                            }, # Payload of the request.
                            'status': 200 # HTTP status code
                        }
                except Exception as e:
                    self.logger.exception(e)
                    return {
                            'payload': {
                                'lookup_file': lookup_file,
                                'backup_count': 0,
                                'backup_size_readable': "0 MB",
                            }, # Payload of the request.
                            'status': 404 # HTTP status code
                    }

            """
            This code block will handle bulk operations to get all data with size.
            """

            url = '/servicesNS/-/-/data/lookup-table-files?count=-1&output_mode=json'
            _, data = simpleRequest(url, method="GET", sessionKey=request_info.session_key)
            res = json.loads(data)

            if 'entry' in res:
                result_count = len(res["entry"])
                if result_count > 0:
                    n_threads = 5
                    # Splitting the items into chunks equal to number of threads

                    array_chunk = []
                    for i in range(0, n_threads):
                        array_chunk.append(res["entry"][i::n_threads])
                    thread_list = []
                    all_data = []

                    for x in range(n_threads):
                        all_data.append([])

                    self.logger.info("---- Need data for ------ %s ---- Threads %s", result_count, n_threads)

                    for thr in range(n_threads):
                        thread = threading.Thread(target=self.calculate_things, args=(array_chunk[thr], request_info, all_data[thr]))
                        thread_list.append(thread)
                        thread_list[thr].start()

                    for thread in thread_list:
                        thread.join()

                    lookup_results = []
                    for result in all_data:
                        lookup_results.extend(result)

            return {
                'payload': lookup_results, # Payload of the request.
                'status': 200 # HTTP status code
            }

        except TimeoutError as e:

            payload = {
                "message": "Process timed out"
            }

            logger.error(e)
            return {
            'payload': payload, # Payload
            'status': 400 # HTTP status code
        }
        finally:
            signal.alarm(0)

    def get_lookup_metadata(self, request_info, lookup_file=None, namespace=None, owner=None,
                                **kwargs):
        return self.run_lookup_metadata_query(request_info, lookup_file, namespace, owner, **kwargs)

    def post_lookup_metadata(self, request_info, lookup_file=None, namespace=None, owner=None,
                                **kwargs):
        return self.run_lookup_metadata_query(request_info, lookup_file, namespace, owner, **kwargs)

    def calculate_things(self, res, request_info, chunk_result):
        self.logger.info("Calculating for %s", len(res))

        try:
            for i in range(len(res)):
                lookup_name = res[i]["name"]
                lookup_author = res[i]["author"]
                lookup_app = res[i]["acl"]["app"]
                lookup_owner = res[i]["acl"]["owner"]
                canWrite = res[i]["acl"]["can_write"]
                sharing = res[i]["acl"]["sharing"]
                updated = res[i]["updated"]
                url = res[i]["id"]
                removable = res[i]["acl"]["removable"]

                if res[i]["acl"]["sharing"] == 'global' or res[i]["acl"]["sharing"] == 'app':
                    endpoint_owner = 'nobody'
                else:
                    endpoint_owner = lookup_owner

                if self.is_supported_lookup(lookup_name=lookup_name):
                    backup_details = self.get_lookup_backup_size(request_info=request_info, lookup_file=lookup_name, namespace=lookup_app, owner=endpoint_owner)
                    

                    backup_size = backup_details[0]
                    recent_backup = backup_details[1]
                    backup_count = backup_details[2]

                    chunk_result.append({
                        'name': lookup_name,
                        'author': lookup_author,
                        'owner': lookup_owner,
                        'app': lookup_app,
                        'endpoint_owner': endpoint_owner,
                        'backup_size': backup_size,
                        'backup_size_readable': self.format_bytes(backup_size),
                        'recent_backup': recent_backup,
                        'backup_count': backup_count,
                        'canWrite': canWrite,
                        'sharing': sharing,
                        'updated': updated,
                        'url': url,
                        'removable': removable
                    })
                    
        except Exception as e:
            self.logger.exception(e)       

    def run_file_size_query(self, request_info, lookup_data=None, **kwargs): 
        if lookup_data is None:
            userEncoded = urllib.parse.quote(request_info.user)
            url = f'/servicesNS/{userEncoded}/-/data/lookup-table-files?count=-1&output_mode=json'
            response, data = simpleRequest(url, method="GET", sessionKey=request_info.session_key)
            res = json.loads(data)
        else:
            res = json.loads(lookup_data)
        lookup_list = []
        app_list = self.fetch_app_lists(request_info=request_info)

        if 'entry' in res:
            result_count = len(res["entry"])
            if result_count > 0:
                for i in range(result_count):
                    lookup_name = res["entry"][i]["name"]
                    lookup_author = res["entry"][i]["author"]
                    lookup_app = res["entry"][i]["acl"]["app"]
                    lookup_owner = res["entry"][i]["acl"]["owner"]
                    lookup_data = res["entry"][i]["content"]["eai:data"]
                    size = os.path.getsize(lookup_data)
                    date =  res["entry"][i]["updated"]
                    can_write = res["entry"][i]["acl"]["can_write"]
                    lookup_sharing = res["entry"][i]["acl"]["sharing"]
                    lookup_id = res["entry"][i]["id"]
                    removable = res["entry"][i]["acl"]["removable"]
                    self.logger.info("entry: %s", res["entry"][i])

                    if res["entry"][i]["acl"]["sharing"] == 'global' or res["entry"][i]["acl"]["sharing"] == 'app':
                        endpoint_owner = 'nobody'
                    else:
                        endpoint_owner = lookup_owner

                    if self.is_supported_lookup(lookup_name=lookup_name):
                        lookup_list.append({
                            'name': lookup_name,
                            'author': lookup_author,
                            'app': self.find_app_label_from_name(app_list=app_list, app_name=lookup_app),
                            'can_write': can_write,
                            'owner': lookup_owner,
                            'sharing': lookup_sharing,
                            'lookup_id': lookup_id,
                            'removable': removable,
                            'namespace': lookup_app,
                            'endpoint_owner': endpoint_owner,
                            'info': lookup_data,
                            'size': size,
                            'size_readable': self.format_bytes(size),
                            'date': date
                        })
        return {
            'payload': lookup_list, # Payload of the request.
            'status': 200 # HTTP status code
        }

    def get_file_size(self, request_info, lookup_data=None, **kwargs): 
        return self.run_file_size_query(request_info, lookup_data, **kwargs)

    def post_file_size(self, request_info, lookup_data=None, **kwargs): 
        return self.run_file_size_query(request_info, lookup_data, **kwargs)

    def get_daily_lookup_backup_size(self, request_info, lookup_file=None, namespace=None, owner=None,
                           **kwargs):
        """
        Get a total backup size the lookup file.
        """

        daily_backups = self.lookup_editor.get_daily_backup_files(request_info.session_key, lookup_file,
                                                      namespace, owner)
        self.logger.info("lookup name: %s", lookup_file)
        self.logger.info("daily backups: %s", daily_backups)
        # Make the response
        total_backup_size = 0
        backup_count = len(daily_backups)

        if daily_backups and backup_count > 0:
            for backup in daily_backups:
                try: 
                    if backup["size"] >0:
                        total_backup_size += backup["size"]

                except ValueError:
                    self.logger.warning("Backup file name is invalid, file_name=%s", backup)
        return total_backup_size

    def get_lookup_daily_data(self, request_info, **kwargs):

        url = '/servicesNS/-/-/data/lookup-table-files?count=-1&output_mode=json'
        response, data = simpleRequest(url, method="GET", sessionKey=request_info.session_key)
        res = json.loads(data)
        lookup_list = []
        
        if 'entry' in res:
            result_count = len(res["entry"])
            if result_count > 0:

                for i in range(result_count):
                    lookup_name = res["entry"][i]["name"]
                    lookup_author = res["entry"][i]["author"]
                    lookup_app = res["entry"][i]["acl"]["app"]
                    lookup_owner = res["entry"][i]["acl"]["owner"]

                    if res["entry"][i]["acl"]["sharing"] == 'global' or res["entry"][i]["acl"]["sharing"] == 'app':
                        endpoint_owner = 'nobody'
                    else:
                        endpoint_owner = lookup_owner

                    if self.is_supported_lookup(lookup_name=lookup_name):
                        daily_backup = self.get_daily_lookup_backup_size(request_info=request_info, lookup_file=lookup_name, namespace=lookup_app, owner=endpoint_owner)
                        lookup_list.append({
                            'name': lookup_name,
                            'author': lookup_author,
                            'owner': lookup_owner,
                            'app': lookup_app,
                            'endpoint_owner': endpoint_owner,
                            'daily_backup': daily_backup,
                            'backup_size_readable': self.format_bytes(daily_backup),
                       
                        })
        return {
            'payload': lookup_list, # Payload of the request.
            'status': 200 # HTTP status code
        }
