
# encoding = utf-8

import os
import sys
import time
import requests
import json
import asyncio
from onetrust_assessments_collector_engine import OneTrustArchivalState, OneTrustAssessmentsCollector
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
    pass

async def ot_engine_start(helper, ew, otcollector_instance):
    async for a in otcollector_instance.start():
        data = json.dumps(a, separators=(',', ':'))
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=a.get("sourceType", "onetrust:assessments"), data=data)
        ew.write_event(event)
    
def collect_events(helper, ew):
    
    opt_base_url = helper.get_arg('base_url')
    opt_api_token = helper.get_arg('api_token')
    opt_assessment_archival_state = helper.get_arg('assessment_archival_state')
    opt_created_since = helper.get_arg('created_since')
    opt_template_name_filter = helper.get_arg('template_name_filter')
    opt_exclude_skipped_questions = helper.get_arg('exclude_skipped_questions')
    
    esq = {"true": True, "false": False}[opt_exclude_skipped_questions.lower()]
    
    otcollector = OneTrustAssessmentsCollector(base_url=opt_base_url, 
                                               api_key=opt_api_token, 
                                               archival_state=OneTrustArchivalState(opt_assessment_archival_state),
                                               template_name=opt_template_name_filter, 
                                               created_since=opt_created_since,
                                               exc_skipped_q=esq)
    
    asyncio.run(ot_engine_start(helper, ew, otcollector))
    