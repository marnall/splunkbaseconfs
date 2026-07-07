import json
import os
import sys


from splunk.persistconn.application import PersistentServerConnectionApplication

try:
    from splunk.clilib.bundle_paths import make_splunkhome_path
    sys.path.insert(0, make_splunkhome_path(['etc', 'apps', 'DA-ITSI-ContentLibrary', 'lib']))
except ImportError:
    sys.path.insert(0, os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'DA-ITSI-ContentLibrary', 'lib'))

from itsi_content_constants import CONTENT_TYPE_TO_ITOA_TYPE
from itsi_content_utils import HTTPError
from itsi_content_setup_logging import logger


class EntitlementRuleHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        """
        Basic constructor

        @type: string
        @param command_line: command line invoked for handler

        @type: string
        @param command_arg: args for invoked command line for handler
        """
        super(PersistentServerConnectionApplication, self).__init__()

    def handle(self, args):
        """
        Blanket handler for all REST calls on the interface routing the GET/POST/PUT/DELETE requests.
        Derived implementation from PersistentServerConnectionApplication.

        @type args: json
        @param args: a JSON string representing a dictionary of arguments to the REST call.

        @rtype: json
        @return: a valid REST response
        """
        args = json.loads(args)
        rest_method = args['method']
        if rest_method != 'GET':
            raise HTTPError(status="500", message="Unsupported HTTP method {}.".format(rest_method))
        rest_path = args['rest_path']
        path_parts = rest_path.strip().strip('/').split('/')
        if path_parts[2] == 'content_pack_level':
            payload = {"entitlement": self.get_content_pack_level_entitlement(path_parts[3])}
        elif path_parts[2] == 'object_type_level':
            payload = self.get_object_level_entitlement(path_parts[3])
        return {'payload': payload, 'status': 200}

    def get_content_pack_level_entitlement(self, content_pack_id):
        """
        Retrieve complete list of entitlements of a content pack.
        We read entitlements for all content types of this content pack from rule.json
        and return a list that contains unique values of all these entitlements

        :param content_pack_id: the content pack version id
        :type content_pack_id: str

        :return: content pack level entitlement
        :rtype: list

        eg: ['standard', 'plus']
        """
        logger.info('getting content pack level entitlement for %s', content_pack_id)
        object_manifest = self.read_content_pack_file(content_pack_id, 'itsi', 'manifest.json')
        rules = self.read_content_pack_file(content_pack_id, 'itsi', 'rule.json')
        object_types = [key for key in object_manifest.keys() if key in CONTENT_TYPE_TO_ITOA_TYPE]
        entitlements = set()
        for entity_type, entitlement_list in rules.get('object_type_entitlement').items():
            if entity_type in object_types:
                entitlements.update(entitlement_list)
        return list(entitlements)

    def get_object_level_entitlement(self, content_pack_id):
        """
        Retrieve entitlements for all content types of a content pack
        We read entitlements for all content types of this content pack from rule.json and return as is

        :param content_pack_id: the content pack version id
        :type content_pack_id: str

        :return: object type level entitlement
        :rtype: dict

        eg:
        {
            "correlation_searches": [
                "itsi_cp_service_overview"
            ],
            "entity_types": [
                "itsi_cp_infra_overview",
                "itsi_cp_service_overview"
            ],
            "kpi_base_searches": [
                "itsi_cp_service_overview"
            ],
            "services": [
                "itsi_cp_service_overview"
            ],
            "notable_event_aggregation_policies": [
                "itsi_cp_service_overview"
            ]
        }
        """
        logger.info('getting object type level entitlement for %s', content_pack_id)
        object_manifest = self.read_content_pack_file(content_pack_id, 'itsi', 'manifest.json')
        rules = self.read_content_pack_file(content_pack_id, 'itsi', 'rule.json')
        object_types = [key for key in object_manifest.keys() if key in CONTENT_TYPE_TO_ITOA_TYPE]
        entitlements = rules['object_type_entitlement']
        entitlements = {key: value for key, value in entitlements.items() if key in object_types}
        return entitlements

    def read_content_pack_file(self, content_pack_id, *path_to_file):
        """
        Returns thclient.connect(e file data for the given content pack file.

        :param content_pack_id: the content pack id
        :type content_pack_id: str

        :param path_to_file: list of arguments that specifies path to file
        :type path_to_file: list

        :return: the file data
        :rtype: dict
        """
        file_path = EntitlementRuleHandler.make_path_to_content_pack_file(content_pack_id, *path_to_file)
        with open(file_path, 'r') as file_object:
            contents = file_object.read()

        return json.loads(contents)

    @staticmethod
    def make_path_to_content_pack_file(content_pack_id, *path_to_file):
        """
        Returns the file path to the content pack file or directory.

        :param content_pack_id: the content pack id
        :type content_pack_id: str

        :param path_to_file: list of arguments that specifies path to file
        :type path_to_file: list

        :return: the file path to the content pack file or directory
        :rtype: str
        """
        try:
            file_path = make_splunkhome_path([
                'etc',
                'apps',
                content_pack_id,
                *path_to_file
            ])
            if os.path.exists(file_path):
                return file_path
            else:
                return make_splunkhome_path([
                    'etc',
                    'apps',
                    'DA-ITSI-ContentLibrary',
                    *path_to_file
                ])
        except Exception as e:
            logger.exception('Failed to read content pack file for content pack id: %s', content_pack_id)
            raise e
