class Error(Exception):
	def __init__(self, message):
		# Call the base class constructor with the parameters it needs
		super(Error, self).__init__(message)

		# store the error message
		self.message = message