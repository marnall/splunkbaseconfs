TA_Zimbra v0.0.2
----------------

GETTING ZIMBRA DATA IN
----------------------
It is a requirement to have the following add-ons installed:

Splunk-TA-nix (https://splunkbase.splunk.com/app/833/).  This will help parsing on syslog data.

Splunk Add-on for NGINX (https://splunkbase.splunk.com/app/3258/). Used for the proxy logs.

Splunk Add-on for Apache Web Server(https://splunkbase.splunk.com/app/3186/).  Used for Z-Push Logs (if using Apache as the web server) for CIM compliance

Install Universal forwarder on each Zimbra server and configure inputs.conf as follows (rename index to whatever is applicable):

GLOBAL LOGS (configure on all servers)
--------------------------------------
[monitor:///var/log/zimbra.log]  
index=zimbra  
sourcetype=zimbra:zsyslog

[monitor:///var/log/audit.log]  
index=zimbra  
sourcetype=zimbra:auditlog

[monitor:///var/log/maillog]  
index=zimbra  
sourcetype=zimbra:postfix


MAILBOX SERVER
--------------
NOTE: In multi server environment we need to make some changes on the proxy to send the X-Forwarded-For field and then to show X-Forwarded-For IP address in the Zimbra logs

Configure your external proxy to send the X-Forwarded-For data (out of scope of this doc)

Perform the following as Zimbra user.

1. Check that Zimbra is configured to recieve X-Forwarded-For
   zmlocalconfig zimbra_http_originating_ip_header
   Expected Result : zimbra_http_originating_ip_header = X-Forwarded-For
   
2. Get current list of trusted proxies
   zmprov gcf zimbraMailTrustedIP

3. Add trusted Proxies (inc localhost).
   zmprov mcf +zimbraMailTrustedIP 127.0.0.1 +zimbraMailTrustedIP x.x.x.x +zimbraMailTrustedIP y.y.y.y 

4. Restart Mailbox service
   zmmailboxdctl restart

[monitor:///opt/zimbra/log/access_log.*]  
index=zimbra  
sourcetype=zimbra:mailbox:access 

[monitor:///opt/zimbra/log/mailbox.log]  
index=zimbra  
sourcetype=zimbra:mailbox

[monitor:///opt/zimbra/log/zmmailboxd.out]  
index=zimbra


MTA SERVER
----------

[monitor:///opt/zimbra/log/freshclam.log]  
index=zimbra  
sourcetype=zimbra:clamd:updates

[monitor:///opt/zimbra/log/clamd.log]  
index=zimbra  
sourcetype=zimbra:clamd

[monitor:///opt/zimbra/log/spamtrain.log]  
index=zimbra


PROXY SERVER
------------
NOTE: If in a multi server environment, behind another proxy (e.g. Nginx) you need to configure sending the X-Forwarded-For field and we need alter the Zimbra config to show the real IP address of the source.

Configure your external proxy to send the X-Forwarded-For data (out of scope of this doc)

1. On Zimbra proxy server edit /opt/zimbra/conf/nginx/templates/nginx.conf.web.templates
2. Locate the logging section and hash out the default log profile and add a new one.  
   
    #FIND THIS LINE (the original log template)  
    log_format upstream '$remote_addr:$remote_port - $remote_user [$time_local]  '
      '"$request_method $scheme://$host$request_uri $server_protocol" $status $bytes_sent '
      '"$http_referer" "$http_user_agent" "$upstream_addr" "$server_addr:$server_port"';
    
    #HASH THIS LINE OUT  
    #access_log ${web.logfile} upstream;

    #THIS IS THE CUSTOM LOG FORMAT WE USE SO ADD THIS    
    log_format upstream_post_proxy '$http_x_forwarded_for - $remote_user [$time_local]  '
      '"$request_method $scheme://$host$request_uri $server_protocol" $status $bytes_sent '
      '"$http_referer" "$http_user_agent" "$upstream_addr" "$upstream_status" "$server_addr:$server_port" - "$http_cookie"';
      
	#ENABLE THIS NEW LOG PROFILE  
    access_log ${web.logfile} upstream_post_proxy;


[monitor:///opt/zimbra/nginx.access.log]  
index=zimbra  
sourcetype=zimbra:proxy

[monitor:///opt/zimbra/nginx.error.log]  
index=zimbra  
sourcetype=nginx:plus:error

[monitor:///opt/zimbra/nginx.log]  
index=zimbra

Z-PUSH SERVER
-------------
Notes : If running Z-Push on Apache behind a proxy (Nginx, etc), enable the proxy to pass the X-Forwarded-For header. Follow these steps to show the "real" IP in the Apache logs.

1. Create custom Log format in httpd.conf (note %a for client instead of %h, this is used to capture the X-Forwarded-For address:   
	LogFormat "time=%{%s}t.%{usec_frac}t, bytes_in=%I, bytes_out=%O, cookie=\"%{Cookie}i\", server=%v, dest_port=%p, http_content_type=\"%{Content-type}i\", http_method=\"%m\", http_referrer=\"%{Referer}i\", http_user_agent=\"%{User-agent}i\", ident=\"%l\", response_time_microseconds=%D, client=%a, status=%>s, uri_path=\"%U\", uri_query=\"%q\", user=\"%u\"" splunk_kv
		
2. Assign log profile to your SSL configure (ssl.conf):  
	CustomLog logs/ssl_splunk_access_log splunk_kv
		
3. Alter default SSL Request Log to use %a instead of %h  
	CustomLog logs/ssl_request_log "%t %a %{SSL_PROTOCOL}x %{SSL_CIPHER}x \"%r\" %b"


inputs.conf

[monitor:///var/log/httpd/ssl_splunk_access_log]  
index=zimbra  
sourcetype=apache:access:kv <--If using Apache as the Z-Push web server.

[monitor:///var/log/httpd/ssl_*_log]  <-- No Sourcetype specified.  Splunk will sort the remaining logs.  
index=zimbra


CHANGES IN THIS VERSION  
-----------------------   
Added ingestion for Z-Push  
Documentation on how to get real IP address in logs if behind proxy  
CIM compliance work on web logs  
Tidied up this doc to be more friendly with markdown views (e.g. Okular)

FUTURE RELEASE PLANS
--------------------
Further CIM compliance  
Accompanying App is in development and will be released soon.

BUILD NOTES
-----------
This add-on was built on Splunk Enterprise v9.0.1 but will work with 8.x  
This add-on was configured against a multi-server Zimbra Open Source installation running v8.8.15_GA_4372
