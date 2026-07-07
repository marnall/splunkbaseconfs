#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Splunk specific dependencies
import sys, os, glob

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))  # Much cleaner than put splunklib in bin
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators, splunklib_logger as logger


@Configuration(type='reporting')
class fileinfoCommand(GeneratingCommand):
    filepath = Option(require=True)

    def generate(self):
        try:
            file_list = glob.glob(self.filepath)
            if len(file_list) == 0:
                yield ({"Error":"File not found"})
            for file in file_list:
                record = {}
                try:
                    file_info = os.stat(file)
                    record['file_mode'] = oct(file_info.st_mode)[-3:]
                    record['file_ino'] = file_info.st_ino
                    record['file_dev'] = file_info.st_dev
                    record['file_nlink'] = file_info.st_nlink
                    record['file_uid'] = file_info.st_uid
                    record['file_gid'] = file_info.st_gid
                    record['file_size_bytes'] = file_info.st_size
                    record['file_modification_time'] = file_info.st_mtime
                    record['file_most_recent_access_time'] = file_info.st_atime
                    record['file_metadata_change_time'] = file_info.st_ctime
                    record['file_fullpath'] = file
                except Exception as err:
                    record = ({"Error": err})
                
                yield record

        except Exception as err:
            record = ({"Error:": err})
            yield record


dispatch(fileinfoCommand, sys.argv, sys.stdin, sys.stdout, __name__)
