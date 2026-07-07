"""Extended mapping definitions for GTI add-on."""

from gti.core import constants
from gti.core import formatters

# Fields specific for GTI integration
EXTENDED_FIELDS = [
    {
        'splunk_field': constants.FIELD_ORIGIN,
        'response_field': 'attributes.origin',
        'observable_types': constants.ADVERSARY,
        'formatter': formatters.identity,
    },
    {
        'splunk_field': constants.FIELD_COLLECTION_TYPE,
        'response_field': 'attributes.collection_type',
        'observable_types': constants.ADVERSARY,
        'formatter': formatters.identity,
    },
    {
        'splunk_field': constants.FIELD_SCORE,
        'response_field': 'attributes.gti_assessment.threat_score.value',
        'observable_types': constants.IOCS,
        'formatter': formatters.identity,
    },
    {
        'splunk_field': constants.FIELD_VERDICT,
        'response_field': 'attributes.gti_assessment.verdict.value',
        'observable_types': constants.IOCS,
        'formatter': formatters.threat_verdict,
    },
    {
        'splunk_field': constants.FIELD_SEVERITY,
        'response_field': 'attributes.gti_assessment.severity.value',
        'observable_types': constants.IOCS,
        'formatter': formatters.threat_severity,
    },
]
