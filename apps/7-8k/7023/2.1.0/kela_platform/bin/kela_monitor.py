import sys, os, json, traceback

# NOTE: splunklib and kela must exist within ../lib/splunklib for this
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.modularinput import *
from kela import Kela, FeedItemType, APIError

# Import from utils seperatly, thus line number indicated source of linkage problem
from utils import SplunkService
from utils import MonitorCheckpointer
from utils import SplunkLogger
from utils import ProxyService
from utils import AppService
from utils import IncidentService

#from utils import save_event_to_file #For debug

# init logger
logger = SplunkLogger()
splunk = SplunkService()


# The Incident type names and titles that splunk is going to use as input items inorder to determine which typ of incidents to load
# NOTE: bool args stands for all the boolean arguments that indicate incident types to load or not load
bool_args_variable_names_and_titles = [
    ('hacking_discussions', "Hacking Discussions"),
    ('instant_messaging', "Instant Messaging"),
    ('leaked_credentials', "Leaked Credentials"),
    ('network_vulnerabilities', "Network Vulnerabilities"),
    ('credit_cards', "Credit Cards"),
    ('botnets', "Compromised Accounts"),
]
bool_args_variable_names = [t[0] for t in bool_args_variable_names_and_titles]
bool_arg_to_name_dict = { 
    t[0]: t[1] for t in bool_args_variable_names_and_titles
}

