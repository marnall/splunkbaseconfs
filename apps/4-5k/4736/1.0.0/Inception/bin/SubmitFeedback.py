import splunk.Intersplunk as si
import sys

import requests
import json

try:
    #This allows us to get the sessionKey for the logged in Splunk user that executed this script
    results, dummyresults, settings = si.getOrganizedResults()
    sessionKey = settings.get("sessionKey")

    appName = "Inception"
    #KV Stores entries can be user-specific or global (nobody is used to specify a global entry)
    #Note: User-specific KV Store entries cannot be accessed through inputlookup/lookup
    user = "nobody"
    #This is the name of the KV Store we want to add the entry to
    collectionName = "SubmittedFeedback"
    #This value is passed into the script as an argument
    feedbackText = sys.argv[1]

    #Note: This will not work if the REST API port has been changed from the default of 8089
    url = 'https://localhost:8089/servicesNS/{}/{}/storage/collections/data/{}'.format(user, appName, collectionName)

    #These headers are used to authenticate our request and specify that we're passing the data as json
    headers = { "Authorization" : "Splunk " + sessionKey,
                "content-type" : "application/json" }

    #This is our new KV Store entry
    entry = { "feedbackText" : feedbackText }

    #Adds the KV Store entry
    #Note: We set 'verify' to False because we are connecting to the localhost, and the name on the certificate is unlikely to match
    response = requests.post(url, headers=headers, data=json.dumps(entry), verify=False)

    #TODO: If you use this code in production, validate response status code and data here to ensure entry was added properly
    
#TODO: If you use this code in production, add error handling here
except:
    pass
    
