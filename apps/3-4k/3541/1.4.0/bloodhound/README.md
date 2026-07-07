# Bloodhound

## Installation:

To install app via Splunk web UI click on the cog on the home dashboard or click on manage apps from the Apps dropdown. From here click install app from file and select the .spl file associated with this app. Once selected click Upload and the app should be installed.

To install app via the configuration files untar the downloaded app. Copy or move the bloodhound folder to the $SPLUNK_HOME/etc/apps directory. Restart Splunk.

### **Deploy to single server instance**

Install the Bloodhound App on the single server using the methods described above.

### **Deploy to distributed deployment**

In a distributed deployment the Bloodhound App should be installed on the following:

_Search Head:_ The Bloodhound App should only be installed on the search heads.

## Configuration/Setup:

Once the app is installed proceed to access the app via the web UI. Go to Settings -&gt; Searches, reports, and alerts. If the App context is not selected as Bloodhound set that now, and check the box for &quot;Show only objects created in this app context&quot;. Three searches should appear: bloodhound_inventory_kvstore_gen, bloodhound_inventory_kvstore_job, and bloodhound_inventory_kvstore_job_cleanup. These searches are used to run the corresponding scripts to populate the Bloodhound KV Stores for the app to function. These also have schedules associated with them and the searches are disabled by default. Each search consists of a script command followed by the script name ex. &quot;| script bloodhound_inventory_gen&quot;

There are 2 arguments that follow the script name, host and port.

- Host is the Splunk server that is queried to obtain information about the dashboards, searches, and jobs. This value should be set to &quot;localhost&quot; as querying remote servers is not supported with this release.
- Port is the Splunk Management port associated with the host instance of Splunk, by default 8089 is the mgmt port ex. &quot;port=8089&quot;

There is a third argument for bloodhound_inventory_kvstore_job_cleanup, time.

- Time is the number days to store the job information since it was initially created. Ex. &quot;time=30&quot;

Once these values are edited on your setup for the three searches, enable the searches. This should begin running the scripts at specific intervals and having the lookup/app begin populating with results. Results of the scripts will be stored in KV Stores on the &quot;localhost&quot; server where the search is executed.

The schedule for bloodhound_inventory_kvstore_job may need to be edited dependent on current searches running within environment. By default this search is scheduled to run once every 8 minutes. However, if scheduled searches exist that are on an interval less than this amount we suggest changing the bloodhound_inventory_kvstore_job search interval to something that meets your criteria.

### **NOTE:**

If after running the scripts the KV Stores are not being populated/updated, view the results of the script search. The scripts also include logging of the script files located at $SPLUNK_HOME/var/log/splunk/bloodhound.log. This is used to log specific points within the script for completion along with logging any errors that occur during the script. Easy way to gain access to this log via Splunk can be found by using the search:

- index=\_internal source=\*bloodhound.log

Upon proper completion of a script the search will return an event stating that the script has ran successfully. If an error will occur either the search will return the error or the error can be found within the bloodhound.log. If an error exist and both host and port are correct for your setup contact support with the search query and the resulting error for help in solving the problem.

## Dashboard Information:

Here we will go ever each dashboard in more detail on what is being shown.

### **Dashboard Analysis**

The Dashboard Analysis page is the initial landing page for the app and consists of multiple single value visualizations. The only input associated with these single values and further drilldown panels is that of designating a specific App. If changed the submit button will need to be pressed in order for the panels to update. All single values also include a drilldown panel associated with them so upon clicking on its value a more detailed table of the values will appear below.

The first single value drilldown is that associated with Potentially Bad Dashboards. This value is figured as the dashboards that have greater than 5 base searches and 0 saved searches and 0 post process searches associated with it. This is due to the fact of efficiency of running base searches is worse than that of either post process or saved, and these dashboards should be rethought on the searches contained or changing the searches to post process or saved. Upon clicking on the value, we list out the Dashboard, App, Number of Base searches, Number of Post Process searches, Number of Saved searches, and Total number of searches for the dashboards that fit this use case.

The second single value drilldown is for Potentially Bad Searches. This looks through the searches on all dashboards and looks for a list of commands that could lead to bad searches. These commands being: Append, Dedup, Join, Map, Sub-Search, Transaction. Upon clicking on the value the count of these commands in each query that has 1 will appear along with the Dashboard App and the actual query associated with it.

The third single value drilldown is Dashboards with Bad Inputs. These are the number of inputs located on apps that contain base searches that don&#39;t contain specific commands that make up an inefficient input query. The commands that being looked for are: Inputlookup, Metadata, Loadjob, and $\*. As these are the initial signs of a good input query that is efficient to run. Upon clicking on the value more details of the query, app, and dashboard can be found for each case.

The fourth panel is for Malformed Dashboards. This consists of the number of dashboards with malformed xml associated with it. Upon click on the value will give the App, Author, Dashboard Name, ID, number of inputs, number of panels, and number of searches for each malformed dashboard. This panel also includes another drilldown as when clicking on one of these dashboards will take you to the xml editor for that specific dashboard view.

