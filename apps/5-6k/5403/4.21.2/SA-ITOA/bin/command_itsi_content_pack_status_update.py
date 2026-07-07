# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
import time
from functools import cmp_to_key
from json.decoder import JSONDecodeError

from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))

from SA_ITOA_app_common.splunklib.searchcommands import dispatch, GeneratingCommand, Configuration

from itsi.content_packs.constants import ContentType, CONTENT_PACK_SOURCE_FIELD, CONTENT_PACK_SOURCE_VERSION_FIELD, \
    CONTENT_TYPE_TO_ITOA_TYPE, ContentPackFields
from itsi.content_packs.itoa import get_itoa_object_class
from itsi.content_packs.readers import ContentPackMetadataReader, get_content_packs_conf
from itsi.content_packs.retriever import retrieve_saved_search_count_details

from itsi.objects.itsi_content_pack_status import ItsiContentPackStatus

from ITOA.setup_logging import setup_logging
from ITOA.saved_search_utility import APP_FILTER_PREFIX, SavedSearch
from ITOA.version_check import VersionCheck

LOGGER = setup_logging(
    logfile_name='itsi_content_packs_saved_search_status.log',
    logger_name='itsi.content_packs.saved_search_status'
)


@Configuration()
class ITSIContentPackStatusUpdateCommand(GeneratingCommand):
    owner = 'nobody'

    def get_content_pack_objects(self, content_pack_id_list):
        """
        Bulk fetch all objects of cp supported type from KV Store

        @param content_pack_id_list: a list of _keys of the content pack status collection records
        @type list

        :return: list of content pack objects which has object['source_itsi_da'] == content_pack_id

        """
        if not content_pack_id_list:
            return []
        content_pack_id_query_list = [
            {CONTENT_PACK_SOURCE_FIELD: key} for key in content_pack_id_list
        ]
        content_pack_objects = []
        content_types = [item for item in CONTENT_TYPE_TO_ITOA_TYPE.keys() if
                         (item != ContentType.GLASS_TABLE_IMAGE and item != ContentType.GLASS_TABLE_ICON)]

        for content_type in content_types:
            filter_data = {'$or': content_pack_id_query_list} if content_pack_id_query_list else {}
            fields = [CONTENT_PACK_SOURCE_FIELD, CONTENT_PACK_SOURCE_VERSION_FIELD]
            itoa_object_class = get_itoa_object_class(content_type)
            content_pack_objects += itoa_object_class(
                self._metadata.searchinfo.session_key,
                ITSIContentPackStatusUpdateCommand.owner
            ).get_bulk(owner=ITSIContentPackStatusUpdateCommand.owner, filter_data=filter_data, fields=fields)
        return content_pack_objects

    @staticmethod
    def get_content_pack_version_dict(content_pack_id_list, content_pack_objects):
        """
        Bulk fetch all objects of cp supported type from KV Store

        @param content_pack_id_list: a list of _keys of the content pack status collection records
        @type list

        @param content_pack_objects: all content pack objects of cp supported type from KV Store
        @type list

        :return: a dict where keys are content_pack_ids
        values are list of versions of current existing content pack objects

        """
        content_pack_version_dict = {content_pack_id: set() for content_pack_id in content_pack_id_list}
        for obj in content_pack_objects:
            content_pack_version_dict[obj[CONTENT_PACK_SOURCE_FIELD]].\
                add(obj[CONTENT_PACK_SOURCE_VERSION_FIELD])
        for content_pack_id, content_pack_version_set in content_pack_version_dict.items():
            content_pack_version_dict[content_pack_id] = sorted(list(content_pack_version_set),
                                                                key=cmp_to_key(VersionCheck.compare)
                                                                )
        return content_pack_version_dict

    def get_content_pack_status_object_list(self):
        """
        Bulk fetch all records from content pack status collection as a list

        :return: list of content pack status object keys,
        eg:
        [
            {
                "identifying_name": "",
                "object_type": "content_pack_status",
                "installed_versions": [
                    "1.0.0",
                    "5.0.0"
                ],
                "_version": "4.7.0",
                "mod_source": "REST",
                "mod_timestamp": "2020-09-09T17:48:09.588552+00:00",
                "_user": "nobody",
                "_key": "CP-ITSI-NIX"
            },
            {
                "identifying_name": "",
                "object_type": "content_pack_status",
                "installed_versions": [
                    "1.0.0",
                    "10.0.0"
                ],
                "_version": "4.7.0",
                "mod_source": "REST",
                "mod_timestamp": "2020-09-09T17:48:09.588584+00:00",
                "_user": "nobody",
                "_key": "CP-ITSI-PHANTOM"
            }
        ]

        """
        content_pack_status_object_list = ItsiContentPackStatus(
            self._metadata.searchinfo.session_key,
            ITSIContentPackStatusUpdateCommand.owner
        ).get_bulk(owner=ITSIContentPackStatusUpdateCommand.owner)
        return content_pack_status_object_list

    def update_content_pack_status_versions(self, content_pack_status_object_list, content_pack_version_dict):
        """
        Bulk fetch all objects of cp supported type from KV Store

        @param content_pack_status_object_list: a list of content pack status objects in current KV Store collection

        @param content_pack_version_dict: a dict where each key is a content pack id
        and each value is a list of this content pack id's versions

        update installed_versions field of each content pack status record
        with the current versions of existing content pack objects

        :return: a dict where keys are content pack ids,
        values are updated content pack status objects
        eg: [
            CP-ITSI-GT:
                {
                    "installed_versions": [
                        "1.0.0",
                        "2.0.0"
                    ],
                    "mod_source": "REST",
                    "object_type": "content_pack_status",
                    "_version": "4.7.0",
                    "identifying_name": "",
                    "_user": "nobody",
                    "_key": "CP-ITSI-WIN"
                },
            CP-ITSI-WIN:
                {
                    "installed_versions": [
                        "1.0.0",
                        "2.0.0"
                    ],
                    "mod_source": "REST",
                    "object_type": "content_pack_status",
                    "_version": "4.7.0",
                    "identifying_name": "",
                    "_user": "nobody",
                    "_key": "CP-ITSI-WIN"
                }
            ]

        """
        new_content_pack_status_object_list = []
        for status_object in content_pack_status_object_list:
            status_object_key = status_object['_key']
            if not content_pack_version_dict[status_object_key]:
                ItsiContentPackStatus(
                    self._metadata.searchinfo.session_key,
                    ITSIContentPackStatusUpdateCommand.owner
                ).delete(ITSIContentPackStatusUpdateCommand.owner, status_object_key)
                continue
            status_object[ContentPackFields.VERSION_INSTALLED] = content_pack_version_dict[status_object_key]
            new_content_pack_status_object_list.append(status_object)
        if new_content_pack_status_object_list:
            ItsiContentPackStatus(
                self._metadata.searchinfo.session_key,
                ITSIContentPackStatusUpdateCommand.owner
            ).save_batch(
                owner=ITSIContentPackStatusUpdateCommand.owner,
                data_list=new_content_pack_status_object_list,
                validate_names=False
            )
        return {item['_key']: item for item in new_content_pack_status_object_list}

    def generate(self):
        """
        Update installed_versions field of each record in itsi_content_pack_status collection
        output each updated record as an event

        :return: yield events with some fields, eg content_pack_id, _time, _raw
        """
        content_pack_status_object_list = self.get_content_pack_status_object_list()
        content_pack_id_list = [content_pack_status_object.get('_key') for content_pack_status_object in
                                content_pack_status_object_list]
        content_pack_objects = self.get_content_pack_objects(content_pack_id_list)
        content_pack_version_dict = ITSIContentPackStatusUpdateCommand.get_content_pack_version_dict(
            content_pack_id_list, content_pack_objects)
        updated_content_pack_status_object_dict = self.update_content_pack_status_versions(
            content_pack_status_object_list, content_pack_version_dict)
        for content_pack_id in content_pack_version_dict.keys():
            updated_record = {}
            if content_pack_id not in updated_content_pack_status_object_dict.keys():
                updated_record['_raw'] = '{} record deleted'.format(content_pack_id)
            else:
                updated_record = updated_content_pack_status_object_dict[content_pack_id]
                updated_record['_raw'] = '{} record updated with installed versions {}'.format(
                    content_pack_id,
                    updated_record[ContentPackFields.VERSION_INSTALLED]
                )
            updated_record['content_pack_id'] = content_pack_id
            updated_record['_time'] = time.time()
            yield updated_record

        conf_getargs = {
            'count': 0,
            'output_mode': 'json'
        }

        conf = get_content_packs_conf(
            getargs=conf_getargs,
            session_key=self._metadata.searchinfo.session_key
        )

        reader = ContentPackMetadataReader(
            logger=LOGGER,
            session_key=self._metadata.searchinfo.session_key
        )

        for entry in conf:
            try:
                updated_record = {}
                content_pack = reader.read(entry)
                saved_searches = retrieve_saved_search_count_details(self._metadata.searchinfo.session_key, content_pack[ContentPackFields.ID])
                updated_record['_raw'] = 'content_pack_name={} total_saved_Searches={} enabled_saved_searches={} disabled_saved_searches={}'.format(content_pack[ContentPackFields.ID], saved_searches['total'], saved_searches['enabled'], saved_searches['disabled'])
                updated_record['content_pack_name'] = content_pack[ContentPackFields.ID]
                updated_record['total_saved_searches'] = saved_searches['total']
                updated_record['enabled_saved_searches'] = saved_searches['enabled']
                updated_record['disabled_saved_searches'] = saved_searches['disabled']
                updated_record['_time'] = time.time()
                yield updated_record
            except JSONDecodeError as exc:
                LOGGER.error('Error while reading content pack entry="%s"', entry)
                LOGGER.exception(exc)
                yield exc

            except TypeError as exc:
                LOGGER.error('Error while reading content pack entry="%s"', entry)
                LOGGER.exception(exc)
                yield exc

            except FileNotFoundError as exc:
                LOGGER.error('Error while reading content pack entry="%s"', entry)
                LOGGER.exception(exc)
                yield exc

            except Exception as exc:
                LOGGER.error('Error while reading content pack entry="%s"', entry)
                LOGGER.exception(exc)
                yield exc


dispatch(ITSIContentPackStatusUpdateCommand, sys.argv, sys.stdin, sys.stdout, __name__)
