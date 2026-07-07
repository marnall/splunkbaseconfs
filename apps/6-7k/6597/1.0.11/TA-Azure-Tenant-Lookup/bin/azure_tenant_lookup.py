#!/usr/bin/env python

import csv
import sys
import os
import logging
from logging import handlers
from datetime import datetime


# Import APP Modules
LIBDIR=os.path.join(os.path.dirname((os.path.abspath(__file__))), 'lib')
sys.path.insert(0, LIBDIR)
import msal
import jwt
import json
import requests
import splunklib.client as client
from splunk.clilib import cli_common as cli


### Variables ###############
#                           #
#############################
BINDIR=os.path.dirname((os.path.abspath(__file__)))
APPHOME=os.path.join(os.path.sep.join(BINDIR.split(os.path.sep)[0:-1]))
SPLUNKHOME=os.path.join(os.path.sep.join(APPHOME.split(os.path.sep)[0:-3]))
LOGFILE=os.path.join(os.path.sep.join((SPLUNKHOME, 'var', 'log', 'splunk', 'ta-azure-tenant-lookup.log')))
LOGNAME="tenant_lookup"
LOGLEVEL="INFO"
GRAPHURI = 'https://graph.microsoft.com/beta/tenantRelationships'


### Functions ###############
#                           #
#############################

def create_logger(logger_name: str, log_level: str, log_file: str) -> logging.Logger:
    """Cretate Logger Instance"""
    logger = logging.getLogger(logger_name)
    logger.propagate = False
    logger.setLevel(log_level)
    file_handler = handlers.RotatingFileHandler(log_file, maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter("%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d | %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger

def msgraph_auth(tenantID: str, clientID: str, clientSecret: str) -> dict:
    """Azure Authentication"""
    authority = f"https://login.microsoftonline.com/{tenantID}"
    logger.debug(f"Authority: {authority}")
    scope = ["https://graph.microsoft.com/.default"]
    logger.debug("Create App")
    app = msal.ConfidentialClientApplication(clientID, authority=authority, client_credential=clientSecret)
    logger.debug("App Created")
    try:
        accessToken = app.acquire_token_silent(scope, account=None)
        if not accessToken:
            try:
                accessToken = app.acquire_token_for_client(scopes=scope)
                if accessToken['access_token']:
                    logger.info(f"New access token retreived for clientID: {clientID}, tenantID: {tenantID}")
                    requestHeaders = {'Authorization': 'Bearer ' + accessToken['access_token']}
                else:
                    logger.error('Error aquiring authorization token. Check your tenantID, clientID and clientSecret.')
            except:
                pass
        else:
            logger.info('Token retreived from MSAL Cache....')
        logger.debug(f"Access Token: {accessToken}")
        decodedAccessToken = jwt.decode(accessToken['access_token'], options={"verify_signature": False})
        accessTokenFormatted = json.dumps(decodedAccessToken, indent=2)
        logger.debug(f"Decoded Access Token: {accessTokenFormatted}")
        # Token Expiry
        tokenExpiry = datetime.fromtimestamp(int(decodedAccessToken['exp']))
        logger.info('Token Expires at: ' + str(tokenExpiry))
        return requestHeaders
    except Exception as err:
        logger.exception(f"msgraph_auth Exception: {err}")

def TenantLookup(resource: str, requestHeaders: dict) -> dict:
    """query graphapi for tenantinfos"""
    try:
        results = requests.get(resource, headers=requestHeaders).json()
        logger.debug(f"Results: {results}")
        return results
    except Exception as err:
        logger.exception(f"TenantLookup Exception: {err}")
        return {}

def main():
    """MainFunction"""
    # verify args
    if len(sys.argv) != 3:
        print("Usage: python external_lookup.py [host field] [ip field]")
        sys.exit(1)
    idfield = sys.argv[1]
    namefield = sys.argv[2]
    logger.debug(f"idfield: {idfield}, namefield: {namefield}")
    infile = sys.stdin
    outfile = sys.stdout
    r = csv.DictReader(infile)
    header = r.fieldnames
    logger.debug(f"header: {header}")
    w = csv.DictWriter(outfile, fieldnames=r.fieldnames)
    w.writeheader()

    # get clientsecret
    clientsecret=json.loads(cli.decrypt(sec_settings["password"]))["clientsecret"]

    # authenticate against azure
    headers = msgraph_auth(tenantID=app_settings["tenantid"], clientID=app_settings["clientid"], clientSecret=clientsecret)
    logger.debug(f"Headers: {headers}")

    for result in r:
        logger.debug(f"resultKeys: {result}")
        # Perform the lookup or reverse lookup if necessary
        if result[idfield] and result[namefield]:
            # both fields were provided, just pass it along
            w.writerow(result)

        elif result[idfield]:
            # only tenantID was provided, add other fields
            logger.info(f"Lookup for TenantId: {result[idfield]}")
            ressource=f"{GRAPHURI}/findTenantInformationByTenantId(tenantId=\'{result[idfield]}\')"
            data = TenantLookup(ressource,headers)
            try:
                result[namefield] = data['defaultDomainName']
                result["displayName"] = data['displayName']
                result["federationBrandName"] = data['federationBrandName']
            except:
                logger.exception(f"Lookup for TenantId: {result[idfield]}, Data: {data}")
            w.writerow(result)

        elif result[namefield]:
            # only defaultDomainName was provided, add other fields
            logger.info(f"Lookup for Domain: {result[namefield]}")
            ressource=f"{GRAPHURI}/findTenantInformationByDomainName(domainName=\'{result[namefield]}\')"
            data = TenantLookup(ressource,headers)
            try:
                result[idfield] = data['tenantId']
                result["displayName"] = data['displayName']
                result["federationBrandName"] = data['federationBrandName']
            except:
                logger.exception(f"Lookup for Domain: {result[namefield]}, Data: {data}")
            w.writerow(result)
            

### Main ####################
#                           #
#############################

# get config
log_settings = cli.getConfStanza('ta_azure_tenant_lookup_settings','logging')
app_settings = cli.getConfStanza('ta_azure_tenant_lookup_settings','additional_parameters')
sec_settings = cli.getConfStanza('passwords','credential:__REST_CREDENTIAL__#TA-Azure-Tenant-Lookup#configs/conf-ta_azure_tenant_lookup_settings:additional_parameters``splunk_cred_sep``1:')

# create logger
if "loglevel" in log_settings:
    log_level = log_settings["loglevel"]
else:
    log_level = LOGLEVEL
logger = create_logger(LOGNAME, log_level, LOGFILE)

logger.debug(f"LogSettings: {log_settings}")
logger.debug(f"AppSettings: {app_settings}")
logger.debug(f"SecSettings: {sec_settings}")

# run main
main()
