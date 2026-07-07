"""vt4splunk command implementation."""

import asyncio
import ipaddress
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
from splunklib.searchcommands import Option
from splunklib.searchcommands import StreamingCommand
from splunklib.searchcommands import validators
import vt
# pylint: enable=import-error

CACHES = {
    constants.FILE: constants.FILE_CACHE,
    constants.URL: constants.URL_CACHE,
    constants.IP: constants.IP_CACHE,
    constants.DOMAIN: constants.DOMAIN_CACHE,
}

logger = log.get_logger(__file__)


@Configuration(distributed=False)
class VirusTotalCommand(StreamingCommand):
  """Event enrichment via VirusTotal API v3."""

  hash = Option(
      doc="""
    **Syntax:** hash=<field>
    **Description:** Hash field name to lookup in Virustotal
    """,
      validate=validators.Fieldname(),
  )

  ip = Option(
      doc="""
    **Syntax:** ip=<field>
    **Description:** IP field name to lookup in Virustotal
    """,
      validate=validators.Fieldname(),
  )

  domain = Option(
      doc="""
    **Syntax:** domain=<field>
    **Description:** Domain field name to lookup in Virustotal
    """,
      validate=validators.Fieldname(),
  )

  url = Option(
      doc="""
    **Syntax:** url=<field>
    **Description:** URL field name to lookup in Virustotal
    """,
      validate=validators.Fieldname(),
  )

  nocache = Option(
      doc="""
    **Syntax:** nocache=true
    **Description:** Force to get the enrichment from the VT API
    """,
      validate=validators.Fieldname(),
  )

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    self.field_name = None
    self.field_type = None
    self.vt_env = None
    self.cache = None
    self.cache_ttl = 1
    self.skip_cache = False
    self.errors = set()

  def stream(self, records):
    for type_ in constants.IOCS:
      if hasattr(self, type_):
        try:
          self.field_name = getattr(self, type_)
        except Exception:  # pylint: disable=broad-except
          pass
        if self.field_name:
          self.field_type = type_
          break

    if not self.field_name or not self.field_type:
      return

    self.vt_env = environment.VirusTotalEnv(
        self._metadata.searchinfo.session_key
    )
    self.cache = cache.VtEnrichmentCache(
        CACHES[self.field_type], self.vt_env.service
    )
    self.cache_ttl = int(
        self.vt_env.get_config_value(
            constants.CORRELATION_SETTINGS_STANZA,
            constants.CONFIG_DATA_FRESHNESS,
            1,
        )
    )
    self.skip_cache = getattr(self, 'nocache', None) == 'true'

    try:
      self.vt_env.api_key
    except vt.APIError as ex:
      self.write_error(f'{ex.code}: {ex.message}')
      logger.error('%s: %s', ex.code, ex.message)
      return

    records_updated = asyncio.get_event_loop().run_until_complete(
        self.process_records(records)
    )

    for record in records_updated:
      try:
        if record['error'] is not None:
          if isinstance(record['error'], vt.APIError):
            code, msg = record['error'].code, record['error'].message
            code_msg = f'{code}: {msg}'
            logger.error(
                'Error when enriching %s %s. %s',
                self.field_type,
                record['record'][self.field_name],
                code_msg,
            )
            if code_msg not in self.errors:
              self.errors.add(code_msg)
              self.write_error(f'{code_msg}')
              logger.error('%s', code_msg)
          else:
            self.write_error(
                (
                    f'Unexpected error when enriching '
                    f'{self.field_type} '
                    f"{record['record'][self.field_name]}: "
                    f"{record['error']}"
                )
            )
            logger.error(
                '[LOG] Unexpected error when enriching %s %s: %s',
                self.field_type,
                record['record'][self.field_name],
                record['error'],
            )
        yield record['record']
      except Exception as ex:  # pylint: disable=broad-except
        # This should never happen
        self.write_error(f'Unexpected error: {ex}')
        logger.error('Unexpected error: %s', ex)

    logger.info(
        "Command '%s %s=%s nocache=%s' executed successfully.",
        constants.COMMAND_ENRICH_IOCS,
        self.field_type,
        self.field_name,
        str(self.skip_cache).lower(),
    )

    self.vt_env.client.close()

  async def process_record(self, index, record):
    """
    Process record asynchronously.

    Args:
    - index (int): Index of the record
    - record (dict): Record from Splunk

    Returns:
    - record_updated (dict): Dict with the updated record as 'record'
                             and the possible exception as 'error'
    """
    vt_fields = self.init_vt_fields()
    error = None
    try:
      if index % 1 == 0 and self.field_name in record:
        if record[self.field_name] and record[self.field_name] != '':
          ip_is_private = False
          if self.field_type == constants.IP:
            ip = record[self.field_name]
            try:
              ip_is_private = ipaddress.ip_address(ip).is_private
            except ValueError as ex:
              raise vt.APIError(
                  'InvalidArgumentError',
                  f'IP "{ip}" is not a valid IP address pattern',
              ) from ex
          if ip_is_private:
            vt_fields[constants.FIELD_INFO] = (
                'Skipping the enrichment since '
                'this IP address belongs to a '
                'private network range'
            )
          else:
            vt_fields = await self.get_enrichment_object(
                record[self.field_name]
            )
            logger.debug(
                '%s %s enriched successfully.',
                self.field_type.capitalize(),
                record[self.field_name],
            )
            vt_fields[constants.FIELD_INFO] = ''
    except vt.APIError as ex:
      code_msg = f'{ex.code}: {ex.message}'
      vt_fields[constants.FIELD_INFO] = code_msg
      if ex.code == 'NotFoundError':
        logger.info(
            '%s not found %s: %s',
            self.field_type,
            record[self.field_name],
            code_msg,
        )
      else:
        error = ex
        logger.error('process_record: %s', code_msg)
    except Exception as ex:  # pylint: disable=broad-except
      logger.error('process_record: %s', str(ex))
      vt_fields[constants.FIELD_INFO] = ''
      error = ex
    record.update(vt_fields)
    record_updated = {'record': record, 'error': error}
    return record_updated

  async def process_records(self, records):
    """
    Process records asynchronously. Exception in any coroutine will be returned
    as the rest of solutions.

    Args:
    - records (dict): Records from Splunk

    Returns:
    - records_updated (list[Future]): List of futures with the updated records
    """
    records_updated = await asyncio.gather(
        *[self.process_record(i, record) for i, record in enumerate(records)],
        return_exceptions=True,
    )
    return records_updated

  def init_vt_fields(self):
    """
    Initialize vt_fields with empty fields to allow vt4splunk to print all the
    fields of the enriched events.
    If the function is not used, the output will not show the enriched fields
    that don't appear in all the events.

    Returns:
    - vt_fields (dict[str, str]): vt_fields with the fields as keys and
    empty strings as values
    """
    vt_fields = {'_key': '', constants.FIELD_ID: '', constants.FIELD_FOUND: ''}
    fields = filter(
        lambda f: self.field_type in f['observable_types'], mappings.FIELDS
    )
    for field in fields:
      vt_fields[field['splunk_field']] = ''

    return vt_fields

  async def get_enrichment_object(self, id_):
    """
    Enrich object asynchronously.

    Args:
    - id (str): ID of the object to be enriched

    Returns:
    - splunk_object (dict): Enriched object
    """
    # Trasform url to id
    if self.field_type == constants.URL:
      id_ = vt.url_id(id_)

    # Final object to be merged into the original event
    splunk_object = {'_key': id_, constants.FIELD_ID: id_}

    # Get from cache
    cached_object = None
    refresh = False
    try:
      cached_object = self.cache.get_object(id_)
      if cached_object:
        splunk_object[cache.CACHE_FIRST_SEEN] = cached_object[
            cache.CACHE_FIRST_SEEN
        ]
        cached_object = self.cache.check_object_ttl(
            cached_object, self.cache_ttl
        )
    except cache.CacheNotFoundError as ex:
      self.write_error(f'KVStore Unavailable: {ex}')
      logger.error('KVStore Unavailable: %s', ex)

    if not self.skip_cache and cached_object and cached_object['_key'] == id_:
      splunk_object = cached_object
    else:
      # Call VT API
      collection_relationships = [
          'collections',
          'related_threat_actors',
          'campaigns',
          'malware_families',
          'software_toolkits',
      ]
      vt_data = await self.vt_env.client.get_data_async(
          constants.API_ENDPOINTS[self.field_type] + id_,
          params={
              'relationships': ','.join(
                  collection_relationships + ['comments']
              ),
          },
      )

      # Get fields for the current observable type
      fields = filter(
          lambda f: self.field_type in f['observable_types'], mappings.FIELDS
      )

      # Extract value from vt response and populate the splunk object
      for field in fields:
        value = utils.get_key(vt_data, field['response_field'])
        splunk_object[field['splunk_field']] = field['formatter'](value)

      splunk_object[constants.FIELD_FOUND] = 'True'
      refresh = True

    try:
      self.cache.save_object(splunk_object, refresh)
    except Exception as exc:  # pylint: disable=broad-except
      logger.error(
          'Error when saving %s %s in KVStore: %s',
          self.field_type.capitalize(),
          id_,
          str(exc),
      )

    self.update_cve_cache(splunk_object)

    return splunk_object

  def update_cve_cache(self, splunk_object):
    if self.field_type == constants.FILE:
      cve_cache = cache.VtEnrichmentCache(
          constants.CVE_CACHE, self.vt_env.service
      )
      cves = self.get_cves(splunk_object)
      for cve in cves:
        cached_object = cve_cache.get_object(cve)
        try:
          if cached_object:
            cve_cache.save_object(cached_object)
          else:
            cve_cache.save_object({'_key': cve, constants.FIELD_ID: cve})
        except Exception:  # pylint: disable=broad-except
          logger.error('Error when saving CVE %s in KVStore.', cve)

  def get_cves(self, splunk_object):
    tags = splunk_object.get(constants.FIELD_TAGS, '').split(', ')
    return list(filter(lambda tag: 'cve-' in tag, tags))


dispatch(VirusTotalCommand, sys.argv, sys.stdin, sys.stdout, __name__)
