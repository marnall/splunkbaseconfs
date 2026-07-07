Value Journey for Splunk  = 1.0.0
Description: This application is focused on ramping up the Splunk Knowledge and Experience for New Splunkers, using example dashboards, reports and step-by-step walkthroughs.

**Required Secondary Application:
Value Journey Manager for Splunk - Version 1.0.0 
https://splunkbase.splunk.com/app/4566/

For documentation, either use the documentation dashboard within the Application UI. 
	(Value Journey for Splunk: Configuration --> How To Use Value Journey for Splunk)
	(App File Directory PDFs: /vjm_splunk/appserver/static/documentation)

Value Journey for Splunk - Installation Location:
	- Splunk Search Head Only
	
Value Journey for Splunk - Requireed Application:
	- The Value Journey for Splunk application requires the "Value Journey Manager for Splunk" application.
		- The Value Journey Manager for Splunk application is used for getting and indexing the 
		sample data that is used by the Reports, Dashboards, and Walkthroughs in the
		Value Journey for Splunk application.   
		- The Value Journey Manager for Splunk also provides a dashboard for creating the 
		"User" Splunk Accounts that will be journeying through the Value Journey for Splunk
		application.   This same dashboard also provides a way of creating the "Owner" 
		accounts that will be able to review progress and assist the "User" as they 
		navigate through the different example Reports, Dashboards, and Walkthroughs.
			- This process is needed because the "User" needs to have their basic information 
			added to a lookup, assign them to the vj_user Splunk Role and to 
			create their Splunk User account.  

Installation and Configuration Overview:
Below is an overview of the Installation and Configuration steps for the Value Journey for Splunk
solution.   

1. Install the Value Journey for Splunk and Value Journey Manager for Splunk application.
2. Create the "Owner" account, who will be the individual(s) that will be monitoring the 
progress of the "Users" and providing assistance if needed.
3. Create the "User" account, who will be the individual(s) that will be walking through
the Example Dashboards, Reports, and Walkthroughs.  
	- Note: If the targeted Owner, Or User already has a Splunk Account, still go 
	through the VJM - User Creation dashboard steps in the 
	"Value Journey Manager for Splunk" application . It will add their Splunk Account to 
	the correct Splunk Role, and add their information into the Splunk Lookup.
4. Create the required indexes (vj_ex, vj_walk, vj_sgs)  
5. Load the Current Day's Example Data (Using either the "VJM - Getting Started or VJM - Config - Load Example Data" Dashboards)
	- Description: This script is used for indexing demo data used by the Value Journey for Splunk application's Reports, Dashboards, and Walkthroughs.
	- Function: 
		- It Performs the following Steps: 
			- Step 1: Get OS Value
				- To determine the appropriate sed command format.
			- Step 2: Leftover Data Files Check 
				- remove if any found with upd_ prefix in the vjm_splunk/logs/data directory.
			- Step 3: Change Directory to the logs/data
			- Step 4: un-gzip the data template files to new files with an upd_ prefix
			- Step 5: Replaces variable text (##Tmday##) in the upd_ files with the Current or Next Days Date Value
			- Step 6: gzip the updated data files so they can be indexed with the Batch:... inputs
	- Scripted Input: This Script is provided as a possilble scripted input but is currently commented out in the inputs.conf file. 
	- Manual Input: ***(Default for Current Day, Optional for Next Day) You will use either of the following dashboard's to generate 
	  the demo data using the vjm_data_gen_cs_init.py or vjm_data_gen_cs_next.py custom search command vjm_data_gen_cs_init or vjm_data_gen_cs_next:
		- VJM - Getting Started
		- VJM - Config - Load Example Data	
6. Use the applications email, or manually email the Users their login credentials.
7. Once the User has gone through the initial, quick, Configuration Wizard, they will
	see Use Case Menu's with the Use Case Examples. 

Detailed Installation Steps:
Note: Search Head Only - The Value Journey for Splunk application only needs to be installed on the Splunk Search Head.  
1. Using the Splunk UI, navigate into the Apps Dropdown Menu, and click the Manage Apps
2. Click the Browse more apps button.
3. Enter in the search text box Value Journey for Splunk.
4. Select and install the Value Journey for Splunk application, do not restart the Splunk Instance when
prompted, until after completing the remaining steps.  
5. After installing the Value Journey for Splunk application, click the Browse more apps button again.
6. Enter in the search text box Value Journey Manager for Splunk
7. Select and install the Value Journey Manager for Splunk application, and restart the Splunk 
Service/Daemon on the Splunk Search Head.
8. Create the Value Journey for Splunk Owner and User Accounts using the VJM - User Creation
dashboard in the Value Journey Manager for Splunk application.
9. Create the required indexes (vj_ex, vj_walk, vj_sgs)  
	- Note: If the Splunk Indexer is a seperate system, then make sure to create the indexes on the Splunk Indexer system.
10. Load the Current Day's Example Data (Using either the "VJM - Getting Started or VJM - Config - Load Example Data" Dashboards)
	- Description: This script is used for indexing demo data used by the Value Journey for Splunk application's Reports, Dashboards, and Walkthroughs.
	- Function: 
		- It Performs the following Steps: 
			- Step 1: Get OS Value
				- To determine the appropriate sed command format.
			- Step 2: Leftover Data Files Check 
				- remove if any found with upd_ prefix in the vjm_splunk/logs/data directory.
			- Step 3: Change Directory to the logs/data
			- Step 4: un-gzip the data template files to new files with an upd_ prefix
			- Step 5: Replaces variable text (Ex. ##Tmday##) in the upd_ files with the Current or Next Days Date Value
			- Step 6: gzip the updated data files so they can be indexed with the Batch:... inputs
	- Scripted Input: This Script is provided as a possilble scripted input but is currently commented out in the inputs.conf file. 
	- Manual Input: ***(Default for Current Day, Optional for Next Day) You will use either of the following dashboard's to generate 
	  the demo data using the vjm_data_gen_cs_init.py or vjm_data_gen_cs_next.py custom search command vjm_data_gen_cs_init or vjm_data_gen_cs_next:
		- VJM - Getting Started
		- VJM - Config - Load Example Data
	- Distributed Options: You can manually index the Current Days demo data running the following command from another system with a Splunk Forwarder and that
	has the Value Journey Manager for Splunk application installed.  (Required: UX/Linux/OSX)
		- Command to index the Current Day's Demo Data Manually:
			1. Navigate into $SPLUNK_HOME/bin directory in a terminal
			2. Run ./splunk cmd python /$SPLUNK_HOME/etc/apps/vjm_splunk/bin/vjm_data_gen_cs_init.py
		- The Next Day's data is scheduled to generate at 11:50pm using a scripted input.   For doing a one time/manual load of the next Days data do:
			1. Navigate into $SPLUNK_HOME/bin directory in a terminal
			2. Run ./splunk cmd python /$SPLUNK_HOME/etc/apps/vjm_splunk/bin/vjm_data_gen_cs_next.py	
	- In the Splunk UI navigate to Value Journey for Splunk - Managment --> Configuration --> VJM Getting Started, and verify that the data has been indexed. 	
11. Send the User's their login credentials.  
	- Note: The first User to login will walk through an initial Configuration Wizard, which
	determines what Use Case Examples will be available. 
	
