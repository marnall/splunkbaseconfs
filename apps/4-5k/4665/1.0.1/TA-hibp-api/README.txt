# Have I Been Pwned checker (v3 API) add-on

# OVERVIEW
	Have I Been Pwned checker (v3 API) add-on allows you to search across multiple data breaches to see if your email address(es) has been compromised. This add-on supports the latest v3 API.
	
	Author: Jawahar
	Date: 10 Sep 2019
	Version: 1.0.1

# INSTALLATION AND CONFIGURATION
	Note:
	**hibp command must not use at starting of the search**

	Warning:
	Uninstall Haveibeenpwned Checker app (if installed already)

	Configuration:
	Enter your API key in the App setup page.
	Manage Apps -> Click Set up against 'HaveIBeenPwnedAPI' app -> Enter API key under 'API key' section
	
# USER GUIDE

	hibp command search email ids in haveibeenpwned.com.

	Example1: | makeresults | eval email="xxx@email.com" | hibp field=email
	Example2: | inputlookup email_suspicious | table mail | hibp field=mail

	Options:
	- "field" : searching value field (email)

	Output fields:
	Pwned_details ( contains Breach Title, Breach Date, DataClasses)
	Title: Dailymotion, BreachedDate: 2016-10-20, DataClasses: ['Email addresses', 'Passwords', 'Usernames']

	Usage:
	<base_query> | hibp field=<emailfield>

	produces new field called Pwned_Details and it has three possible values :

	if email found - > produces result with Breach Title,Date, DataClases
	if email not found -> produces static message "Not Pwned"
