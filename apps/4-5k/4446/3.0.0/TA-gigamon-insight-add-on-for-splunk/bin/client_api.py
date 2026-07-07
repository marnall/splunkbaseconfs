import requests
from IPy import IP

default_timeout = 30
default_verify = False
class InsightAPI(object):

    def __init__(self, api_key, user_agent):
        self.api_key = api_key
        self.user_agent = user_agent
        self.headers = {
            "Authorization": 'IBToken ' + self.api_key,
            "user-agent": self.user_agent,
            "content-type": 'application/json'

        }

    def make_url(self,
                 api: str = None,
                 env: str = None,
                 sld: str = "icebrg",
                 version: int = None,
                 endpoint: str = None):
        api_string = 'https://{}{}.{}.io/v{}/{}'
        if env is None:
            env = ""
        else:
            env = '-' + env
        return api_string.format(api, env, sld, version, endpoint)

    def get_events(self, helper, query, order, start_date, end_date,
                   timeout=default_timeout,
                   verify=default_verify, **kwargs):

        url = self.make_url(api="events",
                            version=2,
                            endpoint="query")

        payload = {"query": query,
                   "order": order,
                   "start_date": start_date,
                   "end_date": end_date}
        payload.update(kwargs)
        response = helper.send_http_request(url, method="POST",
                                            payload=payload,
                                            headers=self.headers,
                                            timeout=timeout,
                                            verify=verify)
        return response

    def get_detections(self, helper, timeout=default_timeout,
                       verify=default_verify, **kwargs):

        url = self.make_url(api="detections",
                            version=1,
                            endpoint="detections")
        params = {}
        params.update(kwargs)
        response = helper.send_http_request(url,
                                            method="GET",
                                            parameters=params,
                                            headers=self.headers,
                                            timeout=timeout,
                                            verify=verify)
        return response

    def get_detection_rule_events(self,
                                  helper,
                                  uuid,
                                  account_uuid,
                                  timeout=default_timeout,
                                  verify=default_verify):

        url = self.make_url(api="detections",
                            version=1,
                            endpoint='rules/' + uuid + '/' + 'events')

        params = {
            "account_uuid": account_uuid
        }
        response = helper.send_http_request(url,
                                            method="GET",
                                            parameters=params,
                                            headers=self.headers,
                                            timeout=timeout,
                                            verify=verify)
        return response

# entity API
    def get_entity_summary(self, helper, entity, timeout=default_timeout,
                           verify=default_verify):

        url = self.make_url(api="entity",
                            version=1,
                            endpoint='entity/' + entity + '/' + 'summary')
        summary_response = helper.send_http_request(url,
                                                    method="GET",
                                                    headers=self.headers,
                                                    timeout=timeout,
                                                    verify=verify)
        return summary_response

    def get_entity_pdns(self, helper, entities, filter_training=None,
                        timeout=default_timeout,
                        verify=default_verify):
        # Build pdns data dictionary
        pdns_data = {}
        # Iterate through each entity for pdns info
        for i in range(0, len(entities)):
            url = self.make_url(api="entity",
                                version=1,
                                endpoint='entity/' + entities[i] + '/' + 'pdns')
            response = helper.send_http_request(url,
                                                method="GET",
                                                headers=self.headers,
                                                timeout=timeout,
                                                verify=verify)
            # Check the response stats for success
            response.raise_for_status()
            # Convert response to json
            resp_data = response.json()
            # Remove training environment enrichment if necessary
            pdns = []
            for data in resp_data['passivedns']:
                if filter_training:
                    if data['account_uuid'] != 'f6f6f836-8bcd-4f5d-bd61-68d303c4f634':
                        pdns.append(data)
                else:
                    pdns.append(data)
            pdns_data[entities[i]] = pdns
        return pdns_data

    def get_entity_dhcp(self, helper, entities, filter_training=None,
                        timeout=default_timeout,
                        verify=default_verify):
        # Build dhcp data dictionary
        dhcp_data = {}
        # Iterate through each entity for DHCP info
        for i in range(0, len(entities)):
            # If entity is a private IP, continue with DHCP lookup
            ip = IP(entities[i])
            if ip.iptype() == 'PRIVATE':
                url = self.make_url(api="entity",
                                    version=1,
                                    endpoint='entity/' + entities[i] + '/' + 'dhcp')

                response = helper.send_http_request(url,
                                                    method="GET",
                                                    headers=self.headers,
                                                    timeout=timeout,
                                                    verify=verify)
                # Check the response stats for success
                response.raise_for_status()
                # Convert response to json
                resp_data = response.json()
                # Remove training environment enrichment if necessary
                dhcp = []
                for data in resp_data['dhcp']:
                    if filter_training:
                        if data['customer_id'] != 'chg':
                            dhcp.append(data)
                    else:
                        dhcp.append(data)
                dhcp_data[entities[i]] = dhcp
        return dhcp_data
