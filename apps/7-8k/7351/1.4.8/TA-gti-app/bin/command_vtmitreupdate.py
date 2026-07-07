"""vtmitreupdate command implementation."""

import asyncio
import sys
from gti.core import cache
from gti.core import log
from gti.core import mappings
from gti.core import environment
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
class VTMITRECommand(GeneratingCommand):
  """Update MITRE Lookup Table."""

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    self.vt_env = None
    self.file_cache = None
    self.mitre_cache = None
    self.techniques = {}

  def generate(self):
    self.vt_env = environment.VirusTotalEnv(
        self._metadata.searchinfo.session_key
    )
    self.file_cache = cache.VtEnrichmentCache(
        constants.FILE_CACHE, self.vt_env.service
    )
    self.mitre_cache = cache.VtEnrichmentCache(
        constants.MITRE_CACHE, self.vt_env.service
    )
    self.subtechniques_mitre_cache = cache.VtEnrichmentCache(
        constants.MITRE_SUBTECHNIQUES_CACHE, self.vt_env.service
    )
    added_objects = []

    try:
      self.vt_env.api_key
    except vt.APIError as ex:
      self.write_error(f'{ex.code}: {ex.message}')
      logger.error('%s: %s', ex.code, ex.message)
      return

    try:
      added_objects = asyncio.get_event_loop().run_until_complete(
          self.update_mitre_cache()
      )
      logger.debug('MITRE ATT&CK lookup table updated successfully.')
    except Exception as ex:  # pylint: disable=broad-except
      self.write_error(f'Unexpected error: {ex}')
      logger.error('Unexpected error: %s', ex)

    for technique_id, technique in self.techniques.items():
      technique_name = technique['name']
      link = technique['link']
      try:
        technique_object = {
            '_key': technique_id,
            'technique_id': technique_id,
            'technique_name': technique_name,
            'link': link,
        }
        self.subtechniques_mitre_cache.save_object(technique_object)
      except Exception as ex:  # pylint: disable=broad-except
        self.write_error(
            'Error when saving MITRE technique'
            f'{technique_id} ({technique_name}) in KVStore.'
        )
        logger.error(
            'Error when saving MITRE technique %s (%s) in KVStore.',
            technique_id,
            technique_name,
        )

    yield from added_objects

    logger.info(
        'Command %s executed successfully.', constants.COMMAND_MITRE_UPDATE
    )

    self.vt_env.client.close()

  async def update_mitre_cache(self):
    """
    Update the MITRE cache to keep it synchronized with the file cache.

    Returns:
    - returning_objects (list[dict]): List of modified objects
    """
    objects_expected = set()
    objects_existing = set()
    returning_objects = []

    # Get expected object ids from IoC lookup tables
    objects = self.file_cache.get_objects(
        {constants.FIELD_DETECTIONS: {'$gt': 0}}
    )
    if objects:
      for object_ in objects:
        objects_expected.add(object_['_key'])

    # Get existing object ids from attribution lookup table
    objects = self.mitre_cache.get_objects({})
    if objects:
      for object_ in objects:
        objects_existing.add(object_['_key'])

    # Delete from attribution lookup table the ids not expected and existing
    for id_ in objects_existing.difference(objects_expected):
      try:
        self.mitre_cache.delete_object({'_key': id_})
        returning_objects.append({'ID': id_, 'Change': 'Deleted'})
      except Exception as ex:  # pylint: disable=broad-except
        logger.error('Error when deleting %s from MITRE cache: %s', id_, ex)

    # Add to attribution lookup table the ids expected and not existing
    try:
      vt_objects_added = await asyncio.gather(
          *[
              self.add_vt_object(id_)
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

    return returning_objects

  async def add_vt_object(self, id_):
    """
    Add an object from VT (if found) to cache.

    Args:
    - id_ (str): ID of the object

    Returns:
    - object_added (dict): Object added
    """
    try:
      vt_data = await self.vt_env.client.get_data_async(
          constants.API_ENDPOINTS[constants.MITRE_TREE]
          + id_
          + '/behaviour_mitre_trees'
      )
      splunk_object = self.vt_data_to_splunk_object(vt_data, id_)
      self.mitre_cache.save_object(splunk_object)

      for tactics_dict in vt_data.values():
        for tactic in tactics_dict['tactics']:
          for technique in tactic['techniques']:
            self.techniques[technique['id']] = {
                'name': technique['name'],
                'link': technique['link'],
            }

      return {'ID': id_, 'Change': 'Added'}
    except vt.APIError as ex:
      if ex.code in ('ForbiddenError', 'QuotaExceededError'):
        # If missing permissions or the quota is exceeded, stop execution
        raise ex
      else:
        self.write_error(f'Error in File {id_}. {ex.code}: {ex.message}')
        logger.error('Error in File %s. %s: %s', id_, ex.code, ex.message)

  def vt_data_to_splunk_object(self, vt_data, id_):
    """
    Response's data from `vt.get_data` to Splunk object.

    Args:
    - vt_data (dict): Response's data
    - id_ (str): ID of the object

    Returns:
    - splunk_object (dict): Splunk object created
    """
    splunk_object = {'_key': id_, constants.FIELD_ID: id_}

    # Get fields for the current observable type
    fields = filter(
        lambda f: constants.MITRE_TREE in f['observable_types'], mappings.FIELDS
    )

    # Extract value from vt response and populate the splunk object
    for field in fields:
      if vt_data is not None:
        splunk_object[field['splunk_field']] = field['formatter'](vt_data)
      else:
        splunk_object[field['splunk_field']] = ''

    return splunk_object


dispatch(VTMITRECommand, sys.argv, sys.stdin, sys.stdout, __name__)
