from __future__ import unicode_literals
import os
import sys
import traceback
import time
import datetime
import csv
import base64

from pyhop import pyhop

def get_connection(opts):
    '''Gets connection object to Extrahop device
       If the connection fails, print the traceback and exit with status 1
    '''

    try:
        c = pyhop.Client(host=opts['hostname'],user=opts['username'],passwd=opts['password'])
    except Exception,e:
        print "Error in Extrahop_metrics ehm_device_lookup.py"
        print(e)
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)

    return c


def main(opts):
    '''main program logic'''
    
    header = ["name","oid"]
    conn = get_connection(opts)

    result = conn.get_all_devices() 

    if len(result) > 0:
        with open(os.path.join(opts['output_path'],'ehm_all_devices.csv'), 'wb') as fh:
            headers = ['name','oid']
            w = csv.DictWriter(fh,headers)
            w.writeheader()
            for d in result:
                results = {}
                name = ''
                oid = ''
                for k,v in d.iteritems():
                    if k == 'name':
                        results['name'] = v
                    if k == 'oid':
                        results['oid'] = v
                w.writerow(results)

    conn.logout()
    sys.exit(0)


if __name__ == '__main__':
    if len(sys.argv) == 5:
        opts = {'username': sys.argv[1],
                'password': base64.b64decode(sys.argv[2]),
                'hostname': sys.argv[3],
                'output_path': sys.argv[4]}
        main(opts)
        sys.exit(0)
    else:
        print "wrong number of arguments sent to ehm_device_lookup.py"
        print "Please check the wrapper script to ensure proper arguments are sent to this script"
        sys.exit(1)