Introduction
------------
Welcome to the Splunk for Squid app! This app provides field extractions for Squid access logs as well as a dashboard and a request search interface.

This app is maintained by Patrik Nordlen <patrik@nordlen.se>. Suggestions and bug reports are appreciated.


Installation
------------
To install, extract the .spl file in $SPLUNK_HOME/etc/apps

You will need to enable the appropriate inputs, either via inputs.conf, or through the Manager in the Splunk GUI. Splunk for Squid expects Squid access logs to have a sourcetype of "squid".


Using Splunk for Squid
----------------------
-- Field extractions --

The most basic feature provided by this app is to extract fields from Squid access logs. The following fields are extracted:

    * duration (Time in milliseconds required for handling the request)
    * clientip (Client IP address)
    * action (Resulting action for a request, like TCP_HIT or TCP_MISS for instance)
    * http_status (The HTTP status returned for a request)
    * bytes (The amount of bytes returned to client, including headers)
    * method (HTTP method)
    * uri (Requested URI)
    * uri_host (Host portion of the requested URI)
    * uri_path (Path portion of the requested URI)
    * username (Username associated with the client connection)
    * hierarchy (Hierarchy data tags)
    * server_ip (The IP address of the destination host)
    * content_type (Content type for data returned)

These field extractions are applied to all logs with sourcetype "squid".


-- Request search --

The app includes a custom search interface for Squid requests, available under "Request search". This interface shows tables and statistics for requests handled by Squid.


-- Dashboards --

A traffic dashboard is provided, showing statistics over time for amount of requests and bandwidth consumed, as well as statistics concerning most prominent client IP addresses and destination sites.
