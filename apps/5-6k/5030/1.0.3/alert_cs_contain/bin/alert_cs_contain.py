import sys
import json
import requests

#####
## Uses a search query containing a CrowdStrike Falcon AID to network-contain the host (for instance, if there is an A/V detection event).
## See https://www.groundsecurity.com/crowdstrike-auto-contain/ for details.
#####

# Gets Bearer token and then contains selected host
def host_contain(aid, csauthid,csauthkey):
    tokenurl = "https://api.crowdstrike.com/oauth2/token"
    containurl = "https://api.crowdstrike.com/devices/entities/devices-actions/v2?action_name=contain"
    json_headers = {'Content-type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'}
    json_body = {'client_id':csauthid, 'client_secret':csauthkey}
    tokencall = requests.post(tokenurl, headers=json_headers, data=json_body)
    if tokencall.status_code == 201:
        tokendata = tokencall.json()
        token = tokendata["access_token"]
        bearerauth = "Bearer " + token
        idslist = [aid]
        containheaders = {"Authorization":bearerauth,"Content-type":"application/json"}
        containbody = {"ids":idslist}
        jsonbytes = json.dumps(containbody).encode('utf-8')
        containcall = requests.post(containurl, headers=containheaders, data=jsonbytes)
        if containcall.status_code == 202:
            return True
        else:
            apierror = "API call error " + str(containcall)
            return apierror
    else:
        apierror = "Get token error " + str(tokencall)
        return apierror


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit(1)
    try:
        settings = json.loads(sys.stdin.read())
        print >> sys.stderr, "DEBUG Settings: %s" % settings
        cs_auth_id = settings['configuration'].get('csauthid')
        cs_auth_key = settings['configuration'].get('csauthkey')
        cs_host_aid = settings['result'].get('event.SensorId')
        cs_call = host_contain(cs_host_aid, cs_auth_id, cs_auth_key)
        if cs_call == True:
            sys.exit(0)
        else:
            print >> sys.stderr, "ERROR Unexpected error: %s" % cs_call
            sys.exit(2)
    except Exception as e:
        print >> sys.stderr, "ERROR Unexpected error: %s" % e
        sys.exit(3)