class MyScript(Script):
    """All modular inputs should inherit from the abstract base class Script
    from splunklib.modularinput.script.
    They must override the get_scheme and stream_events functions, and,
    if the scheme returned by get_scheme has Scheme.use_external_validation
    set to True, the validate_input function.
    """

    def get_scheme(self):
        """When Splunk starts, it looks for all the modular inputs defined by
        its configuration, and tries to run them with the argument --scheme.
        Splunkd expects the modular inputs to print a description of the
        input in XML on stdout. The modular input framework takes care of all
        the details of formatting XML and printing it. The user need only
        override get_scheme and return a new Scheme object.

        :return: scheme, a Scheme object
        """
        # "random_numbers" is the name Splunk will display to users for this input.
        scheme = Scheme("KELA Monitor")
        scheme.description = "Monitor incidents powered by KELA"
        # If you set external validation to True, without overriding validate_input,
        # the script will accept anything as valid. Generally you only need external
        # validation if there are relationships you must maintain among the
        # parameters, such as requiring min to be less than max in this example,
        # or you need to check that some resource is reachable or valid.
        # Otherwise, Splunk lets you specify a validation string for each argument
        # and will run validation internally using that string.
        scheme.use_external_validation = True
        
        # NOTE: At the moment we can only support single instance because of http reuest rate limit. 429 will be thrown if changed to False.
        scheme.use_single_instance = True

        monitor_id_arg = Argument("monitor_id")
        monitor_id_arg.title = "Monitor ID"
        monitor_id_arg.data_type = Argument.data_type_number
        monitor_id_arg.description = "The ID of monitor in Kela"
        monitor_id_arg.required_on_create = True
        scheme.add_argument(monitor_id_arg)

        for bool_arg in bool_args_variable_names_and_titles:
            name = bool_arg[0]
            title = bool_arg[1]
            arg = Argument(name)
            arg.title = title
            arg.data_type = Argument.data_type_boolean
            arg.description = f"Do you want to monitor {title}?"
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
        
        # Get the parameters from the ValidationDefinition object,
        # then typecast the values as floats
        monitor_id = int(validation_definition.parameters["monitor_id"])
        
        if monitor_id < 0:
            raise ValueError(f"Monitor ID must be bigger than 0")

        # NOTE: check is disabled because it causes:
        #   Encountered the following error while trying to update: Splunkd daemon is not responding: ('Error connecting to /servicesNS/nobody/launcher/data/inputs/kela_monitor/1981: The read operation timed out',)
        
        # session_key = validation_definition.metadata["session_key"]
        # api_key = SplunkService(session_key).get_token()
        # # proxy logic
        # proxies = self._get_proxies()
        
        # k = Kela(api_key, proxies) 
        # monitor = k.monitor(monitor_id)

        # # example: {hacking_discussion: '0', leaked_credential: '1'...}
        # incident_types_conf = {
        #     name: validation_definition.parameters[name] 
        #     for name in bool_args_variable_names
        # }
        # IncidentService.assert_monitor_conf(monitor, incident_types_conf, bool_arg_to_name_dict, logger)

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
    
    def perform_reset(self, monitor_id: str, chk: MonitorCheckpointer, input_name, input_item, session_key, logger):
        logger.info(f"Performing reset {monitor_id}: Trunctaing all checkpiont files...")
        
        # Delete all files in checkpoint directory
        chk.truncate_monitor_checkpoints()
        
        logger.info(f"Performing reset {monitor_id}: Deleting events...")
        
        splunk.delete_events(monitor_id)
        
        logger.info(f"Performing reset {monitor_id}: Updating parameter...")
        
        # example: {"monitor_id": 1981, "hacking_discussions": '1', ...}
        argdict = {
            **{
                "monitor_id": monitor_id
            },
            **{
                # dict_of_all_bool_arguments_and_their_values
                arg_name: input_item[arg_name] 
                for arg_name in input_item
                if arg_name in bool_args_variable_names
            }
        }
        
        splunk.update_reset_parameter(input_name, argdict, logger)
        
        logger.info(f"Reset performed succesfully.")
    
    def stream_event_logic(self, inputs, event_writer):
        '''The purpuse of this function is to be wrapped in try catch section so that fatal errors are being logged graceously'''

        logger.info(f"Starting up stream logic... [ Python version: {sys.version} | Python version info: {sys.version_info} ]")
        
        # get KELA API from Setup Page
        session_key = self._input_definition.metadata["session_key"]
        splunk.session_key = session_key
        api_key = splunk.get_token()

        # proxy logic
        proxies = self._get_proxies()

        k = Kela(api_key, proxies) 

        i = 0
            
        # Go through each input for this modular input (monitors)
        for input_name, input_item in list(inputs.inputs.items()):
            
            monitor_id = int(input_item["monitor_id"])
            chk = MonitorCheckpointer(self.checkpoint_dir, monitor_id)
            
            monitor = k.monitor(monitor_id)
            
            pure_input_name = input_name.replace("kela_monitor://","")   
            if input_item.get("cmd") == "reset": 
                # Note: from kela_monitor://{name} to {name}
                self.perform_reset(monitor_id, chk, pure_input_name, input_item, session_key, logger)

            logger.info(f"Starting to stream events to monitor {monitor_id} from input {pure_input_name}")
            
            # NOTE: for each activated incident type (AKA name) get it's last loaded date
            # example: {hacking_discussion: 1727694590, leaked_credential: None...}
            incident_types_conf = {
                name: chk.get_last_date(name)
                for name in bool_args_variable_names
                # Note: Activated arguments are "1" and disabled are "0"
                if input_item[name] == '1' 
            }
            
            logger.info(f"Respawn info {monitor_id}: {incident_types_conf}.")
            
            incident_type_names = incident_types_conf.keys()
            
            # inicdent type is mandatory in get_incdients api, so it is needed to loop over them
            for feed_item_type_name in incident_type_names:
                # NOTE: feed_item_type_name represent the names of the enum and not the values (because the values wack)
                feed_item_type = FeedItemType(feed_item_type_name)
                
                # this is the last newest_incident_date, we do not need to scroll beyond that date. but we may need to re-scroll it, in case new events are of the same incident_date
                from_date: Optional[int] = incident_types_conf[feed_item_type_name]
                
                # this date that will be saved to narrow the scroll in next run
                newest_incident_date: Optional[int] = None
                
                logger.info(f"Starting to scroll {monitor_id}:{feed_item_type_name}...")
                
                # we want to notify just once
                notified_already_indexed = False
                
                for incident in IncidentService.get_incidents(monitor, feed_item_type, from_date, logger):
                    inc_id = incident['kela_id']
                    inc_type = incident['kela_type']

                    if not inc_id:
                        logger.warn(f"No ID for incident: {incident}")
                        continue
                        
                    if not inc_type:
                        logger.warn(f"No Type for incident: {incident}")
                        continue
            
                    if chk.is_indexed_event(inc_type, inc_id):
                        if not notified_already_indexed:
                            logger.info(f"Reached to an already indexed event. ID:{inc_id} | TYPE:{inc_type} | DATE:{incident['incident_date']}")
                            notified_already_indexed = True
                        # NOTE: results are returned from new to old. from unindexed to indexed. thus, when reached to an indexed one. it might be a time to stop... but!
                        # DO NOT BREAK HERE, just for the sake of having NEW incidents on top of the SAME incident_date... who knows...
                        continue
                    
                    if not newest_incident_date:
                        newest_incident_date = incident['incident_date']

                    i += 1

                    if i % 1000 == 0 and i > 0:
                        logger.info(f"{i} events have been streamed to monitor {monitor_id} of type {feed_item_type_name}")

                    event = Event()
                    event.stanza = input_name

                    # unique identification for all sourcetypes and all indexes from this modular input
                    incident['kela_modular_input_uid'] = '96f52f08e05a942c607f3b9b888f27cd'

                    # save_event_to_file(x, i, inc_id)
                    event.data = json.dumps(incident)
                    event.sourceType = "kela:monitor"

                    # Tell the EventWriter to write this event
                    event_writer.write_event(event)
                    chk.set_event_as_indexed(inc_type, inc_id)
                
                
                if newest_incident_date is not None:
                    chk.update_last_date(feed_item_type.value, newest_incident_date)
                    logger.info(f"Saved the newest incident_date: {newest_incident_date} for incidents of type {feed_item_type_name} in monitor {monitor_id}.")
                logger.info(f"Finished scrolling over {monitor_id}:{feed_item_type_name}.")

            logger.info(f'Completed event streaming for monitor {monitor_id}')
        logger.info(f"KELA Monitor event streaming has completed sucessfuly")

    def stream_events(self, inputs, event_writer):
        """This function handles all the action: splunk calls this modular input
        without arguments, streams XML describing the inputs to stdin, and waits
        for XML on stdout describing events.

        If you set use_single_instance to True on the scheme in get_scheme, it
        will pass all the instances of this input to a single instance of this
        script.

        :param inputs: an InputDefinition object
        :param event_writer: an EventWriter object
        """

        # To connect with Splunk, use the instantiated service object which is created using the server-uri and
        # other meta details and can be accessed as shown below
        # Example:-
        #    service = self.service
        #    info = service.info //access the Splunk Server info

        logger.setEventWritter(event_writer)
      
        try:
            self.stream_event_logic(inputs, event_writer)
        except Exception as e:
            logger.fatal(f"Fatal Error while streaming events: {e}")
            raise e
    
    @property
    def checkpoint_dir(self) -> str:
        return self._input_definition.metadata["checkpoint_dir"]

if __name__ == "__main__":
    try:
        sys.exit(MyScript().run(sys.argv))
    except Exception as e:
        logger.fatal(f'{str(e)} | traceback: {traceback.format_exc()}')
        raise e