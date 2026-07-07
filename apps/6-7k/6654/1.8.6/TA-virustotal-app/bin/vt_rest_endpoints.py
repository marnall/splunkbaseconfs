"""File for VT rest endpoints."""

# pylint: disable=wrong-import-position
import sys
import os
import json
import traceback

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..', 'lib')))
import import_declare_test  # pylint: disable=unused-import

import vt
from virustotal.core import log
from virustotal.core import environment
from virustotal.api import handlers

try:
  from splunk.persistconn.application import (
      PersistentServerConnectionApplication,
  )
except ModuleNotFoundError:
  # Running tests
  class PersistentServerConnectionApplication:
    pass


logger = log.get_logger(__file__)


def get_gti_collections(vt_env: environment.VirusTotalEnv, in_dict):
  """Returns a list of GTI collections based on a search query."""
  query_params = in_dict.get('query', [])
  search_term = ''
  for key, val in query_params:
    if key == 'search':
      search_term = val
      break

  items = []
  try:
    col_types = ['malware-family', 'threat-actor', 'campaign']
    types_query = ' OR '.join([f'collection_type:{x}' for x in col_types])
    filter_query = (
        f'origin:"Google Threat Intelligence" owner:Mandiant ({types_query})'
    )
    if search_term:
      filter_query = f'{filter_query} name_wildcard:"*{search_term}*"'

    params = {
        'limit': 20,
        'attributes': 'collection_type,name,alt_names',
        'filter': filter_query,
    }

    response = vt_env.client.get_data('/collections', params=params)

    for collection in response:
      try:
        collection_id = collection['id']
        collection_type = collection['attributes']['collection_type']
        collection_name = collection['attributes']['name']
        if collection_type == 'campaign':
          collection_name = collection['attributes']['alt_names'][0]

        items.append(
            {
                'id': collection_id,
                'name': collection_name,
                'type': collection_type,
            }
        )

      except Exception as e:
        logger.error('Unexpected error adding collection: %s', str(e))

    payload = {'items': items}
    status = 200

  except vt.APIError as e:
    logger.error('VT API Error getting collections: %s', e.code)
    # Return an empty list on error, but log the issue
    payload = {'items': [], 'error': f'API Error: {e.code}'}
    status = 500
  except Exception as e:
    logger.error('Unexpected error getting collections: %s', str(e))
    payload = {'items': [], 'error': 'An unexpected error occurred.'}
    status = 500

  return payload, status


def get_splunk_indexes(vt_env: environment.SplunkEnv, in_dict):  # pylint: disable=unused-argument
  """Returns a list of all splunk indexes."""
  try:
    indexes = [index.name for index in vt_env.service.indexes]
    return indexes, 200
  except Exception as e:
    logger.error('Error getting splunk indexes: %s', e)
    return {'error': 'Error getting splunk indexes'}, 500


class VtHandler(PersistentServerConnectionApplication):
  """Handler to get data from VT."""

  def __init__(self, command_line, command_arg):  # pylint: disable=unused-argument
    PersistentServerConnectionApplication.__init__(self)

  def handle(self, in_string):
    payload = {}
    status = 200

    rest_handlers = {
        'check': (handlers.get_user_quota_usage, environment.VirusTotalEnv),
        'privileges': (handlers.get_user_privileges, environment.VirusTotalEnv),
        'widget': (handlers.create_widget_url, environment.VirusTotalEnv),
        'get_user_quota_usage': (
            handlers.get_user_quota_usage,
            environment.VirusTotalEnv,
        ),
        'get_user_privileges': (
            handlers.get_user_privileges,
            environment.VirusTotalEnv,
        ),
        'create_widget_url': (
            handlers.create_widget_url,
            environment.VirusTotalEnv,
        ),
        'post_saved_search': (
            handlers.post_saved_search,
            environment.SplunkEnv,
        ),
        'delete_saved_search': (
            handlers.delete_saved_search,
            environment.SplunkEnv,
        ),
        'get_saved_search': (handlers.get_saved_search, environment.SplunkEnv),
        'get_saved_searches': (
            handlers.get_saved_searches,
            environment.SplunkEnv,
        ),
        'update_saved_search': (
            handlers.update_saved_search,
            environment.SplunkEnv,
        ),
        'migrate_saved_search': (
            handlers.migrate_saved_search,
            environment.SplunkEnv,
        ),
        'get_current_saved_search_version': (
            handlers.get_current_saved_search_version,
            None,
        ),
        'get_threat_hunt': (handlers.get_threat_hunt, environment.SplunkEnv),
        'get_threat_hunts': (handlers.get_threat_hunts, environment.SplunkEnv),
        'post_threat_hunt': (handlers.post_threat_hunt, environment.SplunkEnv),
        'delete_threat_hunt': (
            handlers.delete_threat_hunt,
            environment.SplunkEnv,
        ),
        'run_threat_hunt': (
            handlers.run_threat_hunt,
            environment.VirusTotalEnv,
        ),
        'get_threat_hunt_job': (
            handlers.get_threat_hunt_job,
            environment.SplunkEnv,
        ),
        'get_splunk_job': (
            handlers.get_splunk_job,
            environment.SplunkEnv,
        ),
        'get_threat_hunt_status': (
            handlers.get_threat_hunt_status,
            environment.SplunkEnv,
        ),
        'get_threat_hunt_jobs': (
            handlers.get_threat_hunt_jobs,
            environment.SplunkEnv,
        ),
        'get_gti_collections': (get_gti_collections, environment.VirusTotalEnv),
        'get_splunk_indexes': (get_splunk_indexes, environment.SplunkEnv),
    }

    try:
      in_dict = json.loads(in_string)
    except Exception:  # pylint: disable=broad-except
      return {
          'payload': {
              'links': {},
              'entry': [{'name': 'debug', 'content': 'Failed parsing request'}],
          },
          'status': 500,
      }

    try:
      endpoint_str = in_dict.get('path_info')
      endpoint_handler = rest_handlers.get(endpoint_str)
      vt_env = None
      rest_handler = None
      if endpoint_handler:
        rest_handler = endpoint_handler[0]
        if endpoint_handler[1]:
          vt_env = endpoint_handler[1](in_dict['session']['authtoken'])
          payload, status = rest_handler(vt_env, in_dict)
        else:
          payload, status = rest_handler()
        logger.info('Success -> Status: %s. Payload: %s', status, payload)
      else:
        payload, status = {'content': 'Handler not found'}, 404

      if isinstance(vt_env, environment.VirusTotalEnv):
        vt_env.client.close()

    except vt.APIError as err:
      payload, status = {'code': err.code, 'message': err.message}, 200
      logger.error('vt.APIError -> Status: %s. Payload: %s', status, payload)
    except Exception as err:  # pylint: disable=broad-except
      payload = {
          'content': 'Internal error in handling phase: '  # pylint: disable=consider-using-f-string
          r'%s\n%s' % (err, traceback.format_exc())
      }
      status = 500
      logger.error(
          'Unexpected error -> Status: %s. Payload: %s', status, payload
      )
    return {'payload': payload, 'status': status}
