import sys
import json
from radar_client import RadarClient
from radar_settings_manager import RadarSettingsManager


def send_message(payload):
    """
    Create outbound payload from alert contents and POST to RADAR API endpoint.
    """
    settings_mgr = RadarSettingsManager(payload['server_uri'],
                                        payload['session_key'],
                                        payload['app'],
                                        payload['owner'])
    cli = RadarClient(settings_mgr.get_radar_settings())
    if not 'configuration' in payload or not payload['configuration']:
        raise Exception("RADAR add-on has not been configured.")
    cli.create_incident(payload['configuration'], payload['results_link'], payload['search_name'])

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        try:
            # Retrieve message payload from Splunk
            raw_payload = sys.stdin.read()
            payload = json.loads(raw_payload)
            send_message(payload)
        except BaseException, e:
            print >> sys.stderr, "FATAL %s: %s" % (e.__class__.__name__, e)
            sys.exit(3)
    else:
        print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit(1)
