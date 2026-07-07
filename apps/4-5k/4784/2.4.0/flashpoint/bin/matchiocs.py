# Standard library imports
import os
import re
import hashlib
import time

import logger_manager as log
# Splunk imports
import splunk.Intersplunk
import splunk.search as splunk_search

logger = log.setup_logging('ta_flashpoint_intelligence_matching_matchiocs')


# Create hashes of an event
def _get_event_value_hashes(lengths, event):
    parts_re = re.compile(r'\w+|\W')
    parts = parts_re.findall(event)
    result = set()
    if lengths:
        seq_len = len(parts)
        for start in range(seq_len - min(lengths) + 1):
            max_length = seq_len - start
            for end in (start + length for length in lengths
                        if length <= max_length):
                result.add(hashlib.sha1(str(parts[start:end]).encode('utf-8')).hexdigest())
    return result


try:
    app_name = __file__.split(os.sep)[-3]
    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
    sessionKey = settings.get("sessionKey")

    keywords, options = splunk.Intersplunk.getKeywordsAndOptions()
    ioc_type_filter = options.get('ioc_type', None)
    logger.info(f"starting Matching Configurations for {ioc_type_filter} type")
    if ioc_type_filter == 'all' or ioc_type_filter == '*':
        ioc_type_str = 'where type="*"'
    else:
        ioc_type_str = f'where type="{ioc_type_filter}"'
    list_iocs = splunk_search.searchAll(
        r"| inputlookup list_iocs {}".format(ioc_type_str), sessionKey=sessionKey, namespace=app_name)
    values = []
    iocs = {}
    matched_indicators = []
    indicators = []
    # create indicators dictionary
    for item in list_iocs:
        iocs[item['value']] = item['type']

    ind_value_lengths = set()
    indicators_by_hash = {}
    parts_re = re.compile(r'\w+|\W')
    for indicator in iocs:
        parts = parts_re.findall(
            str(indicator).replace('\\\\', '\\'))
        ind_value_lengths.add(len(parts))
        indicators_by_hash[hashlib.sha1(
            str(parts).encode('utf-8')).hexdigest()] = indicator

    indicator_hashes = set(indicators_by_hash.keys())
    for event in results:
        field_values = []
        for key, value in event.items():
            if key not in ['_raw', '_time', 'index', 'type'] and value:
                field_values.append(str(value))
        
        combined_text = ' '.join(field_values) if field_values else ''
        event_value_hashes = _get_event_value_hashes(ind_value_lengths, combined_text)
        matched_hashes = event_value_hashes & indicator_hashes

        for matched_hash in matched_hashes:
            matched = {}
            matched['value'] = indicators_by_hash[matched_hash]
            matched['event_time'] = event['_time']
            matched['index'] = event['index']
            matched['event'] = event['_raw']
            matched['_time'] = int(time.time())
            matched['type'] = iocs[indicators_by_hash[matched_hash]]
            matched_indicators.append(matched)

    logger.info("Total Matched Indicators= {}".format(len(matched_indicators)))
    logger.info("Matched is  {}".format(matched_indicators))
    splunk.Intersplunk.outputResults(matched_indicators)
except Exception as e:
    logger.exception("Exception occurred: {}".format(e))
