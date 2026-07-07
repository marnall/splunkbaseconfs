import logging
import logging.handlers
import os, os.path as op
from .patterns import singleton

@singleton
class LogHandler(object):
	def __init__(self, namespace=None, defaultLogLevel=logging.INFO):
		self._loggers = {}
		self._defaultLogLevel = defaultLogLevel
		if namespace is None:
			namespace = self.__getNamespaceFromPath(op.abspath(__file__))
		if namespace:
			namespace = namespace.lower()
		self._namespace = namespace

	def getLogger(self, name, level=None, maxFileSize=25000000, filesToKeep=5):
		if level is None:
			level = self._defaultLogLevel
		name = self.__getLogFileName(name)
		if name in self._loggers:
			return self._loggers[name]
		logfile = op.normpath(op.join(os.environ.get("SPLUNK_HOME", "."), 'var', 'log', 'splunk', name))
		logger = logging.getLogger(name)
		if not any([True for h in logger.handlers if h.baseFilename == logfile]):
			file_handler = logging.handlers.RotatingFileHandler(logfile, mode='a', maxBytes=maxFileSize, backupCount=filesToKeep)
			formatter = logging.Formatter("%(asctime)s %(levelname)s pid=%(process)d tid=%(threadName)s file=%(filename)s:%(funcName)s:%(lineno)d | %(message)s")
			file_handler.setFormatter(formatter)
			logger.addHandler(file_handler)
			logger.setLevel(level)
			logger.propagate = False
		self._loggers[name] = logger
		return logger

	def setLogLevel(self, level, name=None):
		if name is not None:
			name = self._get_log_name(name)
			logger = self._loggers.get(name)
			if logger is not None:
				logger.setLevel(level)
		else:
			self._defaultLogLevel = level
			for logger in self._loggers.itervalues():
				logger.setLevel(level)

	def __getNamespaceFromPath(self, absolutePath):
		parts = absolutePath.split(op.sep)
		parts.reverse()
		try:
			idx = parts.index("apps")
		except ValueError:
			return None
		else:
			try:
				if parts[idx + 1] == "etc":
					return parts[idx - 1]
				return None
			except IndexError:
				return None

	def __getLogFileName(self, name):
		if name.endswith(".py"):
			name = name.replace(".py", "")
		if self._namespace:
			name = "{}_{}.log".format(self._namespace, name)
		else:
			name = "{}.log" .format(name)
		return name