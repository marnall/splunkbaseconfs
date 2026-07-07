import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators

from splunk.clilib import cli_common as cli

from cwpsa import CWManage

@Configuration()
class connectWiseTicket(StreamingCommand):
    """ %(synopsis)

    ##Syntax

    %(syntax)

    ##Description

    %(description)

    """

    def stream(self, events):
        for event in events:
            createTicket = True
            error = []

            if not 'summary' in event:
                createTicket = False
                error.append("summary")

            if not 'initialDescription' in event:
                createTicket = False
                error.append("initialDescription")

            if not 'companyId' in event:
                createTicket = False
                error.append("companyId")

            if not 'contactId' in event:
                createTicket = False
                error.append("contactId")

            if not 'agreementId' in event:
                createTicket = False
                error.append("agreementId")

            if not 'boardId' in event:
                createTicket = False
                error.append("boardId")

            if not 'priorityId' in event:
                createTicket = False
                error.append("priorityId")

            if createTicket:
                payload = {
                    "summary": json.dumps(event['summary']),
                    "initialDescription": json.dumps(event['initialDescription']),
                    "board": {
                        "id": event['boardId']
                    },
                    "contact": {
                        "id": event['contactId']
                    },
                    "company": {
                        "id": event['companyId']
                    },
                    "priority": {
                        "id": event['priorityId']
                    },
                    "agreement": {
                        "id": event['agreementId']
                    }
                }

                cwm_conf = cli.getConfStanza('connectwise', 'general')

                company_id = cwm_conf.get('company')
                client_id = cwm_conf.get('clientId')
                public_key = cwm_conf.get('publicKey')
                api_version = cwm_conf.get('version')
                base_uri = cwm_conf.get('url')
                release = cwm_conf.get('release')

                service = self.service
                storage_passwords = service.storage_passwords

                credential_name = "connectWiseQuery:%s:" % public_key
                credential = False

                for storage_password in storage_passwords.list():
                    if storage_password.name == credential_name:
                        credential = storage_password
                        break

                private_key = credential['clear_password']

                endpoint = 'service/tickets'

                manage_api = CWManage(company_id, client_id, base_uri, release, api_version, endpoint, public_key, private_key)

                try:
                    manage_api.query(payload=payload)

                    if len(manage_api.events) > 0:
                        event['ticketNumber'] = manage_api.events[0]['id']
                except Exception as e:
                    event['error'] = "PSA Error: '%s'" % e.reason
            else:
                event['error'] = "Missing required fields: %s" % ', '.join(error)

            yield event


dispatch(connectWiseTicket, sys.argv, sys.stdin, sys.stdout, __name__)
