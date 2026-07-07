"""vtdeleteiocs command implementation."""

from datetime import datetime
import sys
from gti.core import cache
from gti.core import environment
from gti.core import constants
from gti.core import log
import import_declare_test  # pylint: disable=unused-import
# pylint: disable=import-error
from splunklib.searchcommands import Configuration
from splunklib.searchcommands import dispatch
from splunklib.searchcommands import Option
from splunklib.searchcommands import EventingCommand
from splunklib.searchcommands import validators
# pylint: enable=import-error

CACHES = {
    constants.FILE: constants.FILE_CACHE,
    constants.URL: constants.URL_CACHE,
    constants.IP: constants.IP_CACHE,
    constants.DOMAIN: constants.DOMAIN_CACHE,
}

CACHES_REVERSE = {
    constants.FILE_CACHE: constants.FILE,
    constants.URL_CACHE: constants.URL,
    constants.IP_CACHE: constants.IP,
    constants.DOMAIN_CACHE: constants.DOMAIN,
}

OPTIONS = ['lookups', 'ttl']

logger = log.get_logger(__file__)


@Configuration()
class VTDeleteCommand(EventingCommand):
  """Delete IoCs from Lookup Tables."""

  lookups = Option(
      doc="""
    **Syntax:** lookups=<list>
    **Description:** Type of lookup table [hash/url/domain/ip]
    """,
      validate=validators.List(),
  )

  ttl = Option(
      doc="""
    **Syntax:** ttl=<int>
    **Description:** Maximum TTL (days)
    """,
      validate=validators.Integer(),
  )

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    self.vt_env = None
    self.cache = None
    self.cache_ttl = 0

  def transform(self, records):
    self.vt_env = environment.VirusTotalEnv(
        self._metadata.searchinfo.session_key
    )

    options = {}
    for option_key in OPTIONS:
      options[option_key] = getattr(self, option_key, None)

    options['iocs'] = [
        {'_key': r[constants.FIELD_ID]}
        for r in records
        if constants.FIELD_ID in r
    ]

    deleted_objects = self.delete_iocs(options)

    for object_ in deleted_objects:
      last_seen = datetime.fromtimestamp(object_[cache.CACHE_LAST_SEEN])
      yield {
          'Last seen in events': last_seen.strftime('%Y-%m-%d %H:%M:%S'),
          'Type of IoC': object_['type'],
          'ID': object_[constants.FIELD_ID],
          'Detections': object_[constants.FIELD_DETECTIONS],
      }

    logger.info(
        'Command %s executed successfully.', constants.COMMAND_DELETE_IOCS
    )

    self.vt_env.client.close()

  def delete_iocs(self, options):
    lookups_ = list(CACHES.values())
    ttl = None
    query = {}
    deleted_objects = []
    for key, value in options.items():
      if value:
        if key == 'lookups':
          lookups_ = [CACHES[v] for v in value]
        elif key == 'ttl':
          ttl = int(value)
        elif key == 'iocs':
          query['$or'] = value

    for lookup in lookups_:
      self.cache = cache.VtEnrichmentCache(lookup, self.vt_env.service)
      objects = self.cache.get_objects(query, ttl)
      if objects:
        for object_ in objects:
          object_['type'] = CACHES_REVERSE[lookup]
        deleted_objects.extend(objects)
        try:
          self.cache.delete_objects(objects)
        except Exception as ex:  # pylint: disable=broad-except
          logger.error('Error when deleting from %s cache: %s', lookup, ex)

    return deleted_objects


dispatch(VTDeleteCommand, sys.argv, sys.stdin, sys.stdout, __name__)
