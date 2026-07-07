import json
import os
import requests

import splunk
import splunk.admin as admin
import splunk.rest as rest
from splunk.clilib.bundle_paths import make_splunkhome_path
import splunk.entity as en

import mint.utils as utils
logger = utils.logger

"""
EAI REST Handler to persist CDS tokens
"""
def get_cds_and_ssl(token, userName, sessionKey, https_proxy, cloud_install):
    logger.info('Getting CDS token and SSL keys...')
    # Set up params for http request to CDS. Default CDS auth server
    # is v2 for on-prem, but if TA is on-cloud, CDS auth server is v3
    CDS_auth_server = 'https://auth.cds.splkmobile.com/api/v2/authenticate'
    if cloud_install and cloud_install == True:
        CDS_auth_server = 'https://auth.cds.splkmobile.com/api/v3/authenticate'
    payload = {'guid': token}
    headers = {'content-type': 'application/json'}
    req_args = {
            "verify": True,
            "stream": False,
            "timeout": 10
    }

    if https_proxy:
        req_args["proxies"] = { "https": https_proxy }

    # Make the call to the CDS to verify the token
    try:
        r = requests.post(CDS_auth_server, data=json.dumps(payload),
                          headers=headers, **req_args)
    except Exception as e:
        logger.error("Data Collector authentication exception: %s" % str(e))
        raise admin.InternalException('Data Collector authentication exception \'%s\'' % str(e))
    except requests.exceptions.Timeout as e:
        logger.error("Data Collector authentication timeout: %s" % str(e))
        raise admin.InternalException('Data Collector authentication timeout \'%s\'' % str(e))

    if r.status_code == 401:
        # Response status code is bad, token was invalid
        logger.error('Invalid Authentication Token')
        raise admin.InternalException('Invalid authentication token')
    elif r.status_code == 200:
        # Response status code is good, continue
        response = json.loads(r.text)
        endpoint = response['endpoint']

        try:
            # Create entity for inputs.conf
            logger.info('Attempting to create inputs entity')
            ent = en.getEntity('configs/conf-inputs',
                               'mi_cds://default',
                               namespace='Splunk_TA_mint',
                               owner=userName,
                               sessionKey=sessionKey)


            # Persist CDS endpoint to inputs.conf entity
            ent['cds_url'] = endpoint
            en.setEntity(ent, sessionKey=sessionKey)
            logger.info('Entity successfully created and committed')
        except Exception as ex:
            logger.error("Entity persistence exception: %s" % str(ex))
            raise ex

        # Save ssl keys and pass inside Mint TA, only if on-prem installation.
        if not cloud_install:
            mint_ta_path = make_splunkhome_path(['etc', 'apps', 'Splunk_TA_mint', 'auth'])
            save_to_file(mint_ta_path, 'mint.key', response.get('private_key'))
            save_to_file(mint_ta_path, 'mint.pem', response.get('public_key'))
            logger.info('SSL keys successfully saved')

        # Pass endpoint back to modular input
        return endpoint
    else:
        logger.error('Could not connect with Data Collector')
        raise admin.InternalException('Could not connect with Data Collector')


def save_to_file(path, file, content):
    if not content:
        logger.info('Content of %s in %s is empty'%(file, path))
        content = ''
    if not os.path.exists(path):
        os.makedirs(path)
    with open(path + os.sep + file, "w+") as f:
        f.write(content)
