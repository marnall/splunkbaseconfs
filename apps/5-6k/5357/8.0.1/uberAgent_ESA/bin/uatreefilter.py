#!/usr/bin/env python

# Backports from Python 3.x to 2.x
# Probably not required by us, the the Splunk Python SDK uses them, so we adjust
from __future__ import absolute_import, division, print_function, unicode_literals

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option, validators 

#
# Python 2/3 compatibility for which no __future__ imports are available
# Splunk 7.2.3 uses Python 2.7.15
#
try:
    # Python 2
    range = xrange
except NameError:
    # Python 3
    pass


@Configuration()
class uATreeFilterCommand(EventingCommand):
    rootId = Option(
        doc='''
      **Syntax:** **rootId=***<ID>*
      **Description:** ID of the tree root item''')
    idField = Option(
        doc='''
      **Syntax:** **idField=***<fieldname>*
      **Description:** Name of the field that holds the item's ID''',
        require=True, validate=validators.Fieldname())
    parentIdField = Option(
        doc='''
      **Syntax:** **parentIdField=***<fieldname>*
      **Description:** Name of the field that holds the item's parent ID''',
        require=True, validate=validators.Fieldname())
    startField = Option(
        doc='''
      **Syntax:** **startField=***<fieldname>*
      **Description:** Name of the field that holds the item's start/creation time''',
        require=True, validate=validators.Fieldname())
    childCountField = Option(
        doc='''
      **Syntax:** **childCountField=***<fieldname>*
      **Description:** Name of the field that will hold the item's child count''')
    childCountRecursiveField = Option(
        doc='''
      **Syntax:** **childCountRecursiveField=***<fieldname>*
      **Description:** Name of the field that will hold the item's recursive child count''')
    typeField = Option(
        doc='''
      **Syntax:** **typeField=***<fieldname>*
      **Description:** Name of the field that holds the item's type''')

    #
    # Function called by the Python SDK when the command is run
    #
    def transform(self, records):
        rootId = self.rootId
        idField = self.idField
        parentIdField = self.parentIdField
        startField = self.startField
        childCountField = self.childCountField
        childCountRecursiveField = self.childCountRecursiveField
        typeField = self.typeField

        # Build a list from all records
        recordList = list(records)

        # No ID given and no child count requested, either -> do nothing
        if (not rootId) and (not childCountField) and (not childCountRecursiveField):
            return recordList

        # Use the following for logging to search.log:
        # self.logger.error('message: %s', variable)

        if len(recordList) == 0:
            return recordList

        # Stop with meaningful error messages (displayed in Splunk's UI) if required fields are missing
        # The parentIdField may be missing (at least for some records). Those records are ignored.
        if idField not in recordList[0]:
            raise Exception(
                'The field <%s> was specified as <idField> in the search but is missing in the results' % idField)
        if startField not in recordList[0]:
            raise Exception(
                'The field <%s> was specified as <startField> in the search but is missing in the results' % startField)

        # Sort by start/creation time
        recordList.sort(key=lambda x: x[startField])

        # Build a dictionary of all IDs we are interested in
        # The value holds the direct children we found
        if rootId:
            # Only children of the root ID
            idsChildren = {rootId: 0}
            for record in recordList:
                if not parentIdField in record:
                    # The parent ID field is missing in this record -> ignore
                    continue

                if record[parentIdField] in idsChildren:
                    if record[typeField] != 'Exec':
                        # The parent has a new child
                        idsChildren[record[parentIdField]] += 1
                    # The child starts with zero children of its own
                    idsChildren[record[idField]] = 0
        else:
            idsChildren = {}
            for record in recordList:
                if not parentIdField in record:
                    # The parent ID field is missing in this record -> ignore
                    continue
                
                # The parent has a new child
                if record[parentIdField] in idsChildren:
                    if record[typeField] != 'Exec':
                        # The parent has a new child
                        idsChildren[record[parentIdField]] += 1
                else:
                    idsChildren[record[parentIdField]] = 1
                # The child starts with zero children of its own
                idsChildren[record[idField]] = 0

        idsChildrenRec = {}
        if childCountRecursiveField:
            # Determine children recursively (including grandchildren etc.) by iterating backwards and counting
            for i in range(len(recordList) - 1, -1, -1):
                record = recordList[i]

                if not parentIdField in record:
                    # The parent ID field is missing in this record -> ignore
                    continue
            
                # Get the child count of the current record
                currentItemChildCount = 0
                if record[idField] in idsChildren:
                    currentItemChildCount = idsChildren[record[idField]]

                # Check if we have an entry for the current ID in the recursive count dict
                if not record[idField] in idsChildrenRec:
                    # No recursive entry yet. Initialize with its own direct child count
                    if record[typeField]:
                        idsChildrenRec[record[idField]] = currentItemChildCount
                else:
                    # There is a recursive entry already (with grandchildren count). Add the direct children if not a exec.
                    if record[typeField] != 'Exec':
                        idsChildrenRec[record[idField]] += currentItemChildCount

                # Check if we have an entry for the current parent ID in the recursive count dict
                if not record[parentIdField] in idsChildrenRec:
                    # The parent starts with the recursive child count of the current item
                    if record[typeField] != 'Exec':
                        idsChildrenRec[record[parentIdField]] = idsChildrenRec[record[idField]]
                else:
                    # The parent gets the recursive child count of the current item, too
                    if record[typeField] != 'Exec':
                        idsChildrenRec[record[parentIdField]] += idsChildrenRec[record[idField]]

        # Iterate over the list, removing items that are not in the dictionary we just built
        # Make sure this happens without creating a copy of the list
        for i in range(len(recordList) - 1, -1, -1):
            record = recordList[i]
            if not record[idField] in idsChildren:
                del recordList[i]
            else:
                if childCountField:
                    record[childCountField] = idsChildren[record[idField]]
                if record[idField] in idsChildrenRec:
                    if childCountRecursiveField:
                        record[childCountRecursiveField] = idsChildrenRec[record[idField]]

        # Return the filtered and sorted list
        return recordList


if __name__ == "__main__":
    dispatch(uATreeFilterCommand, sys.argv, sys.stdin, sys.stdout, __name__)
