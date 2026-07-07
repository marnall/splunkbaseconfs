import sys
import os
import time
import logger_manager as log
import splunk.search as splunkSearch
from threading import Thread

app_name = __file__.split(os.sep)[-3]
logger = log.setup_logging('trustar_threat_intelligence')

## Get the checkpoint stored in the local directory of the addon.
def get_checkpoint(checkpoint_file_name):
    if os.path.exists(checkpoint_file_name):
        with open(checkpoint_file_name, "r") as checkpoint_file:
            checkpoint = checkpoint_file.read().strip()
        if checkpoint:
            logger.info("Got checkpoint " + checkpoint + " successfully.")
            return checkpoint
        else:
            logger.info("No checkpoint stored in checkpoint file.")
            return False
    else:
        logger.error("No checkpoint file found.")
        return False

## Save the current epoch time in the checkpoint file.
def set_checkpoint(checkpoint, checkpoint_file_name):
    try:
        local_dir = os.path.join(os.environ["SPLUNK_HOME"], "etc", "apps", app_name, "local")
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)
        with open(checkpoint_file_name, "w") as checkpoint_file:
            checkpoint_file.write(str(checkpoint))
        logger.info("Saved checkpoint " + str(checkpoint) + " to file " + checkpoint_file_name + " successfully.")
    except Exception as e:
        logger.exception("Failed to save checkpoint " + str(checkpoint) + " to file " + checkpoint_file_name + ". Error: %s" % str(e))

# Create search query based on the type of the indicator
def create_search_query(collection, end_time, start_time):
    search_query =   '| inputlookup trustar_all_indicators_cumulative_lookup where'
    if start_time:
        search_query += " _time>" + str(start_time)
    if end_time:
        search_query += " _time<=" + str(end_time)
    description = ' | eval description="TruSTAR Threats" | where [| inputlookup trustar_false_positive_indicators_cumulative_lookup | fields value | format | eval search= if(search=="NOT ()","1=1","NOT "+search) | return $search] '
    if collection == "ip_intel":
        search_query += ' type="IP" ' + description + ' | rename value as ip | table ip, description, weight | outputlookup local_ip_intel append=true'
    elif collection == "hash_file_intel":
        search_query += ' (type="MD5" OR type="SHA256" OR type="SHA1") ' + description + ' | rename value as file_hash | table file_hash, description, weight | outputlookup local_file_intel append=true'
    elif collection == "name_file_intel":
        search_query += ' type="SOFTWARE" ' + description + ' | rename value as file_name | table file_name, description, weight | outputlookup local_file_intel append=true'
    elif collection == "http_intel":
        search_query += ' type="URL" ' + description + ' | rename value as url | table url, description, weight | outputlookup local_http_intel append=true'
    elif collection == "registry_intel":
        search_query += ' type="REGISTRY_KEY" ' + description + ' | rename value as registry_path | table registry_path, description, weight | outputlookup local_registry_intel append=true'
    elif collection == "email_intel":
        search_query += ' type="EMAIL_ADDRESS" ' + description + ' | rename value as src_user | table src_user, description, weight | outputlookup local_email_intel append=true'
    else:
        return False
    return search_query

# Execute queries to store threats in Threat Intelligence collections
def execute_query(collection, session_key):
    file_name = "trustar_" + collection + "_checkpoint.txt"
    checkpoint_file_path = os.path.join(os.environ["SPLUNK_HOME"], "etc", "apps", app_name, "local", file_name)
    start_time = get_checkpoint(checkpoint_file_path)
    end_time = time.time()
    query = create_search_query(collection, end_time, start_time)
    if query:
        try:
            splunkSearch.searchAll(query, sessionKey=session_key, namespace=app_name, owner='nobody')
            # Save the endTime in the checkpoint file
            set_checkpoint(end_time, checkpoint_file_path)
        except Exception as e:
            logger.info("Failed to execute queries to store threats in Threat Intelligence collections. %s" % str(e))
    else:
        logger.info("No matching type found")

def main():
    session_key = sys.stdin.readline().strip()
    collections = ["ip_intel", "hash_file_intel", "name_file_intel", "http_intel", "registry_intel", "email_intel"]
    logger.info("Starting execution of the threads")
    
    # Create threads to execute queries based on the type of threat
    threads = []
    try:
        for collection in collections:
            thread = Thread(target=execute_query, args=(collection, session_key,))
            threads.append(thread)
            thread.start()

        logger.info("Completed execution of the threads")
    
    except Exception as e:
        logger.error("Failed to save threats in lookups. Error %s" % str(e))

if __name__ == '__main__':
    main()