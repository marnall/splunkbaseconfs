# encoding utf-8
from rs_utility import requests_retry_session, make_risksense_url


class RisksenseConnect(object):
    def __init__(self, logger, client_id, token, platform_url, asset_type, filters, proxies):
        '''
        Initialize connection parameters.

        :param logger: Logger object
        :param client_id: Client id
        :param token: API token
        :param platform_url: RiskSense URL
        :param asset_type: Type of finding hosts / Applications
        :param filters: Custom Filters
        :param proxies: Proxy details
        '''
        # Get the session object having retry mechnaism
        self.session = requests_retry_session()
        self.filters = filters
        self.page_size = 500

        self.asset_type = "applicationFindings"
        if asset_type == "HOSTFINDINGS":
            self.asset_type = "hostFindings"

        self.client_id = client_id
        self.url = make_risksense_url(platform_url, self.asset_type, self.client_id)

        self.headers = {
            "content-type": "application/json",
            "x-api-key": token
        }

        self.payload = {
            "page": 0,
            "size": self.page_size,
            "projection": "internal",
            "filters": filters
        }

        self.proxies = proxies
        self.logger = logger