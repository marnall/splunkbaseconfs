# encoding = utf-8

import os
import sys
import time
import datetime
import hashlib
import json
import uuid
import traceback

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # text = definition.parameters.get('text', None)
    pass


def collect_events(helper, ew):
    __version__ = "1.0.2"
    try:
        from .ls_tools import JamfPatch, JamfSplunkPatchSync, RoutineJamfPatchSync, JamfProSDK, JamfProMacUAPIDevice
        from .ls_tools import JamfProMacApplications, LSIO
    except ImportError:
        from ls_tools import JamfPatch, JamfSplunkPatchSync, RoutineJamfPatchSync, JamfProSDK, JamfProMacUAPIDevice
        from ls_tools import JamfProMacApplications, LSIO

    run_id = uuid.uuid4().hex

    settings = {
        "jamf_pro_url": helper.get_arg("jamf_pro_url", None),
        "client_id": helper.get_arg("client_id", None),
        "client_secret": helper.get_arg("client_secret", None),
        "exclude_unmanaged": helper.get_arg("exclude_unmanaged", None),
        "limit_inventory_time": helper.get_arg("limit_inventory_time", None),
        "api_sections": helper.get_arg("api_sections", None),
        "meta_builder": helper.get_arg("meta_builder", None),
        "application_patching": helper.get_arg("application_patching", None),
        "share_analytics": helper.get_arg("share_analytics", None),
        "vulnerability_detections": helper.get_arg("vulnerability_detections", None),
        "vulnerability_requirements": helper.get_arg("vulnerability_requirements", None),
        "loonsecio_base_url": helper.get_arg("loonsecio_base_url", None),
        "loonsecio_client_id": helper.get_arg("loonsecio_client_id", None),
        "loonsecio_client_secret": helper.get_arg("loonsecio_client_secret", None),
        "sla_days_critical": helper.get_arg("sla_days_critical", None),
        "sla_days_high": helper.get_arg("sla_days_high", None),
        "sla_days_medium": helper.get_arg("sla_days_medium", None),
        "sla_days_low": helper.get_arg("sla_days_low", None),
        "headers": {
            "User-Agent": f"loonsecio splunkbase {__version__}"
        }
    }

    # Check Jamf Pro for Token, error out on failure
    try:
        jpro_api = JamfProSDK(helper=helper, ew=ew, jamf_pro_url=settings.get("jamf_pro_url"), settings=settings, client_id=settings.get('client_id'), client_secret=settings.get('client_secret'))
    except:
        helper.log_critical(msg="Failed Initial tests, unable to get Jamf Pro Access Token")

        return None
    # Load Jamf Patch Data
    if 'JAMFPATCH' in settings.get("application_patching", []):
        try:
            RoutineJamfPatchSync(helper, ew).run()
        except Exception as E:
            msg = {'error': 'error in updating Jamf Patch Title', 'error_s': str(E),
                   '_time': time.time(), 'execution_id': run_id}
            ew.write_event(helper.new_event(data=json.dumps(msg),
                                            index=helper.get_output_index(),
                                            sourcetype="lsio:jamfDevices:error_msg",
                                            done=True,
                                            unbroken=True))
    start_time = time.time()
    try:
        groups = jpro_api.get_groups()
    except Exception as E:
        msg = {'error': 'error in updating Jamf Groups', 'error_s': str(E),
               '_time': time.time(), 'execution_id': run_id}
        ew.write_event(helper.new_event(data=json.dumps(msg),
                                        index=helper.get_output_index(),
                                        sourcetype="lsio:jamfDevices:error_msg",
                                        done=True,
                                        unbroken=True))
        groups = []

    try:
        departments = jpro_api.get_departments()
    except Exception as E:
        msg = {'error': 'error in updating Jamf Departments', 'error_s': str(E),
               '_time': time.time(), 'execution_id': run_id}
        ew.write_event(helper.new_event(data=json.dumps(msg),
                                        index=helper.get_output_index(),
                                        sourcetype="lsio:jamfDevices:error_msg",
                                        done=True,
                                        unbroken=True))
        departments = []

    try:
        buildings = jpro_api.get_buildings()
    except Exception as E:
        msg = {'error': 'error in updating Jamf Buildings', 'error_s': str(E),
               '_time': time.time(), 'execution_id': run_id}
        ew.write_event(helper.new_event(data=json.dumps(msg),
                                        index=helper.get_output_index(),
                                        sourcetype="lsio:jamfDevices:error_msg",
                                        done=True,
                                        unbroken=True))
        buildings = []

    apps_hash = []
    try:
        lsio_vulns = LSIO.JamfMacAppVulns(splunk_helper=helper, lsio_url=settings['loonsecio_base_url'],
                                          lsio_api_client=settings['loonsecio_client_id'],
                                          lsio_api_secret=settings['loonsecio_client_secret']
                                          )
        apps = JamfProMacApplications(lsio_vulns=lsio_vulns)

    except Exception as E:
        msg = {'error': 'Fatal Error Setting up Apps', 'error_s': str(E),
               '_time': time.time(), 'execution_id': run_id}
        ew.write_event(helper.new_event(data=json.dumps(msg),
                                        index=helper.get_output_index(),
                                        sourcetype="lsio:jamfDevices:error_msg",
                                        done=True,
                                        unbroken=True))

    finished_computers = False
    page_count = 0
    try:
        while not finished_computers:
            apps_hash_run = {}
            computer_page = jpro_api.get_computers_page(page_size=200, page_number=page_count)

            for computer in computer_page['results']:
                for application in computer['applications']:
                    app_md5_s = f"{application['name']}{application['version']}{application['bundleId']}"
                    app_md5 = hashlib.md5(app_md5_s.encode()).hexdigest()
                    apps_hash_run[app_md5] = application
            cache_list = []

            for key in apps_hash_run.keys():
                if key not in apps_hash:
                    cache_list.append(key)
            lsio_vulns.get_app_vulns_api(app_list=cache_list)
            # Here goes the Requested Data
            apps_hash.extend(apps_hash_run.keys())
            # Here goes the Requested Data
            for computer in computer_page['results']:
                this_computer = JamfProMacUAPIDevice(jamf_device=computer, departments=departments, buildings=buildings,
                                                     groups=groups, app_details=apps)
                splunk_events = this_computer.get_splunk_events()
                for splunk_event in splunk_events:
                    ew.write_event(helper.new_event(json.dumps(splunk_event.get('event', {})), sourcetype=splunk_event.get('sourcetype', 'unknown'), index=helper.get_output_index(), done=True, unbroken=True))
            if len(computer_page['results']) == 0:
                finished_computers = True
            else:
                page_count += 1
    except Exception as E:
        msg = {'error': 'Fatal Error Collecting Devices', 'error_s': str(E), 'trace': str(traceback.format_exc()),
               '_time': time.time(), 'execution_id': run_id}
        ew.write_event(helper.new_event(data=json.dumps(msg),
                                        index=helper.get_output_index(),
                                        sourcetype="lsio:jamfDevices:error_msg",
                                        done=True,
                                        unbroken=True))

