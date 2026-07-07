"""
Wrapper around the stdlib logger to provide Splunk-friendly contextual, structured logging
"""
import logging

class StructuredContextualLoggerAdapter(logging.LoggerAdapter):
    def __init__(self, logger):
        super().__init__(logger, extra={})

    def process(self, msg: str, kwargs):
        context_vars = self.extra
        
        if "extra" in kwargs:
            context_vars = {**kwargs["extra"], **self.extra}
        formatted_message = self._format_message(msg, context_vars)
        return formatted_message, kwargs

    def _format_message(self, msg, context_variables):
        """Format a message, adding contextual variables to the log message

        Args:
            msg (string): The original log message
            context_variables (dict): Context variables to be added to the structured log output
        """

        msg = f'msg="{msg}"'

        for key, value in context_variables.items():

            if " " in key:
                key = f'"{key}"'

            msg += f' {key}="{value}"'
        
        return msg


class StructuredContextualLogger:
    """Logger 
    """
    def __init__(self, name, level):
        self.logger = logging.getLogger(name)
        self.structured_logger = StructuredContextualLoggerAdapter(self.logger)
        self.structured_logger.setLevel(level)

        self.context_vars = {}

        
    def setVar(self, key, val):
        self.context_vars[key] = val
        self.structured_logger.extra = self.context_vars

    def delVar(self, key):
        if key in self.context_vars:
            del self.context_vars[key]

    def addHandler(self, *args, **kwargs):
        self.logger.addHandler(*args, **kwargs)

    def setLevel(self, level: str):
        self.structured_logger.setLevel(level)

    def info(self, *args, **kwargs):
        self.structured_logger.info(*args, **kwargs)

    def warning(self, *args, **kwargs):
        self.structured_logger.warning(*args, **kwargs)

    def debug(self, *args, **kwargs):
        self.structured_logger.debug(*args, **kwargs)

    def critical(self, *args, **kwargs):
        self.structured_logger.critical(*args, **kwargs)

    def exception(self, *args, **kwargs):
        self.structured_logger.exception(*args, **kwargs)

    def error(self, *args, **kwargs):
        self.structured_logger.error(*args, **kwargs)

if __name__ == "__main__":

    logger = StructuredContextualLogger('hello', logging.DEBUG)
    console_formatter = logging.Formatter("[%(levelname)s] %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)

    logger.addHandler(console_handler)

    logger.setVar("funkd asd", "test")

    logger.info("hello")

    logger.delVar("funkd asd")
    logger.info("starting", {"task_status": "asd", "sid": "asd"})
