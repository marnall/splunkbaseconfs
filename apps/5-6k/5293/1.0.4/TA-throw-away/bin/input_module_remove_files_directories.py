
# encoding = utf-8

import os
import sys
import time
from datetime import datetime
from pathlib import Path
import re
import shutil

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    #config the vars
    global_source = helper.get_input_type()
    global_source_type = helper.get_sourcetype()
    global_index = helper.get_output_index()
    global_pattern = re.compile(helper.get_arg('pattern'))
    matching_files = []
    
    #get directory content and pick only stuff that matches the provided pattern
    try:
        working_dir = os.listdir(helper.get_arg('working_directory'))
        matching_files = [ s for s in working_dir if global_pattern.match(s) ]
    except Exception as e:
        err = "Error during list dir. Check directory permissions or existence.\nException: "+str(e)
        helper.log_error(err)
        #ew.write_event(helper.new_event(source=global_source, index=global_index, sourcetype=global_source_type, data=err))
    
    #retention filter
    if(helper.get_arg('retention_policy')):
        matching_files2 = list(matching_files)
        try:
            minimum_age = int(helper.get_arg('retention_period'))
        except:
            minimum_age = 0
        
        try:
            if minimum_age > 0:
                for i in matching_files2:
                    path = helper.get_arg('working_directory')+i
                    target = int(time.time())-minimum_age
                    mtime = os.path.getmtime(path)
                    #the line below uses the splunk index bucket's naming convention
                    #and it picks the latest date from the name of the bucket
                    ntime = re.compile("[dr]b_(\d{10,11})_\d{10,11}_.*").search(i).group(1)
                    #helper.log_info("ntime: "+str(ntime)+" vs target:"+str(target))
                    
                    #remove filenames from the list if they are not old enough
                    if(helper.get_arg('timestamp_location')=="name"):
                        if int(ntime) > int(target):
                            matching_files.remove(i)
                    else:
                        if int(mtime) > int(target):
                            matching_files.remove(i)
                            #yes, i know both branches do the same, but maybe in the future this will not be the case..
                            
            else:
                data = "Retention period set to 0 or empty. Will remove all matching files..."
                ew.write_event(helper.new_event(source=global_source, index=global_index, sourcetype=global_source_type, data=data))
        except Exception as e:
            err = "Error during retention filter processing. Check pattern, retention period, file names, modified date. Exiting without removing files.\nException: "+str(e)
            helper.log_error(err)
            #ew.write_event(helper.new_event(source=global_source, index=global_index, sourcetype=global_source_type, data=err))
            sys.exit(0)
    
    #iterate over the matching items (files that are old enough)    
    try:
        for i in matching_files:
            path = helper.get_arg('working_directory')+i
            
            #calculate space in bytes saved
            directory = Path(path)
            free_mem = sum(f.stat().st_size for f in directory.glob('**/*') if f.is_file())
            
            #push starting event
            data = "Attempting to remove: "+path
            ew.write_event(helper.new_event(source=global_source, index=global_index, sourcetype=global_source_type, data=data))
            
            #remove file
            if(os.path.isfile(path)):
                os.remove(path)
            else:
                shutil.rmtree(path)
            
            #push ending event
            data = "Success for: "+path+"\nSpace recovered (bytes): "+str(free_mem)
            ew.write_event(helper.new_event(source=global_source, index=global_index, sourcetype=global_source_type, data=data))
    except Exception as e:
        err = "Error during removal. Check directory permissions or existence.\nException: "+str(e)
        helper.log_error(err)
        #ew.write_event(helper.new_event(source=global_source, index=global_index, sourcetype=global_source_type, data=err))