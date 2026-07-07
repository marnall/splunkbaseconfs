#!/usr/bin/env python
# coding=utf-8

from __future__ import absolute_import, division, print_function, unicode_literals
import time
import sys
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.client import KVStoreCollection, KVStoreCollectionData
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


@Configuration(local=True)
class CleanTimeKVGeneratingCommand(GeneratingCommand):
    collection = Option(
        doc='''
        **Syntax:** **hash=***collection*
        **Description:** Name of the collection to be affected''',
        require=True)

    timestamp_field = Option(
        doc='''
            **Syntax:** **timestamp_field=***<fieldname>*
            **Description:** The ''',
        require=True)

    maxage = Option(
        doc='''
                **Syntax:** **maxage=*** The maximum age to keep. In seconds. *
                **Description:** The ''',
        require=True, validate=validators.Integer(0))

    def generate(self):
        """
        Hooking point for splunk.
        :return: yields events one at a time
        """

        self.logger.debug('CleanTimeKV: %s', self)  # logs command line

        collection = self.collection
        try:
            collection = self.service.kvstore[collection]  # type: KVStoreCollection
        except KeyError:
            self.error_exit(None, "CleanTimeKV: Could not find collection: '%s'" % self.collection)

        coll_fields = {}
        for k, v in collection.content.items():
            if k.startswith('field.'):
                coll_fields[k[6:]] = v

        if self.timestamp_field not in coll_fields:
            self.error_exit(None, "CleanTimeKV: Collection '%s' does not have a field named '%s'."
                            % (self.collection, self.timestamp_field))

        if coll_fields[self.timestamp_field].strip() != "int" \
                and coll_fields[self.timestamp_field].strip() != "time":
            self.error_exit(None, "CleanTimeKV: Field '%s' in collection '%s' is of type '%s', expected 'int' or 'time'."
                            % (self.timestamp_field, self.collection, coll_fields[self.timestamp_field]))

        data = collection.data  # type: KVStoreCollectionData

        age = int(time.time()) - self.maxage
        clean_query = {self.timestamp_field: {"$lte": age}}
        clean_query = json.dumps(clean_query)
        out = data.delete(clean_query)

        out_body = out['body'].readall()

        raw = out_body if len(out_body) > 5 else out

        yield {'_time': time.time(), "_raw": str(raw), 'response': str(out), 'response_body': str(out_body)}


dispatch(CleanTimeKVGeneratingCommand, sys.argv, sys.stdin, sys.stdout, __name__)
