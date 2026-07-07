# D3 Donuts Calendar

New features: changes I provide on this app are al recorded on the app page in splunkbase. 
https://splunkbase.splunk.com/app/3305/

This app try to give you a free style to decide start date and end date on your data flow to keep a focus on this time range.   

## Sample Searches
Please check the search example fragment under the visualisation choices menu.
You can also dirctly use this one:
| inputlookup test_donutscalendar.csv   | table lostservice categoryname outageid

## version support
For bugsfinding and troubleshooting please contact me: Xue.Meng@lcsystems.de
LC Systems GmbH	  	
Landsberger Strasse 302	  	
D-80687 München	  	
www.lcsystems.de
Mobile:	+49 152 0 9999 875	Email:	Xue.Meng@lcsystems.de

For customized D3 Visualisation on Splunk also can contact me and my company LC Systems.
## system requirements
Splunk 6.4 is now what I use for coding.
## installation
Add wich Splunk App Manager or unzip files on Splunk-Home/etc/apps
##  configuration

## troubleshooting 
Now some Pattern bugs and position bugs fixed, I always keep records in comments on Splunk base. 