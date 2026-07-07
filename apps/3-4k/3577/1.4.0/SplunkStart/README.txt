Author: Nimish Doshi

Configuration Pages Author: David McDonald

Dislaimer: Use as is. Neither Splunk nor the author is responsible for the use
or misuse of this app.

Welcome to the SplunkStart app for Splunk, which will be called Splunk Start
for the rest of this write up.

This app will use your data and field extractions to create dashboards with
your titles for the panels using Python scripts to substitute macros. It also
comes with a sample custom Splunk command and sample modular alert that you
can edit to put in your own code to test it out. This is explained in the
end of this file.

NOTE: KEEP ALL NAMES UNIQUE for macros, saved searches, and titles.

1)
First untar (example: tar zcvf SplunkStart.tgz) the whole distribution into a clean Splunk
etc/apps directory. This will create the SplunkStart app. If you are using
Search Heads and Indexers, install this app on the Search Head. If you are only
using one indexer and no Search Head, install this app on the Indexer.

The Advance Visual Dashboard is dependent upon Splunk Advance Visualizations
available for free from Splunkbase. Please download the following apps from
Splunkbase and install in the same instance as Splunk Start.

Horizon Chart

https://splunkbase.splunk.com/app/3117/

Sankey Diagram

https://splunkbase.splunk.com/app/3112/

Status Indicator

https://splunkbase.splunk.com/app/3119/

Timeline

https://splunkbase.splunk.com/app/3120/

Treemap

https://splunkbase.splunk.com/app/3118/

This will load the sankey, timeline, status indicator,
treemap, and horizon chart modular visuals downloaded from Splunkbase
into the directory. You can update the TA s, whenever you want.

/******* Optional *********/

Next copy or move the directory
splunk-modular-alert-advice in SplunkStart/src/apps to your
$SPLUNK_HOME/etc/apps directory.

Rename app.conf.old to app.conf in
directory $SPLUNK_HOME/etc/apps/splunk-modular-alert-advice/default

Change permissions for the Python scripts in the modular alerts directory:

chmod 755 $SPLUNK_HOME/etc/apps/splunk-modular-alert-advice/bin/get_advice_log_message.py

chmod 755 $SPLUNK_HOME/etc/apps/splunk-modular-alert-advice/bin/modular_alert_example_app/*

/******** Optional *********/


(If you want to try out the distribution out of the box, please go to
 Splunkbase and download the Eventgen TA. It is located at:
https://splunkbase.splunk.com/app/1924/

OPTIONAL: Next, install the Cisco ASA TA from Splunkbase on the same instance:
https://splunkbase.splunk.com/app/1620/

NOTE: As of 2019, the Cisco TA does not include sample data. You will have to
provide your own sample Cisco ASA data that is CIM compliant, if you want to
test with this data source. It is not required to test with this data source.
The same is true of the Splunk for Bluecoat TA.

Install the Eventgen TA as per the instructions otherwise you will have empty
dashboards when you first install SplunkStart. You must provide your own sample
data for the event gneration to occur or provide live data that is current if
you do not want to use event generation with cisco events.

This will also load the cisco FW TA's (for sample events) into the apps 
directory. Finally, splunk_modular_alert_advice will be loaded into
$SPLUNK_HOME/etc/apps. The way to use the App is to install the Eventgen 
first and just restart Splunk and look at the included dashboards: Timecharts,
Tops/Rares, Stats, Advance Visuals, Simple Analytics, Lookups, and Maps. This
should just work and get you a foundation app.)

END OPTIONAL

1A) Optional. This is only needed if you rename the SplunkStart Directory to
another name.

In the bin directory, there is a shell script called change_app_dir_name.sh.
If you make a copy of ORIGINAL SplunkStart app (the one you download) and put
it into the same SPLUNK_HOME/etc/apps, you would go into each copy’s bin
directory and run this script to change the names of all hard coded places
that used be called SplunkStart. For example, copy SplunkStart to
 $SPLUNK_HOME/etc/apps/SA1, $SPLUNK_HOME/etc/apps/SB2,
 $SPLUNK_HOME/etc/apps/SC3.
 
Then, go into each app's bin directory (cd $SPLUNK_HOME/etc/apps/SA1/bin) and
run:
 
./ change_app_dir_name.sh SA1
 
cd ../../SB2
 
./ change_app_dir_name.sh SB3
 
cd ../../SC3
 
./ change_app_dir_name.sh SC3
 
Now, assign each user their own app (SA1, SB2, SC3, etc).
 

2)
Next, load your own data into the Splunk indexer with proper sourcetypes and
field extractions as needed. Now, you are ready to use your own data with the
included dashboards. 

If you don't understand your data in terms of index names, sourcestypes, and
field names that you are entitled to view, then from the SplunkStart app,
click on the "Discover Fields" menu item and click on an index and sourcetype
to discover these things to find out the cardinality of your field values
along with whether they represent strings, numbers, or IP addresses.

There are two ways to update the dashboards after you understand your field
names. One is through the web interface of the app (recommended) and for
advance users, use command line.


