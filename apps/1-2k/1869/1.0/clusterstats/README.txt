clusterstats/README.txt

clusterstats v1.0 by Sean Foley, tested on Splunk 6.1.2

clusterstats is an external python search command packaged as an add-on for 
Splunk.

I wrote clusterstats to give stats about clusters of anomalous (slow) 
transactions. The search I was working with used transaction to tie related 
events into a transaction and add the duration field. I then piped the results 
into a command to filter out the normal transactions and leave the slow ones:

| search duration > 3


The command expects to be passed a maxspansecs=X argument and it expects to be 
piped events which contain _time and duration fields, and it expects the results
to be in reverse order since it needs to process in time order to calculate the
start of a cluster, the end of a cluster, the number of transactions in the 
cluster, the max and mean duration for the cluster. Keep in mind that the max is
probably accurate but the mean is only averaging the duration from the filtered events so it is the mean duration for the cluster of events > than 3 seconds if the above filtering search is used.

The command returns a new set of events to splunk web which represent timings 
and statistics from each cluster identified in the original set of events as
determined by the maxspansecs window. The following fields are returned:

_time :                the start time of the cluster

cluster_end_time :     the calculated end time of the event based on the latest
                       transaction end time (transaction start + duration).
cluster_max_duration : the highest duration value from cluster transactions

cluster_mean_duration : the mean of the duration values for the cluster 

As a starting point I use the following to nicely format the epoch times and float values after my base search, the transaction command, and the search duration filter above: 

| clusterstats maxspansecs=30 
| convert timeformat="%m/%d/%Y %H:%M:%S" ctime(cluster_end_time) 
as cluster_end_time 
| convert timeformat="%m/%d/%Y %H:%M:%S" ctime(cluster_last_txn_start) 
as cluster_last_txn_start 
| table _time cluster_end_time cluster_txn_count cluster_max_duration 
cluster_mean_duration 
| eval cluster_max_duration=round(cluster_max_duration,2) 
| eval cluster_mean_duration=round(cluster_mean_duration,2) 
| rename _time as cluster_start_time 
|convert timeformat="%m/%d/%Y %H:%M:%S" ctime(cluster_start_time) 
as cluster_start_time

This should get you going. Please send any questions or comments to:
naturaldog@gmail.com
