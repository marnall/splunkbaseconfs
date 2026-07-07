# encoding = utf-8
from __future__ import print_function

import sys
import json
import csv
from io import StringIO
from datetime import datetime
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

from splunk.persistconn.application import PersistentServerConnectionApplication
from logger import Logger
from common import Common
from service.app_kvstore_service import KVStoreService
from validator import cummulative_validator
from exceptions import InvestigatereportDownloadException
from global_org_client import GlobalOrgClient

sys.path.append(dirname(abspath(__file__)))

cisco_investigate_domains = None
cisco_investigate_ips = None
cisco_investigate_hashes = None
cisco_investigate_urls = None

class DownloadInvestigateReport(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        """This is constructor of class DownloadInvestigateReport."""

        PersistentServerConnectionApplication.__init__(self)
        
    # Flatten function to handle nested dictionaries
    def flatten_dict(self, data, parent_key='', sep='_'):
        items = []
        for key, val in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            if isinstance(val, dict):
                items.extend(self.flatten_dict(val, new_key, sep=sep).items())
            elif isinstance(val, list):
                # Convert lists to a comma-separated string
                items.append((new_key, ', '.join(map(str, val))))
            else:
                items.append((new_key, val))
        return dict(items)

    def handle(self, in_string):
        """This is cloud_security_dashboard_api_client handler."""
        try:
            response = []
            params = Common().parse_in_string(in_string)
            session_token = params['session']['authtoken']
            org_id = GlobalOrgClient(session_token).global_org
            field_type = params["query"]['field_type']
            report_name = params["query"]['report_name']
            if not (field_type or report_name ):
                raise InvestigatereportDownloadException(error_code=400,
                                    error_msg="field type and report name are required fields")
            if field_type == "domain":
                global cisco_investigate_domains
                if not cisco_investigate_domains:
                    cisco_investigate_domains = KVStoreService('cisco_investigate_domains', session_token)
                main_response = json.loads(cisco_investigate_domains.query_items('cisco_investigate_domains', session_token, 
                                                          query_conditions={"Report_name": report_name, "orgId": org_id}))
            elif field_type == "ip":
                global cisco_investigate_ips
                if not cisco_investigate_ips:
                    cisco_investigate_ips = KVStoreService('cisco_investigate_ips', session_token)
                main_response = json.loads(cisco_investigate_ips.query_items('cisco_investigate_ips', session_token, 
                                                          query_conditions={"Report_name": report_name, "orgId": org_id}))
            elif field_type == "hash":
                global cisco_investigate_hashes
                if not cisco_investigate_hashes:
                    cisco_investigate_hashes = KVStoreService('cisco_investigate_hashes', session_token)
                main_response = json.loads(cisco_investigate_hashes.query_items('cisco_investigate_hashes', session_token, 
                                                          query_conditions={"Report_name": report_name, "orgId": org_id}))
            elif field_type == "url":
                global cisco_investigate_urls
                if not cisco_investigate_urls:
                    cisco_investigate_urls = KVStoreService('cisco_investigate_urls', session_token)
                main_response = json.loads(cisco_investigate_urls.query_items('cisco_investigate_urls', session_token, 
                                                          query_conditions={"Report_name": report_name, "orgId": org_id}))                                       
            if not main_response:
                raise InvestigatereportDownloadException(error_code=400,
                                    error_msg="There is no data for selected report")
            # Flatten the data
            flattened_data = [self.flatten_dict(item) for item in main_response]
            # Collect field names (CSV headers)
            fieldnames = set()
            for item in flattened_data:
                fieldnames.update(item.keys())
            fieldnames = sorted(fieldnames)
            Logger().info("API: download_investigate_report, Report generated successfully for report_name: {0}, org_id: {1}".format(report_name, org_id))
            # Create the CSV in-memory
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(flattened_data)

            # Resetting the buffer to the start
            output.seek(0)
            headers = [('Content-Type', 'application/octet-stream'),
                        ('Content-Disposition', f'attachment; filename={report_name}_{org_id}.csv')]
            return {'payload': output.getvalue(),  
                    'status': 200,
                    'headers': headers}
        except InvestigatereportDownloadException as e:
            Logger().error("API: download_investigate_report, Exception : {0}".format(str(e)))
            return {"payload": {"error_msg": e.error_msg}, "status": e.error_code}
        except Exception as e:
            Logger().error("API: download_investigate_report, Exception : {0}".format(str(e)))
            return {"payload": {"error_msg": str(e)}, "status": 500}
