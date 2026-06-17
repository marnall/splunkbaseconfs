The vast majority of time when searching your data, you want to search by the time parsed in the event. This is the norm. This is what Splunk is optimized for.

Sometimes, however, it would be nice to search by the time that the event arrived. This value is stored in an internal field called _indextime. It is not convenient to query this field, because it is simply stored as a string representing the epoch time value. Searching for _indextime>12345678 actually requires a complete index scan for the time period specified, which is needless to say inefficient.

This application provides a command and a macro that allows you to search reasonably efficiently against the _indextime field by building a subsearch that affects the main query, then filters against the specific values. 

NOTE:
The macro must be the last item in the original query to function properly!

Use cases...
1. Alerting on events when they arrive in Splunk, regardless of when they happened.
For instance, you have a specific event that would be logged if the network is down, but that event would not make it to Splunk while the network is down. This can also be accomplished using real time alerting, and that may be a better solution in most cases.

2. Summary indexing of data that does not arrive in a consistent timeframe. 
Most of the time, summary indexing is configured to run against data older than any expected latency. For instance, if it is possible that data will arrive wihin 2 minutes, then summary indexing might be configured to query data that has a date no newer than 5 minutes, just in case. This is an acceptable margin. But what if your data might arrive between one hour and three days? You could set the summary query to wait 3 days, but it certainly would be nice to be able to build summary entries for the data that does arrive sooner.


Usage:
For example 1, you would write a query such as:
  index=network pingtest failure `indextimesearch("-2m@m","-1m@m")`
You would run such a query every minute, but over a long timeframe, say 6 hours.

The actual query that would be run would be something like this:
  index=network pingtest failure
  (_indextime=1320618110* OR _indextime=1320618100* OR _indextime=1320618090* OR _indextime=1320618080* OR _indextime=1320618070* OR _indextime=1320618060*)
  | eval et=relative_time(now(),"-2m@m")
  | eval lt=relative_time(now(),"-1m@m")
  | where _indextime>=et
  | where _indextime<lt


Example 2 is more complicated, because there are several sliding times. Usual summary indexing would be something like:
  index=network | sistats count sum(bytes) by host
This would be configured to run with the timeframes earliest=-1h@h latest=-0h@h, then the cron set to run a few minutes after each hour. This assumes that data is arriving in near real time. The output of this command will be one entry per host for that hour. The beginning of the previous hour will be the time used in the summary index.

To build the summary based off of index time, we have to do a few other things, because we don't know what the parsed time of the event is.
  index=network `indextimesearch("-1h@h","-0h@h")` | bucket span=1h _time | sistats count sum(bytes) by host _time
This would be configured to run over the timeframe that is worth querying for possible events. This might be days or weeks.  The output would be a summary entry for each parsed hour and host that had data that arrived in the previous hour. The summary entries might actually be for days in the past, even though the events just arrived.

You will possibly end up with multiple summary entries for the same slice of time. This is acceptable because the summary entries represent different source data. When you query the data later, the results will be as if all data arrived at one time.

I know this is confusing, so let me know if I can help.

Cheers,
Vincent Bumgarner
vbumgarner@splunk.com
vincent.bumgarner@gmail.com


