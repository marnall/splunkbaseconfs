import sys
import json
import requests
import datetime
import pytz
from scalr_python_api.client import ScalrApiClient

try:
   import splunk.entity as entity
except ImportError:
   import splunk_dummy.entity as entity

myapp = 'scalr_app_for_splunk'
#datetime_now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S %z')
#datetime_now = datetime.datetime.now(pytz.timezone("America/New_York"))
datetime_now = datetime.datetime.now()
datetime_now_str = datetime_now.strftime('%Y-%m-%d %H:%M:%S')

def str2bool(v):
        return v.lower() in ("yes", "true", "t", "1")

def getCredentials(sessionKey):
        try:
           api_obj = entity.getEntity('scalr_setup/api_input', 'api', namespace=myapp, owner='nobody', sessionKey=sessionKey)
           api_secret = entity.getEntity('storage/passwords', 'api:secret', namespace=myapp, owner='nobody', sessionKey=sessionKey)
        except Exception as e:
           sys.stderr.write("DATALOADER_SCRIPT_ERROR - Could not get Scalr API Credentials from Splunk. Exception: %s\n" % (str(e)))
           exit(2)

        #print(api_obj)
        #print(api_secret)
        return api_obj['url'], api_obj['key'], api_secret['clear_password'], str2bool(api_obj['verify_ssl'])

def getFetch(api_endpoint):
        try:
           result = api_client.fetch(api_endpoint,verify=api_verify_ssl)
        except Exception as e:
           sys.stderr.write("DATALOADER_SCRIPT_ERROR - Could not access {}. Exception: {}\n".format(api_endpoint,str(e)))
        else:
           return result

def getList(api_endpoint):
        result = []
        try:
           result = api_client.list(api_endpoint,verify=api_verify_ssl)
        except Exception as e:
           sys.stderr.write("DATALOADER_SCRIPT_ERROR - Could not access {}. Exception: {}\n".format(api_endpoint,str(e)))
        return result

def prettyPrintData(api_endpoint,json_data,param=''):
        if json_data != None:
           print('{{"api_reqTime": "{}", "request": {{"api_endpoint": "{}"{}}}, "response": {}}}' \
           .format(datetime_now_str,api_endpoint,param,json.dumps(json_data)))

def prettyPrintList(api_endpoint,json_list,param=''):
        # print("Found {0} records like:".format(len(json_list)))
        # print(json_list)
        if json_list != None:
           for i in json_list:
              prettyPrintData(api_endpoint,i,param)

def prettyPrintParamList(api_endpoint,param_key,param_value,json_list):
        prettyPrintList(api_endpoint,json_list,', "{}": "{}"'.format(param_key,param_value))

def prettyPrintParam2List(api_endpoint,param_key1,param_value1,param_key2,param_value2,json_list):
        prettyPrintList(api_endpoint,json_list,', "{}": "{}", "{}": "{}"'.format(param_key1,param_value1,param_key2,param_value2))

def prettyPrintParam2Data(api_endpoint,param_key1,param_value1,param_key2,param_value2,json_data):
        prettyPrintData(api_endpoint,json_data,', "{}": "{}", "{}": "{}"'.format(param_key1,param_value1,param_key2,param_value2))

def listEnvironments():
        l = getList("/api/v1beta0/account/environments/")
        prettyPrintList('account/environments',l)
        for e in l:
           prettyPrintList('account/environments/clouds',getList("/api/v1beta0/account/environments/{}/clouds/".format(e["id"])))
           prettyPrintList('account/environments/teams',getList("/api/v1beta0/account/environments/{}/teams/".format(e["id"])))
        return l

def getGlobalAPIData():
        prettyPrintList('global/global-variables',getList("/api/v1beta0/global/global-variables/"))
        prettyPrintList('global/images',getList("/api/v1beta0/global/images/"))
        prettyPrintList('global/os',getList("/api/v1beta0/global/os/"))
        prettyPrintList('global/role-categories',getList("/api/v1beta0/global/role-categories/"))
        gRoles = getList("/api/v1beta0/global/roles/")
        prettyPrintList('global/roles',gRoles)
        for r in gRoles:
           prettyPrintParamList('global/roles/global-variables','req_roleId',r["id"], \
           getList("/api/v1beta0/global/roles/{}/global-variables/".format(r["id"])))
           prettyPrintParamList('global/roles/images','req_roleId',r["id"],getList("/api/v1beta0/global/roles/{}/images/".format(r["id"])))
           prettyPrintParamList('global/roles/orchestration-rules','req_roleId',r["id"], \
           getList("/api/v1beta0/global/roles/{}/orchestration-rules/".format(r["id"])))

