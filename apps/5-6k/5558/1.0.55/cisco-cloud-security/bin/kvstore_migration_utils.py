import functools
import json
from datetime import datetime as dt
import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))
from service.app_kvstore_service import KVStoreService
from logger import Logger

destinations = None

@functools.lru_cache(maxsize=2)
def migrate_destination_list_collection(session_token):
    global destinations
    if not destinations:
        destinations = KVStoreService('destinations', session_token)
    dest_info = json.loads(destinations.query_items('destinations', session_token))
    epoch = dt(1970, 1, 1)
    for res in dest_info:
        try:
            modified_time = res['modificationtime'].split('+')[0]
            res['modificationtime'] = (dt.strptime(modified_time, '%Y-%m-%dT%H:%M:%S') - epoch).total_seconds()
        except Exception as e:
            res['modificationtime'] = res['modificationtime']
        try:
            destinations.update_item_by_key('destinations', res['_key'],
                                                session_token,
                                                {
                                                    'name': res['name'],
                                                    'id': res['id'],
                                                    'comment': res['comment'],
                                                    'status': res['status'],
                                                    'action': res['action'],
                                                    'source':res['source'],
                                                    'modificationtime': str(res['modificationtime']),
                                                    'destinationListId': res['destinationListId'],
                                                    'destinationListName': res['destinationListName'],
                                                    'loggedinuser': res['loggedinuser'],
                                                    'orgId': res['orgId'] if 'orgId' in res else ''
                                                })
        except Exception as e:
            migrate_destination_list_collection(session_token)
    return 1
        