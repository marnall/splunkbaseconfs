import json
import logging
import os
import requests
import signal
import sys
import time
from splunk.clilib import cli_common as cli

logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)

polling_interval = 3600

api_response_alert_field = 'event'

api_poll_params_config_stanza = 'area_api_request_params'

api_poll_params_config_file = 'areaoneapi.conf'


def get_self_conf_stanza(stanza, config_file_name):
    '''
    Returns a dictionary of application config params after provided stanza
    and config file
    '''
    appdir = os.path.dirname(os.path.dirname(__file__))
    apikeyconfpath = os.path.join(appdir, 'default', config_file_name)
    apikeyconf = cli.readConfFile(apikeyconfpath)
    localconfpath = os.path.join(appdir, 'local', config_file_name)
    if os.path.exists(localconfpath):
        localconf = cli.readConfFile(localconfpath)
        for name, content in localconf.items():
            if name in apikeyconf:
                apikeyconf[name].update(content)
            else:
                apikeyconf[name] = content
    return apikeyconf[stanza]


def get_time_from_time_file():
    '''
    Read and return the epoch time from the file.
    Set the time in the file to the current time if it does not exist
    or is invalid
    '''
    logging.debug('Getting time')
    appdir = os.path.dirname(os.path.dirname(__file__))
    time_file_path = os.path.join(appdir, 'appserver/static', 'timefile.txt')
    try:
        with open(time_file_path, 'r') as f:
            epoch = f.read().strip()
            if epoch:
                try:
                    ts = int(epoch)
                    logging.debug('Got time epoch')
                    return ts

                except Exception:
                    logging.exception("Couldn't get epoch time as int")

    except Exception:
        logging.exception('Time file did not exist')

    return None


class Updater(object):
    '''
    Keeps track of the last update and periodically runs the update on
    a schedule
    '''

    def __init__(self, url, a1s_user, a1s_pass, poll_interval):
        '''
        Returns an instance of the updater.
        @param url: str representing the API URL
        @param a1s_user: str representing API username
        @param a1s_pass: str representing API password
        @param poll_interval: int representing the update interval, in seconds
        '''
        self.url = url
        self.creds = requests.auth.HTTPBasicAuth(a1s_user, a1s_pass)
        self.interval = poll_interval
        # Last time an update was found. Will be updated by self.get_time()
        self.last = None
        self.syslog = logging.getLogger('SyslogClient')
        self.syslog.propagate = False
        self.syslog.setLevel(logging.INFO)

    def set_time(self):
        '''
        Set the epoch time in the file.
        Failure to open the file is fatal.
        '''
        logging.debug('Setting time')
        appdir = os.path.dirname(os.path.dirname(__file__))
        time_file_path = os.path.join(appdir, 'appserver/static', 'timefile.txt')
        with open(time_file_path, 'w') as f:
            if self.last:
                try:
                    f.write(str(self.last))
                    logging.debug('Set time to {}'.format(self.last))
                    return

                except Exception:
                    logging.exception("Couldn't write to time file \"{}\"".format(time_file_path))

    def perform_poll(self, disposition):
        '''
        Polls the API and sends results over index
        '''
        logging.debug('Polling API')

        end_ts = int(time.time())

        if not self.last:
            since_ts = end_ts - self.interval
        else:
            since_ts = self.last

        params = {
            'disposition': disposition,
            'since': str(since_ts),
            'end': str(end_ts),
        }

        try:
            resp = requests.get(self.url, auth=self.creds, params=params)
            if not resp.ok:
                logging.exception("API status {}: {}".format(resp.status_code, resp.reason))
                return

            self.last = end_ts
            update = json.loads(resp.content)
            if update:
                logging.debug('Received {} alerts'.format(len(update)))
                for alert in update:
                    event = alert.get(api_response_alert_field)
                    print(json.dumps(event))
                logging.debug('Polling complete')
                self.set_time()
                return

            logging.debug('No polling content')

        except Exception:
            logging.exception("Exception contacting the API server")


def main():
    def handle_int(signal, stack):
        sys.stderr.write('Exiting\n')
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_int)

    args = get_self_conf_stanza(api_poll_params_config_stanza, api_poll_params_config_file)

    updater = Updater(
        args.get('area_api_url'),
        args.get('username'),
        args.get('password'),
        polling_interval
    )

    updater.last = get_time_from_time_file()

    updater.perform_poll(args.get('disposition'))


if __name__ == '__main__':
    main()
