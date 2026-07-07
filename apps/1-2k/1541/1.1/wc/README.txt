Usage:


This is a pretty basic app.  Use it in a search like this:

 search some_string |wc fieldname 

The 'fieldname' is optional, if supplied then the words in 'fieldname' will be counted.  If omitted then _raw will be used.

To create a table / chart, use stats.

 search some_string |wc fieldname |stats sum(count) by word

By default, a list of (English) stop words are filtered & not counted in stats.  To disable the stop words (and get a full count of words) add 'usestopwords=f' to the command:

 search some_string |wc usestopwords=f |stats sum(count) by word


