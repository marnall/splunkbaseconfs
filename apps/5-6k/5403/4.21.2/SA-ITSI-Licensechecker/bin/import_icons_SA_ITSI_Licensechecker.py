'''
This script automatically collects icons from glasstable_icon_library.conf and imports them to the KV store icon collection.
It utilizes icon_collection endpoint from apiiconcollection.
Icons with conflicting names not imported.

@author lbudchenko
'''

from builtins import str
import sys
import splunk.rest as rest
import json
import logging
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path
from itsi_py3 import _
from ITOA.storage.itoa_storage import ITOAStorage

ICON_COLLECTION_ENDPOINT = 'services/%s/v1/icon_collection' % 'SA-ITSI-Licensechecker'

# initialize logging
sys.path.insert(0, make_splunkhome_path(['etc', 'apps', 'SA-ITSI-Licensechecker', 'lib', 'SA_ITSI_Licensechecker_app_common']))
from SA_ITOA_app_common.solnlib.server_info import ServerInfo
from solnlib import log
log.Logs.set_context(log_format='%(asctime)s %(levelname)s %(message)s')
logger = log.Logs().get_logger('gt_icon_collection')
logger.setLevel(logging.INFO)

def get_conf(session_key, conf_name, count=0, app='-'):
    '''
    Retrieves data from a conf file
    '''
    getargs = {'output_mode': 'json', 'count': count}
    path = rest.makeSplunkdUri() + 'servicesNS/nobody/' + app + '/configs/conf-' + conf_name
    response, content = rest.simpleRequest(
        path,
        method='GET',
        getargs=getargs,
        sessionKey=session_key,
        raiseAllErrors=False
    )
    if response.status != 200:
        logger.error('Failed to load config: %s.' % path)

    return {'response': response, 'content': content}

def conf_to_json(conf):
    '''
    Converts response object from conf request to json object formatted for icon_collection endpoint
    Skips duplicates.
    '''
    entries = conf['entry']
    iconsInfo = [entry['content'] for entry in entries]
    icons = []
    seen = []
    for iconInfo in iconsInfo:
        label = iconInfo['iconLabel']
        category = iconInfo['iconCategory']
        if (label,category) in seen:
            continue # skip duplicates
        icon = {
            'title': label,
            'category': category,
            'default_width': iconInfo['defaultWidth'],
            'default_height': iconInfo['defaultHeight'],
            'svg_path': iconInfo['svgPath']
        }
        icons.append(icon)
        seen.append((label,category))
    return icons

def get_all_icons_from_kvstore(session_key):
    '''
    Requests a list of icons from KV store to check for conflicts
    '''
    getargs = {'fields': 'title,category'}
    path = rest.makeSplunkdUri() + ICON_COLLECTION_ENDPOINT
    response, content = rest.simpleRequest(
        path,
        method='GET',
        getargs=getargs,
        sessionKey=session_key,
        raiseAllErrors=False
    )
    if response.status != 200:
        logger.error('Failed to load KV store: ' + str(response.status) + ' ' + str(content))
    return {'response': response, 'content': content}

def put_kvstore(session_key, payload):
    '''
    Saves new icons in KV store
    '''
    path = rest.makeSplunkdUri() + ICON_COLLECTION_ENDPOINT
    response, content = rest.simpleRequest(
        path,
        method='PUT',
        jsonargs=payload,
        sessionKey=session_key,
        raiseAllErrors=False
    )
    return {'response': response, 'content': content}


def run_script():
    session_key = sys.stdin.readline().strip()
    server_info = ServerInfo(session_key)

    # log the message for restartless upgrade testing which can be useful while debugging.
    logger.info('Restartless upgrade - Reloaded modular input '
                'script://$SPLUNK_HOME/etc/apps/SA-ITOA/bin/import_icons_SA_ITOA.py')

    if len(session_key) == 0:
       logger.error("Did not receive a session key from splunkd. " +
                    "Must enable passAuth in inputs.conf for this " +
                    "script to run.\n")
       exit(2)

    try:
        logger.info(f"Modular input running on instance: {server_info.server_name}")
        logger.info('Glass table icon importer has started.')
        response = get_conf(session_key, 'glasstable_icon_library')
        conf_icons = conf_to_json(json.loads(response['content']))
        kvstore = ITOAStorage()

        kvstore_output = []
        if kvstore.wait_for_storage_init(session_key):
            # KV store might be not available yet - get icons after storage init
            kvstore_output = get_all_icons_from_kvstore(session_key)
        else:
            logger.error('Error connecting to the KV store.')
            return

        kvstore_tuples = [(res['title'],res['category']) for res in json.loads(kvstore_output['content'])['result']]
        new_icons = []
        for icon in conf_icons:
            if (icon['title'],icon['category']) in kvstore_tuples:
                # skip icons already existing in KV store
                continue
            icon['immutable'] = 1 # mark icons that are being imported
            new_icons.append(icon)

        if len(new_icons) > 0:
            put_kvstore(session_key, json.dumps(new_icons))
            logger.info('Successfully imported %s icons to the KV store.' % str(len(new_icons)))

    except Exception as e:
        logger.error(str(e))

if __name__ == '__main__':
    run_script()

    sys.exit(0)