def getAccountAPIData():
        prettyPrintList('account/acl-roles',getList("/api/v1beta0/account/acl-roles/"))
        prettyPrintList('account/cloud-credentials',getList("/api/v1beta0/account/cloud-credentials/"))
        prettyPrintList('account/cost-centers',getList("/api/v1beta0/account/cost-centers/"))
        #prettyPrintList('account/environments',getList("/api/v1beta0/account/environments/"))
        prettyPrintList('account/events',getList("/api/v1beta0/account/events/"))
        prettyPrintList('account/global-variables',getList("/api/v1beta0/account/global-variables/"))
        prettyPrintList('account/images',getList("/api/v1beta0/account/images/"))
        prettyPrintList('account/orchestration-rules',getList("/api/v1beta0/account/orchestration-rules/"))
        prettyPrintList('account/os',getList("/api/v1beta0/account/os/"))
        prettyPrintList('account/role-categories',getList("/api/v1beta0/account/role-categories/"))
        aRoles = getList("/api/v1beta0/account/roles/")
        prettyPrintList('account/roles',aRoles)
        for r in aRoles:
           prettyPrintParamList('account/roles/global-variables','req_roleId',r["id"], \
           getList("/api/v1beta0/account/roles/{}/global-variables/".format(r["id"])))
           prettyPrintParamList('account/roles/images','req_roleId',r["id"], \
           getList("/api/v1beta0/account/roles/{}/images/".format(r["id"])))
           prettyPrintParamList('account/roles/orchestration-rules','req_roleId',r["id"], \
           getList("/api/v1beta0/account/roles/{}/orchestration-rules/".format(r["id"])))
        aScripts = getList("/api/v1beta0/account/scripts/")
        prettyPrintList('account/scripts',aScripts)
        for s in aScripts:
           prettyPrintParamList('account/scripts/script-versions','req_scriptId',s["id"], \
           getList("/api/v1beta0/account/scripts/{}/script-versions/".format(s["id"])))
        prettyPrintList('account/teams',getList("/api/v1beta0/account/teams/"))

