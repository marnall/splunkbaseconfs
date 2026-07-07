import os
import time


class Logger(object):
    ERROR, INFO, DEBUG = range(1, 4)
    level = DEBUG
    level_name = {ERROR: 'error', INFO: 'info', DEBUG: 'debug'}

    def __init__(self, logfile='/log/log.txt'):
        bin_dir = os.path.dirname(os.path.join(os.getcwd(), __file__))
        local_dir = os.path.normpath(os.path.join(bin_dir, "..", "local"))
        self.logfile = os.path.normcase(''.join([local_dir, logfile]))
        self.logpath = os.path.dirname(self.logfile)

        if not os.path.exists(self.logpath):
            os.makedirs(self.logpath)

    def get_name(self, level):
        return self.level_name.get(level, 'debug')

    def write_to_log(self, level, message):
        output = file(self.logfile, "a+")
        if(level <= self.level):
            datetime = time.strftime("%d-%m-%Y %H:%M:%S")
            log = ''.join([datetime, " [", self.get_name(level), "] ", message, "\n"])
            output.write(log)
        output.close()
