#!usr/bin/env python2
import sys
import json
from datetime import datetime, timedelta
from splunklib.modularinput import Script, Scheme, Argument, Event
from splunknova import Client


class SplunkNovaInput(Script):
    def get_scheme(self):
        scheme = Scheme('Splunk Nova Modular Input')
        scheme.description = 'Indexes events from Splunk Nova'

        scheme.add_argument(Argument('client_id', title='Nova Client ID',
                                     data_type=Argument.data_type_string,
                                     required_on_create=True))
        scheme.add_argument(Argument('client_secret', title='Nova Client Secret',
                                     data_type=Argument.data_type_string,
                                     required_on_create=True))
        scheme.add_argument(Argument('search', title='Search string',
                                     description='* returns all events',
                                     data_type=Argument.data_type_string,
                                     required_on_create=True))
        scheme.add_argument(Argument('checkpoint', title='Checkpoint time',
                                     description='Splunk timespec to track which events have already been '
                                                 'ingested. Can leave blank to get all events on the first run, '
                                                 'or use Splunk timespecs like "2/20/2018:16:30:00", "-mon", or "@d" '
                                                 'to control how much history is ingested. This value is updated '
                                                 'automatically by the input as it gathers new data.',
                                     data_type=Argument.data_type_string,
                                     required_on_create=False))
        scheme.add_argument(Argument('entity_is_host', title='Entity = Host',
                                     description='Use the Nova "entity" field to populate the Splunk "host" field. '
                                                 'Otherwise, it uses the host value specified under "More Options".',
                                     data_type=Argument.data_type_boolean,
                                     required_on_create=True))

        return scheme

    @staticmethod
    def parse_nova_timestamp(time):
        return datetime.strptime(time, '%Y-%m-%dT%H:%M:%S.%f+00:00')

    @staticmethod
    def format_splunk_timestamp(time):
        return time.strftime('%m/%d/%Y:%H:%M:%S')

    def update_checkpoint(self, name, item, checkpoint):
        new_checkpoint = checkpoint + timedelta(seconds=1)
        serv_inputs = self.service.inputs
        for input_item in serv_inputs:
            if unicode(input_item.kind) + '://' + input_item.name == name:
                input_item.update(checkpoint=self.format_splunk_timestamp(new_checkpoint))

    def stream_events(self, inputs, ew):
        for name, item in inputs.inputs.iteritems():
            nova = Client(item['client_id'], item['client_secret'])
            if 'checkpoint' in item and item['checkpoint'] != '' and item['checkpoint'] is not None:
                search = nova.events.search(item['search'], earliest=item['checkpoint'])
            else:
                search = nova.events.search(item['search'])
            latest_timestamp = datetime(1970, 1, 1)
            for evt in search.iter_events():
                time = self.parse_nova_timestamp(evt['time'])
                if time >= latest_timestamp:
                    latest_timestamp = time
                e = Event()
                e.stanza = name
                e.source = evt['source']
                e.data = json.dumps(evt)
                e.time = time.strftime('%s')
                if item['entity_is_host'] in ['true', True, 1, '1']:
                    e.host = evt['entity']
                ew.write_event(e)
            if latest_timestamp != datetime(1970, 1, 1):
                self.update_checkpoint(name, item, latest_timestamp)


if __name__ == '__main__':
    sys.exit(SplunkNovaInput().run(sys.argv))
