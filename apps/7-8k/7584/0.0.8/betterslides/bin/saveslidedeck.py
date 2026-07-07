import sys
import os
import logging
import json
import splunk
import splunk.rest as rest
import splunk.entity as entity
import splunk.auth

# Load own libs from ../lib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Import modules from ../lib
import splunklib.client as client
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

# Set up logging to stderr
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', stream=sys.stderr)
logger = logging.getLogger(__name__)

@Configuration()
class SaveSlidedeckCommand(StreamingCommand):
    deck = Option(
        doc='''
        **Syntax:** **deck=***<deck_name>*
        **Description:** Name of the deck to save the results to''',
        require=True, validate=validators.Fieldname())

    def ensure_conf_file(self, service):
        conf_file = 'slidedeck'
        try:
            # Check if the conf file exists
            service.confs[conf_file]
            logger.info(f"Conf file {conf_file} already exists")
        except KeyError:
            logger.info(f"Conf file {conf_file} not found. Creating...")
            try:
                # Create the conf file
                service.confs.create(conf_file)
                logger.info(f"Conf file {conf_file} created successfully")
            except Exception as create_error:
                logger.error(f"Error creating conf file: {str(create_error)}")
                raise

    def save_to_conf(self, service, records):
        #conf_file = 'slidedeck'

        try:
            # Convert records to JSON
            json_data = json.dumps(list(records))
            print(json_data, file=sys.stderr)

            # Get all stanzas in the conf file
            conf_file = splunk.entity.getEntities('configs/conf-slidedeck', sessionKey=self.metadata.searchinfo.session_key, namespace='betterslides', owner='-')
            
            # Create the new stanza
            new_stanza = splunk.entity.Entity('configs/conf-slidedeck', self.deck, namespace='betterslides', owner=self.metadata.searchinfo.username)

            # Add settings to the new stanza
            new_stanza["slidedeck"] = json_data
            
            # Save the new stanza
            splunk.entity.setEntity(new_stanza, sessionKey=self.metadata.searchinfo.session_key)
            
            logger.info(f"Save operation completed successfully for stanza {self.deck}")
            return True
        except Exception as e:
            logger.error(f"Error saving slidedeck: {str(e)}", exc_info=True)
            return False

    def stream(self, records):
        try:
            # Create a Service instance using the session key
            service = client.Service(token=self.metadata.searchinfo.session_key)

            self.ensure_conf_file(service)
            
            all_records = list(records)
            save_success = self.save_to_conf(service, all_records)
            
            for record in all_records:
                record['_slidedeck_saved'] = save_success
                record['_slidedeck_deck'] = self.deck
                if not save_success:
                    record['_slidedeck_error'] = "Error saving to conf file"
                yield record
            
        except Exception as e:
            logger.error(f"Unexpected error in stream method: {str(e)}", exc_info=True)
            for record in records:
                record['_slidedeck_saved'] = False
                record['_slidedeck_deck'] = self.deck
                record['_slidedeck_error'] = str(e)
                yield record

dispatch(SaveSlidedeckCommand, sys.argv, sys.stdin, sys.stdout, __name__)