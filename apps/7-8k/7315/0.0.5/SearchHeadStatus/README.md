## Introduction

This applications purpose is to provide a REST endpoint that can be used by a load balancer to check the search head status
The status is based on the response to the REST endpoint:
```/services/shcluster/member/info```

## Installation
This application only needs to be installed on a search head cluster, it is not useful on any other instance as the endpoint is not active

## How do I use this application?
You can hit the endpoint via curl, for example ```curl -k https://localhost:8089/services/searchheadstatus```

And this will return the response based on the internal REST call, such as "Up", or "ManualDetention"

## Are there alternatives?

As of Splunk 9.1.x, a new endpoint exists:
```/shcluster/member/ready```

You can use this via:
```curl -k https://localhost:8089/services/shcluster/member/ready```

or on the web port via:
```curl -k http://localhost:8000/en-GB/splunkd/__raw/services/searchheadstatus```

This is not documented as of the 2024-04-16 but may be documented in the future, it returns an XML response such as:
```
<?xml version="1.0" encoding="UTF-8"?>
<!--This is to override browser formatting; see server.conf[httpServer] to disable. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .-->
<?xml-stylesheet type="text/xml" href="/static/atom.xsl"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:s="http://dev.splunk.com/ns/rest" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <title>shclusterready</title>
  <id>https://localhost:8089/services/shcluster/member/ready</id>
  <updated>2024-04-13T15:50:05+10:00</updated>
  <generator build="d95b3299fa65" version="9.1.3"/>
  <author>
    <name>Splunk</name>
  </author>
  <opensearch:totalResults>0</opensearch:totalResults>
  <opensearch:itemsPerPage>30</opensearch:itemsPerPage>
  <opensearch:startIndex>0</opensearch:startIndex>
  <s:messages/>
</feed>
```

Or when the SHC member is in detention:
```
<?xml version="1.0" encoding="UTF-8"?>
<response>
  <messages>
    <msg type="ERROR">Search Head is in detention</msg>
  </messages>
</response>
```

This application was developed because such an endpoint didn't exist prior to 9.1.x

## Troubleshooting
### SSL validation errors
If you see an error such as:
`Caused by SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self signed certificate in certificate chain (_ssl.c:1106)')))`

or you see the response of:
`SSL_Verify_Error`

This simply means that the port 8089 is running an SSL certificate that is not trusted by the default certificate store in use by Splunk's python
You can change `verify=True` to `verify=False` in the bin/search_head_status.py file and this will bypass SSL validation of your local Splunk instance on port 8089 (note that this comes with a minor security risk)

## Feedback?
Feel free to open an issue on github or use the contact author on the [SplunkBase link](https://splunkbase.splunk.com/app/7315) and I will try to get back to you when possible, thanks!

## Other
Thanks to Harshil Marvania (harsmarvania57) for bringing the new endpoint to my attention.
Icons by Bing CoPilot

## Release Notes
### 0.0.5
Removed python SDK, it was not in use in this app

Updated status to return a 503 error if the status of the SHC member is not "Up", this makes it easier to use in an AWS ALB

### 0.0.4
Adding python.required in `restmap.conf` as requested by splunkbase, this is supported in 10.2 and above. Harmless warning messages may occur on older Splunk versions.

Updated Splunk python SDK to 2.1.1

### 0.0.3
Updated Splunk python SDK from 2.0.2 to 2.1.0 as per Splunk cloud compatibility requirements

### 0.0.2
Updated splunk python SDK from 2.0.1 to 2.0.2 as per Splunk cloud compatability requirements

### 0.0.1
Initial version

