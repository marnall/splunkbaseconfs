# PerformanceInsight APP deploy and develop manual
## How to use it?
In splunk web, go to **Manage Apps** page, choose **Install App from file**, then upload the package **performanceinsight.spl**.  

In case you want to replace an existing app, in your $Splunk_Home$/bin directory, type
``` 
./splunk remove app [appname] -auth [username]:[password]
```
Then delete the folder at $Splunk_Home$/etc/users/[username]/[appname]. 

#### Ooops! No results shown?
When you open performance diagnose page, searches will run automatically. If you check the $Splunk_Home$/etc/apps/performanceinsight/lookups folder, you shall see many Inputxxx.csv files(for data gathering) and the result file perf_diag_result.csv.   
For some reason, maybe permission issues, perf_diag_result.csv file cannot be read directly and no results are shown on the page in your initial run. You may open the search page, type in
```
|inputlookup perf_diag_result.csv
```
Run this command for several times, and you will see the results. Then go back to performance diagnose page, everything is fine now :).  
(Anyone know how to fix this, please help me!)

## How to add more panels and functionalities to it?
You have two options: edit dashboards in Splunk web UI, or directly edit files in $Splunk_Home$/etc/apps/performanceinsight/default/data/ui/.
### Edit Dashboards in Splunk Web UI
First, open the xml source edit panel. I will give you a quick tour about some concepts:
- Tokens: Tokens are like programming variables. A token name represents a value that can change. You can set or unset tokens in a context, then use token values somewhere else.
- Depends/Rejects: These two verbs can create sequential dependencies in various dashboards. Eg. when search B depends on the result of search A, you can write like this:
``` xml
This is search A
 <search>
    <query>xxxx<query>
    <progress><unset token="A_done"></unset></progress>
    <done><set token="A_done">true</set></done>
 </search>
This is search B
<search depends="$A_done$">
    <query>xxxx<query>
</search>
```

- Tokens can also be used in html elements. This is extremely useful when you want do display search results in a customized way. You can set tokens to save search results in \<done>\</done> context, and access the tokens in any html elements.


You may find these docs very useful:
> https://docs.splunk.com/Documentation/Splunk/7.3.1/Viz/PanelreferenceforSimplifiedXML
https://docs.splunk.com/Documentation/Splunk/7.3.2/Viz/tokens#Define_search_tokens
https://docs.splunk.com/Documentation/Splunk/7.3.2/Viz/EventHandlerReference

Note: Your modifications will be saved in $Splunk_Home$/etc/apps/performanceinsight/local/ folder. If you want to save these changes for future app package and release, remember to move files from /local to /default.

### Edit default files directly
You may have more freedom in this way. In $Splunk_Home$/etc/apps/performanceinsight/default/data/ui/nav/default.xml, you can edit or add more views for your app.  
Also, you can add js scripts or css files in $Splunk_Home$/etc/apps/performanceinsight/appserver/static, so you can have more control over your xml page.
Refer to them like this:
```
<form script="my.js" stylesheet="my.css">
```

## How to package and release it?
When your changes are ready, refer to this doc to check whether your app is ready to be packaged. 
> https://dev.splunk.com/enterprise/docs/releaseapps

A shorter version for you:
1. Ensure all the files in /local folder are moved into /default folder with the same structure, then delete the /local folder, and /metadata/local.metadata(if there is one).
2. Delete all the files in /lookups you may generate when testing.
3. Go to $Splunk_Home$/bin, run this command
```
./splunk package app [appname]
```
