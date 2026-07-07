#!/usr/bin/env python
import requests, json, sys, os,time,csv,datetime
requests.packages.urllib3.disable_warnings()

"""
You must uncomment and enter your Nessus url, username, and passwords in the fields below once this is done, you invoke the script by running ./getscanID.py it will generate a report with scan names and Id's. Starting with Nessus version 6.4+ , Api keys are preferred, you may enter the keys instead of username and password.
**The Nessus account must have read access to the scans you want to see.
"""
url = 'https://127.0.0.1:8834'
username = 'gandalf'
password = 'thehobbit'

#enter your nessus api access keys here , version 6.4+ allows you to create api keys. Please refer to nessus documentation for nessus 6.4+
accessKey = 'my access key'
secretKey = 'my secret key'

verify = False
token = ''
sid = ''
hid = ''
fid =''
file_id = ''
pidf = ''
hoid =''
count = 0


def login(usr, pwd):
        login = {'username': usr, 'password': pwd}
        data = connect('POST', '/session', data=login)
        return data['token']

def build_url(resource):
        return '{0}{1}'.format(url, resource)

def connect(method, resource, data=None):
        #headers = {'X-Cookie': 'token={0}'.format(token), 'content-type': 'application/json'}
        data = json.dumps(data)
        if method == 'POST':
                r = requests.post(build_url(resource), data=data, headers=headers, verify=verify)
        elif method == 'PUT':
                r = requests.put(build_url(resource), data=data, headers=headers, verify=verify)
        elif method == 'DELETE':
                r = requests.delete(build_url(resource), data=data, headers=headers, verify=verify)
        else:
                r = requests.get(build_url(resource), params=data, headers=headers, verify=verify)

        if r.status_code != 200:
                e = r.json()
                print e['error']
                sys.exit()

        if 'download' in resource:
                return r.content
        else:
                return r.json()


def timeStamped(fname, fmt='{fname}_%Y%m%d-%H%M%S.log'):
    return datetime.datetime.now().strftime(fmt).format(fname=fname)

def getname(sid):
        data = connect('GET', '/scans/{0}'.format(sid))
        return data['info']['name']


def allsidsname():
        data = connect('GET', '/scans/')


        return dict((h['id'], h['name']) for h in data['scans'])


if __name__ == '__main__':
    headers = {'X-ApiKeys': 'accessKey={0} ; secretKey={1}'.format(accessKey,secretKey), 'content-type': 'application/json'}
    resource = '/session'
    data = requests.get(build_url(resource), headers=headers, verify=verify)

    if data.status_code is 200:
        print "using API keys for Login"

    else:
        print "Api keybased log in failed, double check the access and secret keys,  reverting to session based login"
        #get token via username and password and set header settings for session based login
        token = login(username, password)
        headers = {'X-Cookie': 'token={0}'.format(token), 'content-type': 'application/json'}
        resource = '/session'
        data = requests.post(build_url(resource), headers=headers, verify=verify)
    sid = ''



    sa = allsidsname()
    print "Scan ID\t\t" , "Scan Name"
    for s,n in sa.items():
        #n = getname(s)
        #print sa
        print  s,"\t\t" , n
