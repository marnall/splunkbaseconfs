from __future__ import absolute_import
import os
import sys
import json
import requests
import time
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
from dt_api_wrapper import DtApiWrapper
from dt_logger import DTLogger
from domaintools.exceptions import (
    ServiceException,
    NotAuthorizedException,
    ServiceUnavailableException,
    InternalServerErrorException
)
import dt_exception_messages


@Configuration()
class IrisInvestigateCommand(GeneratingCommand):
    """This custom search command makes a request to the iris-investigate API endpoint and appends the data to given domains.

        Inherits from the GeneratingCommand custom search type. Override the `generate` method as the entrypoint to this script

        Example:
            | dtirisinvestigate domain=domaintools.com
    """

    domain = Option(require=False, default=False)
    pivot_type = Option(require=False, default=False)
    pivot_value = Option(require=False, default=False)
    no_cache = Option(require=False, default=False)
    table_error = Option(require=False, default=False)
    feature = Option(
        doc="""
                **Syntax:** **feature=***<feature>*
                **Description:** Feature in the app where this was called""",
        default="adhoc",
        require=False,
    )

    def get_user(self):
        """get current logged in user"""
        return self.metadata.searchinfo.username

    def get_cached_record(self, splunk_service, query):
        cache = splunk_service.get(
            path_segment="/servicesNS/nobody/{0}/storage/collections/data/dt_iris_investigate".format(APP_ID),
            query=query
        )

        return json.loads(cache.body.read())

    def should_use_cache(self, cached_record):
        '''
        only use cache for non domain pivots
        only use cache if a cached result exists
        don't use cache if user wants to skip cache
        '''
        return not self.domain and not self.no_cache and cached_record

    def handle_error(self, exception, error_message, options={"status": "down"}):
        self.dt_log.error(exception, options)
        if self.table_error:
            yield {"message": error_message}
        else:
            raise Exception(error_message)

    def generate(self):
        """This is the entry point to a GeneratingCommand subclass. You must override this method

            :return: generator rows to pass on to next command of SPL search after transform
        """
        self.dt_log = DTLogger(
            "iris_investigate",
            os.path.basename(__file__),
            self.get_user(),
            self.feature,
        )
        self.dt_log.info("starting iris_investigate.py")

        cached_record = None
        if not self.domain: # Only use cache for pivot, not domain profile
            if self.pivot_type and self.pivot_value:
                query = json.dumps({ "$and": [ {"dt_pivot_type":self.pivot_type} , {"dt_pivot_value":self.pivot_value} ]})
                cached_record = self.get_cached_record(self.service, query)

            else:
                raise Exception("You must either provide a 'domain' or 'pivot_type' and 'pivot_value'")

        if self.should_use_cache(cached_record):
            self.dt_log.info("Using Iris Investigate cache for {0}={1}".format(self.pivot_type, self.pivot_value))
            for result in cached_record[0]["dt_investigate_raw"]:
                yield {"domain": result["domain"], "_raw": json.dumps(result), "cache": True}
        else:
            api_wrapper = DtApiWrapper(self.service, self.dt_log)
            api = api_wrapper.create_dt_api()
            missing_domains = None

            try:
                if self.domain:
                    self.dt_log.info("Querying Iris Investigate api for {0}".format(self.domain))
                    response = api.iris_investigate(self.domain).response()
                else:
                    self.dt_log.info("Querying Iris Investigate api for {0}={1}".format(self.pivot_type, self.pivot_value))
                    kwargs = {self.pivot_type: self.pivot_value}
                    response = api.iris_investigate(**kwargs).response()
                
                if not self.domain:
                    # Save to cache
                    body = json.dumps({
                            "dt_pivot_type": self.pivot_type, 
                            "dt_pivot_value": self.pivot_value, 
                            "dt_investigate_raw": response.get("results"),
                            "_dt_created": time.time()})
                    kwargs = {'body': body}
                    self.service.post(
                        path_segment="/servicesNS/nobody/{0}/storage/collections/data/dt_iris_investigate".format(APP_ID),
                        headers=[('Content-Type', 'application/json')],
                        **kwargs
                    )

                missing_domains = response.get("missing_domains")

                for result in response.get("results"):
                    yield {"domain": result["domain"], "_raw": json.dumps(result), "cache": False}
               
                self.dt_log.info("api status up", {"status": "up"})
            except NotAuthorizedException as e:
                yield from self.handle_error(e, dt_exception_messages.not_autorized)
            except ServiceUnavailableException as e:
                yield from self.handle_error(e, dt_exception_messages.service_not_available)
            except InternalServerErrorException as e:
                yield from self.handle_error(e, dt_exception_messages.search_hash_error)
            except requests.exceptions.ProxyError as e:
                yield from self.handle_error(e, dt_exception_messages.proxy_error)
            except requests.exceptions.SSLError as e:
                yield from self.handle_error(e, dt_exception_messages.ssl_error.format(e))
            except Exception as e:
                yield from self.handle_error(e, dt_exception_messages.generic.format(e))

            if missing_domains:
                message = dt_exception_messages.missing_domains.format(",".join(missing_domains))
                exception = Exception(message)
                yield from self.handle_error(exception, message, {"code": "EAL204"})

        
        self.dt_log.info("completed iris_investigate.py")

dispatch(IrisInvestigateCommand, sys.argv, sys.stdin, sys.stdout, __name__)
