# This is an example webhooks.conf. Use this file to configure
# webhook episode action.
#
# To use one or more of these configurations, copy the configuration block
# into webhooks.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/local.  
# You must restart Splunk to enable configurations.
# Or simply use UI to create/update/delete the webhooks.
#
# To learn more about configuration files please see
# the documentation located at
# <Link of documentation>
#
# This example is for webhook.


[<webhook name>]
uri = <string> Webhook URL, for example, https://myaccount.com.
username = <string> Webhook account username.
description = <string> Webhook description.
auth_type = <string> Type of authentication used. {No Auth|Bearer Token|Basic Auth}
should_ssl_verified = <bool> Whether to disable SSL certificate validation or not.
allowed_ips = <string> Optional. Comma-separated list of IP addresses to use for the webhook request.
    * When configured, these IPs are used directly without DNS lookup, allowing private/internal IPs.
    * When not configured, DNS lookup is performed and only public IPs are allowed.
    * Supports failover - if first IP fails, tries next IP in the list.
    * Example: 192.168.1.100, 192.168.1.101, 10.0.0.50
header = <string> Optional. Custom HTTP headers to include in the webhook request.
    * Format: JSON object with header name-value pairs.
    * Example: {"Content-Type": "application/json", "X-Custom-Header": "value"}
