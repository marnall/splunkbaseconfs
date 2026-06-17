# Copyright (C) 2005-2011 Splunk Inc.  All Rights Reserved.  Version 4.x
# Splunk Author: Nimish Doshi
import sys,splunk.Intersplunk
import string
import socket
import traceback

# Idea and trace route function is by Leonid Grinberg
# http://blog.ksplice.com/2010/07/learning-by-doing-writing-your-own-traceroute-in-8-easy-steps/ 
# https://github.com/leonidg/Poor-Man-s-traceroute 

# Hardcode the port, max_hops, and MAX_ASTR (number of non determined hosts)
port = 33434
max_hops = 20
MAX_ASTR = 4
socket_timeout = 2

def traceroute(dest_name):
    try:
        dest_addr = socket.gethostbyname(dest_name)
    except:
        result="No Route Found"
        return result
    icmp = socket.getprotobyname('icmp')
    udp = socket.getprotobyname('udp')
    ttl = 1
    astr_count=0
    result=""

    while True:
        recv_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
        send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, udp)
        send_socket.setsockopt(socket.SOL_IP, socket.IP_TTL, ttl)
        recv_socket.bind(("", port))
        send_socket.sendto("".encode(), (dest_name, port))
        curr_addr = None
        curr_name = None
        try:
# Added Timeout
            recv_socket.settimeout(socket_timeout)
            _, curr_addr = recv_socket.recvfrom(512)
            curr_addr = curr_addr[0]
            try:
                curr_name = socket.gethostbyaddr(curr_addr)[0]
            except socket.error:
                curr_name = curr_addr
        except socket.error:
            pass
        finally:
            send_socket.close()
            recv_socket.close()

        if curr_addr is not None:
            curr_host = "%s (%s)" % (curr_name, curr_addr)
        else:
            curr_host = "*"
            astr_count += 1

        result +=  "[" + str(ttl) + "]"  + " " + curr_host

        ttl += 1
        if curr_addr == dest_addr or ttl > max_hops or astr_count>MAX_ASTR:
            break
        else:
            result += "\n"
    return result
#
addressfield="address"

if len(sys.argv)>1 and len(sys.argv) != 4:
    print ("Usage |traceroute address as <local-field> (or have address field name in data)")
    sys.exit()
elif len(sys.argv) == 4:
    addressfield=sys.argv[3]


results = []

try:

    results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
    
    for r in results:
        if "_raw" in r:
            if addressfield in r:
                traceresult=""
                r["traceroute"] = "none"

                try:
                    # get address and traceroute results
                    address=r[addressfield]
                    traceresult=traceroute(address)
                    if traceresult!="":
                        r["traceroute"] = traceresult
                    else:
                        r["traceroute"] = "none"
                except:
                    r["traceroute"] = "none"
                    traceback.print_exc(file=sys.stderr)



except:
    import traceback
    stack =  traceback.format_exc()
    results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

splunk.Intersplunk.outputResults( results )
