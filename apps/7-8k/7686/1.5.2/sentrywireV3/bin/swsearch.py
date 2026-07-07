# SentryWire specific imports
from sentrywire.client import Sentrywire
from swstorage import SentryWireStore
from swutils import *
from swconst import *

# General imports
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional
import sys, json, time, configparser, re

try:
    from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
    from splunklib import client
except ImportError as e:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".", "lib"))
    from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
    from splunklib import client

@Configuration()
class SentrywireCommand(StreamingCommand):
    search_name = Option(require=True, validate=validators.Match("search_name", ".*"))
    begin_time = Option(require=False, validate=validators.Match("begin_time", ".*"))
    end_time = Option(require=False, validate=validators.Match("end_time", ".*"))
    search_filter = Option(require=True, validate=validators.Match("search_filter", ".*"))
    node_name = Option(require=True, validate=validators.Match("node_name", ".*")) # Ask Chris about this
    max_packets = Option(require=False, default=10000, validate=validators.Integer())

    # Grouping of events
    def stream(self, events):
        splunk_user = self._metadata.searchinfo.username
        session_key = self._metadata.searchinfo.session_key

        logger = setup_logging()
        if SENTRYWIRE_DEBUG_MODE:
            logger.warning("Debug mode is enabled! This disables SSL checks!")

        # Splunk password storage handling
        service = client.connect(token=session_key, app='sentrywireV3', owner=splunk_user)
        logger.info(f"Splunk user '{splunk_user}' authenticated with Splunk using session key")

        storage_passwords = service.storage_passwords

        # TODO: Clean this up
        try:
            storage_passwords = service.storage_passwords
            if not storage_passwords:
                raise Exception("Failed to load stored passwords")
        except Exception as e:
            logger.error(f"Failed to load stored passwords", extra=debug_extras)
            raise e

        # TODO: Redo all this logging with a json based format
        # NOTE: Credential retrieve HERE is the cause of the error
        try:
            credential_string = get_encrypted_token(storage_passwords, splunk_user)
            host, token = credential_string.split(':')
            logger.info(f"Retrieved Sentrywire login info for Splunk user '{splunk_user}'")
        except KeyError as e:
            logger.error(f"Failed to retrieve Sentrywire login information for Splunk user '{splunk_user}'")
            raise e
        except AttributeError as e:
            logger.error(f"Failed to parse {splunk_user}'s credential string '{credential_string}'")
            raise e

        # Make sure to provide a valid 'rest_token'
        sw = Sentrywire(host=host, rest_token=token, ssl_verify=(not SENTRYWIRE_DEBUG_MODE))

        parsed_begin_time, parsed_end_time = parse_datetime(self.begin_time, self.end_time)
        
        # Check if search was submitted successfully 
        # Using '.strip()', but may not be needed
        try:
            response = sw.searches.create(
                search_name=self.search_name.strip('\"'),
                begin_time=parsed_begin_time,
                end_time=parsed_end_time,
                search_filter=self.search_filter.strip('\"'),
                max_packets=self.max_packets)
            if not response.status_code == 200:
                raise Exception(f"status code: {response.status_code}")
        except Exception as e:
            logger.error(f"Search initiated by Splunk user '{splunk_user}' failed: {e}")
            raise e

        # Try block handles parsing the server response
        try:
            # Content should come back as b'[{...},...]\n' so we need to parse using json
            # Currently, we only care about the first entry
            content = json.loads(response.content)

            # "Fix" for potential nested lists
            for _ in range(4):
                if isinstance(content, dict):
                    break
                content = content[0]
            
            # Use '.get()' to prevent any errors caused by missing links                 
            check_status_link = content.get("checkstatus")
            get_pcaps_link = content.get("getpcaps")
            metadata_link = content.get("metadata")
            objects_link = content.get("objects")
        except Exception as e:
            logger.error(f"Failed to parse search response for search started by Splunk user '{splunk_user}': {e}")
            raise e

        search_id = re.search(r"searchname=([\w\d_]+)", check_status_link).group(1)

        try:
            db = SentryWireStore()
        except Exception as e:
            logger.error("Failed to initialize Sentrywire SearchStore")
            raise e

        db.store_search(
            splunk_user=splunk_user,
            search_id=search_id,
            search_filter=self.search_filter.strip('\"'),
            begin_time=parsed_begin_time,
            end_time=parsed_end_time,
            check_status_link=check_status_link,
            get_pcaps_link=get_pcaps_link,
            metadata_link=metadata_link,
            objects_link=objects_link
        )

        db.remove_expired(splunk_user=splunk_user)

        event = [
            {
                '_time': time.time(),
                'event_no': 1,
                'raw': f"Search Status: {check_status_link}\nGet Pcaps: {get_pcaps_link}\nGet Metadata: {metadata_link}\nGet Objects: {objects_link}",
                'checkstatus': check_status_link,
                'getpcaps': get_pcaps_link,
                'metadata': metadata_link,
                'objects': objects_link
            }
        ]
        return event
        


def parse_datetime(begin_time: str, end_time: str) -> Optional[Tuple[datetime, datetime]]:
    """Brute force conversion of datetime strings to datetime objects

    Args:
        begin_time (str): a string containing a datetime
        end_time (str): a string containing a datetime

    Raises:
        Exception: Unable to parse a datetime from both arguments

    Returns:
        Optional[Tuple[datetime, datetime]]: Tuple of Datetime objects or Tuple of None
    """
    if not begin_time or not end_time:
        raise ValueError(f"Timestamps must not be 'None', begin_time: {begin_time}, end_time: {end_time}")

    parsed_begin_time, parsed_end_time = None, None

    try:
        parsed_begin_time = datetime.strptime(begin_time,"%Y-%m-%dT%H:%M:%S")
        parsed_end_time = datetime.strptime(end_time,"%Y-%m-%dT%H:%M:%S")
    except:
        pass
    
    if not (parsed_begin_time and parsed_end_time):
        try:
            parsed_begin_time = datetime.strptime(begin_time,"%Y-%m-%dT%H:%M")
            parsed_end_time = datetime.strptime(end_time,"%Y-%m-%dT%H:%M")
        except:
            pass
    
    if not (parsed_begin_time and parsed_end_time):
        try:
            parsed_begin_time = datetime.strptime(begin_time,"%Y-%m-%d %H:%M")
            parsed_end_time = datetime.strptime(end_time,"%Y-%m-%d %H:%M")
        except:
            pass
    
    if not (parsed_begin_time and parsed_end_time):
        try:
            parsed_begin_time = datetime.strptime(begin_time,"%Y-%m-%d %H:%M:%S")
            parsed_end_time = datetime.strptime(end_time,"%Y-%m-%d %H:%M:%S")
        except:
            pass
    
    if (parsed_begin_time and parsed_end_time):
        return parsed_begin_time, parsed_end_time
    else:
        raise Exception("Unable to parse 'begin_time' and/or 'end_time'")

try:
    dispatch(SentrywireCommand, sys.argv, sys.stdin, sys.stdout, __name__)
except Exception as e:
    print(str(e))
