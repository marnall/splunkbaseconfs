=== IBM Cloud Event Management Alert Action ===

Author: Jen Chyi, Chan

Version/Date: 1.0 / 20180211

Description: IBM Cloud Event Management Alert Action is a custom webhook trigger alert action for the user to define the Splunk search and result fields with the IBM Cloud Event Management

Usage: IBM Cloud Event Management Alert Action is a custom webhook trigger alert action for the user to define the Splunk search and result fields with the IBM Cloud Event Management (CEM) event format in the webhook payload. The user can use this custom alert action to define the resource name, resource type, event type, summary, severity and etc in the payload so that IBM CEM will create the incidents based on the these definition.

Limitations: 
  - N/A

License: 
  - IBM Splunk App for Cloud Event Management 1.0
  http://www-03.ibm.com/software/sla/sladb.nsf/displaylis/DC75D3A5A88A0F228525822E006BD748?OpenDocument

=== Example Payload ===

{
  "severity": "Major",
  "summary": "Linux1: CPU load exceeds 97.88 percent by host",
  "search_name": "CPU_Exceeds_Percent_by_Host",
  "custom": "statusOrThreshold:97.88,expiryTime:900,resource.service:nagios,resource.location:malaysia,url.test_url:http:://test.ibm.my,resolution:true",
  "app": "splunk_app_for_nix",
  "resourceName": "linux1",
  "resourceType": "Server",
  "eventType": "CPU Exceeds 90 Percent by host",
  "sid": "rt_scheduler__admin_c3BsdW5rX2FwcF9mb3Jfbml4__RMD5b25444ef25a3366d_at_1520408234_56.820",
  "owner": "admin",
  "results_link": "http://Linux1:8000/app/splunk_app_for_nix/@go?sid=rt_scheduler__admin_c3BsdW5rX2FwcF9mb3Jfbml4__RMD5b25444ef25a3366d_at_1520408234_56.820"  ,
  "result": {
    "host_count": "2",
    "sid": "rt_scheduler__admin_c3BsdW5rX2FwcF9mb3Jfbml4__RMD5b25444ef25a3366d_at_1520408234_56",
    "ip": "192.168.1.23",
    "host": "linux1",
    "_timediff": "",
    "severity": "3",
    "Percent_CPU_Load": "7.88",
    "time_fired": "0"
  }
}

=== References ===

[1] https://www.ibm.com/support/knowledgecenter/en/SSURRN/com.ibm.cem.doc/em_splunkent.html
