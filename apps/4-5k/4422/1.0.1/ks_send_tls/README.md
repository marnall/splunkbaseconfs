# Splunk to shipper with TLS!

This is a simple Splunk application that sends a JSON alert on a TLS port on each Splunk Alert triggered

The script is invoked and gets the payload from stdin.
It will then get shipper_host and shipper_port from the configuration and push the payload to the shipper.

We use a logstash with a TCP input plugin and TLS active as the server.

## Build

You'll need to install `slim` and `splunk-appinspect`

* Slim: http://dev.splunk.com/view/packaging-toolkit/SP-CAAAE96
* Splunk-appinspect: http://dev.splunk.com/view/appinspect/SP-CAAAFAK

Then run:
```
cd misc
slim package splunkapp
splunk-appinspect inspect splunkapp-1.0.0.tar.gz
```

## Test

Start a logstash (cfc-shipper) then call the script:

`python2.7 ks_send_tls/bin/ks_send_tls.py --test '{"results_file": {"test": 2}, "configuration": 
{"shipper_host": "localhost", "shipper_port": 6326, "snow_alerting_domain": "company name", "shipper_certificate":"-----BEGIN CERTIFICATE----- MIIC9zCCAd... -----END CERTIFICATE-----"}}'`

**Note:** shipper_certificate MUST be a PEM certificate flattened on one line with spaces between each lines 
(instead of new lines).

For example

```
-----BEGIN CERTIFICATE-----
MIIC9zCCAd+gAwIBAgIJAKYfVCZsf8l9MA0GCSqGSIb3DQEBCwUAMBIxEDAOBgNV
BAMMB3NoaXBwZXIwHhcNMTgxMDExMTUxOTI0WhcNMjgwODE5MTUxOTI0WjASMRAw
...
DxbspQgGswSkZZHuvFjdKNWEl2JmolYR7FmCZELHdmICNObeWbYBRLo1xw==
-----END CERTIFICATE-----
```

becomes:

`
-----BEGIN CERTIFICATE----- MIIC9zCCAd+gAwIBAgIJAKYfVCZsf8l9MA0GCSqGSIb3DQEBCwUAMBIxEDAOBgNV BAMMB3NoaXBwZXIwHhcNMTgxMDExMTUxOTI0WhcNMjgwODE5MTUxOTI0WjASMRAw ... DxbspQgGswSkZZHuvFjdKNWEl2JmolYR7FmCZELHdmICNObeWbYBRLo1xw== -----END CERTIFICATE----- 
`

Using `tr`: `cat multiline_cert.pem | tr '\r\n' ' '`

