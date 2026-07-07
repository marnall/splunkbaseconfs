import sys
import json
import re
import xml.etree.ElementTree as xml
import getpass
import logging
import datetime
import os
import csv
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import splunklib.client as client
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option
import bloodhound_utils
import splunk.Intersplunk

logging = bloodhound_utils.get_logger("bloodhound_inventory_job")
print("_time,name,level_name,message")


def parseArgs():
    if len(sys.argv) == 3:
        if (sys.argv[1][:5].lower() == 'host=' and sys.argv[2][:5].lower() == 'port='):
            host = sys.argv[1][5:]
            port = sys.argv[2][5:]
        elif (sys.argv[1][:5].lower() == 'port=' and sys.argv[2][:5].lower() == 'host='):
            host = sys.argv[2][5:]
            port = sys.argv[1][5:]
        else:
            sys.exit('Error: Incorrect arguments')
    else:
        sys.exit('Error: Incorrect number of arguments')
    return (host, port)


def getCurrentTimestamp():
    dt = datetime.datetime.utcnow()
    epoch = datetime.datetime.utcfromtimestamp(0)
    return math.floor((dt - epoch).total_seconds())


def runInventory():
    settings = dict()
    splunk.Intersplunk.readResults(settings=settings, has_header=True)
    sessionKey = settings['sessionKey']
    #APP = 'bloodhound'
    SPLUNK_HOME = os.environ.get("SPLUNK_HOME")

    logging.info("Script Information Logging")
    HOST, PORT = parseArgs()

    logging.info("Connecting to Splunk Server")
    service = client.connect(
        host=HOST,
        port=PORT,
        token=sessionKey,
        owner="-",
        app="-")

    logging.info("Retrieving KVStore Records")
    kvStoreData = service.kvstore['inventory_jobs'].data

    logging.info("Retrieving Previous Timestamp")
    try:
        previousTSList = kvStoreData.query_by_id('previousTS')
        previousTS = float(previousTSList['previousTS'])
    except:
        previousTS = 0
    logging.info("previousTS: {}".format(str(previousTS)))

    currentTS = getCurrentTimestamp()
    logging.info("currentTS: {}".format(str(currentTS)))

    jobs = []
    # count=0
    folderpath = SPLUNK_HOME + '/var/run/splunk/dispatch'
    logging.info("Processing Job Files from {}".format(folderpath))
    folders = next(os.walk(folderpath))[1]
    for folder in folders:
        full_path = os.path.join(folderpath, folder)

        try:
            status_path = os.path.join(full_path, 'status.csv')
            status_dict = next(csv.DictReader(open(status_path, 'r')))

            job_ts = int(status_dict['start']) + float(status_dict['run_time'])

            if job_ts >= previousTS and job_ts < currentTS and status_dict['state'] == 'DONE':
                iJob = {}

                meta_path = os.path.join(full_path, 'metadata.csv')
                meta_dict = next(csv.DictReader(open(meta_path, 'r')))

                try:
                    try:
                        info_path = os.path.join(full_path, 'info.csv')
                        info_dict = next(csv.DictReader(open(info_path, 'r')))
                        iJob['sid'] = info_dict['_sid']
                        iJob['label'] = info_dict['label']
                        iJob['timestamp'] = info_dict["_timestamp"]
                    except:
                        iJob['sid'] = folder

                    try:
                        request_path = os.path.join(full_path, 'request.csv')
                        request_dict = next(
                            csv.DictReader(open(request_path, 'r')))
                        iJob['ui_dispatch_app'] = request_dict['ui_dispatch_app']

                    except:
                        pass

                    iJob['dispatchState'] = status_dict['state']
                    iJob['diskUsage'] = status_dict['disk_usage']
                    iJob['runDuration'] = status_dict['run_time']
                    iJob['eventCount'] = status_dict['count']
                    iJob['scanCount'] = status_dict['scan_count']
                    iJob['search'] = status_dict['search']
                    iJob['ttl'] = meta_dict['ttl']
                    iJob['app'] = meta_dict['app']
                    iJob['owner'] = meta_dict['owner']
                    jobs.append(iJob)

                except Exception as e:
                    logging.info("Error when parsing job, {0}: {1}".format(
                        info_dict['_sid'], str(e)))
                    logging.error(
                        ' Error when parsing job, ' + info_dict['_sid'] + ' : ' + str(e))

        except Exception as e:
            logging.info("No status.csv found for job, {0}: {1}".format(
                folder, str(e)))
            logging.info(
                ' No status.csv found for job, ' + str(folder) + ' : ' + str(e))

    logging.info("Saving Latest Timestamp")
    if previousTS == 0:
        kvStoreData.insert(json.dumps(
            {'_key': 'previousTS', 'previousTS': currentTS}))
    else:
        kvStoreData.update('previousTS', json.dumps({'previousTS': currentTS}))

    logging.info("Adding Jobs to KVStore")
    for job in jobs:
        kvStoreData.insert(json.dumps(job))

    logging.info("Number of Jobs Added: {}".format(len(jobs)))

    logging.info(
        ' Script ran successfully and inventory_jobs collection was updated')
    logging.info("Script Ran Successfully")


try:
    runInventory()
except SystemExit as Argument:
    logging.info(Argument)
    logging.error(' ' + str(Argument))
except Exception as Argument:
    logging.info(Argument)
    logging.error(' ' + str(Argument))
