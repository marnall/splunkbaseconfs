#!/usr/bin/env python
"""Download ThreatConnect Owner Information Command"""
# standard library
import os
import sys
import uuid
from collections import OrderedDict

# third-party
from base_generating_command import BaseGeneratingCommand
from splunklib.searchcommands import Configuration, List, Option, dispatch


def generate_uuid_from_search(name, tql, owners, version):
    """Generate a UUID of a search."""
    identifier = f'{name} : {version}'
    if not version:
        identifiers = [name, tql, owners]
        identifier = ' : '.join(identifiers)
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, identifier))


@Configuration(retainsevents=True, streaming=False)
class ResetIOCCollectionsCommand(BaseGeneratingCommand):
    """Command to download and indicator from ThreatConnect API.

    Usage:
    | tcresetioccollections <collections>
    """
    # args
    collections = Option(doc='The collections to reset.', require=True, validate=List())

    # properties
    _command = 'tcresetioccollections'
    filename = os.path.basename(__file__)

    def generate(self):
        """Implement generate command for downloading owners."""
        # retrieve owner data from ThreatConnect
        def construct_result(name):
            r = OrderedDict()
            r['name'] = name
            r['found'] = False
            r['old_search_uuid'] = ''
            r['new_search_uuid'] = ''
            r['old_version'] = ''
            r['new_version'] = ''

            return r

        results = [construct_result(n) for n in self.collections]

        for ioc_collection_config in self.tcs.collections.ioc_collection.query():
            if ioc_collection_config.name in self.collections:
                old_search_uuid = ioc_collection_config.search_uuid
                if 'version' in ioc_collection_config:
                    old_version = ioc_collection_config.version
                else:
                    old_version = 'N/A'

                ioc_collection_config['version'] = str(uuid.uuid4())
                ioc_collection_config['dirty'] = True
                ioc_collection_config['search_uuid'] = generate_uuid_from_search(
                    ioc_collection_config.name,
                    ioc_collection_config.tql,
                    ioc_collection_config.owners,
                    ioc_collection_config.version,
                )

                self.tcs.collections.ioc_collection.update(
                    ioc_collection_config._key,
                    ioc_collection_config
                )

                result = [r for r in results if r['name'] == ioc_collection_config.name][0]

                result['found'] = True
                result['old_search_uuid'] = old_search_uuid
                result['new_search_uuid'] = ioc_collection_config.search_uuid
                result['old_version'] = old_version
                result['new_version'] = ioc_collection_config.version

        yield from results

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
           return



if __name__ == '__main__':
    try:
        dispatch(ResetIOCCollectionsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
    except Exception:
        # standard library
        import traceback
        print(traceback.format_exc(), file=sys.stderr)
