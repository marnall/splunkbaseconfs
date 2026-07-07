from __future__ import absolute_import
import os
import sys
import json
import requests
import time
import datetime
from settings import APP_ID


splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(
    os.path.join(splunkhome, "etc", "apps", APP_ID, "lib")
)
from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)
from splunklib import client, results
from dt_api_wrapper import DtApiWrapper
from dt_logger import DTLogger
from domaintools.exceptions import (
    ServiceException,
    NotAuthorizedException,
    ServiceUnavailableException,
)
import dt_exception_messages


@Configuration()
class ExpireCacheCommand(GeneratingCommand):
    """This custom search command removes expired cache from dt_iris_enrich_data

        Inherits from the GeneratingCommand custom search type. Override the `generate` method as the entrypoint to this script

        Example:
            | dtexpirecache feature="Saved Search"
    """

    collection = Option(
        doc="""
                **Syntax:** **collection=***<feature>*
                **Description:** The collection to delete from """,
        require=True,
    )

    time_field = Option(
        doc="""
                **Syntax:** **time_field=***<feature>*
                **Description:** The field to check num_days_back on""",
        require=True,
    )

    num_days_back = Option(
        doc="""
                **Syntax:** **num_days_back=***<feature>*
                **Description:** Number of days back to start deleteing""",
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

    def generate(self):
        """This is the entry point to a GeneratingCommand subclass. You must override this method

            :return: generator rows to pass on to next command of SPL search after transform
        """
        self.dt_log = DTLogger(
            "iris_enrich", os.path.basename(__file__), self.get_user(), self.feature
        )  # No product
        self.dt_log.info("starting expire_cache.py")

        # You can see stacktraces from this in the GUI under the search bar and to the right Job->Inspect Job
        # Scroll to the bottom and expand > Search Job Properties, scroll to the bottom and you will find the search.log

        try:
            # Get number of days to delete past
            retention_days = 30  # 30 by default
            if self.num_days_back:
                retention_days = int(self.num_days_back)
            else:
                jobs = self.service.jobs
                job = jobs.create(
                    "| stats count | eval retention_days =`dt_cache_retention_period` | fields retention_days"
                )

                while True:
                    while not job.is_ready():
                        pass
                    if job["isDone"] == "1":
                        break
                    time.sleep(1)

                for result in results.ResultsReader(job.results()):
                    try:
                        retention_days = int(
                            result["retention_days"]
                        )  # Only one result obv
                    except ValueError as e:
                        pass  # We will just fall back to default, logs will show the number we used
                    except IndexError as e:
                        pass

            # Stored from time.time() so we have to datetime to calculate the day, and then back to timestamp
            meow = datetime.datetime.fromtimestamp(time.time())
            days_ago = meow - datetime.timedelta(days=retention_days)
            days_ago_timestamp = time.mktime(days_ago.timetuple())

            # If dt_retrieved is less than days_ago_timestamp delete it
            query = json.dumps({self.time_field: {"$lt": days_ago_timestamp}})

            # /servicesNS/{owner}/{app}/storage/collections/data/{collection}
            delete_cache = self.service.delete(
                path_segment="/servicesNS/nobody/{0}/storage/collections/data/{1}".format(
                    APP_ID, self.collection
                ),
                query=query,
            )

            status_message = "Expire Iris Enrich Data past {0} days status: {1}: {2}".format(
                str(retention_days), delete_cache.status, delete_cache.reason
            )

            yield ({"status": status_message})
            self.dt_log.info(status_message)
        except NotAuthorizedException as e:
            self.dt_log.error(e, {"status": "expire cache down"})
            raise Exception(dt_exception_messages.not_autorized)
        except ServiceUnavailableException as e:
            self.dt_log.error(e, {"status": "expire cache down"})
            raise Exception(dt_exception_messages.service_not_available)
        except requests.exceptions.ProxyError as e:
            self.dt_log.error(e, {"status": "expire cache down"})
            raise Exception(dt_exception_messages.proxy_error)
        except requests.exceptions.SSLError as e:
            self.dt_log.error(e, {"status": "expire cache down"})
            raise Exception(dt_exception_messages.ssl_error.format(e))
        except Exception as e:
            self.dt_log.error(e, {"status": "expire cache down"})
            raise Exception(dt_exception_messages.generic.format(e))

        self.dt_log.info("Completed expire_cache.py")


dispatch(ExpireCacheCommand, sys.argv, sys.stdin, sys.stdout, __name__)
