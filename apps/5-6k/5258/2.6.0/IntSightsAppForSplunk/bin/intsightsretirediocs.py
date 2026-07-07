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
    IOCsManager,
)
import splunklib.results as results

logger_name = os.path.splitext(os.path.basename(__file__))[0]
logger = setup_logging(logger_name)
MACRO_NAME_DICT = {
    "intsights_domain_ioc_retiring_days": "Domains",
    "intsights_email_ioc_retiring_days": "Emails",
    "intsights_ipaddress_ioc_retiring_days": "IpAddresses",
    "intsights_url_ioc_retiring_days": "Urls",
    "intsights_hash_ioc_retiring_days": "Hashes",
}
TOTAL_IOCS_TYPES = ["Domains", "Emails", "IpAddresses", "Urls", "Hashes"]


class IOCUtils:
    """Provides the needed information to access the lookups."""

    def __init__(self):
        """Initialize the object."""
        self._iocs_manager = None
        self._serviceobj = None

    @property
    def serviceobj(self):
        """Set the serviceobj as property."""
        if self._serviceobj is None:
            session_key = SessionKeyProvider(logger).session_key
            self._serviceobj = create_service(session_key)
        return self._serviceobj

    @property
    def iocs_manager(self):
        """Set iocs_manager as property."""
        if self._iocs_manager is None:
            self._iocs_manager = IOCsManager(
                self.serviceobj, logger, DEFAULT_BACKOFF_FACTOR, DEFAULT_MAX_RETRY
            )
        return self._iocs_manager

    def retired_policy(self):
        """This will return the retired policy dictionary."""
        retired_policy_dict = dict()
        for macro_name in MACRO_NAME_DICT.keys():
            macro_value = get_macro_definition(self.serviceobj, macro_name)
            retired_policy_dict.update({MACRO_NAME_DICT[macro_name]: int(macro_value)})
        return retired_policy_dict


if __name__ == "__main__":
    logger.info("Starting the intsightsretirediocs script execution.")
    CURRENT_TIME = datetime.utcnow()
    ioc_utils = IOCUtils()
    retired_policy_dict = ioc_utils.retired_policy()
    logger.info(
        "Fetched the Retired IOCs policy from the respected macros :{}".format(
            retired_policy_dict
        )
    )
    searchquery_oneshot = (
        "| inputlookup intsights_matched_iocs \
         | lookup intsights_master_lookup _key \
         | where `intsights_retire_ioc_filter(Domains, intsights_domain_ioc_retiring_days)` \
          OR `intsights_retire_ioc_filter(Emails, intsights_email_ioc_retiring_days)` \
          OR `intsights_retire_ioc_filter(Hashes, intsights_hash_ioc_retiring_days)` \
          OR `intsights_retire_ioc_filter(IpAddresses, intsights_ipaddress_ioc_retiring_days)` \
          OR `intsights_retire_ioc_filter(Urls, intsights_url_ioc_retiring_days)` | table value"
    )
    matched_data = list(
        results.ResultsReader(
            ioc_utils.serviceobj.jobs.oneshot(
                searchquery_oneshot, count=0
            )
        )
    )
    matched_iocs = []
    for matched in matched_data:
        if matched.get('value'):
            matched_iocs.append(matched['value'])
    logger.info("Received {} IOCs from intsights_matched_iocs.".format(len(matched_iocs)))
    retired_matched_query_list = []
    for ioc_type in TOTAL_IOCS_TYPES:
        lastupdatetime = (
            (
                CURRENT_TIME
                - timedelta(
                    days=retired_policy_dict[ioc_type],
                    hours=CURRENT_TIME.hour,
                    minutes=CURRENT_TIME.minute,
                    seconds=CURRENT_TIME.second,
                    microseconds=CURRENT_TIME.microsecond,
                )
            )
        ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        lastUpdate_list = []
        lastupdate_dict = {"iocLastSeen": {"$lt": lastupdatetime}}
        type_dict = {"type": ioc_type}
        lastUpdate_list.append(lastupdate_dict)
        lastUpdate_list.append(type_dict)
        endpoint_query = {"$and": lastUpdate_list}
        retired_matched_query_list.append(endpoint_query)

    logger.info("Deleting retired iocs from intsights_master_lookup...")
    for retired_ioc_query in retired_matched_query_list:
        # Responsible to delte data from the master_lookup
        ioc_utils.iocs_manager.delete_from_master_lookup(retired_ioc_query)
    logger.info("Deleting {} retired iocs from intsights_matched_iocs...".format(len(matched_iocs)))
    query_list = generate_query_list_for_lookups(matched_iocs)
    for query in query_list:
        # Responsible to delete the data from matched_lookup
        ioc_utils.iocs_manager.delete_from_matched_lookup(query)

    while True:
        # To handle the scenario of IOCs deleted from master lookup but still present in match lookup.
        search_deleted_from_master = (
            "| inputlookup intsights_matched_iocs \
            | eval value_matched_lookup=value \
            | lookup intsights_master_lookup _key output value \
            | where isnull(value) \
            | table value, value_matched_lookup"
        )

        deleted_from_master_data = list(
            results.ResultsReader(
                ioc_utils.serviceobj.jobs.oneshot(
                    search_deleted_from_master, count=0
                )
            )
        )
        logger.info(
            "Received {} IOCs from intsights_matched_iocs .".format(
                len(deleted_from_master_data)
            )
        )

        in_matched_but_not_in_master = []
        for matched in deleted_from_master_data:
            if not matched.get('value') and matched.get('value_matched_lookup'):
                in_matched_but_not_in_master.append(matched['value_matched_lookup'])

        if len(in_matched_but_not_in_master) == 0:
            logger.info("No IOCs found from intsights_matched_iocs which are deleted from intsights_master_lookup.")
            break

        logger.info(
            "Received {} IOCs from intsights_matched_iocs which are deleted from intsights_master_lookup.".format(
                len(in_matched_but_not_in_master)
            )
        )
        query_list_delete_from_matched = generate_query_list_for_lookups(in_matched_but_not_in_master)
        logger.info("Deleting {} retired iocs from intsights_matched_iocs.".format(len(in_matched_but_not_in_master)))

        for query in query_list_delete_from_matched:
            # Responsible to delete the data from matched_lookup
            ioc_utils.iocs_manager.delete_from_matched_lookup(query)

    logger.info(
        "Time taken - {} seconds.".format(
            (datetime.utcnow() - CURRENT_TIME).total_seconds()
        )
    )
    logger.info("Completed the execution of intsightsretirediocs script")
