#####
##### RST Threat Database add-on for Splunk Enterprise
##### Copyright (c) 2017 RST Cloud
##### https://www.rstcloud.net/
##### 
##### Author: Nikolay Arefiev
##### Contributor: Yury Sergeev
##### 

import csv,sys
import urllib

##### append some python libraries
sys.path.append("/usr/local/lib/python2.7/dist-packages") #TODO: change to a relative path
from netaddr import *
import redis
import splunk.mining.dcutils as dcu

# use the default splunk logger function for alerting
logger = dcu.getLogger()

# set the connection string to Redis DB
redis_server = '127.0.0.1'
redis_port = 6379
redis_ipdb = 0		# for IP lookups
redis_domaindb=1	# TODO: add a domain lookup

def ip_threat(clientip, red):
    threatsource=[]
    threatcategory=[]
    threatscore=[]
    #Find clientip in IP DB list
    try:
       temp = red.smembers('ip:'+clientip) 
    except:
        logger.error('module="ThreatDB", message="Error on ThreatDB query"')
        return (clientip,'','','')
        
    if len(temp)!= 0:
        for i in temp:
            temp_arr=i.split(':')
            threatsource.append(temp_arr[0])
            threatcategory.append(temp_arr[1])
            threatscore.append(temp_arr[2])
        return (clientip, ",".join(threatsource), ",".join(threatcategory), ",".join(threatscore))
    
    #Find clientip in NETs DB list
    if len(temp) == 0:
        try:
            ip = IPAddress(clientip)
        except:
            return (clientip, "none", "none", "0")
        threat_nets=[]
        # Find all networks which have equal first octet
        for i in red.sscan_iter(name='net:index',match=str(ip.words[0])+'*',count=500): #search by fetching 500 values per block
            net = IPNetwork(i)
            #Check if IP from this network
            if ip in net:
                nets_list = red.smembers('net:'+str(net))
                if len(nets_list) != 0:
                    threat_nets = threat_nets + list(nets_list)
        if len(threat_nets) == 0:
            return (clientip, "none", "none", "0")
        for i in threat_nets:
            temp_arr=i.split(':')
            threatsource.append(temp_arr[0])
            threatcategory.append(temp_arr[1])
            threatscore.append(temp_arr[2])
        return (clientip, ",".join(threatsource), ",".join(threatcategory), ",".join(threatscore))
    
def main():
    if len(sys.argv) != 3:
        print "Usage: python redislookup.py [key field] [value field]"
        sys.exit(0)

    in_field = sys.argv[1]
    out_field = sys.argv[2]

    conn_db=0
    if in_field == 'clientip':	#TODO: change 'clientip' to 'ip' everywhere
        conn_db = redis_ipdb    
    try:
        redis_pool = redis.ConnectionPool(host=redis_server, port=redis_port, db=conn_db, socket_timeout=2)
        redis_conn = redis.Redis(connection_pool=redis_pool)
        redis_conn.ping()
    except:
        logger.error('module="ThreatDB", message="No ThreatDB connection"')
        return (clientip,'','','')

    r = csv.reader(sys.stdin)
    w = csv.writer(sys.stdout)
        
    header = []
    first = True

    for line in r:
        if first:
            header = line
            if in_field not in header:
                print "IP field must exist in CSV data"
                sys.exit(0)
            csv.writer(sys.stdout).writerow(header)
            w = csv.DictWriter(sys.stdout, header)
            first = False
            continue

        # Read the result
        result = {}
        i = 0
        while i < len(header):
            if i < len(line):
                result[header[i]] = line[i]
            else:
                result[header[i]] = ''
            i += 1
        
        # If CLIENTIP is set
        if in_field == 'clientip' and len(result[in_field]):
            ip_address, threat_source, threat_category, threat_score = ip_threat(str(result[in_field]),redis_conn)
            out = '%s,"%s","%s","%s"' % (ip_address, threat_source, threat_category, threat_score)
            print out    

    redis_pool.disconnect()

main()
