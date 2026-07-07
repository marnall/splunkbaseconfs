[rest://<name>]


* If you require an encrypted credential in your configuration , then you can enter it on the App's setup page.

* Then in your configration stanza refer to it in the format {encrypted:somekey}

* Where "somekey" is any value you choose to enter on the setup page

* EXAMPLES
* endpoint = http://foo.com/{encrypted:somekey}
* http_header_propertys = authkey={encrypted:somekey}
* url_args = mysecret={encrypted:somekey} 


* REST API Endpoint URL
endpoint= <value>

* You require an activation key to use this App. Visit http://www.baboonbones.com/#activation to obtain a non-expiring key
activation_key = <value>

* HTTP Method (GET,HEAD,POST,PUT)
http_method = <value>

* Request Payload for POST and PUT
request_payload = <value>

* Authentication type [none | basic | digest | oauth1 | oauth2 | custom ]
auth_type= <value>

* for basic/digest
auth_user= <value>

* for basic/digest
auth_password= <value>

*oauth1 params
oauth1_client_key= <value>
oauth1_client_secret= <value>
oauth1_access_token= <value>
oauth1_access_token_secret= <value>

*oauth2 params
oauth2_token_type= <value>
oauth2_expires_in= <value>
oauth2_access_token= <value>
oauth2_refresh_token= <value>
oauth2_refresh_url= <value>
oauth2_refresh_props= <value>
oauth2_client_id= <value>
oauth2_client_secret= <value>

# HEADER | BODY , configure if the client_id/client_secret is sent in the Base64 encoded  Basic Authentication header (default) or in the request body
oauth2_refresh_client_placement= <value>

#authorization_code | password | client_credentials
oauth2_grant_type= <value>

*Enable this to verify Server and Client Certificates using the default bundled "certifi" CA Bundle , values are 0 for false | 1 for true , https://requests.readthedocs.io/en/master/user/advanced/#ssl-cert-verification
verify= <value>

*Full path to your CA Bundle if you don't want to use the default bundled "certifi" CA Bundle ie: /path/to/cacert.pem, https://requests.readthedocs.io/en/master/user/advanced/#ssl-cert-verification
ca_bundle_path= <value>

*Full path to your client certificate ie: /path/to/client.crt
client_cert_path= <value>

*Full path to your unencrypted private key ie: /path/to/client.key
client_key_path= <value>

*Alternatively to declaring your certificate and key seperately above , you can enter the full path to your bundled client certificate/unencrypted private key file ie: /path/to/client.pem
client_bundled_path= <value>

* prop=value, prop2=value2
http_header_propertys= <value>

* arg=value, arg2=value2
url_args= <value>

* Response type [json | text]
response_type= <value>

* values are 0 for false | 1 for true
streaming_request= <value>

* ie: (http://10.10.1.10:3128 or http://user:pass@10.10.1.10:3128 or https://10.10.1.10:1080 etc...)
http_proxy= <value>
https_proxy= <value>

*in seconds
request_timeout= <value>

* time to wait for reconnect after timeout or error
backoff_time = <value>

* in seconds or a cron syntax
polling_interval= <value>

* whether multiple requests spawned by tokenization are run in parallel or sequentially. Defaults to false (0)
sequential_mode= <value>

* an optional stagger time period between sequential requests.Defaults to 0
sequential_stagger_time= <value>

* whether or not to index http error response codes
index_error_response_codes= <value>

*Python classname of custom response handler
response_handler= <value>

*Response Handler arguments string ,  key=value,key2=value2
response_handler_args= <value>

*Python Regex pattern, if present , the response will be scanned for this match pattern, and indexed if a match is present
response_filter_pattern = <value>

*Python classname of custom auth handler
custom_auth_handler= <value>

*Custom Authentication Handler arguments string ,  key=value,key2=value2
custom_auth_handler_args= <value>

*Delimiter to use for any multi "key=value" field inputs
delimiter= <value>

*For persisting Cookies
cookies= <value>

* Modular Input script python logging level for messages written to $SPLUNK_HOME/var/log/splunk/restmodinput_app_modularinput.log , defaults to 'INFO'
log_level= <value>





