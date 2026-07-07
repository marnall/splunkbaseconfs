# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import json
import sys

from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))

import itsi_path

from SA_ITOA_app_common.splunklib.searchcommands import Configuration, Option, EventingCommand, dispatch

from ITOA.itoa_common import is_feature_enabled
from ITOA.setup_logging import InstrumentCall, logger
from itsi.csv_import import BulkImporterFactory
from itsi.csv_import.itoa_bulk_import_common import to_string
from itsi.csv_import.itsi_csv_import_utils import generate_import_info_mod_input, massage_import_spec


def to_importable_rows(records):
    """Converts the given search records to a list of bulk importable objects.

    :param records: an iterable object of search records
    :type records: generator
    :returns: a list of objects compatible with bulk import
    :rtype: list
    """
    if not len(records):
        return []

    first_row = records[0]

    # The first row of the results should be a list of column names
    rows = [list(first_row.keys())]

    for record in records:
        values = [to_string(v) for v in list(record.values())]
        rows.append(values)

    return rows


def to_import_specification(import_options):
    """Converts the given import options to a format/specification compatible with Bulk Import.

    :param import_options: the import options describing how fields should be mapped and used
    :type import_options: dict
    :returns: a dict compatible with a Bulk Import specification
    :rtype: dict
    """
    filtered_options = {option: value for option,
                        value in list(import_options.items()) if value}
    massaged_spec, _ = massage_import_spec(filtered_options)
    specification, _ = generate_import_info_mod_input(massaged_spec)
    return specification


def to_service_templates_specification(templates_config):
    """Converts the given service templates config option to a format compatible with Bulk Import.

    :param templates_config: the service templates configuration containing info such as entity rules
    :type templates_config: str
    :returns: a dict compatible with a Bulk Import specification
    :rtype: dict
    """
    if not templates_config:
        return {}

    try:
        service_templates_spec = json.loads(templates_config)
    except ValueError:
        raise ValueError(
            'Ensure the provided service templates configuration is in a valid JSON format.')

    return service_templates_spec


