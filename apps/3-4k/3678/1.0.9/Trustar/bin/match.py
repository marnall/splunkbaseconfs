import sys
import os
import time
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import splunk.search as splunk_search
import logger_manager as log
import splunk.Intersplunk

logger = log.setup_logging('trustar_match')
app_name = __file__.split(os.sep)[-3]
results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
sessionKey = settings.get("sessionKey")


@Configuration(local=True)
class matchCommand(StreamingCommand):
    type = Option(doc='''**Syntax:** **type=***<entity>* **Description:** Name of the type to match fields''', require=True,
                       validate=validators.Fieldname())

    def stream(self, events):
        ioc_type = self.type
        try:
            indicators_list = splunk_search.searchAll(
                "| inputlookup trustar_all_indicators_cumulative_lookup where type=\"{}\" | table value".format(ioc_type), sessionKey=sessionKey, namespace=app_name)
            for event in results:
                matched_ioc = list()
                for indicator in indicators_list:
                    value = str(indicator["value"]).replace("\\\\", "\\")
                    if value in event['_raw']:
                        matched_ioc.append(indicator["value"])

                event["_time"] = int(time.time())
                event["type"] = ioc_type
                event["value"] = matched_ioc
                yield event
        except Exception as e:
            logger.error("TruSTAR 'match' command error: %s" % str(e))

dispatch(matchCommand, sys.argv, sys.stdin, sys.stdout, __name__)
