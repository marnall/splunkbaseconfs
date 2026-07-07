import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option
from requests import Session
import aiohttp
import asyncio


import vt_connector

from vt_exceptions import VTException, VTAPIException, VTConfigException
from vt_constants import COMMAND_OPTIONS_IOC_TYPES, COMMAND_OPTION_IOC_TYPE_HASH, COMMAND_OPTION_IOC_TYPE_URL, \
    COMMAND_OPTION_IOC_TYPE_DOMAIN, COMMAND_OPTION_IOC_TYPE_IP, VT_FIELDS_RESULT
from vt_service import get_fields_custom_prefix
from vt_utils import sanitize_command_option, prefix_builder
from vt_log import setup_logging


logger = setup_logging()

@Configuration()
class VTReport(StreamingCommand):
    """
    Checks a file hash against VirusTotal.
    """

    hash = Option(
        doc="""
        **Syntax:** **hash=***<file_hash>*
        **Description:** File hash to check
        """,
        require=False
    )

    url = Option(
        doc="""
        **Syntax:** **url=***<url>*
        **Description:** URL to check
        """,
        require=False
    )

    domain = Option(
        doc="""
        **Syntax:** **domain=***<domain>*
        **Description:** Domain to check
        """,
        require=False
    )
    
    ip = Option(
        doc="""
        **Syntax:** **ip=***<ip>*
        **Description:** IP to check
        """,
        require=False
    )

    def stream(self, events):
        option_value = None
        option_type = None

        for command_option in COMMAND_OPTIONS_IOC_TYPES:
            if hasattr(self, command_option):
                option_value = getattr(self, command_option, None)
                option_type = command_option
                if option_value:
                    option_type = command_option
                    break

        if not option_value or not option_type:
            raise VTException("The vt command requires a valid option [hash=<string> | url=<string> | domain=<string> | ip=<string>]")

        enriched_events = asyncio.get_event_loop().run_until_complete(self.enrich_events(events, option_value, option_type))
        
        for enriched_event in enriched_events:
            yield enriched_event
            
        logger.info(f"Execution of command vt with param '{option_type}' finished")
    
                  
    async def enrich_events(self, events, option_value, option_type):
        session = aiohttp.ClientSession()
        
        enriched_events = await asyncio.gather(
            *[self.enrich_event(event, session, option_value, option_type) for _, event in enumerate(events)],
            return_exceptions=False
        )
        
        await session.close()
        return enriched_events


    async def enrich_event(self, event, session, option_value, option_type):
        
        enriched_event = event
        
        try:
            fields_custom_prefix = get_fields_custom_prefix(self.service)
        except Exception:
            raise VTConfigException("An error occurred loading the custom prefix configuration")
        result = prefix_builder(fields_custom_prefix, VT_FIELDS_RESULT)
        
        try:
            if option_value in event:
                param_value = event[option_value]
            else:
                param_value = option_value
                
            param_value = sanitize_command_option(param_value)
            
            if param_value:
                params = {option_type: param_value}
                
                if option_type == COMMAND_OPTION_IOC_TYPE_HASH:
                    enriched_event = await vt_connector.make_file_report_request(self.service, event, session, params)
                elif option_type == COMMAND_OPTION_IOC_TYPE_URL:
                    enriched_event = await vt_connector.make_url_report_request(self.service, event, session, params)
                elif option_type == COMMAND_OPTION_IOC_TYPE_DOMAIN:
                    enriched_event = await vt_connector.make_domain_report_request(self.service, event, session, params)
                elif option_type == COMMAND_OPTION_IOC_TYPE_IP:
                    enriched_event = await vt_connector.make_ip_report_request(self.service, event, session, params)
                    
                enriched_event[result] = "success"
                
                return enriched_event
                
        except VTAPIException as error:
            enriched_event[result] = f'{error.code}: {error.message}'
            logger.error('%s: %s', error.code, error.message)
        except VTException as ex:
            enriched_event[result] = str(ex)
            logger.error('%s', ex)
             
        return enriched_event
    
       
dispatch(VTReport, sys.argv, sys.stdin, sys.stdout, __name__)
