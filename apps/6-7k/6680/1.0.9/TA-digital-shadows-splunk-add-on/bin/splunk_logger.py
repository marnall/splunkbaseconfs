from searchlight.logger import Logger


class SplunkLogger(Logger):
    def __init__(self, helper):
        self.helper = helper

    def info(self, msg, *args, **kwargs):
        return self.helper.log_info(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        return self.helper.log_debug(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        return self.helper.log_warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        return self.helper.log_error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        return self.helper.log_critical(msg, *args, **kwargs)
