import json
import os
import sys
import import_declare_test

from common.log import get_logger
from common.indicator_helper import matched_event
from datetime import datetime
from splunklib import client
from splunklib.searchcommands import (dispatch, StreamingCommand, Configuration,
                                      Option)

logger = get_logger(__file__)


def get_file_hash(indicator: dict, hash_type: str) -> str or None:
  for associated_hash in indicator.get('associated_hashes'):
    if associated_hash.get('type') == hash_type:
      return associated_hash.get('value')
  return



def transform_indicator(record: dict) -> dict:
  """Transforms a Mandiant Indicator into a dict compatoble with the Splunk
  hosted `mandiant_master_lookup` KV Store Collection

  Args:
    indicator: a Mandiant Indicator object

  Returns:
    row: a dict that can be used to add / update a row in the
    `mandiant_master_lookup` KV store Collection
  """
  indicator = json.loads(record.get('_raw'))
  row = {
      'id': indicator.get('id'),
      'last_seen': indicator.get('last_seen_index'),
      'mscore': indicator.get('mscore'),
      'type': indicator.get('type'),
      '_user': 'nobody',
      '_key': indicator.get('id')
  }

  if indicator.get('type') == 'md5' and "associated_hashes" in indicator:
    row['sha1'] = get_file_hash(indicator, "sha1")
    row['sha256'] = get_file_hash(indicator, "sha256")

  if "attributed_associations" in indicator:
    threat_actors = []
    malware = []

    for assoc in indicator.get('attributed_associations'):
      assoc_value = f"{assoc.get('id')}||{assoc.get('name')}"
      if assoc.get('type') == "malware":
        malware.append(assoc_value)
      elif assoc.get('type') == "threat-actor":
        threat_actors.append(assoc_value)

    if len(malware) > 0:
      row['malware'] = malware

    if len(threat_actors) > 0:
      row['threat_actor'] = threat_actors

  if indicator.get('threat_rating'):
    row['threat_score'] = indicator.get('threat_rating').get('threat_score')
    row['severity_level'] = indicator.get('threat_rating').get('severity_level')
    row['severity_reason'] = indicator.get('threat_rating').get('severity_reason')

  categories = []
  for source in indicator.get('sources'):
    for cat in source.get('category'):
      if cat not in categories:
        categories.append(cat)

  if len(categories) > 0:
    row['category'] = categories

  campaigns = []
  if indicator.get('campaigns'):
    for campaign in indicator.get('campaigns'):
      campaigns.append(f"{campaign.get('id')}||{campaign.get('name')}")
    if len(campaigns) > 0:
      row['campaigns'] = campaigns

  reports = []
  for report in indicator.get('reports'):
    reports.append(report.get('report_id'))
  if len(reports) > 0:
    row['reports'] = reports

  return row


@Configuration()
class MandiantTransformIndicator(StreamingCommand):
  """Manage the processing of the Mandiant Transform Indicator Command"""

  def stream(self, records):
    """Entry point for the command, inherited from the StreamingCommand class.

    Receives events (records) from the results of a Splunk search, transforms 
    the event into a record that can be added to mandiant_master_lookup

    Yields:
      record: a dict of one of the processed search results
    """
    logger.info("Starting Mandiant Transform Indicators")

    # Process search results one by one
    for record in records:
      indicator = transform_indicator(record)
      if indicator.get('campaigns'):
        logger.info(f"Camapiagn row: {indicator.get('id')}")
      if indicator.get('threat_actor'):
        logger.info(f"Threat actor row: {indicator.get('id')}")
      yield indicator


dispatch(MandiantTransformIndicator, sys.argv, sys.stdin, sys.stdout, __name__)
