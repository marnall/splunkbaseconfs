from datetime import datetime, timedelta
class Collector:

	def __init__(self, interval):
		self.interval = interval
		self.time_of_last = None

	def update(self, connection, currenttime):
		if (self.interval == 0):
			return None
		if (self.time_of_last == None or (currenttime - self.time_of_last) >= timedelta(seconds=self.interval)):
			self.time_of_last = currenttime
			return self.collect(connection)
 