GUI to Update app with your Data:

(PLEASE NOTE FOR ON PREM USERS:
In $SPLUNK_HOME/etc/apps/SplunkStart/default/data/ui/views, you will find 2
files: modify_macros.xml and change_dashboard_titles.xml. Edit each file and
change version="1.1" to version="1.0" in the dashboard section of XML file.
This will allow the see current dashboard button to work as an inline iFrame.)

Under "Configure Splunk Start App", click on "Modify Dashboard Macros". This is
also the screen that can be used to turn on or turn off the Show SPL and Toggle
Comments button. You will see each dashboard listed along with the names of
each macro and their respective parameters that drive the dashboards. Simply
change the macro defintion to be your data. For instance Under Timecharts,
there is a panel called Timechart Averages. Change the macro to use your data

Before:

mac_timechart_avg(main,cisco:asa, bytes_out, 1m, -15m, now)

Sample After using this data, which is what we call "your data":

mac_timechart_avg(main,bluecoat:proxysg:access:syslog, bytes, 1m, -60m, now)

The parameters for each macro are listed. Then press the "Save Macros" button
and press the "See Current Dashboard" to see if it worked. If it did not work,
you can simply change the macro again and test it again. You can do this for
each macro in each dashboard or leave some as is.

If you want to do this all at once, you can click on "Advance Macro Edit" and
load a file that has a list of all the macros that come with the app and
change all the macros at once on that page. For convience, sample macro files
are provided in the app's src/macros directory.

To change the Titles Dashboard Panels:

Click on Configure Splunk Start App and click on "Change Dashboard Titles"
Just as with Change Macros, each panel is listed with its current title. Just
write in your own title and make sure to use uniqe names for each panel's
title. You can do this one title at a time or you can click on "Advance Title
Edit" and write a comma delimited list of old titles and your new titles.
We populate the old titles for you. You can also import a CSV file that has
this format to use. For convience, samples are provided in the app's src/titles
directory.

After making changes to macros and titles, if you are in an admin role, you
don't need to restart Splunk. However, if you are not in an admin role, you
will need to restart Splunk as the http://<host:port>/debug/refresh REST API
sent to Splunk underneath after pressing "Save.." requires admin role rights
to work without a restart.

For Advance Users: Change Macros and Titles by editting a file:

You can change macros  by just editing one file: src/macros/my_macros.txt.
(Make a copy of this file to edit in the same directory).
Each line not listed as a comment represents a search and a panel in dashboard.
Simply put in your index, sourcetype, field(s), and earliest time for a macro.
The file is fully commented to get you started. Save the file and run the
following python command located in the bin directory as directed:

> bin/substitute_macros.py src/macros/my_macros.txt default/savedsearches.conf

This will read the default savedsearches.conf and substitute your macros.txt
to generate a local_savedsearches.conf. Copy and rename:

> mv local_savedsearches.conf local/savedsearches.conf

(Make a local directory under SplunkStart, if it does not exist.)


Restart Splunk and see your data within the dashboards. You can further
change the saved searches from Settings, but note that these changes will not
be reflected in your my_macros.txt file.

(As a side note, after this works, you may want to disable the EventGen app OR
rename eventgen.conf to something else in the Cisco TA or disable each input
in the eventgen.conf so that the previous events are no longer being generated
since you are now using your own data.)

3) 
   Now that you understand how to use your own data within the dashboards,
   you can now make a copy of macros.conf into local/macros.conf and edit
   searches to include filters and other options in the Splunk search
   as needed. If you change the number of parameters to the macro, make the
   same change to your saved_searches.conf and my_macros.txt. Also,for a good
   demo, change the title of each panel and dashboard (labels) to match your
   use case. That can be done from the GUI.

   3a) There is a bonus macro called mac_outliers that finds outlier fields
   values have a count greater than the average count plus standard deviation
   of all event counts. You can run that macro as is from the search bar:
   `mac_outliers(index name, sourcetype, field name, earliest, latest)`

This app should be generic enough to use for any use case such as security,
telco, internet of things, financial services, etc.

More macros and dashboards are to come.

-----

Updating Panel Titles Automatically through the command line

Rather than use the web interface of the app to update title and
rather than update each panel's title in each XML view file manually, you can
do this in one file. First cd into the src/titles directory. Then, edit the
titles.csv file. For each line, in the 2nd column put in
your new title to substitute from the original title. Save the file.

Then, run the sh script in the bin directory from SplunkStart root directory:

> bin/substitute_titles.sh src/titles/titles.csv

This will change all titles for all panels in the local view directory that
matches the original names. It will also make a copy of all dashboards in
default/data/ui/views and copy them to local/data/ui/views. If the dashboard
already exists in the local view directory, it will be used instead of a new
copy from the default view directory.

If you have admin permission you can simpy do
this to change the UI titles after this step without restarting Splunk:

http://<name of Spunk server>:8000/en-US/debug/refresh and click on refresh.

If you do not have admin permsissions, restart Splunk.


