#!/usr/bin/env python

import sys
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators
from difflib import SequenceMatcher
import csv
    
DEFAULT_THRESHOLD = "80" #Between 0 and 100; 100 is identical strings
manufacturerLookup = '../lookups/bah_manufacturers.csv'

def getManufacturerList():
    manufacturerList = []
    manufacturerColumnFound = False
    
    try:
        with open(manufacturerLookup, 'rb') as csvfile:
            spamreader = csv.reader(csvfile)
            rowCounter = 0
            for row in spamreader:
                if (rowCounter == 0):
                    columnNumber = 0
                    for column in row:
                        if column == 'manufacturer':
                            manufacturerColumn = columnNumber
                            manufacturerColumnFound = True
                            continue
                        columnNumber += 1
                if manufacturerColumnFound:
                    manufacturerList.append(row[columnNumber])
                rowCounter += 1
        csvfile.close()
        if not manufacturerColumnFound:
            si.parseError('Column "manufacturer" not found in file: %s' % manufacturerLookup)
    except IOError as e:
        si.parseError('%s' % e)
    
    return manufacturerList

def similar(a, b):
    seq = SequenceMatcher(None, a.lower(), b.lower())
    return seq.ratio()*100
    
@Configuration()
class similarManufacturerCommand(StreamingCommand):
    """ %(synopsis)

    ##Syntax

    %(syntax)

    ##Description

    %(description)

    """    
    field = Option(
        doc='''
        **Syntax:** **field=***<field>*
        **Description:** Name of the field that holds the manufacturer to compare against''',
        require=True, validate=validators.Fieldname())

    threshold = Option(
        doc='''
        **Syntax:** **threshold=***<decimal>*
        **Description:** Threshold percentage to match''',
        require=False, validate=validators.Integer(), default=DEFAULT_THRESHOLD)

    def prepare(self):
        self.manufacturerList = getManufacturerList()
    
    def stream(self, records):
        self.logger.debug('similarManufacturerCommand: %s', self)  # logs command line
        field = self.field
        threshold = self.threshold
        for record in records:
            #Checking for multivalue in field
            self.logger.debug('record[self.field]: %s', record[self.field])
            if isinstance(record[self.field], (list,)):
                returnField = []
                for entry in record[self.field]:
                    found = False
                    for m in self.manufacturerList:
                        if similar(entry, m) > threshold:
                            found = True
                            returnField.append(m)
                    if (found == False):
                        returnField.append(entry)                    
                record[self.field] = returnField
                yield record
            else:
                for m in self.manufacturerList:
                    if similar(record[field], m) > threshold:
                        record[self.field] = m
                        yield record
                yield record

dispatch(similarManufacturerCommand, sys.argv, sys.stdin, sys.stdout, __name__)
