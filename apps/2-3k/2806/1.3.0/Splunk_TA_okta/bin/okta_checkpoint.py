import json
import logging
import os
import traceback
from datetime import datetime

from splunktalib.common import log

_LOGGER = log.Logs().get_logger("ta_okta", level=logging.DEBUG)


class OktaCheckpoint(object):
    """
    Okta checkpoint base class
    """
    def __init__(self, config):
        self.config = config
        self._fname = self._get_fname(config.get("stanza"))
        self.url = config.get("url")
        self.contents = {}
        self.last_event_id = ""
        self.last_event_date = ""

    def _get_fname(self, name):
        """
        the method to generate the full name of the checkpoint file.
        """
        fname = "okta_{}.ckpt".format(name)
        return os.path.join(self.config.get("checkpoint_dir"), fname)

    def _get_content(self):
        return {
            "last_event_date": self.last_event_date,
            "last_event_id": self.last_event_id,
        }

    def _reset_check_point(self):
        self.last_event_id = ""
        self.last_event_date = ""

    def is_end_date_expired(self):
        """
        Check if the end_date is expired.
        """
        end_date = self.config.get("end_date", "")
        last_event_date = self.last_event_date
        if end_date and last_event_date:
            ldate = datetime.strptime(last_event_date, '%Y-%m-%dT%H:%M:%S.%fZ')
            edate = datetime.strptime(end_date, '%Y-%m-%dT%H:%M:%S.%fZ')
            if ldate >= edate:
                _LOGGER.info("End date %s is expired.", end_date)
                return True
        return False

    def read(self):
        _LOGGER.info("Read Checkpoint from file %s", self._fname)
        try:
            if not os.path.isfile(self._fname):
                raise ValueError("Checkpoint file doesn't exist")

            with open(self._fname, "r") as f:
                content = f.read().strip()
                if not content:
                    raise ValueError("Empty checkpoint content")
                ckpt = json.loads(content)
                self.contents = ckpt
                ckpt_url = ckpt.get(self.url, {})
                self.last_event_date = ckpt_url.get("last_event_date", "")
                self.last_event_id = ckpt_url.get("last_event_id", "")
        except ValueError as ex:
            _LOGGER.info(
                "Checkpoint file format is incorrect. %s", ex)
            self._reset_check_point()
        except Exception as ex:
            _LOGGER.warn(
                "Failed to read Checkpoint from file %s, err: %s, will reset checkpoint",
                self._fname, ex)
            self._reset_check_point()

    def write(self):
        if (not self._fname) or (not self._get_content()):
            _LOGGER.info("No checkpoint")
            return None
        _LOGGER.info("Write Checkpoint to file %s.", self._fname)

        with open(self._fname + ".new", "w") as f:
            ckpt = self._get_content()
            self.contents[self.url] = ckpt
            json.dump(self.contents, f, indent=4)

        file_exist = os.path.isfile(self._fname)
        if file_exist:
            try:
                os.rename(self._fname, self._fname + ".old")
            except (OSError, IOError):
                _LOGGER.error(traceback.format_exc())
        else:
            _LOGGER.info(
                'The checkpoint file (%s) of the last event does not exist.'
                ' Splunk add-on for okta will create a new checkpoint file.',
                self._fname)

        os.rename(self._fname + ".new", self._fname)

        if file_exist:
            try:
                os.remove(self._fname + ".old")
            except (OSError, IOError):
                _LOGGER.error(traceback.format_exc())
