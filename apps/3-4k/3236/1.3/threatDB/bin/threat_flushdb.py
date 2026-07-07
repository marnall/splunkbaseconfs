#!/usr/bin/python

#####
##### RST Threat Database add-on for Splunk Enterprise
##### Copyright (c) 2017 RST Cloud
##### https://www.rstcloud.net/
##### 
##### Author: Nikolay Arefiev
##### Contributor: Yury Sergeev
##### 

import sys
import redis

if len(sys.argv) != 3:
    print "Usage: python threat_flushdb.py (all|netsdb) flush "
    sys.exit(0)

db_type = sys.argv[1]
doflush = sys.argv[2]

redis_server = '127.0.0.1'
redis_port = 6379
redis_ipdb = 0
redis_domaindb=1

def make_redisconn(conn_db):
    try:
        redis_pool = redis.ConnectionPool(host=redis_server, port=redis_port, db=conn_db)
        redis_conn = redis.Redis(connection_pool=redis_pool)
    except:
        print 'status=error, message="Redis connection error '+redis_server+':'+redis_port+'"'
        sys.exit(0)
    return redis_conn

def main():
    if db_type == 'all':
        red = make_redisconn(redis_ipdb)
        if doflush == 'flush':
            red.flushdb()   
        print 'status=done, message="ThreatDB all flushed"'
        
    if db_type == 'netsdb':
        red = make_redisconn(redis_ipdb)
        if doflush == 'flush':
            red.delete('net:index')
        print 'status=done, message="ThreatDB nets flushed"'
main()
sys.exit(0)


    
    
