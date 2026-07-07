import logging
import logging.handlers
import random


class SIMLogHandler(logging.handlers.RotatingFileHandler):
    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0,
                 encoding=None, delay=False, errors=None, random_int_range=200):
        '''
        We are appending a random number to the file name to make it distinctive because only
        one python process can write to a single log file. This log life will have multiple
        processes writing to it so ideally we want to generate one file per process.
        Random numbers range will be 200 and mostly customers will have less than
        50 SIM Modular Inputs. Sometimes, it may end up being one file per 2-3 processes but
        mostly it should be one file per process. This should be fine because we have seen
        that 4-6 processes are able to write to the same file.
        '''
        # Note: We are limiting the range of this random integer to 200 because we don't want
        # to create too many files in the directory. Only increase this range if it's absolutely
        # necessary.
        random_id = str(random.randint(1, random_int_range))
        new_file_path = filename.replace("<insert_random_id>", random_id)

        super(SIMLogHandler, self).__init__(
            new_file_path, mode, maxBytes, backupCount, encoding, delay, errors
        )
