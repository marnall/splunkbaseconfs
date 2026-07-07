import sys
import splunk.Intersplunk as si
import logging, logging.handlers
import os

class Usage(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

(isgetinfo, sys.argv) = si.isGetInfo(sys.argv)
if isgetinfo:
		#outputInfo(streaming, generating, retevs, reqsop, preop, timeorder=False):
		si.outputInfo(True, False, True, False, None, False)
		sys.exit(0)

#results = si.readResults(None, None, True)
results,dummyresults,settings = si.getOrganizedResults()

def setup_logger():
	"""
	Setup a logger for the search command
	"""
	
	logger = logging.getLogger('gaugetable')
	logger.setLevel(logging.DEBUG)
	
	file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/gaugetable.log' )
	formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
	file_handler.setFormatter(formatter)
	
	logger.addHandler(file_handler)
	
	return logger

def isNumber(s):
	"""
	Take in a string return whether or not it is a number
	"""
	try:
		val = float(s)
		return True
	except ValueError:
		return False

if __name__ == '__main__':
	try:
		logger = setup_logger()
		
		if len(sys.argv) < 3:
			raise Usage(len(sys.argv))
		
		logger.debug(sys.argv)
		
		x = sys.argv[1];
		yList = sys.argv[2:]
		logger.debug(x)
		logger.debug(yList)
		
		#we don't need to run these checks everytime, especially if there are a lot of strings
		xBool = isNumber(x)
		yBoolList = []
		for y in yList:
			yBoolList.append(isNumber(y))
		
		for r in results:
			if xBool:
				#this is dumb, but they set everything to a set value
				r["x"] = x
			else:
				#put the actual value to the x field
				if r.get(x):
					r["x"] = r[x]
				else:
					#if it doesn't exist default to 0
					r["x"] = 0
			for ii in range(len(yList)):
				if yBoolList[ii]:
					#set to a set number
					r["y"+str(ii+1)] = yList[ii]
				else:
					#put in field value or default to 0
					if r.get(yList[ii]):
						r["y"+str(ii+1)] = r[yList[ii]]
					else:
						#default to 0
						r["y"+str(ii+1)] = 0

		si.outputResults(results)

	except Usage as e:
		results = si.generateErrorResults("Received '%s' arguments. Usage: gaugetable valueField y1,y2,y3..." % e)
		si.outputResults(results)
		
	except Exception as e:
		import traceback
		stack =  traceback.format_exc()
		logger.error("Error '%s'" % stack)
		results = si.generateErrorResults("Error occurred while running custom command: '%s'. See gaugetable.log for more details." % str(e))
		si.outputResults(results)
