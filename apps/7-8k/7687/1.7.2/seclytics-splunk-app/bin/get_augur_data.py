#!/usr/bin/env python

import os
import sys
from csv import DictReader

from augur_command import AugurCommand
from seclytics import BulkDownload
from splunklib.searchcommands import Configuration, GeneratingCommand, Option, dispatch


@Configuration(type="reporting", distributed=False, local=True)
class GetAugurDataCommand(GeneratingCommand, AugurCommand):
    """Use Search Command V2 protocol."""

    bulk_name = Option(require=True)

    @property
    def file_data(self):
        """Load existing data.

        This is just a failsafe in case the download fails.
        """
        # if there is there an error keep the old data
        self.logger.info("Load existing: %s", self.bulk_name)
        bin_dir = os.path.dirname(os.path.realpath(__file__))
        data_dir = os.path.abspath(os.path.join(bin_dir, os.pardir, "lookups"))
        lookup_name = self.bulk_name.replace("private/", "")

        with open(os.path.join(data_dir, lookup_name)) as file_handle:
            reader = DictReader(file_handle)
            for row in reader:
                yield row

    @property
    def download_data(self):
        """Download data from the augur bulk api."""
        self.logger.info("Download data for: %s", self.bulk_name)
        bin_dir = os.path.dirname(os.path.realpath(__file__))
        data_dir = os.path.abspath(os.path.join(bin_dir, os.pardir, "lookups"))
        full_path = "/bulk/" + self.bulk_name
        bulk_download = BulkDownload(self.augur_api, full_path, data_dir=data_dir)
        r = bulk_download.api_reponse
        lines = (line.decode("utf-8") for line in r.iter_lines())
        reader = DictReader(lines)
        for row in reader:
            yield row

    def generate(self):
        """Load the new loookup data.

        Since the output of this method overrides the lookup table, we should
        fail by reading the existing file.
        """
        try:
            for row in self.download_data:
                yield row
        except Exception as exception:
            self.logger.error("Could not download data: %s", str(exception))
            # Read from existing if error
            for row in self.file_data:
                yield row


dispatch(GetAugurDataCommand, sys.argv, sys.stdin, sys.stdout, __name__)