--------- Adding new content or dashboard (Advance Users) ---------

You can create brand new macros and dashboards to add to the app that have
parameterized input. Under "Configure Splunk Start App", click on "Add New
Content"

Fill in the definition of the macro (example provided on the page) and name
your macro with an unique name. Press Create. If What will appear in the
local/macros.conf file looks good, press Submit. Next, click on "Add Saved
Search" and name your search with an unique name. Now, click from the macro
list one of the macros you want to use. Fill in the parameters for each field
with your data. Press "Submit Saved Search" This creates a new saved search
in local/savedsearches.conf

Now, click on "Add Dashboard Page" and type in the name of a new dashboard
and use an unique label to describe the dashboard. Click "Add Dashbord"

Finally, click on "Add Panel to Dashboard" and choose a dashboard, saved
search, type of visualization for the search, and a title for your panel. Then,
press "Save Panel"

If you make a mistake or want to edit your content, please go to Settings on
top of the app and change macros via "Advance Search", change saved searches
via "Searches, Reports, and Alert" and change dashboards via "User Interface"
views.

To add comments to each panel to appear in Splunk, go to Settings->
User Interface->Views->Click on your Dashboard name.

For each panel, place the following snippet of HTML code right after
the <panel> tag:

<html>
                <div id="myDIV" style="display: none">
                Your Comment goes Here.
                </div>
</html>

The id="myDiv" can be any string from myDiv, myDiv1,...myDiv5. This means,
we recommend at most 6 panels per dashboard.


To Create Content Manually without using the app:

1) Create a new search in a local/macros.conf. Make sure the name of the macro
   starts with mac_.
2) Add that macro with real parameters to a search in local/savedsearches.conf
3) Create a new dashboard with a panel in local/data/ui/views/ that calls
   the search in local/savedsearches.conf. Name your dashboard
   <your name>_dashboard.xml

   For each panel in the dashboard, before the </panel> tag, place the
   following HTML snippet:

<html>
	<button class="btn btn-default" id="POC_Test" style="float: right;">
	Show SPL</button>
</html>


	You may also put in a comment in HTML in each panel as discussed above
	right after each <panel> tag.

4) Create a new entry in your src/macros/my_macros.txt file that reflects the
   name of the new macro with actual parameter names. Comment the file.
5) Create a new entry in your src/titles/titles.csv file that reflects the
   name of your title in the panel in the new dashboard in the first column
   with a suggested name to change the title in column 2.
6) Restart Splunk.


--------- Custom Splunk Command  -------------

This app ships with a custom Splunk command that you can use to test out how
to write a custom command.

Background

In the app's default directory, you'll see a commands.conf file. This is the
file that declares the custom commmand. I have put in the minimal attributes
for the stanza. It has the name of the commmand and Python script it invokes.

In the metadata directory, there is a file called local.meta that provides
role based access to the custom command. I have simply added:

[commands/mycommand]
access = read : [ * ], write : [ admin ]
export = system

to the file to say this command (mycommmand) can be read by anyone on the
system and written to only by the admin role.

Python Script

In the app's bin directory, you'll see the mycommand.py. Look at this file and
you'll see some boiler plate code. The heart of this "generating" commmand is
in the *** Put in your custom Code.

This implemenation simply taket the _raw event (r["_raw"] field) and shifts
each alphabetical character 13 positions, which is the famous rot13 trick. You
can remove this and put in any code you want to generate more fields and store
them in the r["<name_of_your_field"]. The usage for this commmand is:

<some search that returns raw events>|mycommmand|table _raw

Example:

sourcetype=cisco:asa|mycommmand|table _time, _raw


***************Modular Alert************* Based on Luke Murphey's Blog

The distribution comes with an already configured Modular Alert that you can
invoke as an alert action. It simply writes some trivial advice gathered from
an URL to the Splunk _internal index. Most of this is based on Luke Murphey's
Blog: https://www.splunk.com/blog/2016/08/22/how-to-create-a-modular-alert/
if you want detailed explanation. The modular alert takes a URL as input from
the user so that it can be invoked at alert time to gather the trivial advice.
I have provided a sample URL as a default. If you would like to run it, set
up an alert condition in Splunk and choose the Splunk Start icon as the alert
action. If you don't have a URL to gather advice for the _internal logs, simply
choose the default URL. Once the alert happens, you can search for it:

index=_internal sourcetype=splunkd component=sendmodalert
		 action="get_advice_log_message"

If you want to keep the same structure, but change the code, go into the
splunk-modular-alert-advice/bin directory to edit the get_advice_log_message.py
file. The actual work is done in the run method that invokes the custom
make_the_log_method, which uses the URL passed into the alert to GET the
advice. If you want to customize this, you can use the payload object
(someVarible = payload.get(<name of field)) to get everything about the
alert such as the name of the search that invoked it, the event/results file,
etc. See this answer for details:

https://answers.splunk.com/answers/442603/how-do-i-get-the-8-standard-alert-action-script-pa-1.html

Go change the code to do something besides gathering trivial advice to put into
the _internal index.





