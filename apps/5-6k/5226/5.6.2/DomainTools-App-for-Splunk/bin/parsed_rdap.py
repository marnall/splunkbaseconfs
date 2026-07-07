from __future__ import absolute_import
import os
import sys
import json
import requests
import time
from settings import APP_ID

splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(os.path.join(splunkhome, "etc", "apps", APP_ID, "lib"))
from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)
from dt_api_wrapper import DtApiWrapper
from dt_logger import DTLogger
from domaintools.exceptions import (
    NotFoundException,
    NotAuthorizedException,
    ServiceUnavailableException,
    InternalServerErrorException,
)
import dt_exception_messages


@Configuration()
class ParsedRDAPCommand(GeneratingCommand):
    """This custom search command makes a request to the whois-history API endpoint and appends the data to given domains.

    Inherits from the GeneratingCommand custom search type. Override the `generate` method as the entrypoint to this script

    Example:
        | parsedrdap domain=domaintools.com
    """

    domain = Option(require=True)
    feature = Option(default="adhoc", require=False)

    def get_user(self):
        """get current logged in user"""
        return self.metadata.searchinfo.username

    def parse_links(self, unparsed_links):
        links = []
        for link in unparsed_links:
            links.append(link.get("href"))

        return links

    def generate(self):
        """This is the entry point to a GeneratingCommand subclass. You must override this method

        :return: generator rows to pass on to next command of SPL search after transform
        """
        self.dt_log = DTLogger(
            "parsed_rdap",
            os.path.basename(__file__),
            self.get_user(),
            self.feature,
        )
        self.dt_log.info("starting parsed_rdap.py")

        try:
            api_wrapper = DtApiWrapper(self.service, self.dt_log)
            api = api_wrapper.create_dt_api()

            self.dt_log.info("Querying Parsed Domain RDAP API for {0}".format(self.domain))
            response = api.parsed_domain_rdap(self.domain).response()

            parsed_fields = response.get("parsed_domain_rdap", {})
            links = self.parse_links(parsed_fields.get("links", []))

            result = {
                "domain": parsed_fields.get("domain"),
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
                "registrar": parsed_fields.get("registrar"),
                "unclassified_emails": parsed_fields.get("unclassified_emails"),
                "raw": response.get("domain_rdap")
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
        except NotFoundException as e:
            self.dt_log.error(e, {"status": "down"})
            raise Exception(dt_exception_messages.not_found_error)
        except Exception as e:
            self.dt_log.error(e, {"status": "down"})
            raise Exception(type(e).__name__)




        self.dt_log.info("completed parsed_rdap.py")


dispatch(ParsedRDAPCommand, sys.argv, sys.stdin, sys.stdout, __name__)
