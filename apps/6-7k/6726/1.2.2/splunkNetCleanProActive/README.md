NetClean ProActive

Setup
1. Install App from splunkbase. 
2. Enable All Tokens
	Go to Settings -> data Inputs -> HTTP Event Collector -> Global settings and enable All Tokens and close the popup window
3. Create a new HTTP Event Collector Token
	Name:  NetClean_ProActive
	Source: NetClean_ProActive
	Indexes:netclean
	Source Type: netclean_json
	Take note of your Token Value  
4. Restart Splunk. 
	Go to Settings --> Server controls and click restart splunk 

4. Configure NetClean
	Please see Netclean Documentation
	WebhookAddress: = https://your.server.com:8088//services/collector/raw
	WebhookAuthorizationHeader = Splunk yourToken

5. Optional
The Dashboard uses Event Timeline Viz to ilustrate the timeline, it can be downloaded from splunkbase
https://splunkbase.splunk.com/app/4370
