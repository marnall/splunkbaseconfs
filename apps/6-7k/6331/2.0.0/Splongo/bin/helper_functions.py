import sys
import time
import datetime
import multiprocessing
import os
import inspect
from pymongo import MongoClient, uri_parser
import json
import pickle
import logging
import traceback
from pymongo.errors import ConnectionFailure,OperationFailure

######FIX LOGGING##############
from solnlib.log import Logs
Logs.set_context(namespace="splongo", root_logger_log_file="interval_query")
logger = logging.getLogger()
# logger.setLevel(logging.INFO)
###############################

mongo_timeouts=10000
run_params = {}
#Kinda hacky way to get the directory of this file
class DummyClass: pass
bin_folder = os.path.dirname(os.path.abspath(inspect.getsourcefile(DummyClass)))
#####

def write_execution_file(run_params, queries):
    time_field_path = run_params['time_field']
    job_name = run_params['name']
    execution_dict = {
        'run_params' : run_params,
        'interval' : int(run_params['interval']),
        'index' : run_params['index'],
        'execution_slot_start' : queries[0][time_field_path]['$gte'],
        'execution_slot_end' : queries[-1][time_field_path]['$lte'],
    }

    with open('{}/last_execution_{}.pkl'.format(bin_folder, job_name), 'wb') as execution_file:
        pickle.dump(execution_dict, execution_file)
    execution_file.close()
    

def get_and_parse_events(query, threadnum, result, run_params,log_level):
    logger.setLevel(log_level)
    logger.debug("Run parameters: {}".format(run_params))
    try:
        globals()['run_params'] = run_params
        keyword_filtering_enabled = run_params['keyword_filtering_enabled']
        tmp = query_mongo(query)
        logger.info('Query returned {} events for thread {}'.format(len(tmp), threadnum))
        if keyword_filtering_enabled:
            tmp = scrape_events(tmp)
        for t in tmp:
            result.append(t)
    except Exception as e:
        logger.debug(traceback.format_exc())
        logger.error(e)
        

def query_mongo(query):    
    connection_string = run_params['mongodb_url']
    collection_name = run_params['collection']
    parsed_uri = uri_parser.parse_uri(connection_string)
    cli = None
    if bool(int(run_params['use_credentials'])) == True:
        try:
            username = run_params['username']
            pwd = run_params['password']
            logger.debug("MongoDB connectionString: {}".format(connection_string))            
            cli = MongoClient(connection_string, username=username, password=pwd, connect=True, connectTimeoutMS=mongo_timeouts, socketTimeoutMS=mongo_timeouts, serverSelectionTimeoutMS=mongo_timeouts)
        except OperationFailure as e:
            logger.debug(traceback.format_exc())
            logger.error(e)           
        except ConnectionFailure as e:
            logger.debug(traceback.format_exc())
            logger.error(e)
    else:
        try:
            logger.debug("MongoDB connectionString: {}".format(connection_string))            
            cli = MongoClient(connection_string, connect=True, connectTimeoutMS=mongo_timeouts, socketTimeoutMS=mongo_timeouts, serverSelectionTimeoutMS=mongo_timeouts)
        except OperationFailure as e:
            logger.debug(traceback.format_exc())
            logger.error(e)          
        except ConnectionFailure as e:
            logger.debug(traceback.format_exc())
            logger.error(e)

    db = cli.get_default_database()
    selected_db = parsed_uri['database']
    if selected_db not in cli.database_names():
        logger.error('DB {} Specified in connection string does not exist. Exiting...'.format(selected_db))
        sys.exit(1)

    if collection_name not in db.collection_names():
        logger.error('Collection {} Specified in connection string does not exist. Exiting...'.format(selected_db))
        sys.exit(1)
    
    collection = db[collection_name]
    projection_fields = create_field_options()
    try:
        if projection_fields:
            result = list(collection.find(query, projection_fields))
        else:
            result = list(collection.find(query))
    except ConnectionFailure:
        logger.error(traceback.format_exc())
    return result

def create_field_options():
    try:
        if 'projected_fields' in run_params:
            supress_fields = int(run_params['project_fields_radio'])
            fields={}
            projected_fields = run_params['projected_fields']
            #trim list for whitespaces
            b = [x.strip() for x in projected_fields.split(',')]
            if supress_fields == 1:
                for f in projected_fields.split(','):
                    fields.update({f : 1})
            if supress_fields == 2:
                for s in projected_fields.split(','):
                    fields.update({s : 0})
            if supress_fields == 0:
                pass
            logger.info("Field Options result: {}".format(fields))
            return fields
        else:
            return {}    
    except Exception as e:
        logger.error('An error occured in creat_field_options(): {}'.format(e))
        logger.debug(traceback.format_exc())
        sys.exit(1)

