# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

"""
Script that periodically import Services and Entities either by reading a CSV file on
your file system or by issuing a Splunk search
"""
import time
import sys
import json
import uuid
import logging
from io import StringIO
# try:  # noqa: F401
#     from typing import (Iterator, Sequence, Dict, List, Text, Type, Any, Optional,  # noqa: F401
#                         Union, Callable, Tuple, Generator, BinaryIO)  # noqa: F401
# except:  # noqa: F401
#     pass  # noqa: F401

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path
import itsi_py3

from SA_ITOA_app_common.solnlib.modular_input import ModularInput
from SA_ITOA_app_common.solnlib.utils import is_true
from SA_ITOA_app_common.splunklib.modularinput.argument import Argument

from itsi.itsi_utils import ITOAInterfaceUtils
import itsi.csv_import.itsi_csv_import_utils as csv_import_utils
from itsi.csv_import import BulkImporter
from itsi.csv_import.itoa_bulk_import_preview_utils import build_reader

import ITOA.itoa_common as utils
from ITOA.setup_logging import logger, getLogger4ModInput
from ITOA.mod_input_utils import skip_run_during_migration
from ITOA.storage.itoa_storage import ITOAStorage


class ITSICSVImport(ModularInput):
    """
    For a run, this modular input will periodically import diffs from a CSV files
    and associate it with entities & services, if possible
    """
    title = "IT Service Intelligence CSV Import"
    description = ("Helps to populate your entities, "
                   "services, and their relationships into the KV store.")
    app = 'SA-ITOA'
    name = 'itsi_csv_import'

    use_single_instance = False
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def extra_arguments(self):
        # type: () -> List[Dict[Text, Any]]
        return [
            {
                'name': "log_level",
                'title': "Logging Level",
                'description': ("This is the level at which the modular input will log data; "
                                "DEBUG, INFO, WARN, ERROR.  Defaults to WARN.")
            },
            {
                'name': "import_from_search",
                'title': "Do you wish to import from search ?",
                'description': ("Required. Do you wish to import further via a search "
                                "or from disk on file?"),
                'required_on_create': True,
                'data_type': Argument.data_type_boolean
            },
            {
                'name': "search_string",
                'title': "Search string to execute for importing",
                'description': ("Search string that would become a saved search for "
                                "importing purposes")
            },
            {
                'name': "service_security_group",
                'title': "Team",
                'description': "Team that the imported service(s) object should be associated with."
            },
            {
                'name': "index_earliest",
                'title': "Earliest index time",
                'description': ("Earliest index time you want to use to with your Splunk "
                                "search to import entities/services. If no value is provided, "
                                "we will default to '-15m'")
            },
            {
                'name': "index_latest",
                'title': "Latest index time",
                'description': ("Latest index time you want to use with your Splunk search "
                                "to import entities/services. If no value is provided, we "
                                "will default to 'now'")
            },
            {
                'name': "csv_location",
                'title': "CSV Location",
                'description': ("The path to the CSV File.  Please note that if it is stored "
                                "remotely it must be accessible to this machine")
            },
            {
                'name': "entity_title_field",
                'title': "Entity Title Column",
                'description': ("Column in CSV file that represents title of an entity. "
                                "Mandatory. Case sensitive")
            },
            {
                'name': "entity_merge_field",
                'title': "Entity Conflict Resolution Field Column",
                'description': ("Column in CSV file that represents the conflict resolution field of an entity. "
                                "Case sensitive")
            },
            {
                'name': "entity_description_column",
                'title': "Entity Description Column",
                'description': ("Comma-separated names of column headers from the CSV file "
                                "that may describe an asset. Case sensitive")
            },
            {
                'name': "entity_identifier_fields",
                'title': "Entity Identifier Fields",
                'description': ("Comma-separated names of column headers to be imported from "
                                "the CSV File that represent fields that may identify the asset. "
                                "Case sensitive.")
            },
            {
                'name': "entity_informational_fields",
                'title': "Entity Informational Fields",
                'description': ("Comma-separated names of column headers to be imported from "
                                "the CSV File that represent fields that provide non-identifying "
                                "data about the asset. Case sensitive.")
            },
            {
                'name': "entity_field_mapping",
                'title': "Entity Field Mappings",
                'description': ("A mapping specification for the CSV (input) fields to ones that "
                                "match Splunk fields (output).  Optional.  It needs to be a comma "
                                "separated list of key=value pairs where the key is the field found "
                                "in the CSV.  For example, if your CSV contains 'foo' and 'bar' as "
                                "headers and you want to map both of them to the Splunk field 'dest', "
                                " you should set field mappings as 'foo=dest,bar=dest'")
            },
            {
                'name': "entity_relationship_spec",
                'title': "Entity Relationship Specification",
                'description': ("Entity Relationship for Entity Import. A dictionary of relationships and list "
                                "of fields. For example, if your CSV contains 'foo' and 'bar' as headers and "
                                "you want to specify both of them relating to entity title field in 'hosts' "
                                "relationship, you should set entity relationship spec as "
                                "{\"hosts\": [\"foo\", \"bar\"]}.")
            },
            {
                'name': "service_title_field",
                'title': "Service Title Column",
                'description': ("Column in CSV file that represents the title of a service. Mandatory. "
                                "Case sensitive")
            },
            {
                'name': "service_description_column",
                'title': "Service Description Column",
                'description': ("Comma-separated names of column headers from the CSV file "
                                "that may describe an asset. Case sensitive")
            },
            {
                'name': "service_tags_field",
                'title': "Service Tags Column",
                'description': ("Comma-separated names of column headers from the CSV file "
                                "that represent descriptor tags for the service being imported. ")
            },
            {
                'name': "service_rel",
                'title': "Service Relationships Specification",
                'description': ("Service Relationship for Service Import/Entity Import. A comma "
                                "separated list of strings. For example, 'service1,service2,service3' "
                                "implies 'service1 depends on service2' 'service2 depends on service3'. "
                                "All services in the line are related to one another. Adding it in "
                                "this fashion would tie up the 'Service Health KPIs' for each of the "
                                "services with each other. Search 'sourcetype=itsi_internal_log' in "
                                "Splunk for any errors")
            },
            {
                'name': "service_dependents",
                'title': "Service Dependencies Specification",
                'description': ("Service Dependencies for Service Import. A comma-separate list of "
                                "field names.  Objects in these fields will be made child objects "
                                "of the service specified in the service_title_field column. Search "
                                "'sourcetype=itsi_internal_log' in Splunk for any errors")
            },
            {
                'name': "selected_services",
                'title': "Existing services to apply",
                'description': ("Comma-separated list of services which need to be attached to "
                                "entities/services being imported. Optional")
            },
            {
                'name': "service_enabled",
                'title': "Enable imported services?",
                'description': "Import services as enabled by default."
            },
            {
                'name': "service_template_field",
                'title': "Service Template Column",
                'description': ("Column in CSV file that contains the name of the service template "
                                "that the imported service should be linked to. Optional")
            },
            {
                'name': "template",
                'title': "Entity Rules to Service Template mappings",
                'description': "Entity rules to Service Template mappings. Optional"
            },
            {
                'name': "backfill_enabled",
                'title': "Enable Backfill for All KPIs?",
                'description': "Enable backfill on all KPIs in Services linked to Service Templates.  Service template field must be specified."
            },
            {
                'name': "update_type",
                'title': "Update Type",
                'description': ("Instructions on how to update existing records.  If APPEND, all "
                                "records are treated as new records. If UPSERT, new information is  "
                                "added to records with matching title fields. If REPLACE, new "
                                "records will replace old records when an existing match on the "
                                "title field is found."),
                'required_on_create': True
            },
            {
                'name': "entity_service_columns",
                'title': "Service Title Associating Service To Entity",
                'description': ("A comma separated list of services found in the CSV file itself "
                                "that are to be associated with the entity for the row. Optional")
            }
        ]

    def wait_for_job(self, searchjob, maxtime=-1):
        """
        This function will wait for search job to get ready

        Args:
            searchjob (service): search job to execute spl search
            maxtime (int, optional): if not provided then waits for forever. Defaults to -1.

        Returns:
            boolean : status of searchjob
        """
        pause = 0.2
        lapsed = 0.0
        while not searchjob.is_done():
            time.sleep(pause)
            lapsed += pause
            if maxtime >= 0 and lapsed > maxtime:
                break
        return searchjob.is_done()

    def set_logging(self, level):
        # type: (Text) -> None
        '''
        Sets the logging level for the modular input.
        We should probably harass them more if they screw this up
        '''
        if level not in ['ERROR', 'WARN', 'INFO', 'DEBUG']:
            logger.warning("Error logging invalid value {}. Defaulting to WARN".format(level))
            level = 'WARNING'
        if level == 'WARN':
            level = 'WARNING'
        logger.setLevel(getattr(logging, level))

    def import_via_search(self, import_info):
        # type: (Dict) -> Union[None, StringIO[Any]]
        '''
        import entity/service info via search
        @param import_info - a dictionary containing the import specification
        @return None or IOobject
        '''
        RETRIES = 3
        count = 0
        service = ITOAInterfaceUtils.service_connection(self.session_key, app_name="SA-ITOA")

        index_earliest = import_info.get('index_earliest')
        if index_earliest is None:
            logger.debug('Modular input did not find index_earliest. Defaulting to "last 15 minutes"')
            index_earliest = '-15m'
        index_latest = import_info.get('index_latest')
        if index_latest is None:
            logger.debug('Modular input did not find any index_latest. Defaulting to "now"')
            index_latest = 'now'

        search_string = import_info['search_string'].lstrip()
        if (len(search_string) > 1) and not (search_string[0] == '|'):
            search_string = "search {}".format(search_string)
        params = {
            'output_mode': 'json',
            'index_earliest': index_earliest,
            'index_latest': index_latest,
            'count': 0
        }

        # create a new search job
        ########################################
        search_job = service.jobs.create(search_string, **params)
        # now let's check if our search is done. we'll check this in a loop
        ########################################
        if not self.wait_for_job(search_job, 300):
            error_message = search_job.messages.get('error', [])
            logger.error('The search failed. If the problem persists, contact support. '
                         + 'This modular input will now exit. Search Error - {}'.format(error_message))
            return None

        if int(search_job["resultCount"]) == 0:
            error_message = search_job.messages.get('error', [])
            logger.error(
                'The search returns 0 events. Search Error - {}'.format(error_message))
            return None

        # we are done running search; now let's fetch results as in csv format
        ########################################
        params = {
            'output_mode': 'csv',
            'count': 0
        }
        while count < RETRIES:
            reader = search_job.results(**params)
            search_results = [res for res in reader]
            if len(search_results) == 0 :
                count += 1
                time.sleep(0.2)
                pass
            else:
                logger.debug('Done running search. Modular input will now try to import your entities/services.')
                break

        if len(search_results) == 0:
            error_message = search_job.messages.get('error', [])
            logger.error('Error while trying to fetch search results. The search may have failed. '
                         'If the problem persists, contact support. This modular input will now exit. '
                         'Search Error - {}, Search - {}'.format(error_message, search_string))
            return None

        csv_data = search_results

        if sys.version_info >= (3, 0):
            csv_data = b''.join(search_results)
            csv_data = csv_data.decode()

        return StringIO(csv_data)

    def import_via_csv(self, csv_filepath):
        # type: (Text) -> Union[file, BinaryIO]
        '''
        import entity/service info via csv file on disk.
        '''
        # verify that file to import isn't empty or None
        valid_csv, msg = csv_import_utils.validate_csv_location(csv_filepath)
        if not valid_csv:
            logger.error(
                'Invalid CSV file location. Make sure that the CSV file exists on '
                'this host and that it is an absolute location. If the problem persists, '
                'contact support. Error - "{}"'.format(msg))
            return None
        if sys.version_info >= (3, 0):
            return open(csv_filepath, 'rt')
        return open(csv_filepath, 'rbU')

    @skip_run_during_migration
    def do_run(self, input_config):
        # type: (dict) -> None
        """
        Entry point of the modinput - method invoked by splunkd
        @type input_config: dict/json basestring
        @param input_config: the input config for this modular input
            the input config basically comes down to us as a dictionary:
            {
                'itsi_csv_import://foo': {
                   'import_from_search': '0',
                   'log_level': 'DEBUG',
                   'host': 'csridhar-mbp.sv.splunk.com',
                   'index': 'default',
                   'update_type': 'UPSERT',
                   'entity_title_field':
                   'etitle', 'interval': '10',
                   'entity_description_column': 'edesc',
                   'csv_location': '/Users/csridhar/Downloads/foo.csv',
                   'entity_identifier_fields': 'etitle'
                   'service_security_group':'2c25ec5e-c52d-4506-bbd6-c035e147755c'
                   }
            }
        """
        logger = getLogger4ModInput(input_config)

        from itsi.csv_import.itoa_bulk_import_common import set_transaction
        transaction_id = str(uuid.uuid1())[0:8]
        set_transaction(transaction_id)

        if not utils.modular_input_should_run(self.session_key, logger=logger):
            logger.info("Will not run modular input on this node.")
            return

        logger.debug("Starting modular input. config=%s", input_config)

        input_config = utils.validate_json('[ITSICSVImport] [run]', input_config)

        # get the actual configuration as a dictionary
        mod_input_spec = list(input_config.values())[0]

        try:
            if 'template' in mod_input_spec and isinstance(mod_input_spec['template'], itsi_py3.string_type):
                mod_input_spec['template'] = json.loads(mod_input_spec['template'])
            else:
                mod_input_spec['template'] = {}
        except Exception:
            logger.error("Modular input received malformed service template entity rules mapping.")
            mod_input_spec['template'] = {}

        self.set_logging(mod_input_spec.get('log_level', 'WARN'))

        # Before attempting any imports, first try to wait for KV store to get initialized
        kvstore = ITOAStorage()
        kvstore.wait_for_storage_init(self.session_key)

        # check if we can import from search & some validations
        import_from_search = is_true(mod_input_spec.get('import_from_search', False))
        logger.info("import_from_search: %s" % import_from_search)
        if import_from_search and not mod_input_spec.get('search_string'):
            logger.error('"search_string" not found in "import_from_search" spec. Received: %s',
                         json.dumps(mod_input_spec))
            return

        # convert strings to appropriate data structs as applicable
        mod_input_spec, msg = csv_import_utils.massage_import_spec(mod_input_spec)
        if not mod_input_spec:
            logger.error('Modular input received an invalid JSON as input %s. This modular input'
                         ' will not run. If the problem persists, contact support.'
                         ' Error - %s', mod_input_spec, msg)
            return

        # generate BulkImportSpecification from mod_input_spec
        import_info, msg = csv_import_utils.generate_import_info_mod_input(mod_input_spec)
        logger.info('import_info: %s', json.dumps(import_info))
        if not import_info:
            logger.error('Modular input could not generate a valid "import information dict".'
                         ' This modular input will not run. If the problem persists, contact support.'
                         ' Error - %s', msg)
            return

        # we can either be importing from a CSV file or via search...
        csvfile = None  # type: Union[BinaryIO, StringIO[Any]]
        if import_from_search is True:
            csvfile = self.import_via_search(mod_input_spec)
        else:
            csvfile = self.import_via_csv(mod_input_spec['csv_location'])

        # Search failed; the loggers in the various import mechanisms have
        # their own reporting schemes.
        if not csvfile:
            return

        reader = build_reader(csvfile)
        bulk_importer = BulkImporter(
            specification=import_info,
            session_key=self.session_key,
            current_user='nobody',
            owner='nobody')
        bulk_importer.bulk_import(reader, transaction_id)


if __name__ == "__main__":
    worker = ITSICSVImport()
    worker.execute()
    sys.exit(0)
