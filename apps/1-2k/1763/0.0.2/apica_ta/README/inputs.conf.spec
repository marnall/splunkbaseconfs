[apica://<name>]

* Endpoint
endpoint= <value>

* HTTP calls (Currently 'read only' supported i.e.  GET)
http_method = <value>

* Authentication type [basic | none ]
auth_type= <value>

* For basic/digest
auth_user= <value>

* for basic/digest
auth_password= <value>

* ie: (http://10.10.1.10:3128 or http://user:pass@10.10.1.10:3128 or https://10.10.1.10:1080 etc...)
http_proxy= <value>
https_proxy= <value>

*Time to stall for timeout in seconds
request_timeout= <value>

* time to wait for reconnect after timeout or error
backoff_time = <value>

*in seconds
polling_interval= <value>


*The sourcetype to use, defaults to apica. If you don't want this data parsed by splunk set to anything other than this
sourcetype=apica






