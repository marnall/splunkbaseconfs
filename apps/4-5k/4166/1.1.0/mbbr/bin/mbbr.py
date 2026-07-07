'''
Version = 1.0.0
'''
from __future__ import print_function
import sys
import os
import subprocess
from subprocess import Popen
import json
import logging
import splunk.entity as entity
from io import open


## Get Splunk Path
def splunkpathdef():
	global splunkPath
	try:
		splunkPath = os.environ['SPLUNK_HOME']

	except Exception as err:
		print("error: Unable to retrieve Splunk home path", file=sys.stderr)
		sys.exit(2)

	return splunkPath

## Change Scan Type
def replaceMultiple(mainString, toBeReplaces, newString):
		# Iterate over the strings to be replaced
			for elem in toBeReplaces :
				# Check if string is in the main string
				if elem in mainString and newString in toBeReplaces:
				# Replace the string
					mainString = mainString.replace(elem, newString,1)

			return  mainString


# Script execution function
def execScript(ip,action,uname,pwd,new_mode):

	try:
		cmd = [r"C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe", r"& '"+splunkPath+"/etc/apps/mbbr/bin/psscript.ps1'",str(ip),str(action),str(uname),str(pwd),str(new_mode)]
		p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)  #invoke the powershell script
		return p.communicate()
	except Exception as err:
		statusLog("title=\"error: Powershell script execution failed \"" + " message=\""+str(err)+"\"")
		print("error: Powershell script execution failed. message:"+str(err), file=sys.stderr)
		sys.exit(7)

## Debug logs function
def statusLog(msg):

	logging.basicConfig(filename=splunkPath+'/var/log/splunk/mbbr_python.log',
                            filemode='a',
                            format='%(asctime)s %(message)s',
                            datefmt='%m/%d/%y %H:%M:%S',
                            level=logging.DEBUG)
	logging.info(msg)


def statusLog2(destip,msg):

	splitip = destip.split(',')

	for i in splitip:
		logging.basicConfig(filename=splunkPath+'/var/log/splunk/mbbr_python.log',
								filemode='a',
								format='%(asctime)s %(message)s',
								datefmt='%m/%d/%y %H:%M:%S',
								level=logging.DEBUG)
		logging.info("dest_ip=" + i + " message=\"" + msg + "\"")

def getCredentials(ip_address,sessionKey):

	myapp = 'mbbr'
	try:
      # list all credentials
		entities = entity.getEntities(['admin', 'passwords'], namespace=myapp,
                                    owner='nobody', sessionKey=sessionKey)

		if str(entities.items())=="[]":
			statusLog("title=\"error: no credential information\"" )
			print("error: no credential information", file=sys.stderr)
			sys.exit(8)

	except Exception as err:
		statusLog("title=\"error: unable to get credentials from Splunk\"message=\""+str(err)+"\"")
		print("error: unable to get credentials from Splunk. message:"+str(err), file=sys.stderr)
		sys.exit(9)

	## return first set of credentials
	try:
		for i, c in entities.items():
			statusLog2(ip_address,"password extracted for the username:"+c['username'])
			return c['username'], c['clear_password']

	except Exception as err:
		statusLog("title=\"error: unable to extract credentials\"message=\""+str(err)+"\"")
		print("error: unable to extract credentials. message:"+str(err), file=sys.stderr)
		sys.exit(10)


if __name__ == '__main__':

	## Get the splunk_home path
	splunkpathdef()

	statusLog("action=\"python script has invoked from an alert action*******\"")

	statusLog("action=\"SPLUNK_HOME path read successfully\"")

	## Read the json payload which release the host names

	try:

		## Read the payload
		payload = json.loads(sys.stdin.read())
		statusLog("action=\"json payload read successfully\"" )

		## Read the configurations from payload	to identify the remediation action
		config = payload.get('configuration')
		action = config.get('remaction')
		statusLog("action=\"configurations read successfully from the json payload\"" )


		new_scan = config.get('type')
		new_mode = config.get('mode')
		list = ['threat','hyper','full -ark']

		with open('mbbr_remove_batch.bat') as f:
			newtxt = f.read()

		replacedstring = replaceMultiple(newtxt, list, new_scan)

		with open('mbbr_remove_batch.bat', "w") as f:
			f.write(replacedstring)


		with open('mbbr_scan_batch.bat') as f:
			newtxt = f.read()

		replacedstring = replaceMultiple(newtxt, list, new_scan)

		with open('mbbr_scan_batch.bat', "w") as f:
			f.write(replacedstring)

		## Read the results from payload
		collection = payload.get('result')
		statusLog("action=\"results read successfully from the json payload\"" )

		## read session key sent from splunkd
		sessionKey = payload.get('session_key')
		statusLog("action=\"session key read successfully from the json payload\"" )

		## extract ips from results
		ip_address = collection.get('src_ip')  # extract source ips from Splunk
		statusLog("action=\"extracted ips = " + str(ip_address) + "\"")

	except Exception as err:
		statusLog("title=\"error: extracting results from the payload\" message=\""+str(err)+"\"")
		print("error: extracting results from the payload. message:"+str(err), file=sys.stderr)
		sys.exit(3)

	statusLog2(ip_address,"checking extracted field validity" )

	if ip_address == "":
		statusLog("message=\"error: cannot find any address in src_ip field\"" )
		print("error: cannot find any address in src_ip field", file=sys.stderr)
		sys.exit(4)

	if sessionKey is None:
		statusLog("title=\"error: did not receive a session key from splunkd. Please enable passAuth in inputs.conf for this script\"" )
		print("error: did not receive a session key from splunkd. Please enable passAuth in inputs.conf for this script", file=sys.stderr)
		sys.exit(5)

	if action == "scan":
		statusLog2(ip_address,"valid remediation action. script execution will be triggered for scanning only" )
	elif action == "remove":
		statusLog2(ip_address,"valid remediation action. script execution will be triggered for scanning and removal" )
	else:
		statusLog("title=\"error: Unspecified  remediation action\"")
		print("error: Unspecified  remediation action", file=sys.stderr)
		sys.exit(6)

	statusLog2(ip_address,"completed extracted field validity" )

	## get username and password using the session key
	statusLog2(ip_address, "fetching service username and password")
	username,password=getCredentials(ip_address,sessionKey)

	if username is None:
		statusLog("title=\"error: empty username\"" )
		print("error: empty username", file=sys.stderr)
		sys.exit(11)

	# Execute the script
	output,error = execScript(ip_address,action,username,password,new_mode)
	statusLog("Powershell output: "+str(output))

	# Exit if there is any error in Powershell script
	if str(error) != "":
		statusLog("error: Powershell script execution has errors: "+str(error))
		print("error: Powershell script execution has errors: "+str(error), file=sys.stderr)
		sys.exit(12)


	statusLog2(ip_address,"script execution triggered")

	statusLog2(ip_address,"end of alert action****")
