import risksense_util as util

class RisksenseConnect(object):
    def __init__(self, helper, account, finding_type):
        '''
        Initialize connection parameters.

        :param helper: object of BaseModInput class
        :param account: Risksense account details
        :param finding_type: Type of finding hosts / Applications
        '''
        # Get the session object having retry mechnaism
        self.session = util.requests_retry_session()
        self.filters = helper.get_arg('filters')
        self.page_size = helper.get_arg('page_size')

        token = account.get('token')
        platform_url = account.get('platform_url')
        self.client_ids = account.get('client_id').strip().split(",")
        self.urls = util.make_risksense_url(platform_url, finding_type, self.client_ids)
        self.client_url = util.make_risksense_url(platform_url, "clients")

        self.headers = {
            "content-type": "application/json",
            "x-api-key": token
        }

        self.payload = {
            "page": 0,
            "size": self.page_size,
            "projection": "detail",
            "filters": util.prepare_filters(helper, self.filters)
        }

        proxy_settings = helper.get_proxy()
        proxy_enabled = True if proxy_settings else False
        self.proxies = util.create_requests_proxy_dict(proxy_enabled, proxy_settings)
