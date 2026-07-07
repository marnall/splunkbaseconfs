What is Version Control?
Version control is a system that records changes of a file or set of files over time, so that you can recall specific versions later.

What is Gogs?
Gogs application is Version control System (VCS) software. It can also be used to control Splunk Configuration. It is 100% open source, backed by Salesforce and free of charge. It also has webhook option to send payload to Splunk. Whenever an activity occurs in Gogs, it does a POST request with an event to the target forwarder of splunk. 

Pre-requesite:
Webhook Inputs: https://splunkbase.splunk.com/app/3308
Sankey Diagram: https://splunkbase.splunk.com/app/3112
Calendar Heat Map: https://splunkbase.splunk.com/app/3162


Configuration in Gogs
1. Setting > Webhook > Add Webhook > Gogs 
2. Specify HF/UF ip address with any port e.g http://192.168.0.10:8900
   Note :- Make sure port is open 
3. Select content type application/json
4. Select "I need everything" option and save the settings

Configuration in splunk
1. Setting > Webhook
2. Specify Port and path with wildcard *
3. Click on more settings, select sourcetype as manual and specify sourcetype as Gogs
4. Select main index 
5. Click on Save

Dashboard Overview

The Gogs app for Splunk offers a rich set of pre-built dashboards to analyze and visualize data from Gogs  – including file created,modified,deleted,issues,pull request,commits,fork and release - all in single,free app.

Each dashboard panel contain dynamic inputs like select repository, user name and time.  

1. Home: It has overall summary for all records including commits,pull,push,issues,release,fork. Also it provides when was the repo last updated with its size and age of the repo. It also gives total count of watchers for that repo. Contribution panel is useful to find out contributor for repositories.

2. Files: This Navigation contains single value panel of file added, modified, removed and also total number of branch. Each single value panel has drilldown which gives details for select single value panel. It also has before after panel which is very useful while tracking commits. URL's for each commmit is easily accessible by Commit URL panel.


3. Issues: This dashboard contain open issues, closed issues, comment on any of the issues. Each panel has drilldown which shows more details about issues like who had created  a issue or write any comments on open issue., it also shows which user has closed issues. User can easily trace each open issue URL.


4. Pull Request: It has two single value panel which shows open and closed pull request. Detailed overview for same is available in below panels. Open Pull Request Details panel show at what time pull request was created with user, request number and title for a request. 
Closed Pull request shows which user has closed a request, with its title and merged time.

5. Fork and Release : It contains indepth  of fork  details like which user had forked any reposotries with its time. For release panel, it has release ID, release time and release user name. 

6. Search :- Used to search custom Queries.

7. Sample :- It contain sample dashboard for each navigation like Home, Files, Issues, Pull Request, Fork and Release.

Contact US
email: support@avotrix.com







# Binary File Declaration
# Binary File Declaration
# Binary File Declaration
