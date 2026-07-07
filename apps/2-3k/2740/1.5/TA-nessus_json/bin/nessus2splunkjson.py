#!/usr/bin/env python
import requests, json, sys, os, time,datetime

"""
uncomment the line below in order to disable ssl warnings
"""
requests.packages.urllib3.disable_warnings()

"""
URL of Nessus scanner
"""
url = 'https://127.0.0.1:8834'


"""
Uncomment and enter your username and password. Starting with Nessus version 6.4+ , Api keys are preferred, you may enter the keys instead of username and password.
"""
username = 'gandalf'
password = 'thehobbit'
"""
If you want to import specific scans , you will specify them under this comment.
example : scan id's 4,678,34 would look like this sa = [4,678,34]
*use ./bin/getscanID.py
The default is to import all scans
*if line 27 is uncommented them line 242 MUST be commented
"""
#sa = []

"""
you can customize drop and pickup directories below
defaults defined
"""
dropdir = '/opt/splunk/etc/apps/TA-nessus_json/drop'
pickupdir = '/opt/splunk/etc/apps/TA-nessus_json/pickup'


verify = False
token = ''

sid = ''
hid = ''
fid =''
file_id = ''
pidf = ''
hoid =''
count = 0

#enter your nessus api access keys here , version 6.4+ allows you to create api keys. Please refer to nessus documentation for nessus 6.4+
accessKey = 'my access key'
secretKey = 'my secret key'




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
#time stamp
def timeStamped(fname, fmt='{fname}_%Y%m%d-%H%M%S.log'):
    return datetime.datetime.now().strftime(fmt).format(fname=fname)

#get plugin id info
def get_pid_info(pid):

    data = connect('GET', '/plugins/plugin/{0}'.format(pid))

    if data is not None:
        return dict((h['attribute_name'], h['attribute_value']) for h in data['attributes'])
#get hostname , hostid
def gethostsdetails(sid,hid):

    data = connect('GET', '/scans/{0}?history_id={1}'.format(sid,hid))
    return dict((h['hostname'], h['host_id']) for h in data['hosts'])
    #return data
#get history id and unique id's
def get_history_uuid(sid):

    data = connect('GET', '/scans/{0}'.format(sid))
    return dict((h['history_id'], h['uuid']) for h in data['history'])
    #return data

def get_history_uuid2(sid,hid):

    data = connect('GET', '/scans/{0}?history_id={1}'.format(sid,hid))
    #return dict((h['history_id'], h['uuid']) for h in data['history'])
    return data

#host id return
def gethostsdetails1(sid):

    data = connect('GET', '/scans/{0}'.format(sid))
    return list((h['host_id']) for h in data['hosts'])


def getnumberofhosts(sid,hid):

    data = connect('GET', '/scans/{0}?history_id={1}'.format(sid,hid))
    return list((h['hostname']) for h in data['hosts'])

def getuuid(sid,hid):

    data = connect('GET', '/scans/{0}?history_id={1}'.format(sid,hid))
    return list((h['uuid']) for h in data['history'])

def get_pid():

    data = connect('GET', '/plugins/families')
    return list((h['id']) for h in data)

#pid information
def get_pidf(pidf):

    data = connect('GET', '/plugins/families/{0}'.format(pidf))
    return list((h['id']) for h in data['plugins'])

#scan status
def scanstatus(sid, hid):

    params = {'history_id': hid}
    data = connect('GET', '/scans/{0}'.format(sid), params)

    return data['info']['status']

# scan status using history id
def scanstatus2(sid, hid):

    params = {'history_id': hid}
    data = connect('GET', '/scans/{0}?history_id={1}'.format(sid,hid))

    return data['info']['status']

def get_history_ids2(sid):

    data = connect('GET', '/scans/{0}'.format(sid))

    return list((h['history_id']) for h in data['history'])


#return all scan id numbers
def allsids():
        data = connect('GET', '/scans/')
        return list((h['id']) for h in data['scans'])


#grab vulnerabilities per host
def gethostsdetails3(sid,hoid,hid):
    data = connect('GET', '/scans/{0}/hosts/{1}?history_id={2}'.format(sid,hoid,hid))
    return list((h['plugin_id']) for h in data['vulnerabilities'])


def gethostsdetails4(sid,hoid):

    data = connect('GET', '/scans/{0}/hosts/{1}'.format(sid,hoid,hid))
    return data

def getname(sid):
        data = connect('GET', '/scans/{0}'.format(sid))
        return data['info']['name']

def jsonf(d,sid,scanname,hid,pid,hostid):

    filename = '/opt/nessus/json/sid_{0}_name_{1}_hid_{2}_pid_{3}_hostID_{4}.json'.format(sid,scanname,hid,pid,hostid)

    print('Saving scan results for pid {0}.'.format(filename))
    with open(filename, 'w') as outfile:
        json.dump(d, outfile)