The final panel is for Unused Dashboards on the current instance. By default, this single value panel is set for only the past 30 days. This counts the number of dashboards that haven&#39;t been visited in the past 30 days. Upon proceeding to the drilldown, a panel and a time range picker will appear. By default, the time range picker is set to past 30 days but is able to be changed. Upon changing this value, the panel below will be updated to allow further exploration of the dates of unused dashboards.

### **Search Analysis**

The Search Analysis also consists of multiple single value drilldown panels where upon click on a value a panel will appear below with further details on the events that match each use case.

The first single value drilldown is Potentially Bad Search Practices. This is similar to the one on the Dashboard Analysis view but rather is viewing the queries of Saved Searches located on the instance. Upon clicking on the single value the panel will show the counts of each command that appears in the queries, the saved search name, app its located on, and the query of the saved search.

The second panel is for counting the number of saved searches that share the same query yet are more than 1 distinct saved search across multiple apps. This is useful in noticing a search that may be popular in multiple apps that could be limited to a single saved search with a larger permission associated with it. Upon clicking on this value the Apps with this saved search, and the saved search names associated with this query will be shown, along with the query.

The final panel is that of Unused Saved Searches. This is the count over the past 30 days by default, of unused saved searches on this instance. Upon clicking on the value a time range picker and a panel will be shown. This time range picker is used for the editing the time range of viewing unused saved searches. The panel shows the saved search name and the app that haven&#39;t been used in that time frame.

### **Summary Index Analysis**

This view provides Splunk Admins insight into the use of Summary Indexes and the searches that are writing to them.

The first panel shows the scheduled searches that are writing to summary indexes grouped by index and sourcetype. This shows admins if there are searches with the same index and sourcetype combination writing to summary indexes. This panel has a drilldown associated with it that shows the search query for each search listed in a row. This will allow the Admin the ability to determine if the searches are similar and if they can be combined or one can be removed.

The final panel shows summary indexes that have not been used. By default, the search goes back 3 months but that can be updated given the time range picker.

### **User Activity**

The User Activity consists of a couple of metrics on the users located on the instance of Splunk.

The first graph shows the Top Users in the past 7 days a long with the number of distinct dashboards the user has gone to.

The second graph shows the user that visits the most dashboards in the past 24 hours. These numbers are not distinct dashboards but total numbers for each user.

The final graph shows the total distinct count of users accessing the instance of Splunk over the past 7 days.

The final panel includes a Time Range input and a statistics panel. This panel is used to view what data has been exported out of Splunk within the specified time range selected. This includes specific information about the exportation of the events such as the search query if one exists and the URI associated with the job.

### **Scheduled Searches on Dashboards**

The Scheduled Searches on Dashboards view consists of multiple inputs and multiple drilldown panels. The inputs consist of selecting an App Name, View Name, Threshold number, and a time picker. The app name is used to select a specific app and the view name is used to select a specific view. The time picker is used to update the dashboard hits within that time range. The threshold number is the number that the user can set to only view the dashboards with less than X dashboard hits over the set time range.

The first panel shows the Dashboards that meet the threshold number of hits and contain a scheduled search. This panel shows the app, the number of scheduled searches on this view, and the users that accessed this app in the time range if any have, along with the number of dashboard hits. Upon clicking on a row in this panel further details about that specific view will appear.

This drilldown panel shows the specific scheduled searches associated with the selected view. Along with showing the scheduled searches it shows the average of the job metrics associated with the scheduled search, along with the owner, time to live, and the schedule of the search. Another drilldown exists for this panel where clicking on it shows the search query and the counts of certain commands associated with the query itself. This panel is similar to the bad search practices panel seen on Dashboard Analysis and Search Analysis page.

### **Expensive Searches on Dashboards**

The Expensive Searches on Dashboards shows specific search metrics associated with the searches ran on a specific dashboard view. This view contains three inputs for the dashboard that consist of selecting the App and View, and selecting the time range for which the job information should be about. This dashboard doesn&#39;t include any metrics on the search dashboard.

The first panel is a summarization of each dashboard panel that contains hits and ran searches in the selected time range. This also contains the User that accessed the dashboard, number of searches, averages of certain job metrics, and the number of dashboard hits. A drilldown is associated with this panel that further explores a specific dashboard view.

The drilldown panel shows the specific search metrics for the searches that were ran within the dashboard. Describing if a search is In-Line or Saved and the specific job metrics of the individual searches. Another drilldown exists on this panel that views the query and the count of specific commands in viewing possible bad search practices on such search.

### **Dashboard Metrics**

This dashboard consists of multiple charts and tables of dashboard specific data. This information is similar to that of User Activity but more focused to dashboards.

The first graph shows the Top Dashboards visited in the past 24 hours along with the number of visits.

The second graph shows the counts of the dashboards over the past 7 days for each day.

