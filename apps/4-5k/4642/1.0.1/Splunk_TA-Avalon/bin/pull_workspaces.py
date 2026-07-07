import os
import sys
import time

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration
from util import init_logger
from api import AvalonAPI, Workspace


logger = init_logger('base.conf')


@Configuration()
class PullWorkspaces(GeneratingCommand):

    def generate(self):
        avalon = AvalonAPI.from_config(
            self, 'configs/inputs/avalon_nodes')
        workspaces = Workspace.list(avalon)
        if hasattr(time, 'tzset'):
            os.environ['TZ'] = 'UTC' # Avalon datetimes in UTC
            time.tzset()
        for workspace in workspaces:
            output = {
                'Title': workspace['Title'],
                'id': workspace['id'],
                'CreatedDate': workspace['CreatedDate']
            }
            creation_time = time.mktime(time.strptime(
                workspace['CreatedDate'].split('.')[0][:-1],
                '%Y-%m-%dT%H:%M:%S'))
            output['_time'] = creation_time
            yield output


if __name__ == '__main__':
    dispatch(PullWorkspaces, sys.argv, sys.stdin, sys.stdout, __name__)

