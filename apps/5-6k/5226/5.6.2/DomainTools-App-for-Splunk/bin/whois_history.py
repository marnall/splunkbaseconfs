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
    ServiceException,
    NotAuthorizedException,
    ServiceUnavailableException,
    InternalServerErrorException,
)
import dt_exception_messages


@Configuration()
class WhoisHistoryCommand(GeneratingCommand):
    """This custom search command makes a request to the whois-history API endpoint and appends the data to given domains.

    Inherits from the GeneratingCommand custom search type. Override the `generate` method as the entrypoint to this script

    Example:
        | whoishistory domain=domaintools.com
        | dtwhoishistory domain=domaintools.com mode="check_existence"
        | dtwhoishistory domain=domaintools.com mode="list" sort="date_desc"
    """

    domain = Option(require=True)
    mode = Option(
        require=False,
        default="list",
        validate=validators.Set("list", "check_existence", "count"),
    )
    sort = Option(
        require=False,
        default="date_desc",
        validate=validators.Set("date_desc", "date_asc"),
    )
    feature = Option(default="adhoc", require=False)

    def get_user(self):
        """get current logged in user"""
        return self.metadata.searchinfo.username

    def generate(self):
        """This is the entry point to a GeneratingCommand subclass. You must override this method

        :return: generator rows to pass on to next command of SPL search after transform
        """
        self.dt_log = DTLogger(
            "whois_history",
            os.path.basename(__file__),
            self.get_user(),
            self.feature,
        )
        self.dt_log.info("starting whois_history.py")

        api_wrapper = DtApiWrapper(self.service, self.dt_log)
        api = api_wrapper.create_dt_api()
        try:
            self.dt_log.info("Querying Whois History api for {0}".format(self.domain))
            response = api.whois_history(self.domain, self.mode, self.sort).response()

            if self.mode == "check_existence":
                yield {"has_history_entries": response.get("has_history_entries")}

            if self.mode == "count":
                yield {"record_count": response.get("record_count")}

            if self.mode == "list":
                for history in response.get("history") or []:
                    whois = history.get("whois")
                    registration = whois.get("registration")
                    yield {
                        "date": history.get("date"),
                        "is_private": history.get("is_private"),
                        "registrant": whois.get("registrant"),
                        "registration_created": registration.get("created"),
                        "registration_expires": registration.get("expires"),
                        "registration_updated": registration.get("updated"),
                        "registration_registrar": registration.get("registrar"),
                        "registration_statuses": registration.get("statuses"),
                        "name_servers": whois.get("name_servers"),
                        "server": whois.get("server"),
                        "record": whois.get("record"),
                    }

            self.dt_log.info("api status up", {"status": "up"})
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

        self.dt_log.info("completed whois_history.py")


dispatch(WhoisHistoryCommand, sys.argv, sys.stdin, sys.stdout, __name__)
