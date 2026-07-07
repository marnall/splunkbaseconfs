# pylint: disable=invalid-name

import import_declare_test  # pylint: disable=unused-import

from virustotal.core import cache
from virustotal.core import validators
from virustotal.core import helpers
from splunk import admin

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
import logging

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=3600,
        validator=validators.ValidateInterval(),
    ),
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=validator.String(
            min_len=1,
            max_len=80,
        ),
    ),
    field.RestField(
        'ioc_stream_filter',
        required=False,
        encrypted=False,
        default=None,
        validator=validators.ValidateIocStreamFilter(),
    ),
    field.RestField(
        'sync_es_threat_intelligence',
        required=False,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField('disabled', required=False, validator=None),
]
model = RestModel(fields, name=None)


class IOCStreamValidationHandler(AdminExternalHandler):

  def _validate_migration(self):
    try:
      session_key = self.getSessionKey()
      vt_env = validators.environment.VirusTotalEnv(session_key)
      correlations_cache = cache.VtEnrichmentCache(
          validators.constants.CORRELATIONS_CACHE, vt_env.service
      )

      splunk_saved_searches = vt_env.service.saved_searches
      for saved_search in splunk_saved_searches:
        if not helpers.is_correlation_search(saved_search):
          continue

        metadata = correlations_cache.get_object(saved_search.name)
        if metadata:
          version = metadata.get(
              validators.constants.FIELD_SAVED_SEARCH_VERSION
          )
          if (
              not version
              or version != validators.constants.CURRENT_SAVED_SEARCH_VERSION
          ):
            raise admin.AdminManagerException(
                'Your saved searches are not migrated. Please, go to "Configuration", '
                'review your saved searches and click "Update" to migrate them.'
            )
    except admin.AdminManagerException:
      raise
    except Exception as err:
      raise admin.AdminManagerException(
          f'Error validating saved searches migration: {err}'
      )

  def handleCreate(self, confInfo):
    self._validate_migration()
    return super(IOCStreamValidationHandler, self).handleCreate(confInfo)

  def handleEdit(self, confInfo):
    self._validate_migration()
    return super(IOCStreamValidationHandler, self).handleEdit(confInfo)


endpoint = DataInputModel(
    'vt_ioc_stream',
    model,
)


if __name__ == '__main__':
  logging.getLogger().addHandler(logging.NullHandler())
  admin_external.handle(
      endpoint,
      handler=IOCStreamValidationHandler,
  )
