import splunk.clilib.cli_common
import os
import requests
import datetime

def getData(access_token, time, query_interval):
    #Pull in all data from the API
    response = requests.get('https://app.envoy.com/api/entries.json?api_key='+access_token)
    
    #Convert to JSON
    events = response.json()
    
    #Cycle through each event
    for data in events:
        
        #start the signed_out_diff time at 9999999. 
	signed_out_diff=9999999

	#Get the signed_in time for the event
        signed_in = datetime.datetime.strptime(data["signed_in_time_utc"], "%Y-%m-%d %H:%M:%S")
	#Get the datetime version of the time we sent to the function
        now = datetime.datetime.strptime(str(time), "%Y-%m-%d %H:%M:%S")
        #Get the difference between now and the event we are examining
        signed_in_difference=now-signed_in
	signed_in_diff=signed_in_difference.seconds

        #If our signed_out_time_utc is not null do this stuff
	if str(data["signed_out_time_utc"]):
		signed_out = datetime.datetime.strptime(data["signed_out_time_utc"], "%Y-%m-%d %H:%M:%S")
		signed_out_difference=now-signed_out
		signed_out_diff=signed_out_difference.seconds


        #If the event took place less than our query_interval ago and our signed_out_time_utc is null, print a signed in event
	if signed_in_diff < query_interval  and not str(data["signed_out_time_utc"]):
                print data["signed_in_time_utc"]+' status=signed_in id='+str(data["id"])+' email=\"'+data["your_email_address"]+'\" signed_out_time_local=\"'+data["signed_out_time_local"]+'\" signed_in_time_local=\"'+data["signed_in_time_local"]+'\" full_name=\"'+data["full_name"]+'\"'
	#If the event took place less than our query_interval ago and our signed_out_time_utc is not null, print a signed out event
        if signed_out_diff < query_interval and str(data["signed_out_time_utc"]):
                print data["signed_out_time_utc"]+' status=signed_out id='+str(data["id"])+' email=\"'+data["your_email_address"]+'\" signed_out_time_local=\"'+data["signed_out_time_local"]+'\" signed_in_time_local=\"'+data["signed_in_time_local"]+'\" full_name=\"'+data["full_name"]+'\"'

#Set this variable to however long your inputs is scheduled to run. This way data is only pulled for the time between the last run of the script and the current run. 
query_interval=60

#Get Splunk Home
splunk_home = os.path.expandvars("$SPLUNK_HOME")

#Get the Current UTC Time
time=datetime.datetime.utcnow()
time=time.strftime('%Y-%m-%d %H:%M:%S')

#Read in all Access Tokens from ENVOY_tokens.conf
settings = splunk.clilib.cli_common.readConfFile(splunk_home+"/etc/apps/ENVOYAddonforSplunk/local/ENVOY_tokens.conf")
for item in settings.iteritems():
        for key in item[1].iteritems():
                token = key[1]
                #Grab Data from Each Token
                getData(token,time,query_interval)

