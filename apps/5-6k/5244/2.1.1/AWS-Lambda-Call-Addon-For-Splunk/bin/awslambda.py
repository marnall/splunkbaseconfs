import requests
import sys,os
import json
import logging
import logging.handlers
import boto3
import splunk.entity as entity
import base64
import re
import ast


def setup_logger(level):
	logger = logging.getLogger("awslambda_alert_logger")
	logger.propogate = False
	logger.setLevel(level)
	file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/awslambda_alert.log',maxBytes=2500000000,backupCount=5)
	formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
	file_handler.setFormatter(formatter)
	logger.addHandler(file_handler)
	return logger

logger = setup_logger(logging.INFO)

def getCredentials(sessionKey,environment):
	try:
		myapp = 'AWS-Lambda-Call-Addon-For-Splunk'
		entities = entity.getEntities(['storage','passwords'],namespace=myapp,owner='nobody',sessionKey=sessionKey)
		#logger.info(entities)
	except Exception as e:
		raise Exception('Could not get Credentials' + str(e))
	for i,c in entities.items():
		if c.get('realm') == environment:
			return c['clear_password'] , c['username']
			break
	else:
		logger.info("E - Authentication failure")
		#raise Exception("Authentication failure")
	

def call_awslambda_function(lambdafunctionname,final,region,username,password):
	try:

		client = boto3.client('lambda',
			aws_access_key_id=username,
			aws_secret_access_key=password,
			region_name=region,)
		response = client.invoke(
			FunctionName=lambdafunctionname,
			InvocationType='RequestResponse',
			LogType='Tail',
			Payload =json.dumps(final)
			)


		aws = (response['Payload'].read())
		requestid= (response['ResponseMetadata']['RequestId'])
		statuscode= (response['ResponseMetadata']['HTTPStatusCode'])
		output = ('"Request ID : ' + str(requestid) + ' StatusCode : ' + str(statuscode) + ' Response Message : ' + str(aws) + ' Lambda Function : ' + str(lambdafunctionname) +'"')

		logger.info(output)

		return aws
		return output

	except Exception as e:
		logger.info("E - Error in calling lambda function. Lambda Function Name - " + str(lambdafunctionname) +  " " + str(e))





def main():
	if len(sys.argv) > 1 and sys.argv[1] == "--execute":
		payload = json.loads(sys.stdin.read())
		#logger.info(payload)
		sessionKey = payload.get('session_key')
		#logger.info(sessionKey)
		if len(sessionKey)==0:
			logger.error("Didn't receive any session key")
			exit()
		#getting alert action parameters
		config = payload.get('configuration')
		lambdafunctionname = config.get('lambda')
		lambdapayload = config.get('lambdapayload')
		region = config.get('region')
		environment = config.get('environment')
		#converting payload into json
		#logger.info("sssss" + str(lambdapayload))

		if lambdapayload == None:
			final =''

		else:

			payload1 = dict(item.split("=") for item in lambdapayload.split(","))
			#print(payload1)
			payload2 = ast.literal_eval(json.dumps(payload1))
			#print(abc)
			payloadrex =str(payload2)
			payloadrex =(re.sub(r"'(-*\d+(?:\.\d+)?)'", r'\1', payloadrex))
			final = ast.literal_eval(payloadrex)
			assert type(final) is dict
			

		password, username = getCredentials(sessionKey,environment)
		#logger.info("username is " + username + "& password is " + password)
		#credentials = [username, password]
		#logger.info(credentials)
		aws = call_awslambda_function(lambdafunctionname,final,region,username,password)
		#output = call_awslambda_function(lambdafunctionname,lambdapayload,region)
		logger.info(aws)

		

if __name__ == "__main__":
	main()