import sys
import os
import logging
import json
from datetime import datetime
import splunk
import splunk.entity as entity

# Load own libs from ../lib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Import modules from ../lib
import splunklib.client as client
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators

# Set up logging to stderr
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', stream=sys.stderr)
logger = logging.getLogger(__name__)

@Configuration()
class ReadSlidedeckCommand(GeneratingCommand):
    deck = Option(
        doc='''
        **Syntax:** **deck=***<deck_name>*
        **Description:** Name of the deck to read from''',
        require=True, validate=validators.Fieldname())

    def generate(self):
        try:
            conf_file = 'slidedeck'
            try:
                logger.error("get entity")
                # Get the specific stanza
                stanza = entity.getEntity(
                    'configs/conf-' + conf_file, self.deck, sessionKey=self.metadata.searchinfo.session_key, namespace='betterslides', owner='-')
            
                logger.error("get stanza")
                # Read the 'slidedeck' setting
                slidedeck_json = stanza.get('slidedeck', '{}')
                print(slidedeck_json, file=sys.stderr)
            
                logger.error("parse json")
                # Parse the JSON
                records = json.loads(slidedeck_json)

                logger.error("loop records")
                # Yield each record as a separate event
                for record in records:
                    # Ensure _time field exists
                    #if '_time' not in record:
                    #    record['_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    yield record
                logger.error("done loop records")

            except KeyError:
                logger.error(f"Stanza {self.deck} not found in {conf_file}")
                yield {'error': f"Stanza {self.deck} not found"}

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON data: {str(e)}", exc_info=True)
            yield {'error': f"Invalid JSON data in stanza {self.deck}"}
        except Exception as e:
            logger.error(f"Unexpected error in generate method: {str(e)}", exc_info=True)
            yield {'error': str(e)}

dispatch(ReadSlidedeckCommand, sys.argv, sys.stdin, sys.stdout, __name__)
