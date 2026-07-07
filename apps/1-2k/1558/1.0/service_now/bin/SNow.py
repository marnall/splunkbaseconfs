#!/usr/bin/python

##  SPLUNK FOR SERVICE NOW (SNow)
##
##  Author:	 Ron Naken (ron@splunk.com)
##  Version:	0.01b
##
##  Copyright (c) 2011 Splunk Inc.  All rights reserved.
##
##  This program provides Service Now API integration to Splunk
##  through a simplified search command.

import os, sys, time, datetime
import splunk.Intersplunk as isp

from SOAPpy import SOAP

_APP_ = 'service_now'

DEFAULT_ARGS = {

    'instance':             '',
    'username':             '',
    'password':             '',
    '_add':                 '',
    '_field':               '',
    'request':              '',
    'action':               '',
    'filter':               '',
    'usenull':              'f',
    '__order_by':           '',
    '__order_by_desc':      '',
    '__exclude_columns':    '',
    '__limit':              '',
    '__first_row':          '',
    '__last_row':           '',
    '__use_view':           '',
    '__encoded_query':      '',
    'aggregate':            '',
    'work_notes':           'Filed by Splunk',
    'sourcetype':           'service_now',

}

SPECIAL_ARGS = [

    '__order_by',
    '__order_by_desc',
    '__exclude_columns',
    '__limit',
    '__first_row',
    '__last_row',
    '__use_view',
    '__encoded_query',

]


_defaults_override_ = [     # defaults OK to pass to query

    'work_notes',

]

ARG_SEPARATOR = ';'
_defaults_ = []
_passwd_ = {}

def arg_join(a, b):
    if (a and b):
        return a + ',' + b
    return a or b

def trim_arg(s):
    filter = [ '"', "'"]
    if s[:1] in filter: s = s[1:]
    if s[-1:] in filter: s = s[:-1]
    return s

def parse_filter(filter, aggr):
    buf = ''
    c = 0
    if not aggr and filter.startswith('__encoded_query='):
        return filter[:16] + "'" + filter[16:] + "'"
    li = filter.split(';')
    for item in li:
        kv = item.split('=')
        if len(kv) > 1:
            val = item[item.find('=') + 1:]
            try:
                val = int(val)
            except:
                val = "'" + val + "'"
            if c > 0: buf += ','
            buf += kv[0] + "=" + str(val)
            c = 1
    return buf

def parse_special(**kwargs):
    s = ''
    c = 0
    for k in SPECIAL_ARGS:
        if not kwargs[k] == '':
            if c > 0: s += ','
            s += k + '="' + kwargs[k] + '"'
            c = 1
    return s

def raw_val(s):
    return str(s).replace('"', '\"')

def soap_query(**kwargs):

    methods = ['getRecords', 'aggregate']

    request, action = kwargs['request'], kwargs['action']
    aggr = (action == 'aggregate')

    if request == 'table': request = kwargs['table']

    username, password, instance = kwargs['username'], kwargs['password'], kwargs['instance']
    proxy = 'https://%s:%s@%s.service-now.com/%s.do?SOAP&displayvalue=all' % (username, password, instance, request)
    namespace = 'http://www.service-now.com/'

    server = SOAP.SOAPProxy(proxy, namespace, simplify_objects=1)
    response = eval("server." + methods[aggr] + "(" + arg_join(parse_special(**kwargs), arg_join(parse_filter(kwargs['aggregate'], 1), parse_filter(kwargs['filter'], 0))) + ")")
    timestamp = time.time()

    if str(response) == '{}':
            isp.generateErrorResults('ERROR: No results were returned.  Your Service Now account may not have permission to perform the requested SOAP operation.')
            exit(0)

    if type(response) == dict:
        response = [ response ]

    output = []
    i = 0
    for record in response:

        rowset = {}

        # set time
        raw = [datetime.datetime.fromtimestamp(timestamp).isoformat()]
        rowset['_time'] = timestamp
            
        # set primary stuff
        rowset['host'] = kwargs['instance'] + '.service-now.com'
        rowset['source'] = request + ':' + action
        rowset['sourcetype'] = kwargs['sourcetype']
        rowset['_cd'] = 1

        if aggr:
            rowset['function'] = kwargs['aggregate']
            raw.append('function="' + rowset['function'] + '"')

        if type(record) == dict:
            for k, v in record.iteritems():
                    if (v == '') and (kwargs['usenull'] == 'f'): continue
                    rowset[k] = v
                    raw.append(k + '="' + raw_val(v) + '"')
        else:
            rowset['response'] = str(record)
            raw.append(raw_val(record))

        splitter = ' '
        rowset['_raw'] = splitter.join(raw)
        output.append(rowset)
        i += 1

    return output

