import os
import sys
import json
import requests

from settings import APP_ID

splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(os.path.join(splunkhome, "etc", "apps", APP_ID, "lib"))
from splunklib.searchcommands import (
    dispatch,
    EventingCommand,
    Configuration,
    Option,
)

from dt_logger import DTLogger
from dt_api_wrapper import DtApiWrapper
from domaintools.exceptions import (
    NotAuthorizedException,
    ServiceUnavailableException,
    InternalServerErrorException,
)
import dt_exception_messages


@Configuration()
class FeedNodCommand(EventingCommand):
    """This custom search command makes a request to the newly-observed-domains-feed-(api) API endpoint and retrieves apex-level domains (e.g. example.com but not www.example.com) observed for the first time by the DomainTools sensor network,
        and which are not present in our DNSDB historical database.

    Inherits from the EventingCommand custom search type. Override the `transform` method as the entrypoint to this script

    Example:
        | dtfeednod after=-60
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

    def transform(self, records):
        """This is the entry point to an EventingCommand subclass. You must override this method

        :param records: generator iterator of rows from previous command of SPL search
        :return: generator rows to pass on to next command of SPL search after transform
        """
        self.dt_log = DTLogger(
            "feed_nod", os.path.basename(__file__), self.get_user(), self.feature
        )
        self.dt_log.info("starting feed_nod.py")

        try:
            api_wrapper = DtApiWrapper(
                self.service,
                self.dt_log,
            )
            api = api_wrapper.create_dt_api()
            results = api.nod(
                after=self.after,
                sessionID=self.sessionID,
                domain=self.domain,
                top=self.top,
            )

            for response in results.response():
                feed_data = response.strip()
                if not feed_data:
                    continue

                feed_result = json.loads(feed_data)
                yield {
                    "timestamp": feed_result.get("timestamp"),
                    "domain": feed_result.get("domain"),
                }
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


dispatch(FeedNodCommand, sys.argv, sys.stdin, sys.stdout, __name__)
