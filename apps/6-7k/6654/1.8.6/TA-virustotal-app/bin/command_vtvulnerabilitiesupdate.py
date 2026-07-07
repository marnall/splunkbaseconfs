"""vtvulnerabilitiesupdate command implementation."""

import sys
from virustotal.core import cache
from virustotal.core import log
from virustotal.core import environment
from virustotal.core import constants
import import_declare_test  # pylint: disable=unused-import
# pylint: disable=import-error
from splunklib.searchcommands import Configuration
from splunklib.searchcommands import dispatch
from splunklib.searchcommands import GeneratingCommand
# pylint: enable=import-error

CACHES_IOC = [
    constants.FILE_CACHE,
    constants.URL_CACHE,
    constants.IP_CACHE,
    constants.DOMAIN_CACHE,
]

logger = log.get_logger(__file__)


@Configuration(type='reporting')
class VTCVECommand(GeneratingCommand):
  """Update CVE Lookup Table."""

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    self.vt_env = None
    self.file_cache = None
    self.cve_cache = None

  def generate(self):
    self.vt_env = environment.VirusTotalEnv(
        self._metadata.searchinfo.session_key
    )
    self.file_cache = cache.VtEnrichmentCache(
        constants.FILE_CACHE, self.vt_env.service
    )
    self.cve_cache = cache.VtEnrichmentCache(
        constants.CVE_CACHE, self.vt_env.service
    )

    deleted_cves = self.update_cve_cache()

    yield from deleted_cves

    logger.info(
        'Command %s executed successfully.', constants.COMMAND_VULNS_UPDATE
    )

    self.vt_env.client.close()

  def update_cve_cache(self):
    """
    Update the CVE cache to keep it synchronized with the IoC caches.

    Returns:
    - deleted_cves (list[dict]): List of objects deleted from the CVE cache
    """
    cves_expected = set()
    cves_existing = set()
    deleted_cves = []

    # Get expected CVEs from file lookup table
    files = self.file_cache.get_objects({})
    if files:
      for file in files:
        if constants.FIELD_TAGS in file:
          for tag in file[constants.FIELD_TAGS].split(', '):
            if 'cve-' in tag:
              cves_expected.add(tag)

    # Get existing CVEs from CVE lookup table
    cves = self.cve_cache.get_objects({})
    if cves:
      for cve in cves:
        cves_existing.add(cve['_key'])

    # Delete from CVE lookup table the CVEs not expected and existing
    for cve in cves_existing.difference(cves_expected):
      try:
        self.cve_cache.delete_object({'_key': cve})
        deleted_cves.append({'ID': cve})
      except Exception as ex:  # pylint: disable=broad-except
        logger.error('Error when deleting %s from CVE cache: %s', cve, ex)

    return deleted_cves


dispatch(VTCVECommand, sys.argv, sys.stdin, sys.stdout, __name__)