def gethostdetails5(sid,hoid,hid):

    params = {'history_id': (hid)}
    data = connect('GET', '/scans/{0}/hosts/{1}?history_id={2}'.format(sid,hoid,hid))
    return data['info']


def logout():
    """
    Logout of nessus.
    """

    connect('DELETE', '/session')



if __name__ == '__main__':
    pid = ''
    pidf = ''
    sid = ''
    hoid = ''
    hon = ''
    hostdict = {}
    hidarray=[]
with open(timeStamped("../logs/nessus2splunkjson_results"), 'w') as log:
        #headers needed for login using api keys
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
    """
    control whether or not to import ALL scans here
    if no scans are specified on line 27, you will need to uncomment the line below this comment section to "sa=allsids()" in order to import all scans.
    ** if line 242 is uncommented , then line 27 should be commented out like so "#sa = []"


    """

    sa = allsids()
#open a log file
    log.write("Start time:"  + time.strftime("%c") + "\n")
    with open("hid_history") as o:
#                hidarray = lines = [line.rstrip('\n').rstrip() for line in open('hid_history')]
        hidarray = [int(i) for i in o.readlines()]






    print "Depending on the size of your scan this can take several hours/days"
    for s in sa:
        x = get_history_ids2(s)
        f = get_history_uuid(s)
        n = getname(s)
        print f.keys()
        seta = list(f.keys())
        setb = list(set(seta) - set(hidarray))
        print "On scan:", n, "Processing historical id's", setb

        for hid in setb:
            status = scanstatus2(s, hid)
            uuid = getuuid(s,hid)


            #check to see if scan is runnings
            #if (status is not 'running' and g is False):
            lg = getnumberofhosts(s,hid)
            hostlen = len(lg)

            if (status != 'running'):
                print "\nProcessing Scan Name:",n, ", scan_id:", s, ", history_id:" ,hid,""
                if (hostlen !=0):
                    count = 0
                    log.write("####################\n")
                    log.write("Processing Scan Name " + str(n) + " Scan_ID: " + str(s) +" History id: " + str(hid))
                    h = gethostsdetails(s, hid)
                    #f = getuuid(s,hid)
                    #print f

                    #create hosts dictionary , upddate items in dictionary
                    for hostname,hostid in h.items():
                                k = gethostdetails5(s,hostid, hid)
                                n = getname(s)
                                d = dict([("hostname", (hostname))])
                                d.update({'scan_id':(s)})
                                d.update({'hid':(hid)})
                                d.update({'host_id':(hostid)})
                                d.update({'ScanName':(n)})
                                d.update({'uuid':(uuid)})
                                d.update({'scan_status':(status)})
                                #d.update({'status':(status)})
                                i = gethostsdetails3(s,hostid,hid)
                                jsonarray = json.dumps(k, ensure_ascii=False)
                                d.update(k)
                                count +=1
                                #print uuid
                                #print hid




                                #grab pid information
                                for pid in i:
                                            pi = get_pid_info(pid)
                                            jsonarray = json.dumps(pi, ensure_ascii=False)
                                            o = jsonarray
                                            #print pid
                                            d.update({'plugin_id':(pid)})
                                            if pi is not None:
                                                d.update(pi)
                                            filename = '{0}/sid_{1}_name_{2}_hid_{3}.json'.format(dropdir,s,n,hid)
                                            with open(filename, 'a') as outfile:
                                                json.dump(d, outfile)
                                                sys.stdout.write("\rHost {0} of {1}".format(count, hostlen))
                    #drop file, do some logging
                    pickupfile = '{0}/sid_{1}_name_{2}_hid_{3}.json'.format(pickupdir,s,n,hid)
                    os.rename(filename,pickupfile)
                    log.write("\nfilename " + filename +  "\n")
                    log.write("was moved to  " + pickupfile +  "\n")
                    log.write("Completed on " + time.strftime("%a %X") +  "\n")
                    hidtextw = open("hid_history", 'a')
                    hidtextw.write(str(hid) + "\n")
                    hidtextw.close()



                else :
                    print  hostlen, " hosts reported."
                    log.write("Scan Name " + str(n) + " Scan_ID: " + str(s) +" History id: " + str(hid))
                    hidtextw = open("hid_history", 'a')
                    hidtextw.write(str(hid) + "\n")
                    hidtextw.close()
                    log.write(" is reporting " + str(hostlen) +" hosts scanned.\n")


            else:

                print "\nSkipping Scan Name:",n, ", scan_id:", s, ", history_id:" ,hid, "appears to be running"
                log.write("Skipped " + str(n) + " Scan_ID: " + str(s) +" History id: " + str(hid) + "\n" )

    log.write("End time:"  + time.strftime("%c") + "\n")
#    logout()
