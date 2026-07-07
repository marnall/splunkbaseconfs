# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.
"""
Script that periodically import Services and Entities either by reading a CSV file
on $SPLUNK_HOME/var/spool/itsi directory
"""

import sys

# try:  # noqa: F401
#     from typing import Iterator, Sequence, Dict, List, Text, Type, Any, Optional, Union, Callable, Tuple, Generator  # noqa: F401
# except:  # noqa: F401
#     pass  # noqa: F401

import logging
from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path
from itsi.csv_import.itoa_bulk_import_modinput_interface_provider import process_bulk_import_spool, set_transaction
from ITOA.setup_logging import getLogger4ModInput
from ITOA.mod_input_utils import skip_run_during_migration
from SA_ITOA_app_common.solnlib.modular_input import ModularInput
from SA_ITOA_app_common.splunklib.modularinput.argument import Argument


class ITSIAsyncCSVLoader(ModularInput):
    """
    Mod input dedicated to import csv data to KV store
    """

    # Overwrite properties in parent class
    title = "IT Service Intelligence Asynchronous CSV Loader"
    description = ("Helps to load your entities, "
                   "services, and their relationships into the KV store.")

    app = 'SA-ITOA'
    name = 'itsi_async_csv_loader'

    use_single_instance = True
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def extra_arguments(self):
        """
        Extra arguments for modular input.
        """
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

    @skip_run_during_migration
    def do_run(self, input_config):
        # type: (Dict[Text, Any]) -> None
        """
        This is the method called by splunkd when mod input is enabled.

        @type input_config: object
        @param input_config: config passed down by splunkd
            input_config is a dictionary key'ed by the name of the modular
            input, its value is the modular input configuration.
        """
        logger = getLogger4ModInput(input_config)

        level = input_config.get('log_level', 'INFO').upper()
        if level not in ['ERROR', 'WARN', 'WARNING', 'INFO', 'DEBUG']:
            level = 'INFO'
        if level == 'WARN':
            level = 'WARNING'

        logger.setLevel(getattr(logging, level))
        set_transaction('pre')
        logger.info('Running itsi_async_csv_loader')
        return process_bulk_import_spool(self.session_key, input_config)


if __name__ == "__main__":
    worker = ITSIAsyncCSVLoader()
    worker.execute()
    sys.exit(0)
