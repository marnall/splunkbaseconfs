import sys
from logger_module import Logger
from splunk_config_module import SplunkConfig
from api_handler import APIHandler


class BitdefenderFeedCollector:
    def __init__(self, script_location, log_file):
        self.logger = Logger(log_file_name=log_file).get_logger()
        self.splunk_config = SplunkConfig(script_location=script_location)
        self.session_key = sys.stdin.readline().strip()

        self.selected_permission = self.splunk_config.get_config('user_configuration', 'main', 'selected_permission')
        self.index_name = self.splunk_config.get_config('user_configuration', 'main', 'index')
        self.api_key = self.splunk_config.get_credentials("main", session_key=self.session_key)

        self.feeds = [
            {
                "name": "file-feed",
                "permission": "file_feed",
                "sourcetype": "bitdefender-file-feed",
                "primary_key": "sha256",
            },
            {
                "name": "web-feed",
                "permission": "web_feed",
                "sourcetype": "bitdefender-web-feed",
                "primary_key": "url",
            },
            {
                "name": "ip-feed",
                "permission": "ip_feed",
                "sourcetype": "bitdefender-ip-feed",
                "primary_key": "ip",
            }
        ]

        self.api_handler = APIHandler(self.logger)

    def collect_feeds(self):
        for feed in self.feeds:
            if feed["permission"] in self.selected_permission:
                self.logger.info(f"Data collection started for feed: {feed['name']}")
                self.api_handler.call_api(
                    api_key=self.api_key,
                    feed_id=feed["sourcetype"],
                    index_name=self.index_name,
                    session_key=self.session_key,
                    feed_name=feed["name"],
                    permission=feed["permission"],
                    ioc_key=feed["primary_key"]
                )
            else:
                self.logger.info(f"Permission not granted for feed: {feed['name']}. Skipping.")


def main():
    collector = BitdefenderFeedCollector(
        script_location=__file__,
        log_file="bitdefender_TI_index_ingestion.log"
    )
    collector.collect_feeds()


if __name__ == '__main__':
    main()