def soap_insert(**kwargs):

    buf = ''
    fields = {}
    for k, v in kwargs.iteritems():
        if (not k in _defaults_) or (k in _defaults_override_):
            fields[k] = v
            buf += k + "='" + v + "', "

    request, action = kwargs['request'], kwargs['action']
    if request == 'table': request = kwargs['table']
    
    username, password, instance = kwargs['username'], kwargs['password'], kwargs['instance']
    proxy = 'https://%s:%s@%s.service-now.com/%s.do?SOAP&displayvalue=all' % (username, password, instance, request)
    namespace = 'http://www.service-now.com/'

    server = SOAP.SOAPProxy(proxy, namespace, simplify_objects=1)
    response = eval("server.insert(" + buf + ")")

    output = []
    rowset = {}

    # set time
    timestamp = time.time()
    raw = [datetime.datetime.fromtimestamp(timestamp).isoformat()]
    rowset['_time'] = timestamp
        
    # set primary stuff
    rowset['host'] = kwargs['instance'] + '.service-now.com'
    rowset['source'] = request + ':' + action
    rowset['sourcetype'] = kwargs['sourcetype']
    rowset['_cd'] = 1

    rowset['action'] = action
    raw.append('action="' + str(action) + '"')

    rowset['request'] = request
    raw.append('request="' + str(request) + '"')

    if type(response) == dict:
        for k, v in response.iteritems():
            rowset[k] = '"' + str(v) + '"'
            raw.append(k + '="' + str(v) + '"')
    else:
        rowset['response'] = str(response)
        raw.append('response="' + str(response) + '"')

    if len(fields) > 0:
        for k, v in fields.iteritems():
            rowset[k] = '"' + str(v) + '"'
            raw.append(k + '="' + str(v) + '"')

    splitter = ' '
    rowset['_raw'] = splitter.join(raw)
    output.append(rowset)

    return output

def soap_request(**kwargs):

    SOAP_TABLE = {
        'query':        soap_query,
        'insert':       soap_insert,
        'aggregate':    soap_query,
    }

    if kwargs['instance'] == '':
            isp.generateErrorResults('ERROR: No instance specified.')
            exit(0)
            
    action = request = ''
    try:
        request, action = kwargs['request'], kwargs['action']
        if not (action in SOAP_TABLE):
            raise
    except Exception, e:
            isp.generateErrorResults('ERROR: Bad action:  request="%s", action="%s".' % (request, action))
            exit(0)

    return SOAP_TABLE[action](**kwargs)

def parse_add(**kwargs):
    if not kwargs['_add'] == '':
        args = kwargs['_add'].split(';')
        for item in args:
            kv = item.split('=')
            if len(kv) > 1:
                val = item[item.find('=') + 1:]
                try:
                    val = int(val)
                except:
                    pass
                kwargs[kv[0]] = str(val)

def get_authinfo():
    global DEFAULT_ARGS, _passwd_
    keys = [ 'username', 'password' ]
    try:
        path = os.environ['SPLUNK_HOME']  
        path = os.path.join(path, 'etc', 'apps', _APP_, 'local', '_passwd_.conf')
        fp = open(path, 'r')
        stanza = 'default'
        _passwd_[stanza] = {}
        for l in fp.readlines():
            l = l.strip()
            if l.startswith('[instance:'):
                stanza = l[10:-1]
                _passwd_[stanza] = {}
                continue
            pos = l.find('=')
            key = l[:pos].strip().lower()
            val = l[pos + 1:].strip()
            if key in keys:
                _passwd_[stanza].update({ key: str(val) })
        fp.close()
    except Exception, e:
        return

def try_passwd(key, instance):
    try:
        val = _passwd_[instance][key]
    except:
        try:
            val = _passwd_['default'][key]
        except:
            return ''
    return val

if __name__ == '__main__':

    get_authinfo()

    args = DEFAULT_ARGS
    for k in args:
        _defaults_.append(k)

    for item in sys.argv:
        kv = item.split('=')
        if len(kv) > 1:
            val = item[item.find('=') + 1:]
            try:
                val = int(val)
            except:
                pass
            args[kv[0]] = str(val)

    if not args['_field'] == '':

        results,dummyresults,settings = isp.getOrganizedResults()
        if results == []:
            isp.generateErrorResults("No events were passed for _field.")
            exit(0)
        for event in results:
            args['_add'] = event.get(args['_field'], '')
            break
    
        if args['_add'] == '':
            isp.generateErrorResults("Field '%s' was not found." % (args['_field']))
            exit(0)            
        else:
            targs = args['_add'].split(';')
            for item in targs:
                kv = item.split('=')
                if len(kv) > 1:
                    val = item[item.find('=') + 1:]
                    try:
                        val = int(val)
                    except:
                        pass
                    args[kv[0]] = str(val)

    if args['username'] == '': args['username'] = try_passwd('username', args['instance'])
    if args['password'] == '': args['password'] = try_passwd('password', args['instance'])

    try:
        results = soap_request(**args)
    except Exception, e:
        results = isp.generateErrorResults(str(e))
        
    isp.outputResults(results)
