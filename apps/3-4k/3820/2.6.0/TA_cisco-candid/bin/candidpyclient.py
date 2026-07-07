import requests
import copy
import candid_logger_manager as log
import json
import jsonpickle
import json_util
# _LOGGER = log.setup_logging("candid_data_collection")
import url_constants
# http_client.HTTPConnection.debuglevel = 1
#global verify
#verify=False
try:
    import urllib
    import httplib as http_client
except ImportError:
    import urllib.parse as urllib
    import http.client as http_client
try:
    from urllib3 import disable_warnings
    from urllib3.exceptions import InsecureRequestWarning
except ImportError:
    pass


class RestClient(object):
    def __init__(self, host_url, username, password, verify, domain_name,timeout):
        self.header_key_otp = None
        self.header_key_token = None
        self.host_url = host_url
        self.username = username
        self.password = password
        self.otp = None
        self.token = None
        self.jsessionid = None
        self.verify = verify
        self.domain = domain_name
        self.timeout = timeout
        if not self.verify:
            try:
                disable_warnings(InsecureRequestWarning)
            except Exception:
                pass
        self.login()

    def __enter__(self):
        host_url = self.host_url
        # print ("Logged on to candid server: " + self.host_url)

#    def __exit__(self, exc_type, exc_value, traceback):
#        self.logout()