@Configuration()
class ItsiImportObjectsCommand(EventingCommand):
    """Imports ITSI objects such as Entities and Services from event data.

    This command receives configuration options through command arguments that specify which fields
    in the events data should be used to import their relevant ITSI object type.
    """
    backfill_enabled = Option(name='backfillEnabled', doc='''
        This setting determines whether to enable backfill on all
        Key Performance Indicators (KPIs) in linked service templates.
        Backfill is the process of getting historical KPI data.
        ITSI backfills the KPI summary index (itsi_summary). You must have
        indexed adequate raw data for the backfill period.
        ''', default=None, require=False)

    entity_description_fields = Option(name='entityDescriptionFields', doc='''
        A list of fields that represents the description of an entity.
        ''', default=None, require=False)

    entity_field_mapping = Option(name='entityFieldMapping', doc='''
        A key-value mapping of fields to re-map to other fields in the data.
        Follows a <field> = <Splunk search field> format.
        For example, ip1 = dest, ip2 = dest, storage_type = volume
        Use this setting to rename a field or column to an alias or info value.
        ''', default=None, require=False)

    entity_identifier_fields = Option(name='entityIdentifierFields', doc='''
        A list of fields that represent identifier data of an entity.
        ''', default=None, require=False)

    entity_informational_fields = Option(name='entityInformationalFields', doc='''
        A list of fields that represent the informational data of an entity.
        ''', default=None, require=False)

    entity_merge_field = Option(name='entityMergeField', doc='''
        The field that should be used when resolving conflicts between entities.
        ''', default=None, require=False)

    entity_merge_fqdn = Option(name='entityMergeFqdn', doc='''
        The field that determines whether to enable FQDN match for entities.
        ''', default=None, require=False)

    entity_title_field = Option(name='entityTitleField', doc='''
        The field that represents the title of an entity.
        ''', default=None, require=False)

    entity_type_field = Option(name='entityTypeField', doc='''
        The field that represents the entity type of an entity.
        ''', default=None, require=False)

    entity_status_tracking = Option(name='entityStatusTracking', doc='''
        Whether the discovery search that triggered this command
        contributes to entity status calculation.
        ''', default=None, require=False)

    field_level_update_type = Option(name='fieldLevelUpdateType', doc='''
        Specify alias/informational fields of entity to be skip/update/replace,
        values can overwrite search level conflict resolution for specified fields,
        if such fields have different desired resolutions.
        ''', default=None, require=False)

    recurring_import_name = Option(name='recurringImportName', doc='''
        The name of the recurring bulk import which triggered this command.
        Used for updating cached entity metadata by recurring import name
        ''', default=None, require=False)

    service_dependents_fields = Option(name='serviceDependentsFields', doc='''
        A list of fields that indicate service dependencies.
        ''', default=None, require=False)

    service_description_fields = Option(name='serviceDescriptionFields', doc='''
        A list of fields that represents the description of a service.
        ''', default=None, require=False)

    service_tags_fields = Option(name='serviceTagsFields', doc='''
        A list of fields that represents one or more tags to be added to a service.
        ''', default=None, require=False)

    service_enabled = Option(name='serviceEnabled', doc='''
        Whether or not imported services should be enabled.
        ''', default=None, require=False)

    service_team = Option(name='serviceTeam', doc='''
        The ITSI team that the imported services belong to.
        ''', default=None, require=False)

    service_sandbox = Option(name='serviceSandbox', doc='''
        The ITSI Service Sandbox that the imported services belong to.
        ''', default=None, require=False)

    service_templates_config = Option(name='serviceTemplatesConfig', doc='''
        A dictionary of key-value pairs that maps entity rules to service templates.
        For example,
        {
            "test_template_2": {
                "entity_rules": [
                    {
                        "rule_items": [{
                            "rule_type": "matches",
                            "field_type": "alias",
                            "field": "foo",
                            "value": "bar"
                        }
                    ],
                    "rule_condition": "AND"
                }]
            },
            "test_template_1": {
                "entity_rules": [
                    {
                        "rule_items": [
                            {
                                "rule_type": "matches",
                                "field_type": "alias",
                                "field": "ta",
                                "value": "da"
                            }
                        ],
                        "rule_condition": "AND"
                    }
                ]
            }
        }
        ''', default=None, require=False)

    service_template_field = Option(name='serviceTemplateField', doc='''
        Determines which service template a service is linked to.
        ''', default=None, require=False)

    service_title_field = Option(name='serviceTitleField', doc='''
        The field that represents the title of a service.
        ''', default=None, require=False)

    update_type = Option(name='updateType', doc='''
        The update/insertion method when uploading entities.
        APPEND: ITSI makes no attempt to identify commonalities between entities.
            All information is appended to the table.
        UPSERT: ITSI appends new entries. Existing entries (based on the value
            found in the title_field) have additional information appended
            to the existing record.
        REPLACE: ITSI appends new entries. Existing entries (based on the value
            found in the title_field) are replaced by the new record value.
        ''', default=None, require=False)

    def transform(self, records):
        """Returns a summary of the import operation in the following format:
            {
                "entities": <number of entities imported>,
                "entities_skip_count": <number of entities skipped during the import>
                "services": <number of services imported>,
                "services_skip_count": <number of services skipped during the import>
            }

        :param records: an iterable object of event records
        :type records: generator
        :returns: a summary of the import
        :rtype: dict
        """
        batched_records = list(records)
        rows = to_importable_rows(batched_records)
        import_spec = self.import_specification

        # Invoke BulkImportFactory with the specification. Specification would route the imports to legacy import vs
        # Service Sandbox imports
        bulk_importer_factory = BulkImporterFactory(
            import_spec,
            session_key=self._metadata.searchinfo.session_key,
            current_user='nobody',
            owner='nobody'
        )

        _instrumentation = InstrumentCall(logger)
        with _instrumentation.track(
            'ItsiImportObjectsCommand.transform', metric_info={"numberOfRows": len(rows)}
        ) as transaction_id:
            logger.debug(f'{transaction_id} Bulk Import specification:{import_spec}')
            import_summary = bulk_importer_factory.bulk_import(
                rows, transaction_id)

        yield import_summary

    @property
    def import_specification(self):
        import_options = {
            'backfill_enabled': self.backfill_enabled,
            'entity_field_mapping': self.entity_field_mapping,
            'entity_description_column': self.entity_description_fields,
            'entity_identifier_fields': self.entity_identifier_fields,
            'entity_informational_fields': self.entity_informational_fields,
            'entity_merge_field': self.entity_merge_field,
            'entity_title_field': self.entity_title_field,
            'entity_type_field': self.entity_type_field,
            'entity_status_tracking': self.entity_status_tracking,
            'service_dependents': self.service_dependents_fields,
            'service_description_column': self.service_description_fields,
            'service_tags_field': self.service_tags_fields,
            'service_enabled': self.service_enabled,
            'service_security_group': self.service_team,
            'service_template_field': self.service_template_field,
            'service_title_field': self.service_title_field,
            'template': to_service_templates_specification(self.service_templates_config),
            'update_type': self.update_type,
            'recurring_import_name': self.recurring_import_name,
            'service_sandbox': self.service_sandbox
        }

        if is_feature_enabled('itsi-duplicate-entity-normalization', self._metadata.searchinfo.session_key):
            import_options['entity_merge_fqdn'] = self.entity_merge_fqdn
            import_options['field_level_update_type'] = self.field_level_update_type

        return to_import_specification(import_options)


dispatch(ItsiImportObjectsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
