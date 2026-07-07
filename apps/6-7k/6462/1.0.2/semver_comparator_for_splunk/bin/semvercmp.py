#!/usr/bin/env python

import sys

import semver
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators


@Configuration()
class SemverCmpCommand(StreamingCommand):
    """ Compares two version numbers and outputs a comparison result """

    outputfield = Option(
        require=False,
        default="semver_result",
        validate=validators.Fieldname()
    )

    def stream(self, records):
        self.logger.debug("SemverCmpCommand: %s", self)

        if len(self.fieldnames) != 2:
            raise ValueError(f"Expected 2 fieldnames, {len(self.fieldnames)} given")

        field1 = self.fieldnames[0]
        field2 = self.fieldnames[1]

        for record in records:
            if not (field1 in record and field2 in record):
                continue

            try:
                value1 = semver.VersionInfo.parse(record[field1])
                value2 = semver.VersionInfo.parse(record[field2])
            except ValueError:
                continue

            record[self.outputfield] = value1.compare(value2)

            yield record

dispatch(SemverCmpCommand, sys.argv, sys.stdin, sys.stdout, __name__)
