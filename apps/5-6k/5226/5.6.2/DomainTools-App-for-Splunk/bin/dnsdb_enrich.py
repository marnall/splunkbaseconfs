from __future__ import absolute_import

import json
import multiprocessing.dummy as mp
import os
import sys

from settings import APP_ID
from six.moves import range

splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(
    os.path.join(splunkhome, "etc", "apps", APP_ID, "lib")
)
import dnsdb2
from dt_logger import DTLogger
from splunklib.searchcommands import (Configuration, EventingCommand, Option,
                                      dispatch, validators)
from splunklib.six.moves.urllib.parse import urlsplit
from utils import get_client_info, get_credentials, get_proxy

QUERY_LIMIT = 10000
THREAD_COUNT = 10

@Configuration()
class DNSDBEnrichCommand(EventingCommand):
    """This custom search command makes a request to the DNSDB API endpoint and appends the data to given domains.

        Inherits from the EventingCommand custom search type. Override the `transform` method as the entrypoint to this script

        Example:
            | makeresults | eval domain="domaintools.com" | dtdnsdbenrich field_in=domain
    """

    field_in = Option(
        doc="""
                **Syntax:** **field_in=***<in>*
                **Description:** Field to extract targets from""",
        require=True,
    )

    field_type = Option(
        doc="""
                **Syntax:** **max_count=***<int>*
                **Description:** Target type. domain, ip, or raw""",
        default="domain",
        require=True,
    )

    lookup_type = Option(
        doc="""
                **Syntax:** **max_count=***<int>*
                **Description:** Lookup type. rrdata or rrset""",
        require=False,
    )

    max_count = Option(
        doc="""
                **Syntax:** **max_count=***<int>*
                **Description:** Max number of dnsdb results to return in Splunk UI per row""",
        default=5,
        require=False,
    )

    rrtype = Option(
        doc="""
                **Syntax:** **rrtype=***<int>*
                **Description:** rrtype to lookup. The resource record type of the RRset, either using the standard DNS type mnemonic, or an RFC 3597 generic type, i.e. the string TYPE immediately followed by the decimal RRtype number. ANY, A, CNAME, NS, etc. """,
        default="ANY",
        require=False,
    )

    time_first_before = Option(
        doc="""
                **Syntax:** **time_first_before=***<int>*
                **Description:** Unix Timestamp. Provide results before the defined timestamp for when the DNS record was first observed.""",
        require=False,
    )

    time_first_after = Option(
        doc="""
                **Syntax:** **time_first_after=***<int>*
                **Description:** Unix Timestamp. Provide results after the defined timestamp for when the DNS record was first observed.""",
        require=False,
    )

    time_last_before = Option(
        doc="""
                **Syntax:** **time_first_after=***<int>*
                **Description:** Unix Timestamp. Provide results before the defined timestamp for when the DNS record was last observed.""",
        require=False,
    )

    time_last_after = Option(
        doc="""
                **Syntax:** **time_last_after=***<int>*
                **Description:** Unix Timestamp. Provide results after the defined timestamp for when the DNS record was first observed.""",
        default=-21600,
        require=False,
    )

    bailiwick = Option(
        doc="""
                **Syntax:** **bailiwick=***<bool>*
                **Description:** The “bailiwick” of an RRset in DNSDB observed via passive DNS replication is the closest enclosing zone delegated to a nameserver which served the RRset.""",
        require=False,
    )

    include_subdomains = Option(
        doc="""
                    **Syntax:** **include_subdomains=***<bool>*
                    **Description:** Preface each lookup with “*.” (e.g. *.inputdomain.com)""",
        default=False,
        require=False,
    )

    feature = Option(
        doc="""
                **Syntax:** **feature=***<feature>*
                **Description:** Feature in the app where this was called""",
        default="adhoc",
        require=False,
    )

    def get_token(self):
        """get session key used to decrpyt api credentials"""
        return self.metadata.searchinfo.session_key

    def get_user(self):
        """get current logged in user"""
        return self.metadata.searchinfo.username

    def format_row(self, record, result):
        """format dnsdb response to Splunk row"""

        max_count = int(self.max_count)
        sorted_result = sorted(result, reverse=True, key=lambda x: max(x.get("time_last", 0), x.get("zone_last", 0)))

        record['dnsdb_time_first'] = [x.get("time_first", "") for x in sorted_result[:max_count]]
        record['dnsdb_time_last'] = [x.get("time_last", "") for x in sorted_result[:max_count]]
        record['dnsdb_rrname'] = [x.get("rrname", "") for x in sorted_result[:max_count]]
        record['dnsdb_rrtype'] = [x.get("rrtype", "") for x in sorted_result[:max_count]]
        record['dnsdb_rdata'] = [json.dumps(x.get("rdata", "")) for x in sorted_result[:max_count]]
        record['dnsdb_zone_time_first'] = [x.get("zone_time_first", "") for x in sorted_result[:max_count]]
        record['dnsdb_zone_time_last'] = [x.get("zone_time_last", "") for x in sorted_result[:max_count]]
        record['dnsdb_count'] = [x.get("count", "") for x in sorted_result[:max_count]]

        return record

    def enrich(self, record):    # sourcery skip: raise-specific-error
        """query DNSDB

            :param api: domaintools.API
            :param target: domain, ip, or raw
            :return: list formatted dnsdb data
        """
        target = (
            f"*.{record[self.field_in]}"
            if self.include_subdomains
            else record[self.field_in]
        )

        if not self.lookup_type:
            # default lookup_type based on field_type if lookup_type is not specified
            lookup_type = "rdata" if self.field_type in ["ip", "raw"] else "rrset"
        else:
            lookup_type = self.lookup_type

        field_type = self.field_type

        query = {
            "rrtype": self.rrtype,
            "field_type": self.field_type,
            "lookup_type": self.lookup_type,
            "time_first_before": self.time_first_before,
            "time_first_after": self.time_first_after,
            "time_last_before": self.time_last_before,
            "time_last_after": self.time_last_after,
            "bailiwick": self.bailiwick,
            "ignore_limited": True,
            "limit": QUERY_LIMIT
        }

        try:
            # rrset lookup only supports domain field type
            if lookup_type == "rrset" and field_type == "domain":
                response = list(self.api.lookup_rrset(target, **query))
            # rdata lookup supports all field types
            elif field_type == "domain":
                response = list(self.api.lookup_rdata_name(target, **query))
            elif field_type == "ip":
                response = list(self.api.lookup_rdata_ip(target, **query))
            elif field_type == "raw":
                response = list(self.api.lookup_rdata_raw(target, **query))
            else:
                raise Exception("Unsupported field_type/lookup_type combination.")
        except dnsdb2.QueryError as e:
            raise Exception(f"Server returned query error: {str(e)}")
        except dnsdb2.QueryFailed as e:
            raise Exception(f"Server encountered an error while running query: {str(e)}")
        except dnsdb2.QueryLimited as e:
            # With ignore_limited=True we should never see this
            raise Exception("Result limit reached")
        except dnsdb2.QueryTruncated as e:
            raise Exception(
                f"Query results are incomplete due to a server error: {str(e)}"
            )
        except dnsdb2.QuotaExceeded as e:
            raise Exception("Query quota for this API key has been reached.")
        except dnsdb2.AccessDenied as e:
            raise Exception("Authorization failed. Check API key")
        except dnsdb2.ConcurrencyExceeded as e:
            raise Exception("Number of concurrent connections has exceeded your limit.")
        except dnsdb2.ProtocolError as e:
            raise Exception(
                f"Invalid data is received via the Streaming Application Framework: {str(e)}"
            )

        return self.format_row(record, response)

    def transform(self, records):
        """This is the entry point to an EventingCommand subclass. You must override this method

            :param records: generator iterator of rows from previous command of SPL search
            :return: generator rows to pass on to next command of SPL search after transform
        """
        self.dt_log = DTLogger(
            "dnsdb_enrich", os.path.basename(__file__), self.get_user(), self.feature
        )
        self.dt_log.info("starting dnsdb_enrich.py")

        session_key = self.get_token()
        credentials = get_credentials(session_key, service=self.service)
        swclient, version = get_client_info(session_key, service=self.service)
        proxy = get_proxy(session_key, service=self.service)

        proxies = {"https": proxy, "http": proxy}
        self.api = dnsdb2.Client(credentials["farsight_key"], swclient=swclient, version=version, proxies=proxies)

        with mp.Pool(THREAD_COUNT) as p:
            yield from p.imap(self.enrich, records)
        self.dt_log.info("completed dnsdb_enrich.py successfully")


dispatch(DNSDBEnrichCommand, sys.argv, sys.stdin, sys.stdout, __name__)
