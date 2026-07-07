[zoom_input://<name>]
cert_file = The path to the SSL certificate file (if you want to use encryption); typically uses .DER, .PEM, .CRT, .CER file extensions. (Default: /opt/splunk/etc/auth/splunkweb/cert.pem)
disable_redaction = By default, all the sensitive info is removed before from the event before ingesting. To ingest the event as it is, tick this box.
disable_verification = By default, only the requests coming from Zoom are accepted. Anything else is rejected with 403 UNAUTHORIZED response. If you want to override this behaviour and accept the underlying risk, check in given field.
dump_requests = 
index = (Default: default)
key_file = The path to the SSL certificate key file (if the certificate requires a key); typically uses .KEY file extension. (Default: /opt/splunk/etc/auth/splunkweb/privkey.pem)
port = The port to run the input on. (Default: 4443)
secret = Secret to use for this input.
