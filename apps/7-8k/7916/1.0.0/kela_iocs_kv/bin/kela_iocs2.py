import sys, os, json, traceback

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

# init Globals
logger = SplunkLogger()

# Note: session_key to be updated
splunk = SplunkService()

class MyScript(Script):

    def get_scheme(self):
        scheme = Scheme("KELA IoCs")
        scheme.description = "IoCs powered by KELA"

        scheme.use_external_validation = True
        
        scheme.use_single_instance = True

        arg = Argument("start_date")
        arg.title = "Start Date (Epoc)"
        arg.data_type = Argument.data_type_number
        arg.description = "The date to start loading IoCs from in unix timestamp format" 
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
        """Validating that monitor exists, it exists if KELA API returns at least on incident for it
        """
        # NOTE: For some reason I consistantly get timeout ont this one
        # session_key = validation_definition.metadata['session_key']
        # di = SplunkRestService.get_data_inputs(session_key)
        # raise ValueError(f"{di}")
        
        # Get the parameters from the ValidationDefinition object,
        # then typecast the values as floats
        start_date = int(validation_definition.parameters["start_date"])

        if start_date < 0:
            raise ValueError(f"Start Date must be bigger than 0")

        session_key = validation_definition.metadata["session_key"]
        
        api_key = SplunkService(session_key).get_token()
        # proxy logic
        proxies = self._get_proxies()
        
        # Try api to see if token & proxy configurations are correct
        k = Kela(api_key, proxies)
        l = k.landscape() 
        x = l.get_iocs()
        for a in x:
            break

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


    def perform_reset(self, chk: Checkpointer, input_name, start_date, logger):
        logger.info(f"Performing reset: Trunctaing all checkpiont files...")
        # Delete all files in checkpoint directory
        chk.truncate_all_checkpoints()
        
        logger.info(f"Performing reset: Deleting iocs...")
        splunk.delete_iocs()
        
        logger.info(f"Performing reset: updating parameter...")
        splunk.update_reset_parameter(input_name, start_date, logger)
        
        logger.info(f"Reset performed succesfully")

    def stream_event_logic(self, inputs, event_writer):
        '''The purpuse of this function is to be wrapped in try catch section so that fatal errors are being logged graceously'''

        logger.info(f"Starting up ioc stream logic...")

        checkpoint_dir = self._get_checkpoint_dir()
        chk = Checkpointer(checkpoint_dir)

        # get KELA API from Setup Page
        session_key = self._input_definition.metadata["session_key"]
        splunk.session_key = session_key
        
        api_key = splunk.get_token()

        # proxy logic
        proxies = self._get_proxies()

        k = Kela(api_key, proxies)
        
        i = 0
        skipping_mode = False
        
        # NOTE: only 1 active input is allowed for this module
        input_items = list(inputs.inputs.items())
        if len(input_items) > 1:
            logger.warn(f"Only one input is allowed on this module. Found {len(input_items)}: {[x[0] for x in input_items]}")
            return
        
        skipping_mode = False
        skipped_items = 0
        
        for input_name, input_item in input_items:
            
            start_date = int(input_item["start_date"])
            last_date=chk.get_last_timestamp()
            current_date = max(start_date, last_date)
            
            if input_item.get("cmd") == "reset":
                # Note: from kela_iocs2://{name} to {name}
                pure_input_name = input_name.replace("kela_iocs2://","")
                self.perform_reset(chk, pure_input_name, start_date, logger)
            
            l = k.landscape(current_date) 
            
            iocs = l.get_iocs(5000)
            logger.info(f"Starting to stream iocs since {current_date}")

            for ioc in iocs:
                i += 1
                ioc_id = ioc['kela_id']
                if not ioc_id:
                    logger.warn(f"No ID for ioc: {ioc}")
                    continue
                
                if chk.is_ioc_indexed(ioc):
                    if not skipping_mode:
                        logger.info("Skipping mode: on | found indexed ioc")
                    skipping_mode = True
                    skipped_items += 1
                    continue
                
                if skipping_mode:
                    logger.info(f"Skipping mode: off | skipped over {skipped_items} item(s) | found new unindexed ioc {ioc}")
                    skipping_mode = False
                
                verbose_rate = 2500
                if i % verbose_rate == 0 and i > 0:
                    logger.info(f"{i} ioc have been streamed | current_date: {ioc['kela_created_date']}")

                splunk.upsert_ioc(ioc)

                # update checkpoint
                chk.set_ioc_as_indexed(ioc)
                
            logger.info(f'Completed event streaming for iocs')
        logger.info(f"KELA IoC event streaming has completed sucessfuly")

    def stream_events(self, inputs, event_writer):
        # init logger 
        logger.setEventWritter(event_writer)
        checkpoint_dir = self._get_checkpoint_dir()
        
        try:
            self.stream_event_logic(inputs, event_writer)
        except Exception as e:
            logger.fatal(f"Fatal Error while streaming events.")
            raise e

    def _get_checkpoint_dir(self) -> str:
        return self._input_definition.metadata["checkpoint_dir"]
    
if __name__ == "__main__":
    try:
        sys.exit(MyScript().run(sys.argv))
    except Exception as e:
        logger.fatal(f'{str(e)} | traceback: {traceback.format_exc()}')
        raise e