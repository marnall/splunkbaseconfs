##Lumeta Add-on and App for Splunk

Lumeta Add-on for Splunk provides CIM compliant field extractions and data enrichment for Syslog and REST API data and the App provides visualizations on these data.

##Supported Versions

Splunk Enterprise:

* Version 8.0.1

Python:

* Version 3.6
#Add-on
## Building Zip package

Follow the step below to create a zip archive to be installed on splunk.

1. Ensure the directory name is `TA-lumeta-addon`. 

2. Remove all .pyc files. In Unix systems the command `find . -name '*.pyc' -delete` will do it.

3. Remove all editor configurations such as `.idea`, `.vscode` etc.

4. Remove the `.git` directory and the `.gitignore` file.

5. Remove the `.coverage` and `.pytest_cache` from `bin` directory.

6. Create a zip file of `TA-lumeta-addon` directory. In Linux systems, the command
`zip -r TA-lumeta-addon.zip TA-lumeta-addon` will do it.

7. Run the splunk app inspect tool to verify the the generated file is in the correct format. Install
the splunk app inspect tool and run `splunk-appinspect inspect TA-lumeta-addon.zip --mode precert --included-tags cloud`.

##Create inputs.conf

1. Extract the zipped package of add-on
2. Go to default folder. Create a file inputs.conf
3. Add the below configurations to ingest port as well as api data

    [tcp://9997]    
    disabled = 0    
    sourcetype = lumeta_log_parser  
    queue = parsingQueue    
    index=lumeta
    
    [lumeta]
    index = lumeta  
    start_by_shell = false  
    python.version = python3    
    sourcetype = lumetaapiparser    
    interval = 30   
    
4. We can configure inputs as needed.

   

## Installation

1. Log in to Splunk and navigate to Apps > Manage Apps. Click install app from file.

2. Select the zip file you want to install, then check on the update addon check box and click on upload button.

3. Once the installation is complete, restart splunk.

4. Login and create index by navigating to Settings > Indexes > New Index. Provide the Index Name > Select aap-name from App drop-down

5. Install CIM package from the following link https://splunkbase.splunk.com/app/1621/#/overview

### Inputs

Go to the apps list and open Lumeta. 

From inputs screen, click on new input. Enter the values and click on `Add`.

The following input configurations are available.

* Name(Required) - Provide a name for the input configuration.
* Interval(Required) - Time interval between each addon invocation. For example, the addon will run in every 5 minutes
if it is set to 300.
* Index(Required) - Select the index to save the data. It will be default
* Lumeta URL(Required) - Provide the base url of the api.
* API Key(Required) - Provide the key to access data from url.

### Configurations

Click on the `Configuration` tab next to `Inputs` tab. 

To configure logging, Select `Logging`. Select the desired log level and click on `Save`

## Search

To see data logged by `Lumeta`, select the `Search` tab. Select the time as 'All Time'. Click on `Data Summary` and select sourcetype 'lumetaapiparser' to view REST API data and sourcetype 'lumeta_log_parser' to view syslog. You can also enter search parameters in search box to filter logs.

##Create indexes.conf if necessary
[lumeta]    
coldPath = $SPLUNK_DB/lumeta/colddb 
enableDataIntegrityControl = 0  
enableTsidxReduction = 0  
homePath = $SPLUNK_DB/lumeta/db 
maxTotalDataSizeMB = 512000   
thawedPath = $SPLUNK_DB/lumeta/thaweddb 

#App

##Installation

1. Log in to Splunk and navigate to Apps > Manage Apps. Click install app from file.

2. Select the lumeta_app.zip file to install, then check on the update addon check box and click on upload button.

3. Once the installation is complete, restart splunk.

4. Go to the apps list and open Lumeta App for Splunk.

5. Navigate through different tabs and check the visualizations by changing the timepicker