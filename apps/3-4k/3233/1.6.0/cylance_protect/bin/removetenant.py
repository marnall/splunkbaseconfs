'''
Description:
    Splunk Custom Command to remove tenant-related files from local filesystem

Authors:
    Peter Uys, Cylance Inc.
'''


import glob
import os
import sys
import time

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


def remove_tenant_files(tenant_name):
    start_dir = os.getcwd()
    local_dir = os.path.join(start_dir, "..", "local")
    file_types = ['devices', 'events',  'indicators', 'threats']
    file_names = []

    for file_type in file_types:
        file_name = os.path.join(tenant_name + '-' + file_type)
        file_names.append(file_name + '.csv')
        file_names.append(file_name + '.sha')

    msg = ''
    os.chdir(local_dir)
    for name in glob.glob("*"):
        if name in file_names:
            try:
                os.remove(os.path.join(local_dir, name))
                file_names.remove(name)
            except Exception as e:
                msg += str(e) + os.linesep

    os.chdir(start_dir)
    if msg:
        return msg
    else:
        return 'Success'


@Configuration()
class RemoveTenantCommand(GeneratingCommand):

    tenantname = Option(require=True)

    def generate(self):

        result = remove_tenant_files(self.tenantname)
        yield {'Result': result }


dispatch(RemoveTenantCommand, sys.argv, sys.stdin, sys.stdout, __name__)
