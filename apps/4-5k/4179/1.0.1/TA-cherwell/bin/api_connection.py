

class Connection:

    def __init__(self, url, username, password, client_id, helper, proxy=False, ssl_verify=True):
        """ This method initializes an object of Connection class with required parameters.

        :param url: Cherwell instance URL
        :param username: Username of the provided account
        :param password: Password of the provided account
        :param client_id: Client ID of the provided account
        :param helper: Object of BaseModInput class
        :param proxy: Boolean value that signifies whether to use proxy or not
        :param ssl_verify: Boolean value that signifies whether to validate certificate or not
        """

        self.token = None
        self.headers = None
        self.url = url.strip('/') + "/CherwellApi"
        self.helper = helper
        self.username = username
        self.password = password
        self.client_id = client_id
        self.proxy = proxy
        self.ssl_verify = ssl_verify

    def connect(self):
        """ This method is used to login in the Cherwell instance and fetch the access token which is used to make
        subsequent requests to Cherwell.
        """

        # Prepare request payload
        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "username": self.username,
            "password": self.password
        }
        data = "&".join([each_param+"="+data[each_param] for each_param in data])

        # Make REST call to Cherwell instance
        response = self.helper.send_http_request(self.url+"/token", method="POST", parameters=None, payload=data,
                                                 headers=None, cookies=None, verify=self.ssl_verify, cert=None,
                                                 timeout=None, use_proxy=self.proxy)

        # Raise exception in case the http status code is other than 200
        if response.status_code != 200:
            if "error" in response:
                self.helper.log_error("[api_connection]: " + response.get("error_description", "")+":" +
                                      response.get("error", ""))
            raise Exception("[api_connection] rest_call to /token :Status code is not 200: status_code=%d"
                            % response.status_code)
            
        # Get response in json format
        response = response.json()
        self.helper.log_info("[api_connection]: Connected to Cherwell Instance..")
        # Get access token
        self.token = response.get("access_token")
        # Prepare headers for subsequent REST calls
        self.headers = {'Accept': 'application/json', "Content-Type": "application/json",
                        "Authorization": "Bearer " + self.token}
        return self.token

    def rest_call(self, method, url, data=None):
        """ This method implements logic to handle various get, post and delete REST requests and returns the response.
        In case of any error or response code other than 200 this method will raise an exception.

        :param method: HTTP method ex: GET/POST/PUT/DELETE
        :param url: Cherwell instance URL
        :param data: Payload that needs to be sent in the request
        :return:
        """

        # GET request
        if method.lower() == "get":
            response = self.helper.send_http_request(self.url + url + "?api_key=%s" % self.client_id, 
                                                     method="GET", parameters=None, payload=None,
                                                     headers=self.headers, cookies=None, verify=self.ssl_verify,
                                                     cert=None, timeout=None, use_proxy=self.proxy)
            
            if response.status_code != 200:
                self.helper.log_debug("[api_connection][response] %s" % response.text)
                raise Exception("[api_connection] rest_call to %s :Status code is not 200 : status_code=%d"
                                % (url, response.status_code))
            else:
                response = response.json()
                return response

        # POST request
        elif method.lower() == "post":
            response = self.helper.send_http_request(self.url + url + "?api_key=%s" % self.client_id, 
                                                     method="POST", parameters=None, payload=data,
                                                     headers=self.headers, cookies=None, verify=self.ssl_verify,
                                                     cert=None, timeout=None, use_proxy=self.proxy)
    
            if response.status_code != 200:
                self.helper.log_debug("[api_connection][response] %s" % response.text)                
                raise Exception("[api_connection] rest_call to %s :Status code is not 200 : status_code=%d"
                                % (url, response.status_code))
            else:
                response = response.json()
                return response

        # PUT request
        elif method.lower() == "put":
            raise Exception("rest_call: put: Not Implemented")

        # DELETE request
        elif method.lower() == "delete":
            response = self.helper.send_http_request(self.url + url + "?api_key=%s" % self.client_id, 
                                                     method="DELETE", parameters=None, payload=None,
                                                     headers=self.headers, cookies=None, verify=self.ssl_verify,
                                                     cert=None, timeout=None, use_proxy=self.proxy)

            if response.status_code != 200:
                self.helper.log_debug("[api_connection][response] %s" % response.text)
                raise Exception(str("[api_connection] rest_call to %s :Status code is not 200 : status_code=%d"
                                    % (url, response.status_code)))
            else:
                return True

    def close_session(self):
        """ This method logs out the user.
        """

        response = self.rest_call('delete', '/api/V1/logout')
        if response:
            self.helper.log_info("[api_connection] logged out")