#    def __del__(self):
#        self.logout()

    def post(self, payload, post_headers=None):
        if post_headers is not None:
            headers = post_headers
        else:
            headers = self.get_json_request_headers()

        headers[self.header_key_token] = self.token
        cookies = {'SESSION': self.jsessionid}
        # print("resp1")
        resp = requests.post(self.host_url, headers=headers, cookies=cookies, data=payload, verify=self.verify, timeout=self.timeout)
        return resp

    def post_files(self, files, post_headers=None):
        if post_headers is not None:
            headers = post_headers
        else:
            headers = self.get_json_request_headers()

        headers[self.header_key_token] = self.token
        cookies = {'SESSION': self.jsessionid}
        resp = requests.post(self.host_url, headers=headers, cookies=cookies, files=files, verify=self.verify, timeout=self.timeout)
        return resp

    def get(self, url, customHeaders=None):
        #print "URL_GET="+str(url)
        headers = self.get_json_request_headers()
        headers[self.header_key_token] = self.token
        cookies = {'SESSION': self.jsessionid}
        if customHeaders != None:
            # headers.update(customHeaders)
            for key in customHeaders:
                headers[key] = customHeaders[key]
        
        # url = self.host_url + url_constants.api_v1_url(url) + '/' + url
        resp = requests.get(url, headers=headers, cookies=cookies, verify=self.verify, timeout=self.timeout)
        return resp

    def put(self, payload):
        headers = self.get_json_request_headers()
        headers[self.header_key_token] = self.token
        cookies = {'SESSION': self.jsessionid}
        resp = requests.put(self.host_url, headers=headers, cookies=cookies, data=payload, verify=self.verify, timeout=self.timeout)
        return resp

    def delete(self, url):
        headers = self.get_json_request_headers()
        headers[self.header_key_token] = self.token
        cookies = {'SESSION': self.jsessionid}
        resp = requests.delete(self.host_url, headers=headers, cookies=cookies, verify=self.verify, timeout=self.timeout)
        return resp

    def get_json_request_headers(self):
        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        return copy.deepcopy(headers)

    def login(self):
        #print("WHO_AM_I_URL: " + self.get_who_am_i_url())
        # print("Headers: ")
        # print(self.get_json_request_headers())
        resp = requests.get(self.get_who_am_i_url(), headers=self.get_json_request_headers(), verify=self.verify, timeout=self.timeout)
        #print resp.json()
        if resp.status_code == 200:
            self.jsessionid = resp.cookies["SESSION"]
            if 'x-nae-login-otp' in resp.headers:
                self.header_key_otp = 'X-NAE-LOGIN-OTP'
                self.header_key_token = 'X-NAE-CSRF-TOKEN'
                self.otp = resp.headers[self.header_key_otp]
            else:
                self.header_key_otp = 'X-CANDID-LOGIN-OTP'
                self.header_key_token = 'X-CANDID-CSRF-TOKEN'
                self.otp = resp.headers[self.header_key_otp]
        else:
            resp.raise_for_status()

        headers = self.get_json_request_headers()
        headers[self.header_key_otp] = self.otp
        cookies = {'SESSION': self.jsessionid}
        if self.domain:
            body = {'username': self.username, 'password': self.password, 'domain': self.domain}
        else:
            body = {'username': self.username, 'password': self.password}
        resp = requests.post(self.get_login_url(), headers=headers, cookies=cookies, data=json.dumps(body), verify=self.verify, timeout=self.timeout)
        if resp.status_code == 200:
            self.token = resp.headers[self.header_key_token]
            self.jsessionid = resp.cookies["SESSION"]
            return self.token
        else:
            resp.raise_for_status()

    def logout(self):
        headers = self.get_json_request_headers()
        headers[self.header_key_token] = self.token
        cookies = {'SESSION': self.jsessionid}

        resp = requests.post(self.get_logout_url(), headers=headers, cookies=cookies, verify=self.verify, timeout=self.timeout)
        if resp.status_code != 200:
            resp.raise_for_status()
        #     print('logout successful')
        # else:


    def get_who_am_i_url(self):
        return self.host_url + url_constants.api_v1_url(url_constants.WHO_AM_I)

    def get_login_url(self):
        return self.host_url + url_constants.api_v1_url(url_constants.LOGIN)

    def get_logout_url(self):
        return self.host_url + url_constants.api_v1_url(url_constants.LOGOUT)

    def base_api_v1_url(self):
        return self.host_url + url_constants.API_V1

    def get_custom_response(self, url):
        """
        Calls rest client get. Also checks if all the pages needs to be fetched
        :return: response
        """
        # url = self.base_api_v1_url() + url
        # print 'get ' + url
        response = self.get(url)
        if "page=" in url or response.status_code != 200:
            # specific page is being requested, no more page to be fetched.
            return response
        else:
            # specific page not requested so need to get all pages until has_more_data is false
            # print 'get all pages for url ' + url
            page_num = 0
            page_content = response.content
            page_list = [page_content]
            content_obj = json.loads(page_content)
            has_more_data = content_obj['value']['data_summary']['has_more_data']
            while has_more_data is True:
                page_num += 1
                if "?" in url:
                    temp_url =  url+'&'+'$page='+str(page_num)
                else:
                    temp_url = url+'?'+'$page='+str(page_num)

                # print 'There is more data, getting page ' + str(page_num)
                response = self.get(temp_url)
                assert response.status_code == 200, response.content
                page_content = response.content
                page_list.append(page_content)
                content_obj = json.loads(page_content)
                has_more_data = content_obj['value']['data_summary']['has_more_data']

            custom_response = requests.Response()
            custom_response.url = url
            custom_response.status_code = response.status_code
            custom_response._content = json_util.merge_pages(page_list)
            return custom_response

    def get_endpoint_url(self, fabric_id=None, url=None):

        if url is not None:
            url = self.host_url + url_constants.api_v1_url(url)
            if fabric_id is not None:
                url = url.format(fabric_id)
                # print ("URL WITH FABRIC ID: " + url)
            return url
        else:
            return self.host_url + url_constants.API_V1
        
    def get_data_from_response(self, response):
        # print response
        nbapi_resp_obj = jsonpickle.decode(response.content)
        return nbapi_resp_obj.get('value', {}).get('data', [])


    def get_datasummary_from_response(self, response):
        # print response.content
        nbapi_resp_obj = jsonpickle.decode(response.content)
        return nbapi_resp_obj.get('value', {}).get('data_summary', [])


    def add_query_params_to_url(self, url, query_param_dict):
        if query_param_dict is not None:
            params = urllib.urlencode(query_param_dict)
            return url + "?" + params
        else:
            return url


def create_rest_client(username, password):
    """ create rest API connection
    :return: RestClient
    """
    # print("create_rest_client called")
    return RestClient(username, password)


def terminate_rest_client(restclient):
    """ clean up rest API connection
    :return: RestClient
    """
    # print("terminate_rest_client called")
    if restclient is not None:
        restclient.logout()
