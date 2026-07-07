import os
import sys
import time
import splunklib.results as results
import logger_manager as log
from splunklib.searchcommands import (
    Configuration,
    GeneratingCommand,
    Option,
    dispatch,
    validators,
)
from threatq_utils import create_service

logger = log.setup_logging("ta_threatquotient_add_on_threatqcleanupeslookups")
app_name = __file__.split(os.sep)[-3]


@Configuration(type="reporting")
class ThreatQCleanupESLookupsCommand(GeneratingCommand):
    """Dictionary to hold mapping of ES local lookup files and ES KV store.

    # collections
    # Dictionary to hold mapping of ES local lookups and Threat Intel fields,
    # ThreatQ IOC types
    """

    lookup_field_types_map = [
        {
            "lookup": "ip_intel",
            "ioc_types": ["IP Address"],
            "ioc_field": "ip",
        },
        {
            "lookup": "email_intel",
            "ioc_types": ["Email Address"],
            "ioc_field": "src_user",
        },
        {
            "lookup": "email_intel",
            "ioc_types": ["Email Subject"],
            "ioc_field": "subject",
        },
        {
            "lookup": "file_intel",
            "ioc_types": ["Filename"],
            "ioc_field": "file_name",
        },
        {
            "lookup": "file_intel",
            "ioc_types": [
                "Fuzzy Hash",
                "GOST Hash",
                "MD5",
                "SHA-1",
                "SHA-256",
                "SHA-384",
                "SHA-512",
            ],
            "ioc_field": "file_hash",
        },
        {
            "lookup": "domain_intel",
            "ioc_types": ["FQDN"],
            "ioc_field": "domain",
        },
        {
            "lookup": "registry_intel",
            "ioc_types": ["Registry Key"],
            "ioc_field": "registry_value_name",
        },
        {
            "lookup": "service_intel",
            "ioc_types": ["Service Name"],
            "ioc_field": "service",
        },
        {
            "lookup": "certificate_intel",
            "ioc_types": ["x509 Serial"],
            "ioc_field": "certificate_serial",
        },
        {
            "lookup": "certificate_intel",
            "ioc_types": ["x509 Subject"],
            "ioc_field": "certificate_subject",
        },
        {
            "lookup": "http_intel",
            "ioc_types": ["URL"],
            "ioc_field": "url",
        },
        {
            "lookup": "user_intel",
            "ioc_types": ["Username"],
            "ioc_field": "user",
        },
    ]

    def generate(self):
        """Generate method of Generating custom command."""
        try:
            latest_time = int(self.metadata.searchinfo.latest_time)
            if latest_time == 0:
                latest_time = int(time.time())
            kwargs_oneshot = {
                "count": 1,
                "earliest_time": "0",
                "latest_time": latest_time
            }
            service = create_service(self.metadata.searchinfo.session_key)
            for item in self.lookup_field_types_map:
                logger.info(
                    "messsage=generate_events_cleaning_indicators |"
                    " Cleaning threatq indicators from {} lookup "
                    "with field {}".format(
                        item["lookup"],
                        item["ioc_field"],
                    )
                )

                searchquery_oneshot = (
                    "| inputlookup {lookup} where "
                    'threat_key!="threatq_indicator" '
                    "| outputlookup {lookup}".format(
                        lookup=item["lookup"]
                    )
                )

                list(
                    results.ResultsReader(
                        service.jobs.oneshot(
                            searchquery_oneshot, **kwargs_oneshot
                        )
                    )
                )
            yield {"Message": "Clear operation successfully completed!"}

        except Exception as e:
            logger.error(
                "ThreatQ 'threatqcleanupeslookups' command error: {}".format(
                    str(e)
                )
            )
            raise


dispatch(
    ThreatQCleanupESLookupsCommand, sys.argv, sys.stdin, sys.stdout, __name__
)
