from __future__ import absolute_import
from urllib.parse import unquote

import os
import sys
import json
import time
import requests

from settings import APP_ID

splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(os.path.join(splunkhome, "etc", "apps", APP_ID, "lib"))
from splunklib.searchcommands import (
    dispatch,
    EventingCommand,
    Configuration,
    Option,
    validators,
)
from domaintools.exceptions import (
    NotAuthorizedException,
    ServiceUnavailableException,
    InternalServerErrorException,
)

from dt_logger import DTLogger
from dt_api_wrapper import DtApiWrapper
import dt_exception_messages


@Configuration()
class FeedDomainRDAPCommand(EventingCommand):
    """This custom search command makes a request to the DNSDB API endpoint and appends the data to given domains.

    Inherits from the EventingCommand custom search type. Override the `transform` method as the entrypoint to this script

    Example:
        | dtfeeddomainrdap after=-60
    """

    after = Option(require=False, default=None)
    sessionID = Option(require=False, default=None)
    domain = Option(require=False, default=None)
    top = Option(require=False, default=None)
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

    def parse_links(self, unparsed_links):
        links = []
        for link in unparsed_links:
            links.append(link.get("href"))

        return links

    def transform(self, records):
        """This is the entry point to an EventingCommand subclass. You must override this method

        :param records: generator iterator of rows from previous command of SPL search
        :return: generator rows to pass on to next command of SPL search after transform
        """
        self.dt_log = DTLogger(
            "feed_domain_rdap", os.path.basename(__file__), self.get_user(), self.feature
        )
        self.dt_log.info("starting feed_domain_rdap.py")
        try:
            api_wrapper = DtApiWrapper(
                self.service,
                self.dt_log,
            )
            api = api_wrapper.create_dt_api()
            results = api.domainrdap(after=self.after, sessionID=self.sessionID)

            for response in results.response():
                feed_data = response.strip()
                if not feed_data:
                    continue

                feed_result = json.loads(feed_data)
                parsed_fields = feed_result.get("parsed_record", {}).get("parsed_fields", {})

                links = self.parse_links(parsed_fields.get("links", []))

                result = {
                    "domain": feed_result.get("domain"),
                    "timestamp": feed_result.get("timestamp"),
                    "conformance": parsed_fields.get("conformance"),
                    "contacts": parsed_fields.get("contacts"),
                    "creation_date": parsed_fields.get("creation_date"),
                    "dnssec_enabled": parsed_fields.get("dnssec", {}).get("signed"),
                    "domain_statuses": parsed_fields.get("domain_statuses"),
                    "email_domains": parsed_fields.get("email_domains"),
                    "emails": parsed_fields.get("emails"),
                    "expiration_date": parsed_fields.get("expiration_date"),
                    "handle": parsed_fields.get("handle"),
                    "last_changed_date": parsed_fields.get("last_changed_date"),
                    "links": links,
                    "nameservers": parsed_fields.get("nameservers"),
                    "iana_id": parsed_fields.get("iana_id"),
                    "name": parsed_fields.get("name"),
                    "unclassified_emails": parsed_fields.get("unclassified_emails"),
                    "raw": feed_result.get("raw_record"),
                }

                yield result
        except NotAuthorizedException as e:
            self.dt_log.error(e, {"status": "down"})
            raise Exception(dt_exception_messages.not_autorized)
        except ServiceUnavailableException as e:
            self.dt_log.error(e, {"status": "down"})
            raise Exception(dt_exception_messages.service_not_available)
        except InternalServerErrorException as e:
            self.dt_log.error(e, {"status": "down"})
            raise Exception(dt_exception_messages.search_hash_error)
        except requests.exceptions.ProxyError as e:
            self.dt_log.error(e, {"status": "down"})
            raise Exception(dt_exception_messages.proxy_error)
        except requests.exceptions.SSLError as e:
            self.dt_log.error(e, {"status": "down"})
            raise Exception(dt_exception_messages.ssl_error.format(e))
        except Exception as e:
            self.dt_log.error(e, {"status": "down"})
            raise Exception(dt_exception_messages.generic.format(e))


dispatch(FeedDomainRDAPCommand, sys.argv, sys.stdin, sys.stdout, __name__)
