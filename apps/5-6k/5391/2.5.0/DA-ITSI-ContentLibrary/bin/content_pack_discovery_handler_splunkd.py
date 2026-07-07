import json
import os
import sys
import http.client

import splunk.rest as rest
from splunk.persistconn.application import PersistentServerConnectionApplication

try:
    from splunk.clilib.bundle_paths import make_splunkhome_path
    sys.path.insert(0, make_splunkhome_path(['etc', 'apps', 'DA-ITSI-ContentLibrary', 'lib']))
except ImportError:
    sys.path.insert(0, os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'DA-ITSI-ContentLibrary', 'lib'))

from itsi_content_utils import HTTPError, SplunkMessageHandler
from itsi_content_setup_logging import logger
from itsi_content_constants import CONTENT_PACK_PREFIX


class ContentPackDiscoveryHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        """
        Basic constructor

        @type: string
        @param command_line: command line invoked for handler

        @type: string
        @param command_arg: args for invoked command line for handler
        """
        super(PersistentServerConnectionApplication, self).__init__()
        self.content_pack_conf_path = \
            rest.makeSplunkdUri() + 'servicesNS/nobody/DA-ITSI-ContentLibrary/configs/conf-itsi_content_packs'

    def handle(self, args):
        """
        Blanket handler for all REST calls on the interface routing the GET/POST/PUT/DELETE requests.
        Derived implementation from PersistentServerConnectionApplication.

        @type args: json
        @param args: a JSON string representing a dictionary of arguments to the REST call.

        @rtype: json
        @return: a valid REST response
        """
        try:
            args = json.loads(args)
            rest_method = args['method']
            session_key = args['session']['authtoken']
            if rest_method != 'POST':
                raise HTTPError(
                    status=http.client.INTERNAL_SERVER_ERROR,
                    message="Unsupported HTTP method {}.".format(rest_method)
                )
            apps = self.get_app_ids(session_key)
            valid_apps = apps['valid_apps']
            added_apps, failed_added_apps = self.add_apps(apps['apps_to_be_added'], session_key)
            removed_apps, failed_removed_apps = self.remove_apps(apps['apps_to_be_removed'], valid_apps, session_key)
            return {
                'payload': {
                    'success': {
                        'apps_added': added_apps,
                        'apps_removed': removed_apps
                    },
                    'failed': {
                        'apps_added': failed_added_apps,
                        'apps_removed': failed_removed_apps
                    },
                    'current_apps_list': valid_apps
                },
                'status': http.client.OK
            }
        except Exception as e:
            logger.exception(e)
            return {
                'payload': {
                    'exception': 'failed to reload content apps because {}'.format(e)
                },
                'status': http.client.INTERNAL_SERVER_ERROR
            }

    def add_apps(self, apps_to_be_added, session_key):
        """
        Add apps which exist on the file system
        but are not registered as stanzas to itsi_content_packs.conf

        @type: list
        @param apps_to_be_added: a list of app names that need to be registered

        @type: string
        @param session_key: the splunkd session key for the request

        @rtype: list
        @return: a list of successfully added app names
        """
        added_apps = []
        failed_added_apps = []
        for app_name in apps_to_be_added:
            file_path = make_splunkhome_path([
                'etc',
                'apps',
                app_name,
                'itsi',
                'config.json'
            ])
            stanza_args = {}
            with open(file_path, 'r') as f:
                config = json.load(f)
                stanza_args['name'] = config.get('id')
                stanza_args['description'] = config.get('description')
                stanza_args['title'] = config.get('title')
                stanza_args['version'] = config.get('version')
                stanza_args['isCustom'] = 1
                try:
                    response, content = rest.simpleRequest(
                        self.content_pack_conf_path,
                        method='POST',
                        postargs=stanza_args,
                        sessionKey=session_key,
                        raiseAllErrors=False
                    )
                    if int(response['status']) == http.client.OK or int(response['status']) == http.client.CREATED:
                        added_apps.append(app_name)
                        logger.info('Added stanza {} to itsi_content_packs.conf'.format(app_name))
                    else:
                        failed_added_apps.append({app_name: {'response': str(response), 'content': str(content)}})
                except Exception as e:
                    failed_added_apps.append({app_name: e.message})
                    message_handler = SplunkMessageHandler(session_key)
                    message = 'Failed to create the content pack stanza {}. Reason: {}'.format(app_name, e)
                    logger.error(message)
                    message_handler.post_or_update_message(app_name,
                                                           SplunkMessageHandler.ERROR,
                                                           message)
        return added_apps, failed_added_apps

    def remove_apps(self, apps_to_be_removed, valid_apps, session_key):
        """
        Remove apps which does not exist on the file system
        but are registered as stanzas to itsi_content_packs.conf

        @type: list
        @param apps_to_be_removed: a list of app names that need to be removed

        @type: list
        @param valid_apps: a list of app names that need to be removed from valid apps

        @type: string
        @param session_key: the splunkd session key for the request

        @rtype: list
        @return: a list of successfully removed app names
        """
        removed_apps = []
        failed_removed_apps = []
        for app_name in apps_to_be_removed:
            try:
                response, content = rest.simpleRequest(
                    self.content_pack_conf_path + '/' + app_name,
                    method='DELETE',
                    sessionKey=session_key,
                    raiseAllErrors=False
                )
                if int(response['status']) == http.client.OK or int(response['status']) == http.client.CREATED:
                    removed_apps.append(app_name)
                    valid_apps.remove(app_name)
                    logger.info('Removed stanza {} from itsi_content_packs.conf'.format(app_name))
                else:
                    failed_removed_apps.append({app_name: {'response': str(response), 'content': str(content)}})
            except Exception as e:
                failed_removed_apps.append({app_name: e.message})
                message_handler = SplunkMessageHandler(session_key)
                message = 'Failed to remove the content pack stanza {}. Reason: {}'.format(app_name, e)
                logger.error(message)
                message_handler.post_or_update_message(app_name,
                                                       SplunkMessageHandler.ERROR,
                                                       message)
        return removed_apps, failed_removed_apps

    def get_app_ids(self, session_key):
        """
        Compare the registered apps and actual apps on the file system
        and get a list of apps_to_be_added, apps_to_be_removed and valid_apps

        @type: string
        @param session_key: the splunkd session key for the request

        @rtype: dict
        @return: a dict with apps_to_be_added, apps_to_be_removed, valid_apps list
        """
        filesystem_apps = self.get_content_pack_apps_on_filesystem()
        registered_apps = self.get_content_pack_apps_registered(session_key)
        logger.info('apps on the file systems are: {}'.format(filesystem_apps))
        logger.info('apps registered in the conf file are: {}'.format(registered_apps))
        valid_apps = list(filesystem_apps.union(registered_apps))
        apps_to_be_added = []
        apps_to_be_removed = []
        for app in filesystem_apps:
            if app not in registered_apps:
                apps_to_be_added.append(app)
        for app in registered_apps:
            if app not in filesystem_apps:
                apps_to_be_removed.append(app)
        return {
            'apps_to_be_added': apps_to_be_added,
            'apps_to_be_removed': apps_to_be_removed,
            'valid_apps': valid_apps
        }

    def get_content_pack_apps_on_filesystem(self):
        """
        Get registered content pack apps that are on the file system
        All content pack apps start with DA-ITSI-CP-

        @rtype: set
        @return: set of app names
        """
        file_path = make_splunkhome_path([
            'etc',
            'apps',
        ])
        apps = set()
        for it in os.scandir(file_path):
            if it.is_dir() and it.name.startswith(CONTENT_PACK_PREFIX):
                apps.add(it.name)
        return apps

    def get_content_pack_apps_registered(self, session_key):
        """
        Get registered apps in the conf file with enterprise endpoints

        @type: string
        @param session_key: the splunkd session key for the request

        @rtype: set
        @return: set of app names
        """

        args = {'output_mode': 'json'}
        response, content = rest.simpleRequest(
            self.content_pack_conf_path,
            method='GET',
            getargs=args,
            sessionKey=session_key,
            raiseAllErrors=False
        )
        results = json.loads(content.decode("utf-8")).get('entry')
        apps = set()
        for item in results:
            apps.add(item.get('name'))
        return apps
