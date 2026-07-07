import os
from datetime import datetime, timedelta

from log_manager import setup_logging
from intsights_utils import (
    generate_query_list_for_lookups,
    get_macro_definition,
    create_service
)
from command_utils import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRY,
    SessionKeyProvider,
    VulnerabilitiesManager,
)
import splunklib.results as results

logger_name = os.path.splitext(os.path.basename(__file__))[0]
logger = setup_logging(logger_name)
VULN_RETIRING_MACRO = "intsights_vuln_retiring_days"


class VulnUtils:
    """Provides the needed information to access the lookups."""

    def __init__(self):
        """Initialize the object."""
        self._vulns_manager = None
        self._serviceobj = None

    @property
    def serviceobj(self):
        """Set the serviceobj as property."""
        if self._serviceobj is None:
            session_key = SessionKeyProvider(logger).session_key
            self._serviceobj = create_service(session_key)
        return self._serviceobj

    @property
    def vulns_manager(self):
        """Set vulns_manager as property."""
        if self._vulns_manager is None:
            self._vulns_manager = VulnerabilitiesManager(
                self.serviceobj, logger, DEFAULT_BACKOFF_FACTOR, DEFAULT_MAX_RETRY
            )
        return self._vulns_manager

    def retired_policy(self):
        """This will return the retired policy."""
        macro_value = get_macro_definition(self.serviceobj, VULN_RETIRING_MACRO)
        try:
            macro_value = int(macro_value.strip())
        except ValueError:
            macro_value = None
        return macro_value


if __name__ == "__main__":
    logger.info("Starting the intsightsretiredvulns script execution.")
    CURRENT_TIME = datetime.utcnow()
    vuln_utils = VulnUtils()
    retired_policy_days = vuln_utils.retired_policy()
    logger.info(
        "Fetched the Retired Vulnerabilities policy from the respected macros :{}".format(
            retired_policy_days
        )
    )
    searchquery_oneshot = (
        "| inputlookup intsights_matched_vulnerabilities \
         | lookup intsights_vuln_master_lookup _key \
         | where `intsights_retire_vuln_filter({})` \
         | table cveId".format(VULN_RETIRING_MACRO)
    )
    matched_data = list(
        results.ResultsReader(
            vuln_utils.serviceobj.jobs.oneshot(
                searchquery_oneshot, count=0
            )
        )
    )
    matched_vulns = []
    for matched in matched_data:
        if matched.get('cveId'):
            matched_vulns.append(matched['cveId'])
    logger.info("Received {} Vulnerabilitiess from intsights_matched_vulnerabilities.".format(len(matched_vulns)))
    updatetime = (
        (
            CURRENT_TIME
            - timedelta(
                days=retired_policy_days,
                hours=CURRENT_TIME.hour,
                minutes=CURRENT_TIME.minute,
                seconds=CURRENT_TIME.second,
                microseconds=CURRENT_TIME.microsecond,
            )
        )
    ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    update_list = [{"updateDate": {"$lt": updatetime}}]
    retired_matched_query = {"$and": update_list}

    logger.info("Deleting retired vulnerabilitiess from intsights_master_lookup...")
    # Responsible to delte data from the master_lookup
    vuln_utils.vulns_manager.delete_from_master_lookup(retired_matched_query)
    logger.info(
        "Deleting {} retired vulnerabilitiess from intsights_matched_vulnerabilities..."
        .format(len(matched_vulns))
    )
    query_list = generate_query_list_for_lookups(matched_vulns)
    for query in query_list:
        # Responsible to delete the data from matched_lookup
        vuln_utils.vulns_manager.delete_from_matched_lookup(query)

    while True:
        # To handle the scenario of Vulnerabilities deleted from master lookup but still present in match lookup.
        search_deleted_from_master = (
            "| inputlookup intsights_matched_vulnerabilities \
            | eval cveId_matched_lookup=cveId \
            | lookup intsights_vuln_master_lookup _key output cveId \
            | where isnull(cveId) \
            | table cveId, cveId_matched_lookup"
        )

        deleted_from_master_data = list(
            results.ResultsReader(
                vuln_utils.serviceobj.jobs.oneshot(
                    search_deleted_from_master
                )
            )
        )
        logger.info(
            "Received {} IOCs from intsights_matched_vulnerabilities .".format(
                len(deleted_from_master_data)
            )
        )

        in_matched_but_not_in_master = []
        for matched in deleted_from_master_data:
            if not matched.get('cveId') and matched.get('cveId_matched_lookup'):
                in_matched_but_not_in_master.append(matched['cveId_matched_lookup'])

        if len(in_matched_but_not_in_master) == 0:
            logger.info(
                "No IOCs found from intsights_matched_vulnerabilities which are "
                "deleted from intsights_vuln_master_lookup."
            )
            break

        logger.info(
            "Received {} Vulnerabilitiess from intsights_matched_vulnerabilities "
            "which are deleted from intsights_vuln_master_lookup.".format(len(in_matched_but_not_in_master))
        )
        query_list_delete_from_matched = generate_query_list_for_lookups(in_matched_but_not_in_master)
        logger.info(
            "Deleting {} retired vulnerabilitiess from intsights_matched_vulnerabilities."
            .format(len(in_matched_but_not_in_master))
        )

        for query in query_list_delete_from_matched:
            # Responsible to delete the data from matched_lookup
            vuln_utils.vulns_manager.delete_from_matched_lookup(query)

    logger.info(
        "Time taken - {} seconds.".format(
            (datetime.utcnow() - CURRENT_TIME).total_seconds()
        )
    )
    logger.info("Completed the execution of intsightsretiredvulns script")
