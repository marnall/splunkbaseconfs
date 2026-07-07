import json
import splunk.Intersplunk
import sys
import logger_manager as log
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration

logger = log.setup_logging('ta_flashpoint_intelligence_mentions')
results, _, _ = splunk.Intersplunk.getOrganizedResults(sys.stdin)

URL_VAL = "https://app.flashpoint.io/search/context/communities/"


@Configuration()
class MentionDetail(StreamingCommand):
    """This class will used for custom command."""

    def stream(self, events):
        """Stream the data to Splunk."""
        for data in results:
            try:
                dict_for_mention = {}
                time = data.get("_time", "N/A")
                data = json.loads(data.get("_raw", "{}"))
                dict_for_mention["_time"] = time
                dict_for_mention["Site Type"] = data.get("type", "N/A")
                dict_for_mention["Site Title"] = data.get("site_title", "N/A")
                dict_for_mention["_mention_fpid"] = data.get("id", "N/A")
                dict_for_mention["_container_fpid"] = data.get("container_id", "N/A")
                dict_for_mention["_timestamp"] = data.get("sort_date", "N/A")
                dict_for_mention["_url_to_redirect"] = URL_VAL + data.get("id")
                for cve_fpid_title in data.get("enrichments", {}).get("cve_ids", []):
                    dict_for_mention["CVE Title"] = cve_fpid_title
                    yield dict_for_mention
            except Exception as e:
                logger.exception("Exception occurred: {}".format(e))


dispatch(MentionDetail, sys.argv, sys.stdin, sys.stdout, __name__)