def getUserAPIData(envId=None):
        prettyPrintParamList('user/cost-centers','req_envId',envId,getList("/api/v1beta0/user/{}/cost-centers/".format(envId)))
        prettyPrintParamList('user/events','req_envId',envId,getList("/api/v1beta0/user/{}/events/".format(envId)))
        uFarms = getList("/api/v1beta0/user/{}/farms/".format(envId))
        prettyPrintParamList('user/farms','req_envId',envId,uFarms)
        for f in uFarms:
           uFarmRoles = getList("/api/v1beta0/user/{}/farms/{}/farm-roles".format(envId,f["id"]))
           prettyPrintParam2List('user/farms/farm-roles','req_envId',envId,'req_farmId',f["id"],uFarmRoles)
           for fr in uFarmRoles:
              prettyPrintParam2List('user/farm-roles/global-variables','req_envId',envId,'req_farmRoleId',fr["id"], \
              getList("/api/v1beta0/user/{}/farm-roles/{}/global-variables".format(envId,fr["id"])))
              prettyPrintParam2Data('user/farm-roles/instance','req_envId',envId,'req_farmRoleId',fr["id"], \
              getFetch("/api/v1beta0/user/{}/farm-roles/{}/instance".format(envId,fr["id"])))
              prettyPrintParam2List('user/farm-roles/orchestration-rules','req_envId',envId,'req_farmRoleId',fr["id"], \
              getList("/api/v1beta0/user/{}/farm-roles/{}/orchestration-rules".format(envId,fr["id"])))
              prettyPrintParam2Data('user/farm-roles/placement','req_envId',envId,'req_farmRoleId',fr["id"], \
              getFetch("/api/v1beta0/user/{}/farm-roles/{}/placement".format(envId,fr["id"])))
              prettyPrintParam2Data('user/farm-roles/scaling','req_envId',envId,'req_farmRoleId',fr["id"], \
              getFetch("/api/v1beta0/user/{}/farm-roles/{}/scaling".format(envId,fr["id"])))
              prettyPrintParam2List('user/farm-roles/servers','req_envId',envId,'req_farmRoleId',fr["id"], \
              getList("/api/v1beta0/user/{}/farm-roles/{}/servers".format(envId,fr["id"])))
           prettyPrintParam2List('user/farms/global-variables','req_envId',envId,'req_farmId',f["id"], \
           getList("/api/v1beta0/user/{}/farms/{}/global-variables".format(envId,f["id"])))
           prettyPrintParam2List('user/farms/servers','req_envId',envId,'req_farmId',f["id"], \
           getList("/api/v1beta0/user/{}/farms/{}/servers".format(envId,f["id"])))
        prettyPrintParamList('user/global-variables','req_envId',envId,getList("/api/v1beta0/user/{}/global-variables/".format(envId)))
        prettyPrintParamList('user/images','req_envId',envId,getList("/api/v1beta0/user/{}/images/".format(envId)))
        prettyPrintParamList('user/os','req_envId',envId,getList("/api/v1beta0/user/{}/os/".format(envId)))
        prettyPrintParamList('user/projects','req_envId',envId,getList("/api/v1beta0/user/{}/projects/".format(envId)))
        prettyPrintParamList('user/role-categories','req_envId',envId,getList("/api/v1beta0/user/{}/role-categories/".format(envId)))
        uRoles = getList("/api/v1beta0/user/{}/roles/".format(envId))
        prettyPrintParamList('user/roles','req_envId',envId,uRoles)
        for r in uRoles:
           prettyPrintParam2List('user/roles/global-variables','req_envId',envId,'req_roleId',r["id"], \
           getList("/api/v1beta0/user/{}/roles/{}/global-variables/".format(envId,r["id"])))
           prettyPrintParam2List('user/roles/images','req_envId',envId,'req_roleId',r["id"], \
           getList("/api/v1beta0/user/{}/roles/{}/images/".format(envId,r["id"])))
           prettyPrintParam2List('user/roles/orchestration-rules','req_envId',envId,'req_roleId',r["id"], \
           getList("/api/v1beta0/user/{}/roles/{}/orchestration-rules/".format(envId,r["id"])))
        prettyPrintParamList('user/scaling-metrics','req_envId',envId,getList("/api/v1beta0/user/{}/scaling-metrics/".format(envId)))
        prettyPrintParamList('user/scripts','req_envId',envId,getList("/api/v1beta0/user/{}/scripts/".format(envId)))
        uScripts = getList("/api/v1beta0/user/{}/scripts/".format(envId))
        prettyPrintParamList('user/scripts','req_envId',envId,uScripts)
        for s in uScripts:
           prettyPrintParam2List('user/scripts/script-versions','req_envId',envId,'req_scriptId',s["id"], \
           getList("/api/v1beta0/user/{}/scripts/{}/script-versions/".format(envId,s["id"])))
        prettyPrintParamList('user/servers','req_envId',envId,getList("/api/v1beta0/user/{}/servers/".format(envId)))

def main():

        #read session key from splunkd
        #sessionKey = splunk.auth.getSessionKey('admin','changeme')
        sessionKey = sys.stdin.readline().strip()
        if len(sessionKey) == 0:
           sys.stderr.write("DATALOADER_SCRIPT_ERROR - Session Key NOT received from splunkd. Please set passAuth in inputs.conf\n")
           exit(2)

        global api_client, api_verify_ssl

        api_url, api_key, api_secret, api_verify_ssl = getCredentials(sessionKey)
        if api_url == None:
           sys.stderr.write("DATALOADER_SCRIPT_ERROR - Scalr URL NOT received from splunkd. Please set url in scalr.conf\n")
           exit(2)
        if api_key == None:
           sys.stderr.write("DATALOADER_SCRIPT_ERROR - API Key NOT received from splunkd. Please set key in scalr.conf\n")
           exit(2)
        if api_secret == None:
           sys.stderr.write("DATALOADER_SCRIPT_ERROR - API Secret NOT received from splunkd. Please set secret in passwords.conf\n")
           exit(2)

        api_client = ScalrApiClient(api_url.rstrip("/"), api_key, api_secret)

        #getGlobalAPIData()

        env = listEnvironments()

        getAccountAPIData()

        for i in env:
           getUserAPIData(i["id"])


if __name__=='__main__':
        main()
