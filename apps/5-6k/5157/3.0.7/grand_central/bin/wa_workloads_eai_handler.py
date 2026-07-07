import logging
import sys
import os
import uuid
import splunk.admin as admin
import wa_workloads_eai_handler_schema
try:
    from urllib.parse import quote_plus
except:
    from urllib import quote_plus
import re
import json
import errno
import base_eai_handler
import log_helper
import time
import uuid
from splunk.clilib.bundle_paths import make_splunkhome_path
from well_architected import WellArchitected
from wa_constants import *

# Setup the logger
logger = log_helper.setup(logging.INFO, 'WaWorkloadsEAIHandler', 'wa_workloads_eai_handler.log')

class WaWorkloadsEAIHandler(base_eai_handler.BaseEAIHandler):

    handledActions = [admin.ACTION_LIST]

    def setup(self):

        # Add our supported args
        for arg in wa_workloads_eai_handler_schema.ALL_FIELDS:
            self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        """
        Called when user invokes the "list" action. Returns the contents of example_eai_handler.conf
        Arguments
        confInfo -- The object containing the information about what is being requested.
        """
        logger.info('List requested.')

        try:
            update_from_aws = bool(self.get_param('update_from_aws', default=False))
        except:
            update_from_aws = False

        if update_from_aws:
            workloads_list_payload = {'entry': []}

            # Get list of existing workloads from conf file
            wa_workloads_eai_handler_conf_path = self.get_conf_handler_path_name('wa_workloads', self.userName)
            wa_workloads_conf_response_payload = self.simple_request_eai(
                wa_workloads_eai_handler_conf_path, 
                'list', 
                'GET', 
                get_args={'count': -1}
            )
            # Get the grand central account information for the organization account
            conf_handler_path = self.get_conf_handler_path_name('grand_central_aws_accounts', 'nobody')
            grand_central_aws_accounts_eai_response_payload = self.simple_request_eai(
                conf_handler_path, 
                'list', 
                'GET', 
                get_args={'count': -1}
            )

            for grand_central_aws_account in grand_central_aws_accounts_eai_response_payload['entry']:
                if grand_central_aws_account['content']['organization_master_account'] == '0':
                    continue
                
                aws_secret_key_link_alternate = grand_central_aws_account['content']['aws_secret_key_link_alternate']
                aws_access_key = grand_central_aws_account['content']['aws_access_key']
                aws_account_id = grand_central_aws_account['content']['aws_account_id']
                passwords_conf_payload = self.simple_request_eai(aws_secret_key_link_alternate, 'list', 'GET')
                aws_secret_key = passwords_conf_payload['entry'][0]['content']['clear_password']

                # create wa instance
                try:
                    wa = WellArchitected(
                        {
                            'service_name': WA_SERVICE_NAME, 
                            'endpoint_url': WA_ENDPOINT_URL,
                            'region_name': WA_REGION_NAME,
                            'aws_access_key_id': aws_access_key,
                            'aws_secret_access_key': aws_secret_key
                        }
                    )
                except Exception as e:
                    logger.error('Error when instantiating wa: {}'.format(e))
                    raise admin.InternalException('Error when instantiating wa: {}'.format(e))
                try:
                    workloads = wa.list_workloads({ 'MaxResults': 50 })
                    logger.info(str(workloads))
                except Exception as e:
                    logger.error('Error when listing workloads: {}'.format(e))
                    raise admin.InternalException('Error when listing workloads: {}'.format(e))

                self.update_workload_list_payload(workloads_list_payload, workloads, aws_account_id)

            logger.info(str(workloads_list_payload))
            self.update_workload_conf_file(workloads_list_payload, wa_workloads_conf_response_payload)

        # Fetch from wa_workloads conf handler
        wa_workloads_eai_handler_conf_path = self.get_conf_handler_path_name('wa_workloads', self.userName)
        wa_workloads_eai_handler_conf_response_payload = self.simple_request_eai(
            wa_workloads_eai_handler_conf_path, 
            'list', 
            'GET', 
            get_args={'count': -1}
        )
        self.set_conf_info_from_eai_payload(confInfo, wa_workloads_eai_handler_conf_response_payload)

    def handleCreate(self, confInfo):
        """
        Called when user invokes the 'create' action.
        Arguments
        confInfo -- The object containing the information about what is being requested.
        """
        logger.info('Create requested.')

        # validate params
        params = self.validate_schema_params()

        # Get aws creds
        grand_central_aws_account_eai_response_payload = self.simple_request_eai(
            params['organization_master_account_link_alternate'], 
            'list', 
            'GET'
        )
        aws_access_key = grand_central_aws_account_eai_response_payload['entry'][0]['content']['aws_access_key']
        aws_secret_key_link_alternate = grand_central_aws_account_eai_response_payload['entry'][0]['content']['aws_secret_key_link_alternate']
        passwords_conf_payload = self.simple_request_eai(aws_secret_key_link_alternate, 'list', 'GET')
        aws_secret_key = passwords_conf_payload['entry'][0]['content']['clear_password']
        
        # Extract POST params
        name = params['name']
        workload_name = params['workload_name']
        description = params['description']
        environment = params['environment']
        regions = params['regions'].replace(' ', '').split(',')
        pillar_priorities = params['pillar_priorities'].replace(' ', '').split(',')
        lenses = params['lenses'].replace(' ', '').split(',')
        review_owner = params['review_owner']

        # create wa instance
        try:
            wa = WellArchitected(
                {
                    'service_name': WA_SERVICE_NAME, 
                    'endpoint_url': WA_ENDPOINT_URL,
                    'region_name': WA_REGION_NAME,
                    'aws_access_key_id': aws_access_key,
                    'aws_secret_access_key': aws_secret_key
                }
            )
        except Exception as e:
            logger.error('Error when instantiating wa: {}'.format(e))
            raise admin.InternalException('Error when instantiating wa: {}'.format(e))

        # create workload
        try:
            response = wa.create_workload(
                { 
                    'Name': workload_name,
                    'Description': description, 
                    'Environment': environment, 
                    'AwsRegions': regions,
                    'PillarPriorities': pillar_priorities,
                    'Lenses': lenses,
                    'ReviewOwner': review_owner
                }
            )
        except Exception as e:
            logger.error('Error creating workload: {}'.format(e))
            raise admin.InternalException('Error creating workload: {}'.format(e))

        post_args = {
            'name': name, 
            'organization_master_account_link_alternate': params['organization_master_account_link_alternate'],
            'workload_name': workload_name, 
            'workload_id': response['WorkloadId'], 
            'workload_owner': params['review_owner'], 
            'workload_arn': response['WorkloadArn'], 
            'aws_regions': regions
        }

        # Create stanza in wa_workloads_eai_handler.conf
        wa_workloads_eai_response_payload = self.simple_request_eai(
            self.get_conf_handler_path_name('wa_workloads'), 
            'create', 
            'POST', 
            post_args
        )

        # Always populate entry content from request to handler.
        wa_workloads_rest_path = '/servicesNS/{}/{}/wa_workloads/{}'.format(
            'nobody', 
            self.appName, 
            quote_plus(name)
        )

        wa_workloads_eai_handler_response_payload = self.simple_request_eai(
            wa_workloads_rest_path, 
            'read', 
            'GET',
            get_args={'update_from_aws': False}
        )

        self.set_conf_info_from_eai_payload(confInfo, wa_workloads_eai_response_payload)

    def handleEdit(self, confInfo):
        """
        Called when user invokes the 'edit' action.
        Arguments
        confInfo -- The object containing the information about what is being requested.
        """
        logger.info('Update requested.')

        params = self.validate_schema_params()

        conf_stanza = quote_plus(params.get('name'))
        del params['name']

        # raise admin.InternalException('HERHEHRHE {} {} {}'.format(params, conf_stanza, confInfo))

        # Get workload ID
        wa_workloads_rest_path = '/servicesNS/{}/{}/wa_workloads/{}'.format(
            'nobody', 
            self.appName, 
            quote_plus(conf_stanza)
        )
        wa_workloads_eai_response_payload = self.simple_request_eai(
            wa_workloads_rest_path,
            'read', 
            'GET'
        )

        workload_id = wa_workloads_eai_response_payload['entry'][0]['content']['workload_id']
        organization_master_account_link_alternate = wa_workloads_eai_response_payload['entry'][0]['content']['organization_master_account_link_alternate']
        
        # Get aws creds
        grand_central_aws_account_eai_response_payload = self.simple_request_eai(
            organization_master_account_link_alternate, 
            'list', 
            'GET'
        )
        aws_access_key = grand_central_aws_account_eai_response_payload['entry'][0]['content']['aws_access_key']
        aws_secret_key_link_alternate = grand_central_aws_account_eai_response_payload['entry'][0]['content']['aws_secret_key_link_alternate']
        passwords_conf_payload = self.simple_request_eai(aws_secret_key_link_alternate, 'list', 'GET')
        aws_secret_key = passwords_conf_payload['entry'][0]['content']['clear_password']

        # Extract POST params
        workload_name = params['workload_name']
        description = params['description']
        environment = params['environment']
        regions = params['regions'].replace(' ', '').split(',')
        pillar_priorities = params['pillar_priorities'].replace(' ', '').split(',')
        lenses = params['lenses'].replace(' ', '').split(',')
        review_owner = params['review_owner']

         # create wa instance
        try:
            wa = WellArchitected(
                {
                    'service_name': WA_SERVICE_NAME, 
                    'endpoint_url': WA_ENDPOINT_URL,
                    'region_name': WA_REGION_NAME,
                    'aws_access_key_id': aws_access_key,
                    'aws_secret_access_key': aws_secret_key
                }
            )
        except Exception as e:
            logger.error('Error when instantiating wa: {}'.format(e))
            raise admin.InternalException('Error when instantiating wa: {}'.format(e))

        # edit workload
        try:
            response = wa.update_workload(
                {
                    'Id': workload_id,
                    'Name': workload_name,
                    'Description': description, 
                    'Environment': environment, 
                    # 'AwsRegions': regions,
                    # 'PillarPriorities': pillar_priorities,
                    # 'ReviewOwner': review_owner

                }
            )
        except Exception as e:
            logger.error('Error editing workload: {}'.format(e))
            raise admin.InternalException('Error editing workload: {}'.format(e))

        post_args = {
            # 'name': conf_stanza, 
            'organization_master_account_link_alternate': params['organization_master_account_link_alternate'],
            'workload_name': workload_name, 
            'workload_id': response['Workload']['WorkloadId'], 
            'workload_owner': params['review_owner'], 
            'workload_arn': response['Workload']['WorkloadArn'], 
            'aws_regions': regions
        }

        conf_handler_path = '{}/{}'.format(
            self.get_conf_handler_path_name('wa_workloads', 'nobody'), 
            conf_stanza
        )

        # Edit wa_workloads.conf
        wa_workloads_eai_handler_response_payload = self.simple_request_eai(
            conf_handler_path, 
            'edit', 
            'POST', 
            post_args
        )

        # Always populate entry content from request to handler.
        wa_workloads_eai_handler_rest_path = '/servicesNS/{}/{}/wa_workloads/{}'.format(
            'nobody', 
            self.appName, 
            conf_stanza
        )
        wa_workloads_eai_handler_response_payload = self.simple_request_eai(
            wa_workloads_eai_handler_rest_path, 
            'read', 
            'GET'
        )
        self.set_conf_info_from_eai_payload(confInfo, wa_workloads_eai_handler_response_payload)

    def handleRemove(self, confInfo):
        """
        Called when user invokes the 'delete' action. Removes the requested stanza from example_eai_handler.conf
        Arguments
        confInfo -- The object containing the information about what is being requested.
        """
        logger.info('Conf stanza deletion requested.')

        name = self.callerArgs.id
        conf_stanza = quote_plus(name)

        # Get workload ID
        deployed_stacksets_rest_path = '/servicesNS/{}/{}/wa_workloads/{}'.format(
            'nobody', 
            self.appName, 
            quote_plus(name)
        )
        wa_workloads_eai_response_payload = self.simple_request_eai(
            deployed_stacksets_rest_path,
            'read', 
            'GET'
        )

        workload_id = wa_workloads_eai_response_payload['entry'][0]['content']['workload_id']
        organization_master_account_link_alternate = wa_workloads_eai_response_payload['entry'][0]['content']['organization_master_account_link_alternate']

        # Get aws creds
        grand_central_aws_account_eai_response_payload = self.simple_request_eai(
            organization_master_account_link_alternate, 
            'list', 
            'GET'
        )
        aws_access_key = grand_central_aws_account_eai_response_payload['entry'][0]['content']['aws_access_key']
        aws_secret_key_link_alternate = grand_central_aws_account_eai_response_payload['entry'][0]['content']['aws_secret_key_link_alternate']
        passwords_conf_payload = self.simple_request_eai(aws_secret_key_link_alternate, 'list', 'GET')
        aws_secret_key = passwords_conf_payload['entry'][0]['content']['clear_password']

        # create wa instance
        try:
            wa = WellArchitected(
                {
                    'service_name': WA_SERVICE_NAME, 
                    'endpoint_url': WA_ENDPOINT_URL,
                    'region_name': WA_REGION_NAME,
                    'aws_access_key_id': aws_access_key,
                    'aws_secret_access_key': aws_secret_key
                }
            )
        except Exception as e:
            logger.error('Error when instantiating wa: {}'.format(e))
            raise admin.InternalException('Error when instantiating wa: {}'.format(e))

        # delete workload
        try:
            wa.delete_workload({
                'WorkloadId': workload_id
            })
            logger.info('workload deleted from aws')
        except Exception as e:
            logger.error('Error when deleting workload: {}'.format(e))
            raise admin.InternalException('Error when deleting workload: {}'.format(e))

        # Delete example_eai_handler.conf stanza
        conf_handler_path = '{}/{}'.format(
            self.get_conf_handler_path_name('wa_workloads'),  
            conf_stanza
        )
        wa_workloads_eai_handler_response_payload = self.simple_request_eai(
            conf_handler_path, 
            'remove', 
            'DELETE'
        )
        logger.info('workload deleted from conf file')

        # Always populate entry content from request to handler.
        wa_workloads_rest_path = '/servicesNS/{}/{}/wa_workloads'.format('nobody', self.appName)
        wa_workloads_eai_handler_response_payload = self.simple_request_eai(
            wa_workloads_rest_path, 
            'list', 
            'GET', 
            get_args={'count': -1}
        )
        self.set_conf_info_from_eai_payload(confInfo, wa_workloads_eai_handler_response_payload)

    def update_workload_list_payload(self, workload_list_payload, workloads, account_id):

        logger.info('update_workload_list_payload')

        organization_master_account_link_alternate = '/servicesNS/nobody/grand_central/grand_central_aws_accounts/{}'.format(account_id)
        
        for workload in workloads:
            try:
                conf_entry = {}
                conf_entry['aws_regions'] = 'us-west-2'
                conf_entry['organization_master_account_link_alternate'] = organization_master_account_link_alternate
                conf_entry['workload_arn'] = workload['WorkloadArn']
                conf_entry['workload_id'] = workload['WorkloadId']
                conf_entry['workload_name'] = workload['WorkloadName']
                conf_entry['workload_owner'] = workload['Owner']
                workload_list_payload['entry'].append(conf_entry)
            except Exception as e:
                logger.error('error: {} -- workload: {}'.format(e, workload))
                break

    def update_workload_conf_file(self, workload_list_payload, wa_workloads_conf_response_payload):

        logger.info('in update_workload_conf_file')

        conf_workload_ids = {workload['content']['workload_id'] for workload in wa_workloads_conf_response_payload['entry']}
        workload_lst = workload_list_payload['entry']

        for i, entry in enumerate(workload_lst):
            if entry['workload_id'] in conf_workload_ids:
                logger.info('workload already in conf_workloads')
                continue

            entry['name'] = str(uuid.uuid4())
            try:
                wa_workloads_eai_response_payload = self.simple_request_eai(
                    self.get_conf_handler_path_name('wa_workloads'), 
                    'create', 
                    'POST', 
                    entry
                )
            except Exception as e:
                logger.error('error in update_workload_conf_file: {}'.format(e))
                raise e

    def log_conf_entries(self, workload_list_payload):
        workload_lst = workload_list_payload['entry']
        for i, workload in enumerate(workload_lst):
            logger.info('entry {}: id: {}, name: {}'.format(i, workload['workload_id'], workload['workload_name']))        

    def validate_schema_params(self):
        """
        Validates raw request params against the example schema
        """
        schema = wa_workloads_eai_handler_schema.workloads_schema
        params = self.get_params(schema=wa_workloads_eai_handler_schema, filter=wa_workloads_eai_handler_schema.CONF_FIELDS)
        return self.validate_params(schema, params)


admin.init(WaWorkloadsEAIHandler, admin.CONTEXT_NONE)