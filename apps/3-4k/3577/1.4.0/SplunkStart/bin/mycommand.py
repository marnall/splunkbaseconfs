# Author: Nimish Doshi
import sys,splunk.Intersplunk
import string

rot13 = string.maketrans( 
    "ABCDEFGHIJKLMabcdefghijklmNOPQRSTUVWXYZnopqrstuvwxyz", 
    "NOPQRSTUVWXYZnopqrstuvwxyzABCDEFGHIJKLMabcdefghijklm")

results = []

try:

    results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
    
    for r in results:
        if "_raw" in r:
###### Put in your custom Code here to change the raw data or change a field

            r["_raw"] = string.translate(r["_raw"], rot13)

###### End Custom Code

except:
    import traceback
    stack = traceback.format_exc()
    results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

splunk.Intersplunk.outputResults( results )