def findall(v, k, p='',result={}):
    if type(v) == type({}):
        for k1 in v:
            if k1.lower() in k:
                res_key = '%s.%s' % (p,k1)
                result.update({res_key : v[k1]})
                p=''
            findall(v[k1], k, p='%s.%s' % (p,k1), result = result)
    filtered_dict={}
    for k,v in result.items():
        if k.startswith('.'):            
            filtered_dict.update({k[1::]:v})
        else:
            filtered_dict.update({k:v})
    return filtered_dict
    
def scrape_events(events):
    try:
        payload_field = run_params['payload_field']
        keywords = run_params['keywords'].split(',')
        keywords = [x.lower() for x in keywords]
        keywords = [x.strip() for x in keywords.split(',')]
        for index,e in enumerate(events):
            filtered_payload = findall(e, keywords,result={})
            e.pop(payload_field)
            e.update({'filtered_payload' : filtered_payload})
            events[index] = e
        return events
    except Exception:
        logger.debug(traceback.format_exc())
        logger.error(e)

def getDictValueFromPath(listKeys, jsonData):
    if isinstance(listKeys,str):
        return jsonData[listKeys]
    else:
        localData = jsonData.copy()
        for k in listKeys:
            try:
                localData = localData[k]
            except:
                return None
        return localData
        
def get_queries_for_reprocessing(cores):
    slices = get_execution_slices(int(cores))
    queries = []
    for s in slices:
        time_field = run_params['time_field']
        query = {time_field : {'$gte' : s['starttime'], '$lte' : s['endtime']}}
        s.update({'query' : query})
        queries.append(query)
    return queries

def get_execution_slices(amount):
    slices = []
    scheduled_runs = []
    #Unpack jobs
    pickle_location = '{}/scheduled_executions.pkl'.format(bin_folder)
    with open(pickle_location, 'rb') as f:
        try:
            while True:
                scheduled_runs.append(pickle.load(f))
        except EOFError:
            pass

    if len(scheduled_runs) <= amount:
        slices = scheduled_runs
        scheduled_runs = []
    else:
        slices = scheduled_runs[0:amount]
        #remove already picked slices
        del scheduled_runs[:amount]
    #recreate pickle file
    os.remove(pickle_location)        
    with open(pickle_location, 'wb') as f:
        for run in scheduled_runs:
            pickle.dump(run, f)
    return slices

def load_params(helper):
    global run_params
    run_params = helper.get_input_stanza()[helper.get_input_stanza_names()]
    return run_params

"""
Checks the timestamps of current and previous run. If there is a big difference in the timestamps, this means that there are missed executions.
Checks and writes them in a .pkl file, which will serve as a DB of small-chunk queries to be executed, which will re-ingest lost data.
"""
def check_missed_run(helper, job_name, buffer = 5):
    try:
        with open('{}\\last_execution_{}.pkl'.format(bin_folder,job_name), 'rb') as pkl:
            last_run = pickle.load(pkl)
    except:
        helper.log_info('Last execution file does not exist yet.')
        return None
    last_exec_time = last_run['execution_slot_end']
    now = datetime.datetime.now()
    delta_seconds = (now - last_exec_time).total_seconds()
    interval = last_run['interval']
    helper.log_info('last job stop time: {} current time: {}, delta : {}'.format(last_exec_time, now, delta_seconds))
    jobs = split_jobs_into_segments(last_exec_time, diff = delta_seconds, interval = interval)
    if delta_seconds > interval + buffer:
        with open('{}/scheduled_executions.pkl'.format(bin_folder), 'ab') as pkl:
            for job in jobs:
                execution_dict = {
                    'job_name' : job_name,
                    'run_params' : last_run['run_params'],
                    'interval' : interval,
                    'starttime' : job['starttime'],
                    'endtime' : job['endtime']
                }
                pickle.dump(execution_dict, pkl)


def split_jobs_into_segments(starttime, diff = 0, interval = 60, jobs = []):
    first_run = True
    while diff > interval:
        if first_run:
            first_run = False
            endtime = starttime + datetime.timedelta(0, interval)
            job = {'starttime' : starttime, 'endtime' : endtime }
        else:
            temp = endtime
            endtime = temp + datetime.timedelta(0, interval)
            job = {'starttime' : temp, 'endtime' : endtime }
        diff = diff - interval
        jobs.append(job)
    else:
        temp = endtime
        endtime = temp + datetime.timedelta(0, diff)
        job = {'starttime' : temp, 'endtime' : endtime }
        diff = diff - interval
        jobs.append(job)
        return jobs

def get_size(obj, seen=None):
    """Recursively finds size of objects"""
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    # Important mark as seen *before* entering recursion to gracefully handle
    # self-referential objects
    seen.add(obj_id)
    if isinstance(obj, dict):
        size += sum([get_size(v, seen) for v in obj.values()])
        size += sum([get_size(k, seen) for k in obj.keys()])
    elif hasattr(obj, '__dict__'):
        size += get_size(obj.__dict__, seen)
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
        size += sum([get_size(i, seen) for i in obj])
    return size