The panel on the bottom shows specific dashboard details. This panel contains three inputs being selecting a specific App and View along with setting a time range for the data. This time range is used in calculating the last time a dashboard was viewed and the number of hits. The information that is shown is that of the dashboard name, dashboard owner, app, last time the dashboard was viewed, number of hits, number of panels, and number of searches. A drilldown is also associated with these dashboards that further looks that the type of searches located within each dashboard.

#### **NOTE:**

Some events within this panel will contain values Unavailable as these are dashboards that the script is not able to reach and perform metrics on. These events do not contain a drilldown associated with them.

## KV Store Information:

The app uses KV Stores to store the information about the dashboards, searches and jobs information across the Splunk instance. The KV Stores are separated into 6 unique stores with their own distinct fields and values. We will go over each lookup and what is contained within it below.

### **inventory_views**

This KV Store is populated via the bloodhound_inventory_gen script. It contains a list of all dashboards that the user running the script can view. The fields in each event are:

- app - the app which the view is located in
- author - the user that created or owns the app
- id - the url of the dashboard within the local instance
- inputs - the number of input searches within the view
- malformed - empty if no xml errors present, has a 1 if an error exists
- label - the dashboard ui name
- name - the dashboard system name
- panels - the number of panels within the view
- searches - the number of searches within the view

### **inventory_view_searches**

This KV Store is populated via the bloodhound_inventory_gen script. It contains a list of searches that are present within dashboard views. The fields in this lookup consist of:

- app - the app which the search is located in
- earliest – the earliest time range that is associated with the search
- latest - the latest time range that is associated with the search
- parent - name of base search if search contains has one
- parent_tag - the tag associated with the search itself
- query - the search query for that specific search, only filled if search is in-line
- savedsearch_name - name of saved search
- type - type of search being either in-line or saved
- view - view that the search is located

### **inventory_saved_searches**

This KV Store is populated via the bloodhound_inventory_gen script. It contains a list of saved searches viewable by the user that runs the script within the Splunk instance. The fields consist of:

- app – the app which the saved search is located in
- disabled – if the search is disabled or enabled (0 for disabled, 1 for enabled), only applicable for scheduled searches
- earliest - the earliest time range that is associated with the saved search
- is_scheduled - if the saved search is scheduled or not (0 for no, 1 for yes)
- latest - the latest time range that is associated with the saved search
- name - name of the saved search
- owner - the owner of the saved search
- query - the saved search query
- schedule - the schedule of the saved search if applicable
- sumary_index - if the saved search uses a summary index (0 for no, 1 for yes)
- summary_index_name - the name of the summary index if applicable

### **inventory_saved_search_summaries**

This KV Store is populated via the bloodhound_inventory_gen script. It contains a list of saved searches that use a summary index. The fields in each event consist of:

- command – list of summary commands that are located within search query
- fields – the fields associated with the summary commands within the search query
- index – the searched index the search query uses, if applicable
- search_name - the name of the saved search
- source – the searched source the search query uses, if applicable
- sourcetype – the searched sourcetype the search query uses, if applicable
- summary_index - the name of the summary index the saved search uses

### **inventory_apps**

This KV Store is populated via the bloodhound_inventory_gen script. It contains information in regards to the apps installed onto the Splunk instance. The fields consist of:

- name - the app system name
- label - the app ui name
- version - the app version number if applicable

### **inventory_jobs**

This KV Store is populated via the bloodhound_inventory_job script. It contains a list of job metrics for searches that have previously ran. The fields consist of:

- app - the app in which the search was ran
- diskUsage – the amount of disk used by the search in bytes
- dispatchState - the state of the search currently, should always be DONE if not please report this as a bug
- eventCount - the number of events returned by the search
- label – custom name created for this search, name of saved search if applicable
- owner – is the user that ran the search
- runDuration – time in seconds that the search took to complete
- scanCount – the number of events that are scanned or read off disk
- search – the search string
- sid – the search ID number
- ttl - the time in seconds indicating the time to live for the search artifacts
- ui_dispatch_app - the name of the app in which Splunk Web dispatched this search

Also contained within this KV Store that are not seen within Splunk are the fields:

- time – the day in which the bloodhound_inventory_job script added the search to the KV Store, in the format of &quot;%m-%d-%y&quot;
- previousTS - the timestamp for the last ran bloodhound_inventory_job script

This time field is used for the bloodhound_inventory_job_cleanup script. As it is the time value that the script uses when deleting old job events from the KV Store that are X number of days ago from the time the script is running. The previousTS is used in optimizing the number of searches that are parsed.

## Troubleshooting

Below are searches that can be used to verify that the lookups above are being populated after running the scripts.

- | inputlookup inventory_views
- | inputlookup inventory_view_searches
- | inputlookup inventory_saved_searches
- | inputlookup inventory_saved_search_summaries
- | inputlookup inventory_apps
- | inputlookup invnetory_jobs

These searches should return some events if the data exists within the instance and the scripts are running as expected.
