import csv
import gzip
import json
import os
import sys
import urllib.parse
import urllib.request

from splunk.clilib import cli_common as cli

if __name__=="__main__":
    # Probably need some better error handling here but hard to predict what to expect here.
    raw_input = sys.stdin.read()
    ticketResults = json.loads(raw_input)

    restrictBoardId = ticketResults['configuration']['board_id']
    postToURI = ticketResults['configuration']['webhook_url']

    cwm_conf = cli.getConfStanza('connectwise', 'general');
    company_id = cwm_conf.get('company')

    if not os.path.exists(ticketResults['results_file']):
        sys.exit(0)

    with gzip.open(ticketResults['results_file'], 'rt') as results_file:
        csvResults = csv.DictReader(results_file)

        for row in csvResults:
            if row['boardId'] != restrictBoardId:
                continue

            post_data = {
                "text": "A new service ticket has been created.",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "New Service Ticket"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Summary*\n%s" % row['summary']
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Ticket Number*\n<https://na.myconnectwise.net/v4_6_release/services/system_io/Service/fv_sr100_request.rails?service_recid=%s&companyname=%s|#%s>" % (row['id'], company_id, row['id'])
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Opened*\n<!date^%s^{date_short} {time_secs}|%s>" % (row['dateEnteredEpoch'], row['dateEntered'])
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Priority*\n%s" % row['priorityName']
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Company*\n%s" % row['companyName']
                            }
                        ]
                    }
                ]
            }

            url_structure = urllib.parse.urlparse(postToURI)

            if url_structure.scheme != 'https':
                sys.exit(0)

            req = urllib.request.Request(postToURI, bytes(json.dumps(post_data), encoding='utf-8'))
            response = urllib.request.urlopen(req)
            # v = response.read()
