import csv
import logging
import os
import sys

import splunk.appserver.mrsparkle.lib.util as app_util
import splunk.search
from six import text_type, PY3

def getOrder(keys, csvHeaders):
    order = []
    for key in keys:
        for i, header in enumerate(csvHeaders):
            if key == header.strip():
                order.append(i)

    return order


def get_hosts_in_lookup_file(file):

    # Opening in different modes to handle incorrect parsing issue on windows
    if PY3:
        csvfile = open(file, 'rt', newline='')
    else:
        csvfile = open(file, 'rb')
    reader = csv.reader(csvfile)
    csvdata = [row for row in reader]

    csvfile.close()

    order = getOrder(['unix_category', 'unix_group', 'host'], csvdata[0])
    old_hosts = dict()
    for row in csvdata[1:]:
        if len(row) == 3:
            if row[order[2]] in old_hosts:
                old_hosts[row[order[2]]].append([row[order[0]], row[order[1]]])
            else:
                old_hosts[row[order[2]]] = [[row[order[0]], row[order[1]]]]
    return old_hosts


def get_hosts():
    token = sys.stdin.readlines()[0]
    token = token.strip()
    job = splunk.search.dispatch('| metadata type=hosts `metadata_index`',
                                 namespace='splunk_app_for_nix',
                                 earliestTime='-7d', sessionKey=token)
    splunk.search.waitForJob(job)
    return [text_type(item['host']) for item in job.results]


def setup_logger():
    LOG_FILENAME = app_util.make_splunkhome_path(['var', 'log',
                                'splunk', 'unix_installer.log'])
    logger = logging.getLogger('unix_installer')
    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler(LOG_FILENAME,
                                                   maxBytes=1024000,
                                                   backupCount=5)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger


if __name__ == '__main__':

    logger = setup_logger()
    logger.info('Started updating hosts lookup file for app-unix')
    lookup_csv = os.path.join(app_util.get_apps_dir(), 'splunk_app_for_nix', 'lookups',
                              'dropdowns.csv')

    filtered_csv_data = []

    if os.path.isfile(lookup_csv):
        hosts = get_hosts()
        old_hosts = get_hosts_in_lookup_file(lookup_csv)

        # To store the count of hosts that are active
        active_hosts = 0
        for host in hosts:
            if host in old_hosts:
                active_hosts = active_hosts + 1
                for host_info in old_hosts[host]:
                    category = host_info[0]
                    group = host_info[1]
                    filtered_csv_data.append([category, group, host])
        
        # Considered "*" as a host in the log
        logger.info(
            'Keeping %d items in the old host lookup file. '
            'Removing %d hosts that are inactive for the last 7 days' %
            (len(filtered_csv_data) + 1,
             len(old_hosts) - active_hosts - 1))

    else:
        logger.info(
            'No existing csv found, creating empty'
            ' csv with default category and group')

    filtered_csv_data.insert(0, ['all_hosts', 'default', '*'])
    filtered_csv_data.insert(0, ['unix_category', 'unix_group', 'host'])

    # Opening in different modes to handle incorrect parsing issue on windows
    if PY3:
        csvfile = open(lookup_csv, 'wt', newline='')
    else:
        csvfile = open(lookup_csv, 'wb')

    writer = csv.writer(csvfile)
    writer.writerows(filtered_csv_data)
    
    csvfile.close()

    logger.info('Finished updating hosts lookup file for app-unix')
