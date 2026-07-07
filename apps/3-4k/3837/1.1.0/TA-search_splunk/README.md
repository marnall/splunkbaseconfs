# Automatic Splunk Search Adaptive Response
Are you lazy like me? Tired of running a set of known searches after you receive an alert? Well worry no more, this Adaptive response action allows you to run searches as a result of a correlation search and store the results in a seperate index.  All results are in JSON format.  
This app leverages the Adaptive Response framework to allow searches to be issued automatically.

## How to
1. Create your correlation search / alert.  
2. Write your search in the 'Splunk Search' section prefixing 'search' with every search (unless it is a generating search like tstats).  Multiple searches can be executed by inserting a hash in between.
3. Enter a description (Optional) 
4. Specify the index to store the results - Default main
5. Specify a timeout for searches to run - Default 120


## Release Notes
Version 0.0.1 - Inital release open for feedback.
Version 1.0.0 - Added default earliest time, increased loggging, added other important fields.  Splunk Appbase ready.