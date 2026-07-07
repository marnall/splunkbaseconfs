import logging
import sys,os
import splunk.Intersplunk
import inspect
import subprocess
import shutil
from time import sleep
from urlparse import urlparse
import httplib
import json
from requests.exceptions import ConnectionError
from setupBoto import copyPackage

logger = logging.getLogger('splunk.saviynt')

'''
    Connect with AWS
'''
def connectToAws(aws_access_key_id,aws_secret_access_key,role_arn,role_session_name):
    try:
        try:
            from boto import ec2
        except:
            logger.info("Setting up AWS for the first time")
            copyPackage("boto-2.42.0.dist-info")
            copyPackage("boto")
            from boto import ec2
        from boto.sts import STSConnection
        from boto.s3.connection import S3Connection
        from boto import s3
        from boto import sts
        logger.info("AWS setup is done")
        stsCon = STSConnection(aws_access_key_id, aws_secret_access_key,anon=False,debug=0)
        tempCred = stsCon.assume_role(role_arn, role_session_name)
        connection = ec2.connect_to_region('us-east-1', aws_access_key_id=tempCred.credentials.access_key, aws_secret_access_key=tempCred.credentials.secret_key,security_token=tempCred.credentials.session_token)
        logger.info("Got AWS Connection")
        return connection
    except ConnectionError, ce:
        logger.info(ce)
        return None
    except ValueError, ve:
        logger.info(ve)
        return None
    except Exception, ex:
        logger.info(ex)
        return None

'''
    Start the connection with Saviynt
'''
def startInstance(aws_access_key_id,aws_secret_access_key,role_arn,role_session_name,instanceId=None):
    url = None
    instance = None
    try:
        ip = None
        if(instanceId is not None and instanceId.strip() != ""):
            connection = connectToAws(aws_access_key_id,aws_secret_access_key,role_arn,role_session_name)
            logger.info("Got Connection")
            if connection is None:
                logger.info("Unable to connect to AWS.")
                return "Unable to connect to AWS",None
            instance = connection.get_all_instances(instance_ids=[instanceId])
            if(len(instance) == 0):
                logger.info("Length is 0")
                return "terminated", None
            state = instance[0].instances[0].state
            if state.strip().lower() == "terminated":
                logger.info("State is terminated")
                return "terminated", None
            state = instance[0].instances[0].state
            logger.info("The state is: " + state)
            if(state != "running"):
                instance[0].instances[0].start(dry_run=False)
                logger.info("The state is: " + state)
                state = None
                minutes = 0
                limitForTimer = 60 #(60/5) = 12 times makes a minute, so 10 min = 120
                while(state != "running" and minutes < limitForTimer):
                    minutes = minutes + 1
                    logger.info("Trying to start connection")
                    instance = connection.get_all_instances(instance_ids=[instanceId])
                    state = instance[0].instances[0].state
                    logger.info("The state is: " + state)
                    sleep(10)
                if(minutes >= limitForTimer and state != "running"):
                    logger.info("Unable to start")
                    return "notstarted",None
            logger.info("The state is: " + state)
            ip = instance[0].instances[0].public_dns_name
            logger.info("The ip got is : "+ip)
            url = "https://" + ip + "/ECM"
            logger.info("The url is: "+url)
            return "True", url
        else:
            logger.info("Nothing to start")
        return "Unable to start instance",url
    except Exception, ex:
        logger.info(ex)
        return str(ex),url
        
'''
    Stop the connection with Saviynt
'''
def stopInstance(aws_access_key_id,aws_secret_access_key,role_arn,role_session_name,instanceId=None):
    try:
        if(instanceId is not None and instanceId.strip() != ""):
            connection = connectToAws(aws_access_key_id,aws_secret_access_key,role_arn,role_session_name)
            logger.info("Got connection")
            if connection is None:
                logger.info("Unable to connect.")
                return False
            logger.info("Getting connection")
            logger.info(connection)
            instance = connection.get_all_instances(instance_ids=[instanceId])
            instance[0].instances[0].stop(force=False,dry_run=False)
            state = instance[0].instances[0].state
            minutes = 0
            limitForTimer = 42 #(60/5) = 12 times makes a minute, so 10 min = 120
            while(state != "stopped" and minutes < limitForTimer):
                minutes = minutes + 1
                logger.info("Trying to stop connection")
                instance = connection.get_all_instances(instance_ids=[instanceId])
                state = instance[0].instances[0].state
                logger.info("The state is: " + state)
                sleep(10)
            if(minutes >= limitForTimer and state != "stopped"):
                logger.info("Unable to stop connection")          
        else:
            logger.info("Nothing to stop")
        return True
    except Exception, ex:
        logger.info(ex)
        return False
        
