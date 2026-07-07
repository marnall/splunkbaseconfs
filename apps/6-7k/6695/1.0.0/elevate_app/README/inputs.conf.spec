#
# Spec file for Elevate Modular Input for polling the Elevate REST API
#
# October 2022
#
# Developed by BaboonBones, Ltd. ( www.baboonbones.com ) for Elevate Security

[elevate_rest://<name>]

* Elevate Service Endpoint to poll
endpoint= <value>

* prop=value, prop2=value2
http_header_propertys= <value>

* arg=value, arg2=value2
url_args= <value>

* ie: (https://10.10.1.10:3128 or https://user:pass@10.10.1.10:3128)
https_proxy= <value>

*in seconds
request_timeout= <value>

* time to wait for reconnect after timeout or error
backoff_time = <value>

* values are 0 for false | 1 for true
streaming_request= <value>

* in seconds or a cron syntax
polling_interval= <value>

* whether or not to index http error response codes
index_error_response_codes= <value>

*Python classname of custom response handler
response_handler= <value>

*Response Handler arguments string ,  key=value,key2=value2
response_handler_args= <value>

*Python Regex pattern, if present , the response will be scanned for this match pattern, and indexed if a match is present
response_filter_pattern = <value>

*Delimiter to use for any multi "key=value" field inputs
delimiter= <value>

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
