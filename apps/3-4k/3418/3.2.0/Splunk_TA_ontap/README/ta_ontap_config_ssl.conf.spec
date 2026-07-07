[general]
ciphers = <string>
* Ciphers will be appended to default ciphers(ssl._DEFAULT_CIPHERS), if python version of Splunk is greater than or equal to 2.7.13
* Set to a string in the OpenSSL cipher list format

validate_ssl_certificate = <bool>
* Whether or not to enable SSL certificate validation.
* Set true to enable SSL certificate validation.
* Defaults to false.