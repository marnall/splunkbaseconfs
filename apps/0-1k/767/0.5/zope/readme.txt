Splunk for Zope
===============

This package adds Zope support to Splunk. The Zope open source application server
provides a bunch of log files. With this app you'll be able to easier process 
and analyze them by Splunk.

This is useful when hunting bugs, performance issues etc.

Splunk for Zope supports these kind of Zope log files:

 * Z2.log - a NCSA style log of requests
 * event.log - a log of errors, warnings etc.
 * zeo.log - a log of database server behavior
 * trace.log - timing of how long all requests take and (with thrashcatcher) how
   much database activity each request causes


Automatic recognition of Zope log files
---------------------------------------

Zope for Splunk tries to recognize all the different Zope log files. First it 
looks at files names, then it looks inside the files for patterns.


Field extraction
-----------------

To make log files analysis and reporting more useful, we are identifying 
significant fields in the log files. 

The trace log is a special case, as the log lines spans multiple, overlapping 
lines. The "flattentracelog" tries to stitch data together.


Search examples
----------------

Most frequent errors::

  "zope_event" ERROR startmonthsago=3 | cluster | sort -cluster_count

Slowest requests::

  "zope_trace" | flattentracelog | search req_time>3 |sort -req_time


Consistent slow pages (multiple times > 5 secs)::

  "zope_trace" | flattentracelog | search req_time > 5 | cluster field=uri | sort -cluster_count


