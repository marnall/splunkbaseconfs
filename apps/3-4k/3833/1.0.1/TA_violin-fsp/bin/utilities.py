import os
import json
import logger_manager as log
import sys

#set up logging
logger = log.setup_logging('violin_fsp')

# Write meta info        
def _write_meta_info(data, filename, file_path=None):
    path = file_path if file_path!=None else sys.path[0]
    pos_file_path = os.path.join(path, filename)
    try:
        if not os.path.exists(file_path):
            os.makedirs(file_path)
        pos_file = open(pos_file_path, "w")
        pos_file.truncate()
        data = json.dumps(data)
        pos_file.write(data)
        pos_file.close()
    except Exception as e:
        logger.error("Violin FSP Error: Error writing certificate issuer info. %s" % str(e))
        raise
    
# Read meta info
def _read_meta_info(filename, file_path=None):
    path = file_path if file_path!=None else sys.path[0]
    pos_file_path = os.path.join(path, filename)    
    file_data = {}
    try:
        if os.path.exists(pos_file_path):
            pos_file = open(pos_file_path, "r")
            file_data = pos_file.read().strip()                
            file_data = json.loads(file_data)
            pos_file.close()
            return file_data
        else:
            return -1
    except Exception as e:
        logger.error("Violin FSP Error: Error reading last certificate issuer info. %s" % str(e))
        raise