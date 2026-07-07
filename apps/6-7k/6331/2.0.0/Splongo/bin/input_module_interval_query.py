
# encoding = utf-8

import os
import sys
import time
import datetime
import multiprocessing
import json
import pickle
import traceback
from helper_functions import check_missed_run, getDictValueFromPath, get_and_parse_events, load_params, write_execution_file, bin_folder, run_params, get_size

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    # run_params = load_params(helper)
    log_level = helper.get_log_level()
    run_params = helper.get_input_stanza()[helper.get_input_stanza_names()]
    helper.log_info(run_params)
    if bool(int(run_params['checkpointing'])) == True:
        check_missed_run(helper, run_params['name'])

    index = run_params['index']
    threadnum = 0
    processes = []

    try:
        multiprocessing.set_start_method("spawn")
        starttime = time.time()
        manager = multiprocessing.Manager()
        result = manager.list()
    except:
        help.log_error(traceback.format_exc())
        
    interval = int(run_params['interval'])
    cores = int(run_params['cores'])
    time_field = run_params['time_field']
    if 'additional_query' in run_params:
        additional_query = run_params['additional_query']
        helper.log_info('Creating queries with additional query criteria: {}'.additional_query)
        queries = get_queries(interval, cores, time_field, helper, additioinal_query=json.loads(additional_query))
    else:
        queries = get_queries(interval, cores, time_field, helper)
    for q in queries:
        helper.log_info('Starting thread #{} with query : {}'.format(threadnum, str(q)))
        p = multiprocessing.Process(target=get_and_parse_events, args=(q, threadnum, result, run_params, log_level))
        processes.append(p)
        p.start()
        threadnum+=1
    
    for p in processes:
        p.join()

    data_size=0
    for r in result:
        data_size+=get_size(r)
        try:
            host = source = None
            try:
                if run_params['host_field_path']:
                    host = run_params['host_field_path']
                if run_params['source_field_path']:
                    source = run_params['source_field_path']
            except KeyError:
                pass
            event = helper.new_event(json.dumps(r,default=str), host=host, index=index, source=source, sourcetype='splongo:collection')
            ew.write_event(event)
        except Exception as e:
            helper.log_error(e)
            raise e
    
    if bool(int(run_params['checkpointing'])) == True:
        write_execution_file(run_params, queries)

    # data_size=get_size(result)/1024
    # data_size=sys.getsizeof(result)
    helper.log_info('Completed in %ss. ingested total %d events with size: %s bytes' % ((time.time() - starttime), len(result), str(data_size)))

def get_queries(interval, cores, time_field, helper, additioinal_query={}):
    intervals=[]
    for i in range(0,cores+1):
        secs = (interval/cores)*i
        intervals.append(datetime.datetime.utcnow() - datetime.timedelta(seconds = secs))
    intervals.sort()
    queries = []
    for i in range(0, cores):
        try:
            starttime = intervals[i]
            endtime = intervals[i+1]
            query = {time_field : {'$gte' : starttime, '$lte' : endtime}}
            if additioinal_query:
                query.update(additioinal_query)
            queries.append(query)
        except IndexError as e:
            helper.log_debug(traceback.format_exc())
            helper.log_error(e)
            pass
        except Exception as e:
            helper.log_debug(traceback.format_exc())
            helper.log_error('Error occured in get_queries() : {}'.format(e))
            sys.exit(1)
    return queries
