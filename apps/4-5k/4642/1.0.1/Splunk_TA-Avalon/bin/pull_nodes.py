import json
import sys

from avalon import WorkspaceName
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from util import init_logger
from api import AvalonAPI, Workspace
from datetime import datetime


logger = init_logger('base.conf')


@Configuration()
class PullNodes(GeneratingCommand):
    id = Option(require=False, validate=validators.Integer())
    title = Option(require=False, validate=WorkspaceName())

    def generate(self):
        if not self.id and not self.title:
            raise RuntimeError('Must provide name or id.')
        avalon = AvalonAPI.from_config(
            self, '/configs/inputs/avalon_nodes')
        workspace = None
        if self.id:
            workspace = Workspace.get(avalon, self.id)
        else:
            workspaces = Workspace.list(avalon)
            for w in workspaces:
                if w['Title'] == self.title:
                    workspace = Workspace.get(avalon, w['id'])
                    self.id = w['id']
        if workspace is not None and 'data' in workspace:
            uuid = workspace['data']['attributes']['UUID']
            nodes = Workspace.get_nodes(avalon, self.id, uuid)
            input_nodes = []
            for node in nodes['data']:
                #input_nodes.append({'node': node[0], 'nodeType': node[1]})
                try:
                    input_nodes.append({'node': node['term'], 'nodeType': node['type'], 'attributes': node['attributes'], 'tags': node['tags']})
                except:
                    input_nodes.append({'node': node['term'], 'nodeType': node['type'], 'attributes': node['attributes']})
            if not input_nodes:
                raise RuntimeWarning('No nodes found for the given workspace')
            if 'avalon' in self.service.indexes:
                self.service.indexes['avalon'].submit(sourcetype='avalon_nodes', source='avalon',
                    event=json.dumps({
                        'workspace': workspace['data'],
                        'nodes': input_nodes,
                        'InsertDate': datetime.now().strftime("%Y-%m-%dT%I:%M:%S")
                    }))
            for node in nodes['data']:
                yield {'_raw': node}
        else:
            raise RuntimeError('Workspace not found')


if __name__ == '__main__':
    dispatch(PullNodes, sys.argv, sys.stdin, sys.stdout, __name__)

