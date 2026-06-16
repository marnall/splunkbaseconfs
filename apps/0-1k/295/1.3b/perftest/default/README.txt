===========================================================================
========================= (c) 2009 The Splunk Community ===================
===========================================================================



==== Contents of Untarred App ====

    * bin/, with benchmark.py
    * extraConfig/, with tasks.conf
    * runLogs/, initially empty
          o Each run will create a log file here, e.g. Wed-Apr-29-11_04_33-2009.log 



==== How to Run ====

   1. Make sure SPLUNK_HOME is set; it should not have spaces, so on Windows use e.g. "set SPLUNK_HOME=c:\PROGRA~1\Splunk"
   2. Edit SPLUNK_HOME/etc/apps/perftest/extraConfig/tasks.conf (see below for details)
   3. In SPLUNK_HOME/etc/apps/perftest/bin/, run
         SPLUNK_HOME/bin/splunk cmd python benchmark.py <username> <password>
      (credentials default to admin/changeme)



==== Format of tasks.conf File ====

The tasks.conf file specifies tasks to be done, in order.  Each task is configured by a stanza.  Stanza names must be unique.  You must specify index tasks before search tasks, since obviously data must be indexed first.



==== Format of tasks.conf File: Index Task ====

Let's take a look at an index task:

[ourData]
type = index
datasetDirectory = /tmp/foo

You must say "type = index" for the script to know this is an index task.  The "datasetDirectory" specifies where the data is, that you want to index; the directory specified by "datasetDirectory" should contain the file(s) to be indexed, before the script starts.  The stanza name, "ourData", will be used to reference perf results for this task.

There is an optional parameter for index tasks:

stopAtEventCount = 314159

Indexing will stop once the specified event count is reached, even if there is more data to index.



==== Format of tasks.conf File: Search Task ====

Let's take a look at a search task:

[bigOne]
type = search
query = * | stats count

You must say "type = search" for the script to know this is an search task.  The "query" specifies what Splunk search is to be performed.  The stanza name, "bigOne", will be used to reference oerf results for this task.

There is an optional parameter for search tasks:

parallelSearchRaces = 1,4,16

This allows you to launch parallel (concurrent) searches.  A race such a launch; the above example specifies a 1-race (single search), followed by a 4-race (4 parallel searches), followed by a 16-race (16 concurrent searches).



==== Other Parts of Splunk Install Affected ====

    * Results go into SPLUNK_HOME/var/run/perftestResults/
          o Each run will create a (very Splunkable) comma-separated key-value file here, e.g. results--Wed-Apr-29-11_04_33-2009.cskv
                + typical line: Wed Apr 29 11:04:33 2009,type=search,task=bigOne,metric=elaSeconds,value=1.7891
                + if you know awk, these files are also eminently awkable (with -F,) 
          o Each task in each run, causes incremental Splunk logs (splunkd.log and metrics.log) to also be copied here, e.g. Wed-May-13-17_13_13-2009--myTask--metrics.log 
    * Default index is not affected; the script creates 2 separate indices, _perf_test and _perf_report
    * 3.x only: 4 new saved searches will be created,
          o Perf Test: all stats, task=* metric=*
          o Perf Test: index tasks, metric=M
          o Perf Test: parallel search stats by race, task=* metric=M
          o Perf Test: search tasks (not parallel), metric=M 



==== Known Issues ====

    * If the files in datasetDirectory are compressed, script stops; this is because dbSizePctOfInput ("compression ratio") metric will be inaccurate.
    * When run for first time, get spurious message ERROR: Could not verify indexes, will not continue (returned 1). 



==== Surprise Issues ====

    * Contact v@splunk.com, who might ask you to re-try after editing the DEBUG = False line in benchmark.py, to be DEBUG = True instead.
          o sed -i '/^DEBUG/ s/False/True/' benchmark.py 

