import traceback
import time
import sys

import splunk.auth

from nbalib import destinations
from nbalib import sections
from nbalib import logger
from nbalib import confs
from nbalib import api


class DestPullError(Exception):
    pass


class DestPull(object):
    """
    DestPull recives destinations summary from AlphaSOC API. Every response
    can contains a new follow value which must be saved in app config.
    It is used to define which items has been already fetched from the API.
    """

    def __init__(self, session_key, log):
        self._session_key = session_key
        self._log = log

        self.app_config = confs.Config(self._session_key, stanza=sections.Destinations.name)

        self.runtime_health_check()
        if not self.is_enabled():
            raise DestPullError("dest pull is disabled")

        self.api_key = self.authorize()

    def runtime_health_check(self):
        self.app_config.set('last_runtime', int(time.time()))

    def is_enabled(self):
        return self.app_config.is_enabled('enabled', default=False)

    def authorize(self):
        auth = api.Auth(self._session_key)
        account_details = auth.account_status(self.app_config, check_master_node=True)
        return account_details.api_key

    def pull(self):
        retrived = 0
        emitted = 0

        more = True
        while more is True:
            follow = self.get_follow()
            response = self.fetch_destinations(follow)

            retrived += len(response.destinations)
            emitted += self.emit_destinations(response.destinations)
            self.save_follow(response.follow)

            more = response.more
            if more is True:
                self._log.info("results were truncated, make additional call to the api")

        self._log.info("retrived destinations: {0}, emitted destinations: {1}".format(retrived, emitted))

    def get_follow(self):
        follow = self.app_config.get("follow", "")
        self._log.info('got current follow value: {0}'.format(follow))
        return follow

    def save_follow(self, follow):
        if follow:
            self.app_config.set("follow", follow)
            self._log.info('new follow value set to: {0}'.format(follow))

    def fetch_destinations(self, follow):
        alphasoc_api = api.API(self._session_key)
        result = alphasoc_api.destinations(self.api_key, follow)

        if result.has_error():
            self._log.error('could not fetch destinations from api: {0}'.format(result.error))
            if result.code != 429:
                self._log.ui_append(logger.MessageAPIConnection(result.code))

        return result

    def emit_destinations(self, api_dests):
        emitted = 0

        for api_dest in api_dests:
            try:
                dest = destinations.Destination(api_dest)
                print(dest.splunk_format())
                emitted += 1
            except Exception as exc:
                self._log.error(repr(exc))

        return emitted


def main(log):
    log.info("dest pull start")

    # If the script is called by splunk, session key is passed in stdin
    if len(sys.argv) > 1:
        session_key = splunk.auth.getSessionKey(sys.argv[1], sys.argv[2])
    else:
        session_key = sys.stdin.readline()
    log.info("got session key")

    try:
        dest_pull = DestPull(session_key, log)
        log.info("dest pull created")

        dest_pull.pull()
    except (DestPullError, api.MasterNodeError) as exc:
        log.warn(str(exc))
    except api.AuthError as exc:
        log.warn(repr(exc))
        log.ui_append(logger.MessageUnauthorizedAPI(exc.api_messages))
    except confs.PerrmisionException as exc:
        log.error(repr(exc))
        log.ui_append(logger.MessageUnauthorizedSplunk())
    except Exception as exc:
        log.error(repr(exc))
        log.error(traceback.format_exc())
        log.ui_append(logger.MessageUnexpectedError(repr(exc)))
    finally:
        config = confs.Config(session_key, stanza=sections.Destinations.name)
        log.ui_save(config)

    log.info("dest pull exit")


if __name__ == "__main__":
    LOGGER = logger.LoggerUI.setup_logger(sections.NBA.name, "dest_pull")

    try:
        main(LOGGER)
    except Exception as exc:
        LOGGER.error(repr(exc))
        LOGGER.error(traceback.format_exc())
