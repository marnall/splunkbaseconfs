import base64
import datetime
import json
import re
import urllib.request

class CWManage:
    def __init__(self, company_id, client_id, base_uri, release, api_version, endpoint, public_key, private_key):
        auth_string = "%s+%s:%s" % (company_id, public_key, private_key)
        auth_header = base64.b64encode(auth_string.encode()).decode()

        self.construct_headers(auth_header, client_id)
        self.base_uri = "https://%s/%s/apis/%s/%s" % (base_uri, release, api_version, endpoint)
        self.checkpoint = ''
        self.lastId = 0
        self.events = []
        self.uri = ''

    def construct_headers(self, auth_header, client_id):
        self.headers = {
            'Authorization': "Basic %s" % auth_header,
            'clientId': client_id,
            'Content-Type': 'application/json'
        }

    def query(self, uri=False, offset=False, payload=False):
        if uri:
            request_uri = uri
        else:
            request_uri = self.base_uri + ("?conditions=lastUpdated>[%s]" % offset if offset else '' )

        self.uri = request_uri

        if payload:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(request_uri, headers=self.headers, data=data)
        else:
            req = urllib.request.Request(request_uri, headers=self.headers)

        with urllib.request.urlopen(req) as response:
            next_page = False
            response_headers = response.getheaders()

            for header in response_headers:
                if header[0] == 'Link':
                    links = header[1].split(', ')

                    for link in links:
                        link_details = re.match( r'<(?P<link_uri>[^>]+)>;\srel="(?P<link_rel>[^"]+)"', link)

                        if link_details and link_details.group('link_rel') == 'next':
                            next_page = True
                            next_uri = link_details.group('link_uri')

            events = json.loads(response.read())

            if not payload:
                for event in events:
                    output_event = self.flatten_event(event)

                    self.events.append(output_event)

                    if 'lastUpdated' in output_event:
                        self.set_checkpoint(output_event['id'], output_event['lastUpdated'])
            else:
                self.events.append(events)

        if next_page:
            self.query(next_uri)

    def flatten_event(self, event):
        flat_event = {}

        for key, value in event.items():
            if type(value) is dict and 'id' in value:
                flat_event["%sId" % key] = value['id']
            elif type(value) is dict and key=='_info':
                if 'lastUpdated' in value:
                    flat_event['lastUpdated'] = value['lastUpdated']

                if 'updatedBy' in value:
                    flat_event['updatedBy'] = value['updatedBy']

                if 'dateEntered' in value:
                    flat_event['dateEntered'] = value['dateEntered']

                if 'enteredBy' in value:
                    flat_event['enteredBy'] = value['enteredBy']
            elif type(value) is list and key=='customFields':
                for customField in value:
                    if 'caption' in customField and 'value' in customField:
                        flat_event['c%s' % re.sub('\W', '', customField['caption'])] = customField['value']
            else:
                if key != 'notes' and key !='signature':
                    # These cause significant truncation issues if HTML formamtting is present.
                    flat_event[key] = value

        return flat_event

    def set_checkpoint(self, event_id, timestamp):
        if not self.checkpoint:
            self.checkpoint = timestamp
        else:
            checkpoint = datetime.datetime.strptime(self.checkpoint, '%Y-%m-%dT%H:%M:%S%z')
            event_time = datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S%z')

            if event_time > checkpoint:
                self.checkpoint = timestamp

        if not self.lastId:
            self.lastId = event_id
        else:
            if event_id > self.lastId:
                self.lastId = event_id
