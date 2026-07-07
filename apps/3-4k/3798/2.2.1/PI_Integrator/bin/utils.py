def convertJsonToDict(obj):
	import json
	return json.loads(obj)

def convertDictToJson(obj):
	import json
	return json.dumps(obj)

class ArgSpecList:
	def __init__(self):
		self.args = []
	def addOptArg(self, argName):
		arg = self.ArgSpec()
		arg.argName = argName
		arg.isRequired = False
		self.args.append(arg)
		return arg
	def addReqArg(self, argName):
		arg = self.ArgSpec()
		arg.argName = argName
		arg.isRequired = True
		self.args.append(arg)
		return arg
	def addOptArgGrp(self, grpName, isJSON, argNames, allRequired):
		arg = self.ArgGroupSpec()
		arg.grpName = grpName
		arg.grpRequired = False
		arg.isJSON = isJSON
		arg.argNames = argNames
		arg.allRequired = allRequired
		self.args.append(arg)
		return arg
	def addReqArgGrp(self, grpName, isJSON, argNames, allRequired):
		arg = self.ArgGroupSpec()
		arg.grpName = grpName
		arg.grpRequired = True
		arg.isJSON = isJSON
		arg.argNames = argNames
		arg.allRequired = allRequired
		self.args.append(arg)
		return arg
	def getReqArgs(self):
		return [arg for arg in self.args if (isinstance(arg, self.ArgSpec) and arg.isRequired) or (isinstance(arg, self.ArgGroupSpec) and arg.grpRequired)]
	def getArgNames(self):
		names = []
		for arg in self.args:
			if isinstance(arg, self.ArgSpec):
				names.append(arg.argName)
			elif isinstance(arg, self.ArgGroupSpec):
				names.append(arg.grpName)
				for argName in arg.argNames:
					names.append(argName)
		return names
	def validatePayload(self, payload):
		isValid = True
		argErrors = ArgErrorList()
		if isinstance(payload, basestring):
			payload = convertJsonToDict(payload)
		if isinstance(payload, dict):
			# Check the payload doesn't contain unsupported args
			for key in payload.keys():
				if key not in self.getArgNames():
					isValid = False
					argErrors.addError(None, key + ' is not supported by this endpoint.')
			if isValid:
				# Check the payload has all the required args
				for arg in self.getReqArgs():
					if isinstance(arg, self.ArgSpec):
						if arg.argName not in payload.keys() or (payload[arg.argName] in [None, ''] or len(str(payload[arg.argName]).strip()) <= 0):
							isValid = False
							argErrors.addError(arg.argName, arg.argName + ' is required.')
					elif isinstance(arg, self.ArgGroupSpec):
						grpPayload = payload
						if arg.isJSON:
							if arg.grpName not in grpPayload.keys():
								isValid = False
								argErrors.addError(arg.grpName, arg.grpName + ' is required.')
								break
							grpPayload = convertJsonToDict(grpPayload[arg.grpName])
						if arg.allRequired:
							for argName in arg.argNames:
								if argName not in grpPayload.keys() or (grpPayload[argName] in [None, ''] or len(str(grpPayload[argName]).strip()) <= 0):
									isValid = False
									argErrors.addError(argName, argName + ' is required.')
						else:
							found = False
							for argName in arg.argNames:
								if argName in grpPayload.keys() and not (grpPayload[argName] in [None, ''] or len(str(grpPayload[argName]).strip()) <= 0):
									found = True
									break
							if not found:
								isValid = False
								argErrors.addError(arg.grpName, arg.grpName + ' is required.')
		else:
			raise Exception('Unsupported payload type (%d), pass a dict or string instead.' % payload.__class__.__name__)
		return payload, isValid, argErrors
	class ArgSpec:
		argName = []
		isRequired = False
	class ArgGroupSpec:
		grpName = []
		grpRequired = False
		isJSON = False
		argNames = []
		allRequired = False

class ArgErrorList:
	def __init__(self):
		self.errors = {}
	def addError(self, argName, message):
		if argName in [None, ''] or len(argName) <= 0:
			argName = '_'
		if argName in self.errors:
			self.errors[argName].append(message)
		else:
			self.errors[argName] = []
			self.errors[argName].append(message)
	def getErrors(self):
		return self.errors