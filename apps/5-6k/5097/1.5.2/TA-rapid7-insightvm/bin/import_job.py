import time
import datetime

import event_utils  
import api_client
import date_utils

LAST_ASSESSED_FOR_VULNERABILITIES = "last_assessed_for_vulnerabilities"
LAST_SCAN_END = "last_scan_end"
CACHE_MAX_SIZE = 10000

__all__ = ['ImportJob',
           'AssetImportJob']

class ImportJob(object):

    def __init__(self, helper, ew, endpoint, is_initial_import):
        self.helper = helper
        self.ew = ew
        self.event_utils = event_utils.EventUtils(helper)
        self.endpoint = endpoint
        self.is_initial_import = is_initial_import
        self.vuln_dict = {"num_processed":0}

        # Generate api object from region and api key
        ivm_conn = helper.get_arg("insightvm_connection")
        region = ivm_conn.get("region")
        api_key = ivm_conn.get("api_key")
        proxy = helper.get_proxy()
        self.api = api_client.APIv4(api_key, region, proxy, helper)

    def start(self, payload, *args, **kwargs):
        return self.api.send_req(self.endpoint, payload, self.extract_info)

    def extract_info(self, response, *args, **kwargs):
        data = response["data"]
        
        for item in data:
            event = self.event_utils.create_event(item, self.helper.get_sourcetype())

            try:
                self.ew.write_event(event)
            except Exception as e:
                self.helper.log_error("Error processing {}: {}".format(self.endpoint, e))
        
        self.vuln_dict["num_processed"] = len(data)
        return self.vuln_dict

