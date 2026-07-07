Send XLS Results



if anything fails  this will show the debug output:

index=_internal sourcetype=splunkd sendmodalert action=sendxlsresults_alert STDERR | eval logmsg=substr(_raw,89) 
| append [search index=_internal source="/opt/splunk/var/log/splunk/sendxlsresults.log" | eval logmsg=_raw]
| table _time,logmsg | reverse
