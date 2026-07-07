######################################
# File: osc_query.py                 #
# Author: OSC                        #
# Version: 2.1                       #
# Date: 29AUG2019                    #
# Purpose: Connect Splunk to OSC API #
######################################


import sys, json, oscq_b, oscq_q
import splunk.Intersplunk
import splunklib.client as splclient
from datetime import datetime

#Parse the JSON into csv for Splunk
def parseData(jsonData, fields):
    if fields == "ALL":
        print("domain,value,value_ip,first_seen,last_seen,record_type,query_name,query_type")    
        my_fields=["domain", "value", "value_ip", "date", "last_seen", "type", "qname", "qtype"]
    else:
        my_fields = fields.split(",")
        print(fields)
    for item in jsonData:
        my_vals = []
        for i in my_fields:
            if item.get(i) is None:
                my_vals.append("")
            else:
                my_vals.append(item.get(i))
        print(",".join(my_vals))


##############
#This is main#
##############

def main(sysargs):
    

    args = oscq_b.qa(sysargs)


    query = oscq_q.query(args)
    query = oscq_q.execute(query)
    json = oscq_q.execute.query(query)
     
    parseData(json.jsonResp, str(query.query.q.args.f))

if __name__ == '__main__':
    main(sys.argv)
