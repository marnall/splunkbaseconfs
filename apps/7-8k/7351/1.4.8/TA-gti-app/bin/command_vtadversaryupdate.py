"""vtadversaryupdate command implementation."""

import asyncio
import sys
from gti.core import cache
from gti.core import utils
from gti.core import environment
from gti.core import mappings
from gti.core import log
from gti.core import constants
import import_declare_test  # pylint: disable=unused-import
# pylint: disable=import-error
from splunklib.searchcommands import Configuration
from splunklib.searchcommands import dispatch
from splunklib.searchcommands import GeneratingCommand
import vt
# pylint: enable=import-error

logger = log.get_logger(__file__)


@Configuration(type='reporting')
class VTAdversaryCommand(GeneratingCommand):
  """Update Adversary Lookup Tables."""

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    self.vt_env = None
    self.from_cache = None
    self.attribution_cache = None

  def generate(self):
    self.vt_env = environment.VirusTotalEnv(
        self._metadata.searchinfo.session_key
    )
    added_objects = []

    try:
      self.vt_env.api_key
    except vt.APIError as ex:
      self.write_error(f'{ex.code}: {ex.message}')
      logger.error('%s: %s', ex.code, ex.message)
      return

    try:
      for cache_updated in constants.ADVERSARY_FIELDS_MAPPING:
        attribution_added = asyncio.get_event_loop().run_until_complete(
            self.update_attribution_cache(cache_updated)
        )
        added_objects.extend(attribution_added)
        logger.debug(
            '%s lookup table updated successfully.',
            cache_updated.replace('_', ' ').capitalize(),
        )
    except Exception as ex:  # pylint: disable=broad-except
      self.write_error(f'Unexpected error: {ex}')
      logger.error('Unexpected error: %s', ex)

    yield from added_objects

    logger.info(
        'Command %s executed successfully.', constants.COMMAND_ADVERSARY_UPDATE
    )

    self.vt_env.client.close()

  async def update_attribution_cache(self, cache_updated):
    """
    Update the attribution cache to keep it synchronized with the IoC caches.

    Args:
    - cache_updated (str): Cache to be updated (collection or threat_actor)

    Returns:
    - returning_objects (list[dict]): List of modified objects
    """
    self.attribution_cache = cache.VtEnrichmentCache(
        constants.CACHES_MAPPING[cache_updated], self.vt_env.service
    )
    objects_expected = set()
    objects_existing = set()
    returning_objects = []
    id_last_seen = {}

    # Get expected object ids from IoC lookup tables
    for cache_reviewed in constants.IOCS:
      self.from_cache = cache.VtEnrichmentCache(
          constants.CACHES_MAPPING[cache_reviewed], self.vt_env.service
      )
      objects = self.from_cache.get_objects(
          {constants.FIELD_DETECTIONS: {'$gt': 0}}
      )
      if objects:
        for object_ in objects:
          if constants.ADVERSARY_FIELDS_MAPPING[cache_updated] in object_:
            for id_ in object_[
                constants.ADVERSARY_FIELDS_MAPPING[cache_updated]
            ].split(', '):
              if id_:
                objects_expected.add(id_)
                if id_ not in id_last_seen:
                  id_last_seen[id_] = object_[cache.CACHE_LAST_SEEN]
                elif object_[cache.CACHE_LAST_SEEN] > id_last_seen[id_]:
                  id_last_seen[id_] = object_[cache.CACHE_LAST_SEEN]

    # Get existing object ids from attribution lookup table
    objects = self.attribution_cache.get_objects({})
    if objects:
      for object_ in objects:
        objects_existing.add(object_['_key'])

    # Delete from attribution lookup table the ids not expected and existing
    for id_ in objects_existing.difference(objects_expected):
      try:
        self.attribution_cache.delete_object({'_key': id_})
        returning_objects.append(
            {'Type': cache_updated, 'ID': id_, 'Change': 'Deleted'}
        )
      except Exception as ex:  # pylint: disable=broad-except
        logger.error('Error when deleting %s from adversary cache: %s', id_, ex)

    # Add to attribution lookup table the ids expected and not existing
    try:
      vt_objects_added = await asyncio.gather(
          *[
              self.add_vt_object(id_, cache_updated)
              for id_ in objects_expected.difference(objects_existing)
          ]
      )
      returning_objects.extend(vt_objects_added)
    except vt.APIError as ex:
      self.write_error(f'{ex.code}: {ex.message}')
      logger.error('%s: %s', ex.code, ex.message)
    except Exception as ex:  # pylint: disable=broad-except
      self.write_error(f'Unexpected error: {ex}')
      logger.error('Unexpected error: %s', ex)

    # Update LAST_SEEN for the rest of the attribution objects
    for id_ in objects_expected.intersection(objects_existing):
      splunk_object = self.attribution_cache.get_object(id_)
      if id_last_seen[id_] > splunk_object[cache.CACHE_LAST_SEEN]:
        self.attribution_cache.save_object(splunk_object)
        returning_objects.append(
            {'Type': cache_updated, 'ID': id_, 'Change': 'Updated'}
        )

    return returning_objects

  async def add_vt_object(self, id_, object_type):
    """
    Add an object from VT (if found) to cache.

    Args:
    - id_ (str): ID of the object
    - object_type (str): Type of object (collection or threat_actor)

    Returns:
    - object_added (dict): Object added
    """
    try:
      vt_data = await self.vt_env.client.get_data_async(
          constants.API_ENDPOINTS[object_type] + id_,
          params={'attributes': ','.join(self.get_attributes(object_type))},
      )
      splunk_object = self.vt_data_to_splunk_object(vt_data, object_type)
      self.attribution_cache.save_object(splunk_object)
      return {'Type': object_type, 'ID': id_, 'Change': 'Added'}
    except vt.APIError as ex:
      if ex.code in ('ForbiddenError', 'QuotaExceededError'):
        # If missing permissions or the quota is exceeded, stop execution
        raise ex
      else:
        self.write_error(
            f"Error in {object_type.replace('_', ' ').capitalize()} {id_}. "
            f'{ex.code}: {ex.message}'
        )
        logger.error(
            'Error in %s %s. %s: %s',
            object_type.replace('_', ' ').capitalize(),
            id_,
            ex.code,
            ex.message,
        )

  def vt_data_to_splunk_object(self, vt_data, object_type):
    """
    Response's data from `vt.get_data` to Splunk object.

    Args:
    - vt_data (dict): Response's data
    - object_type (str): Type of object (collection or threat_actor)

    Returns:
    - splunk_object (dict): Splunk object created
    """
    splunk_object = {'_key': vt_data['id'], constants.FIELD_ID: vt_data['id']}

    # Get fields for the current observable type
    fields = filter(
        lambda f: object_type in f['observable_types'], mappings.FIELDS
    )

    # Extract value from vt response and populate the splunk object
    for field in fields:
      value = utils.get_key(vt_data, field['response_field'])
      if value is not None:
        splunk_object[field['splunk_field']] = field['formatter'](value)
      else:
        splunk_object[field['splunk_field']] = ''

    return splunk_object

  def get_attributes(self, object_type):
    """
    Get attributes given an object type.

    Args:
    - object_type (str): Type of object (collection, threat_actor)

    Returns:
    - attributes (list[str]): Attributes to be asked to VT
    """
    attributes = []
    fields = filter(
        lambda f: object_type in f['observable_types'], mappings.FIELDS
    )
    for field in fields:
      path = field['response_field'].split('.')
      if path[0] == 'attributes':
        attributes.append(path[1])

    return attributes


dispatch(VTAdversaryCommand, sys.argv, sys.stdin, sys.stdout, __name__)
