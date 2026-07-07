from __future__ import absolute_import
import os, sys, requests, json
from six.moves.urllib.parse import unquote
from settings import APP_ID

# from urllib.parse import unquote | python3

splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(
    os.path.join(splunkhome, "etc", "apps", APP_ID, "lib")
)
import httpx
from splunklib.searchcommands import dispatch, GeneratingCommand, Option, Configuration
from dt_logger import DTLogger
from dt_api_wrapper import DtApiWrapper
import dt_exception_messages
from domaintools.exceptions import (
    ServiceException,
    NotAuthorizedException,
    ServiceUnavailableException,
)


@Configuration()
class AccountInfoCommand(GeneratingCommand):
    """This custom search command makes a request to the account_information API endpoint and outputs the results.

        Inherits from the GeneratingCommand custom search type. Override the `generate` method as the entrypoint to this script

        Example:
            | dtaccountinfo
    """

    feature = Option(
        doc="""
                **Syntax:** **feature=***<feature>*
                **Description:** Feature in the app where this was called""",
        default="adhoc",
        require=False,
    )

    params = Option(
        doc="""
                **Syntax:** **params=***<params>*
                **Description:** URL encoded string of json with params to get account info """,
        default=False,
        require=False,
    )

    def get_token(self):
        """get session key used to decrpyt api credentials"""
        return self.metadata.searchinfo.session_key

    def get_user(self):
        """get current logged in user"""
        return self.metadata.searchinfo.username

    def generate(self):
        """This is the entry point to a GeneratingCommand subclass. You must override this method

            :return: generator rows to pass on to next command of SPL search after transform
        """
        self.dt_log = DTLogger(
            "account_info", os.path.basename(__file__), self.get_user(), self.feature
        )
        self.dt_log.info("AccountInfoCommand: starting account_info.py")
        token = self.get_token()

        if self.params:
            if sys.version_info[0] > 2:
                decoded = unquote(self.params)
            else:
                decoded = unquote(self.params).decode("utf-8")
            params = json.loads(decoded)
            api_wrapper = DtApiWrapper(self.service, self.dt_log, params)
        else:
            api_wrapper = DtApiWrapper(self.service, self.dt_log)
        api = api_wrapper.create_dt_api()

        self.dt_log.info("AccountInfoCommand: Querying DomainTools API")
        api_products = []
        try:
            for result in api.account_information():
                api_products.append(result["id"])
                yield {
                    "id": result["id"],
                    "per_month_limit": result["per_month_limit"],
                    "per_minute_limit": result["per_minute_limit"],
                    "absolute_limit": result["absolute_limit"],
                    "usage_today": result["usage"]["today"],
                    "usage_month": result["usage"]["month"],
                    "expiration_date": result["expiration_date"],
                    "queries_remaining": None,
                    "_raw": json.dumps(result),
                }

        except NotAuthorizedException as e:
            self.dt_log.error(e)
            raise Exception(dt_exception_messages.not_autorized)
        except httpx.ConnectError as e:
            self.dt_log.error(e)
            raise Exception(dt_exception_messages.proxy_error)
        except requests.exceptions.SSLError as e:
            self.dt_log.error(e)
            raise Exception(dt_exception_messages.ssl_error.format(e))
        except IOError as e:
            self.dt_log.error(e)
            raise Exception(dt_exception_messages.ssl_error.format(e))
        except Exception as e:
            self.dt_log.error(e)
            raise Exception(dt_exception_messages.generic.format(e))

        self.dt_log.info("AccountInfoCommand: completed account_info.py")


dispatch(AccountInfoCommand, sys.argv, sys.stdin, sys.stdout, __name__)
