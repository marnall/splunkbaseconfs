import sys, os, json
import traceback

# NOTE: splunklib and kela must exist within ../lib/splunklib for this
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.modularinput import *
from kela import Kela, FeedItemType, APIError

# Note: seperated so by line number one knows from log which is causing the problemz
from utils import SplunkService
from utils import Checkpointer
from utils import SplunkLogger
from utils import ProxyService
from utils import AppService
from utils import Logic

# init Globals
logger = SplunkLogger()

# Note: session_key to be updated
splunk = SplunkService()

class MyScript(Script):

    def get_scheme(self):
        scheme = Scheme("KELA Identity")
        scheme.description = "Identity Guard powered by KELA"

        scheme.use_external_validation = True
        scheme.use_single_instance = True

        arg = Argument("workspace_id")
        arg.title = "Workspace ID"
        arg.data_type = Argument.data_type_string
        arg.description = "Set your Identity Guard Workspace ID as it appears on KELA Platform" 
        arg.required_on_create = True
        scheme.add_argument(arg)
        
        arg = Argument("bots")
        arg.title = "Load bot identities"
        arg.data_type = Argument.data_type_boolean
        arg.description = "Do you want to load bots?" 
        arg.required_on_create = True
        scheme.add_argument(arg)
        
        arg = Argument("incidents")
        arg.title = "Load incidents identities"
        arg.data_type = Argument.data_type_boolean
        arg.description = "Do you want to load incidents?" 
        arg.required_on_create = True
        scheme.add_argument(arg)

        arg = Argument("cmd")
        arg.title = "Advanced: Command"
        arg.data_type = Argument.data_type_string
        arg.description = "Caution! 'reset' command will delete all events and reload the monitor from point zero. make sure can_delete permission is set to user role upon reseting" 
        arg.required_on_create = False
        scheme.add_argument(arg)
        
        return scheme

    def validate_input(self, validation_definition):
        """Validating that monitor exists, it exists if KELA API returns at least on incident for it"""
        
        # Note: the japanese have worspace "499"... so... the is no way to test this
        return 
        
        workspace_id = str(validation_definition.parameters["workspace_id"])

        if len(workspace_id) < 5:
            raise ValueError(f"Workspace ID seems incorrect")

    def _get_proxies(self):
        appconf = AppService.get_local_conf()
        has_proxy = bool(appconf.get("proxy_type"))
        proxies = {}
        if has_proxy:
            proxies = ProxyService.proxify(
                schema=appconf.get('proxy_type'), 
                ip=appconf.get('proxy_ip'), 
                port=appconf.get('proxy_port'), 
                user=appconf.get('proxy_user'), 
                pwd=appconf.get('proxy_pwd'))
        return proxies


    def perform_reset(self, chk: Checkpointer, input_name, argdict, logger):
        logger.info(f"Performing reset: Trunctaing all checkpiont files...")
        # Delete all files in checkpoint directory
        chk.truncate_all_checkpoints()
        
        logger.info(f"Performing reset: Deleting identities...")
        
        splunk.delete_identities()
        
        logger.info(f"Performing reset: updating parameter...")
        splunk.update_reset_parameter(input_name, argdict, logger)
        
        logger.info(f"Reset performed succesfully")
    
    def stream_events_of_type(self, _type: str, input_name: str, event_writer: "EventWriter", ig: "IdentityBase", chk: "Checkpointer"):
        # This also asserts _type to be of accepted value
        id_field_name: str = Logic.get_id_field_name(_type)
        
        # when we reach this date we know we finished loading
        # when it's first time this should be equal to 0
        last_loaded_date = chk.get_last_updated_date(_type)
        
        # this is the loaded that will be updated as the last_updated_date
        new_loaded_date = 0
    
        x = ig.get_identities()
        
        logger.info(f"Starting to stream {_type} identities from now backwards")
        i=0
        
        # NOTE: we pick the first updatedDate (which is the newest) and set it as checkpoint only when reached to the end of the scroll (either the oldest item or the previous checkpoint)
        
        # ii stands for identity item
        for ii in x:
            
            # If we reached to a point where the updated_date that we scroll is older than then previously-splunk-handled,
            # then we reached the end.
            if ii['updatedDate'] < last_loaded_date:
                logger.info(f"Reached to the end of the stream for {_type}s identities at {last_loaded_date}. {i} new items Found.")
                break
            
            # When it's first item it means that this is the newest updatedDate and everything newer than this should be handled in next splunk run.
            if i == 0:
                new_loaded_date = ii['updatedDate']
            
            i += 1
            
            ii_id = ii.get(id_field_name)
            if not ii_id:
                logger.warn(f"No ID for event: {ii}")
                continue
            
            if chk.is_indexed(_type, ii):
                logger.info(f"Updating Identity {_type}: {ii_id}...")
                splunk.delete_identity(_type, ii_id)
            
            verbose_rate = 2500
            if i % verbose_rate == 0 and i > 0:
                logger.info(f"{i} items have been streamed | current_date: {ii['updatedDate']}")

            event = Event()
            event.stanza = input_name

            # unique identification for all sourcetypes and all indexes from this modular input
            ii['kela_modular_input_uid'] = '8b89f8a292bacfa8437d3d72f01e62d3'

            # Write event
            event.data = json.dumps(ii)
            event.sourcetype = "kela:identity"
            event_writer.write_event(event)
            
            # update checkpoint
            chk.set_as_indexed(_type, ii)
            
        chk.set_last_updated_date(_type, new_loaded_date)
        logger.info(f'Completed event streaming for identity {_type}s, from {last_loaded_date} to {new_loaded_date}.')

    def stream_event_logic(self, inputs, event_writer):
        '''The purpuse of this function is to be wrapped in try catch section so that fatal errors are being logged graceously'''

        logger.info(f"Starting up identity stream logic...")
        chk = Checkpointer(self._checkpoint_dir)

        # get KELA API from Setup Page
        session_key = self._input_definition.metadata["session_key"]
        splunk.session_key = session_key
        
        api_key = splunk.get_token()

        # proxy logic
        proxies = self._get_proxies()

        k = Kela(api_key, proxies)
        
        i = 0
        
        input_items = list(inputs.inputs.items())
        for input_name, input_item in input_items:
            
            workspace_id = str(input_item["workspace_id"])
            bots = input_item["bots"] == "1"
            incidents = input_item["incidents"] == "1"
            
            logger.info(f"Starting to load for Workspace ID: {workspace_id}. Bots: {bots} | Incidents: {incidents}")
            
            if input_item.get("cmd") == "reset":
                # Note: from kela_identity://{name} to {name}
                pure_input_name = input_name.replace("kela_identity://","")
                argdict = {
                    "workspace_id": workspace_id,
                    "bots": "1" if bots else "0",
                    "incidents": "1" if incidents else "0",
                }
                self.perform_reset(chk, pure_input_name, argdict, logger)
            
            if bots:
                ig = k.identity_bot(workspace_id)
                self.stream_events_of_type("bot", input_name, event_writer, ig, chk)
            
            if incidents:
                ig = k.identity_incident(workspace_id)
                self.stream_events_of_type("incident", input_name, event_writer, ig, chk)
                
            logger.info(f"Finished to load for Workspace ID {workspace_id} Successfuly")
            
        logger.info(f"KELA Identity Guard event streaming has completed sucessfuly")

    def stream_events(self, inputs, event_writer):
        # init logger
        logger.setEventWritter(event_writer)

        try:
            self.stream_event_logic(inputs, event_writer)
        except Exception as e:
            stack_trace = traceback.format_exc()
            logger.fatal(f"Fatal Error while streaming events: {e} | Stack Trace:\n{stack_trace}")
            
            raise e

    @property
    def _checkpoint_dir(self) -> str:
        return self._input_definition.metadata["checkpoint_dir"]
    
if __name__ == "__main__":
    try:
        sys.exit(MyScript().run(sys.argv))
    except Exception as e:
        logger.fatal(str(e))
        raise e