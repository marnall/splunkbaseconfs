import rs_declare

from splunklib.searchcommands import GeneratingCommand

import rs_utility as util

class BaseCommandHandler(GeneratingCommand):
    """
    Base custom command handler class to handle all the exceptions and duplicate code at one place.
    When python script of custom command executes, generate method will be called, and after executing the common code,
    it will call the custom `do_generate` method from the respective command's python script.
    """
    def generate(self):
        
        try:
            # Setup logger
            session_key = self._metadata.searchinfo.session_key
            logger = util.setup_logger(session_key=session_key, log_context=self._metadata.searchinfo.command)

            try:
                message = ''
                # Get Proxy settings
                proxy_settings = util.get_proxy(session_key, logger=logger)

            except Exception as e:
                message = str(e)
            
            if message:
                logger.error("Error occurred while running custom command Error: {}".format(message))
                self.write_error(message)
                exit(1)

            # This will call the do_generate method of the respective class from which this class was called
            # And generate the events
            event_counter = 0
            for event in self.do_generate(session_key, logger, proxy_settings):
                yield event
                event_counter +=1

            if not event_counter:
                self.write_warning("No Findings data available for the given parameters")

            logger.info("Successfully retrieved Findings from Risksense API ")
        
        except Exception as e:
            self.write_error(str(e))

    def do_generate(self, api_key, logger):
        raise NotImplementedError()