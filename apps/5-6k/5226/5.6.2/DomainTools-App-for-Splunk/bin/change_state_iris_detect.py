from __future__ import absolute_import
import os, sys, requests, json
from six.moves.urllib.parse import unquote
from settings import APP_ID

# from urllib.parse import unquote | python3

splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(
    os.path.join(splunkhome, "etc", "apps", APP_ID, "lib")
)

from splunklib import client, results
from splunklib.searchcommands import dispatch, EventingCommand, Option, Configuration
from dt_logger import DTLogger
from dt_api_wrapper import DtApiWrapper
import dt_exception_messages
from domaintools.exceptions import (
    ServiceException,
    NotAuthorizedException,
    ServiceUnavailableException,
)


@Configuration()
class ChangeStateIrisDetectCommand(EventingCommand):
    """This custom search command makes a request to the Iris Detect Add and Remove from Watchlist API endpoint and outputs the results.

        Inherits from the EventingCommand custom search type. Override the `transform` method as the entrypoint to this script

        Example:
            | dtirisdetectchangestate state="watched" domain_id="<domain_id>"
    """

    feature = Option(
        doc="""
                **Syntax:** **feature=***<feature>*
                **Description:** Feature in the app where this was called""",
        default="adhoc",
        require=False,
    )

    domain_id = Option(
        doc="""
                **Syntax:** **domain_id=***<params>*
                **Description:** ID of domain to be triaged. """,
        require=True,
    )

    state = Option(
        doc="""
                **Syntax:** **state=***<params>*
                **Description:** Add domains to watchlist or ignore and mute alerts for those domains. """,
        default="watched",
        require=True,
    )

    def get_token(self):
        """get session key used to decrypt api credentials"""
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
            "iris_detect", os.path.basename(__file__), self.get_user(), self.feature
        )
        self.dt_log.info("ChangeStateIrisDetectCommand: starting change_state_iris_detect.py")

        self.dt_log.info("ChangeStateIrisDetectCommand: Changing domain state in Iris Detect")
        try:
            api_wrapper = DtApiWrapper(self.service, self.dt_log)
            api = api_wrapper.create_dt_api()

            response = api.iris_detect_manage_watchlist_domains([self.domain_id], self.state)

            if self.feature.lower() != "detectdashboard-action":
                # only use this type of KV store update for adhoc search
                # this condition is used in our Detect dashboard to use SPL query to update the KV store
                # rather than thru SDK
                iris_detect_results_kvstore = self.service.kvstore["dt_iris_detect_results"]
                for result_data in iris_detect_results_kvstore.data.query(query=json.dumps({"dt_domain_id": self.domain_id})):
                    result_data["dt_state"] = self.state
                    iris_detect_results_kvstore.data.update(
                        result_data.get("dt_domain"),
                        json.dumps(result_data)
                    )
            yield from response
        except NotAuthorizedException as e:
            self.dt_log.error(e)
            raise Exception(dt_exception_messages.missing_detect_permissions) from e
        except requests.exceptions.ProxyError as e:
            self.dt_log.error(e)
            raise Exception(dt_exception_messages.proxy_error) from e
        except requests.exceptions.SSLError as e:
            self.dt_log.error(e)
            raise Exception(dt_exception_messages.ssl_error.format(e)) from e
        except IOError as e:
            self.dt_log.error(e)
            raise Exception(dt_exception_messages.ssl_error.format(e)) from e
        except Exception as e:
            self.dt_log.error(e)
            raise Exception(dt_exception_messages.generic.format(e)) from e

        self.dt_log.info("ChangeStateIrisDetectCommand: completed change_state_iris_detect.py")


dispatch(ChangeStateIrisDetectCommand, sys.argv, sys.stdin, sys.stdout, __name__)
