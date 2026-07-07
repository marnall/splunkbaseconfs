import itertools
import json
import re
import sys
import time

from splunklib import searchcommands as sc

from api import AvalonAPI, Workspace
from util import init_logger


logger = init_logger('base.conf')


class WorkspaceName(sc.validators.Validator):
    def __call__(self, value):
        if value and not re.match(r'[\w\-]+', value):
            raise ValueError(
                'Workspace name uses illegal characters.')
        return value

    def format(self, value):
        return value


@sc.Configuration()
class Avalon(sc.StreamingCommand):
    create_workspace = sc.Option(require=False, validate=WorkspaceName())
    update_workspace = sc.Option(require=False, validate=WorkspaceName())

    def _find_workspace(self, avalon, title):
        """Find a workspace given its `title`."""
        workspaces = Workspace.list(avalon)
        matching_workspaces = [w for w in workspaces if w['Title'] == title]
        return matching_workspaces

    def stream(self, records):
        if not self.create_workspace and not self.update_workspace:
            raise RuntimeError('No Avalon workspace specified.')

        # Duplicate records generator to preserve its state
        records_return, records_local = itertools.tee(records)
        nodes = [vs for record in records_local
                 for k, vs in list(record.items()) if vs and not k.startswith('_')]
        if not nodes:
            raise RuntimeError('No events were sent to the command.')
        avalon = AvalonAPI.from_config(
            self, '/configs/inputs/avalon_nodes')
        if self.create_workspace:
            workspace_title = self.create_workspace
            workspace_id = Workspace.create(avalon, workspace_title)
            Workspace.add_nodes(avalon, workspace_id, nodes)
        elif self.update_workspace:
            try:
                workspace_id = int(self.update_workspace)
                if 'errors' in Workspace.get(avalon, workspace_id):
                    raise RuntimeError(
                        'No workspace was found given the ID "{}".'
                        .format(self.update_workspace))
            except ValueError:
                workspaces = self._find_workspace(
                    avalon, self.update_workspace)
                if len(workspaces) > 1:
                    raise RuntimeError(
                        'Multiple workspaces exist with the given title "{}".'
                        .format(self.update_workspace))
                elif len(workspaces) == 0:
                    raise RuntimeError(
                        'No workspace was found given the title "{}".'.format(
                            self.update_workspace))
                workspace_id = sorted(
                    workspaces, key=lambda w: w['id'])[-1]['id']
            Workspace.add_nodes(avalon, workspace_id, nodes)

        if 'avalon' in self.service.indexes:
            workspace_data = Workspace.get(avalon, workspace_id)['data']
            workspace_attrs = workspace_data['attributes']
            self.service.indexes['avalon'].submit(
                json.dumps({
                    #'_time': time.time(),
                    'id': workspace_data['id'],
                    'CreatedDate': workspace_attrs['CreatedDate'],
                    'Nodes': nodes,
                    'NumNodes': len(set(nodes)),
                    'Title': workspace_attrs['Title'],
                }),
                source='avalon',
                sourcetype='avalon_push',
            )

        # Return the records to the search
        for record in records_return:
            yield record


if __name__ == "__main__":
    sc.dispatch(Avalon, sys.argv, sys.stdin, sys.stdout, __name__)

