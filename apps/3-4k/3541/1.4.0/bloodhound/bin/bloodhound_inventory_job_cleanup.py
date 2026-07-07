import sys
import json
import re
import xml.etree.ElementTree as xml
import getpass
import logging
import datetime
import os
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import splunklib.client as client
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option
import bloodhound_utils
import splunk.Intersplunk

logging = bloodhound_utils.get_logger("bloodhound_inventory_job_cleanup")
print("_time,name,level_name,message")


def parseArgs():
    if len(sys.argv) == 4:
        if (sys.argv[1][:5].lower() == 'host='):
            host = sys.argv[1][5:]
            if (sys.argv[2][:5].lower() == 'port=' and sys.argv[3][:5].lower() == 'time='):
                port = sys.argv[2][5:]
                time = sys.argv[3][5:]
            elif (sys.argv[2][:5].lower() == 'time=' and sys.argv[3][:5].lower() == 'port='):
                port = sys.argv[3][5:]
                time = sys.argv[2][5:]
            else:
                sys.exit('Error: Incorrect arguments')
        elif (sys.argv[2][:5].lower() == 'host='):
            host = sys.argv[2][5:]
            if (sys.argv[1][:5].lower() == 'port=' and sys.argv[3][:5].lower() == 'time='):
                port = sys.argv[1][5:]
                time = sys.argv[3][5:]
            elif (sys.argv[1][:5].lower() == 'time=' and sys.argv[3][:5].lower() == 'port='):
                port = sys.argv[3][5:]
                time = sys.argv[1][5:]
            else:
                sys.exit('Error: Incorrect arguments')
        elif (sys.argv[3][:5].lower() == 'host='):
            host = sys.argv[3][5:]
            if (sys.argv[1][:5].lower() == 'port=' and sys.argv[2][:5].lower() == 'time='):
                port = sys.argv[1][5:]
                time = sys.argv[2][5:]
            elif (sys.argv[1][:5].lower() == 'time=' and sys.argv[2][:5].lower() == 'port='):
                port = sys.argv[2][5:]
                time = sys.argv[1][5:]
            else:
                sys.exit('Error: Incorrect arguments')
        else:
            sys.exit('Error: Incorrect arguments')
    else:
        sys.exit('Error: Incorrect number of arguments')
    return (host, port, time)


def cleanupInventory():
    settings = dict()
    records = splunk.Intersplunk.readResults(
        settings=settings, has_header=True)
    sessionKey = settings['sessionKey']
    APP = "bloodhound"

    logging.info("Script Information Logging")
    HOST, PORT, TIME = parseArgs()

    logging.info("Connecting to Splunk Server")
    service = client.connect(
        host=HOST,
        port=PORT,
        token=sessionKey,
        owner="-",
        app="-")

    logging.info("Retrieving KVStore Records")
    kvstoredata = service.kvstore['inventory_jobs'].data

    today = datetime.datetime.now()

    logging.info("Deleting Old KVStore Records")
    count = 0
    kvstore_data_query = kvstoredata.query()

    for data in kvstore_data_query:
        if 'timestamp' in data:
            timestamp = datetime.datetime.fromtimestamp(
                float(data["timestamp"]))
            if (today - timestamp).days > int(TIME) or int(TIME) <= 0:
                count = count + 1
                kvstoredata.delete_by_id(data['_key'])
        elif 'time' in data:
            jobTime = data['time']
            try:
                timestamp = datetime.datetime.strptime(
                    jobTime, '%m-%d-%Y')
            except:
                timestamp = today
            if (today - timestamp).days > int(TIME) or int(TIME) <= 0:
                count = count + 1
                kvstoredata.delete_by_id(data['_key'])
        else:
            kvstoredata.delete_by_id(data['_key'])
            count = count + 1

    # if the source kvstore is > 10K rows, then we limit=0 doesn't always get you all the rows, it goes until some
    # unknown limit and then obtaining more involves extra queries, but we don't know the size of the kvstore/collection
    kvstore_length = len(kvstore_data_query)
    logging.debug("KV Store received {0} rows".format(kvstore_length))

    kvstore_limit = 10000
    if kvstore_length > kvstore_limit:
        url = "https://localhost:8089/services/server/introspection/kvstore/collectionstats?output_mode=json&f=data"
        res = requests.get(
            url, headers={'Authorization': 'Splunk ' + sessionKey}, verify=False)
        if (res.status_code != requests.codes.ok):
            logging.error("HTTP status code={0} on URL={1} with result text={3}".format(
                res.status_code, url, res.text))
        json_res = json.loads(res.text)
        if 'entry' in json_res and len(json_res['entry']) > 0:
            entry = json_res['entry'][0]
            if 'content' in entry and 'data' in entry['content']:
                json_data = entry['content']['data']
                for a_data in json_data:
                    start = a_data.find(APP + ".inventory_jobs")
                    if start != -1:
                        slice_start = a_data.find("count", start)
                        slice_end = a_data.find(",", slice_start + 9)
                        found_count = int(a_data[slice_start + 7:slice_end])
                        logging.info("kvstore has {0} total rows, received {1} rows from the first query with limit=0".format(
                            found_count, kvstore_length))
                        break

        # if we have not seen all the rows from the collection we have to keep querying
        if kvstore_length < found_count:
            skip_number = kvstore_length
            while skip_number < found_count:
                logging.info(
                    "kvstore exceeded the code-configured limit of {0}, running a query to remote kvstore and skipping {1} rows".format(kvstore_limit, skip_number))
                # we could loop just the query portion and do a large post at the end but tha might consume a lot of memory
                # so per-loop we submit to the destination kvstore and re-query the source if required
                # TODO repeated code below, could move this into a function
                kvstore_result = kvstoredata.query(limit=0, skip=skip_number)
                logging.debug("KV Store received {0} rows".format(
                    len(kvstore_result)))
                for data in kvstore_result:
                    if 'timestamp' in data:
                        timestamp = datetime.datetime.fromtimestamp(
                            float(data["timestamp"]))
                        if (today - timestamp).days > int(TIME) or int(TIME) <= 0:
                            count = count + 1
                            kvstoredata.delete_by_id(data['_key'])
                    elif 'time' in data:
                        try:
                            timestamp = datetime.datetime.strptime(
                                jobTime, '%m-%d-%Y')
                        except:
                            timestamp = today
                        if (today - timestamp).days > int(TIME) or int(TIME) <= 0:
                            count = count + 1
                            kvstoredata.delete_by_id(data['_key'])
                    else:
                        kvstoredata.delete_by_id(data['_key'])
                        count = count + 1
                skip_number = skip_number + len(kvstore_result)

    logging.info("Number of Jobs Deleted: {}".format(count))

    logging.info('Script ran successfully: jobs older than ' +
                 TIME + ' days were removed from inventory_jobs collection')


try:
    cleanupInventory()
except SystemExit as Argument:
    logging.info(Argument)
    logging.error(
        '' + str(Argument))
except Exception as Argument:
    logging.info(Argument)
    logging.error(
        "" + str(Argument))