class AssetImportJob(ImportJob):

    def __init__(self, helper, ew, endpoint, is_initial_import, is_save_last_scan=False, is_save_last_assessed=False, 
        is_cache_imports=False, excluded_events={}, is_import_vulns=False, is_include_same=False):
        
        super(AssetImportJob, self).__init__(helper, ew, endpoint, is_initial_import)
        self.is_save_last_scan = is_save_last_scan
        self.is_save_last_assessed = is_save_last_assessed
        self.is_cache_imports = is_cache_imports
        self.excluded_events = excluded_events
        self.last_scan_end_date = None
        self.last_assessed_date = None
        self.imported_asset_cache = {}
        self.is_import_vulns = is_import_vulns
        self.is_include_same = is_include_same
        self.vuln_dict = {"vuln_processed_new":0, "vuln_processed_remediated":0, "vuln_processed_same":0, "total_vuln_processed":0, "num_processed":0}
    
    def start(self, payload, current_time, comparison_time, *args, **kwargs):
        self.helper.log_info("Pulling details from InsightVM API to process assets; "
                             "Input name: {}, Current time: {}, Comparison time: {}, Asset filter: {}, Vulnerability "
                             "filter: {}".format(self.helper.get_input_stanza_names(), current_time, comparison_time, 
                             payload.get("asset"), payload.get("vulnerability")))

        success = self.api.send_req(self.endpoint, payload, self.extract_info, current_time, comparison_time, self.is_import_vulns,
            self.is_include_same)
        
        self.helper.log_info("Total vulnerability findings processed: {}".format(self.vuln_dict.get('total_vuln_processed')))
        self.helper.log_info("New vulnerability findings processed: {}".format(self.vuln_dict.get('vuln_processed_new')))
        self.helper.log_info("Remediated vulnerability findings processed: {}".format(self.vuln_dict.get('vuln_processed_remediated')))
        self.helper.log_info("Same vulnerability findings processed: {}".format(self.vuln_dict.get('vuln_processed_same')))

        return success

    def extract_info(self, response, *args, **kwargs):
        last_scan_end_page = None
        last_assessed_page = None
        data = response["data"]
        excluded_count = 0
        
        for item in data:
            same_vulns = item.pop("same", []) if self.is_include_same else []
            new_vulns = item.pop("new", [])
            remediated_vulns = item.pop("remediated", [])

            # When the asset id appears in the list of excluded ids it will not be imported.
            if self.is_excluded_event(item):
                self.helper.log_debug("Skipping asset {} which is on the excluded_ids list".format(item.get("id")))
                excluded_count = excluded_count + 1
                continue

            if self.is_import_vulns:
                self.vulnerability_finding_events(new_vulns, remediated_vulns, same_vulns, item, self.vuln_dict)

            event = self.event_utils.create_event(item, self.helper.get_sourcetype())

            try:                
                self.ew.write_event(event)

                if self.is_import_vulns:
                    self.helper.log_debug("Asset={} imported: new={}, remediated={}, found={}, last_scan={}, last_assessed={}".format(item.get("id"), 
                        len(new_vulns), len(remediated_vulns), len(same_vulns), item.get("last_scan_end"), item.get("last_assessed_for_vulnerabilities")))

                # Cache the asset IDs that are imported. This is useful when multiple jobs are executed in a single run 
                # and it's necessary to dedupe the events between the jobs. Intended  to be used with partial imports.
                if self.is_cache_imports:
                    self.cache_item(item)

                # Save the most recent last_scan_end from this page.
                if self.is_save_last_scan: 
                    last_scan_end_curr = date_utils.string_to_datetime(item.get(LAST_SCAN_END), item.get("id"), self.helper.log_warning)
                    if last_scan_end_curr is not None: 
                        last_scan_end_page = last_scan_end_curr if last_scan_end_page is None else max(last_scan_end_page, 
                            last_scan_end_curr)

                # Save the most recent last_assessed_for_vulnerabilities from this page.
                if self.is_save_last_assessed:
                    # The initial import will return all assets from scans and agent collections. The most recent
                    # last_assessed_for_vulnerabilities may be from a scanned asset, where as intention of using 
                    # last_assessed_for_vulnerabilities is to import agent collections (that have a configurable delay 
                    # of 1-12 hours before syncing to the console). To avoid setting a more recent 
                    # last_assessed_for_vulnerabilities from a scan, than an older one from an agent collection only
                    # set it during the initial pull if the asset hasn't been scanned. Subsequent imports will only 
                    # return agent assets so it can be set even if there is a scan date.
                    if self.is_initial_import and item.get(LAST_SCAN_END) is not None:
                        continue

                    last_assessed_curr = date_utils.string_to_datetime(item.get(LAST_ASSESSED_FOR_VULNERABILITIES), item.get("id"), self.helper.log_warning)
                    if last_assessed_curr is not None: 
                        last_assessed_page = last_assessed_curr if last_assessed_page is None else max(last_assessed_page, 
                            last_assessed_curr)

            except Exception as e:
                self.helper.log_error("There was an error inserting an asset event into the index")
                self.helper.log_error("Error processing {}: {}".format(self.endpoint, e))
        
        # Update the most recent last_scan_end found for this import job.
        if last_scan_end_page is not None:
            self.helper.log_info("Most recent last_scan_end_date at the start of processing page {}".format(self.last_scan_end_date))
            self.last_scan_end_date = last_scan_end_page if self.last_scan_end_date is None else max(self.last_scan_end_date,
                last_scan_end_page)
            self.helper.log_info("Most recent last_scan_end_date at the end of processing page {}".format(self.last_scan_end_date))
        
        # Update the most recent last_assessed found for this import job.
        if last_assessed_page is not None:
            self.helper.log_info("Most recent last_assessed_date at the start of processing this page {}".format(self.last_assessed_date))
            self.last_assessed_date = last_assessed_page if self.last_assessed_date is None else max(self.last_assessed_date,
                last_assessed_page)
            self.helper.log_info("Most recent last_assessed_date at the end of processing this page {}".format(self.last_assessed_date))

        self.vuln_dict["num_processed"] = len(data) - excluded_count
        return self.vuln_dict
  
    def vulnerability_finding_events(self, new_vulns, remediated_vulns, same_vulns, asset, vuln_dict):
        asset_id = asset.get("id", "")
        asset_hostname = asset.get("host_name", "")
        asset_ip = asset.get("ip", "")

        [vuln.update({"finding_status": "new"}) for vuln in new_vulns]
        vuln_dict["vuln_processed_new"] += len(new_vulns)
        [vuln.update({"finding_status": "remediated"}) for vuln in remediated_vulns]
        vuln_dict["vuln_processed_remediated"] += len(remediated_vulns)
        [vuln.update({"finding_status": "found"}) for vuln in same_vulns]
        vuln_dict["vuln_processed_same"] += len(same_vulns)

        all_vulns = new_vulns + remediated_vulns + same_vulns
        vuln_dict["total_vuln_processed"] += len(all_vulns)

        for vuln in all_vulns:
            vuln["asset_id"] = asset_id
            vuln["asset_hostname"] = asset_hostname
            vuln["asset_ip"] = asset_ip
            
            event = self.event_utils.create_event(vuln, "rapid7:insightvm:asset:vulnerability_finding")

            try:
                self.ew.write_event(event)
            except Exception as e:
                self.helper.log_error("There was an error inserting a vulnerability event into the index")
                self.helper.log_error(e)

        return vuln_dict

    def cache_item(self, item):
        item_id = item.get("id")
        
        if len(self.imported_asset_cache) < CACHE_MAX_SIZE:
            self.imported_asset_cache[item_id] = {
                LAST_SCAN_END: item.get(LAST_SCAN_END), 
                LAST_ASSESSED_FOR_VULNERABILITIES: item.get(LAST_ASSESSED_FOR_VULNERABILITIES)
            }
        else:
            self.helper.log_debug("Import cache is full, item {} will not be cached. Data will not be lost,"
                                  " but may result in duplcate data being indexed".format(item_id))

    def is_excluded_event(self, item):
        item_id = item.get("id")
        if item_id is None:
            return False

        excluded_item = self.excluded_events.get(item_id)
        if excluded_item is None:
            return False

        if (item.get(LAST_SCAN_END) == excluded_item.get(LAST_SCAN_END)
            and item.get(LAST_ASSESSED_FOR_VULNERABILITIES) == excluded_item.get(LAST_ASSESSED_FOR_VULNERABILITIES)):
            return True

        return False