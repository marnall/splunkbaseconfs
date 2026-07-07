#!/usr/bin/env python

import os
import os.path
import sys
import csv
import re

# Set some variables to start with
# Please only use alphanumeric characters in your google docs name
inFile = "Anonymous Mood Radiator"

# plus a sanity check to verify there are no issues with the google doc name
if re.search(r'>|<|#|/|;|\|', inFile):
	print "ERROR - your inFile contains characters that could potentially destroy your splunk instance"
	print "ERROR - your inFile contains characters such as <, >, #, /, | and ;"
	print "ERROR - please choose a new name for your inFile before continuing"
	sys.exit(1)

# Locate your app directory
appDir = os.getcwd().rstrip('bin')
# Locate the path for script
scriptLocal = "%s/%s" % (os.getcwd(), __file__)
# create your outfile
outFile = "%sshowlog.log" % appDir


# Line count function
def file_len(fname):
	count = 0
	for x in open(fname):
		count += 1
	return count

# Map to values
MoodDict = { "Very sad" : 1,
		"Confused" : 2,
		"Neutral" : 3,
		"Happy" : 4,
		"Very Happy" : 5}


# Run googlecl to bring down the latest version of the file
cmd = "google docs get %s . --format=csv" % (inFile[0:inFile.find(" ")])

#print "[INFO] - Accessing data from google, and turning it into csv"
#print "[INFO] - Running Command: %s" % (cmd)

os.system(cmd)


# Get the previous line count of the file from the linecount.log file
f = open("linecount.log")
l = f.read()
oldLineCount = int(l.strip("\n"))
#print "[INFO] - Old Line Count: %d" % (oldLineCount)


# Get the current file line count
csvFile = "%s.csv" % (inFile)
newLineCount = int(file_len(csvFile))
#print "[INFO] - New Line Count: %d" % (newLineCount)


# Test if there is new lines in the file
if oldLineCount < newLineCount:
	# If there are new lines move them into the splunk file
	dataFile = open(csvFile, "rb", 0)
	linesCounter = 1
	for line in dataFile:
		# print "[INFO] - linesCounter %d" % linesCounter
		if linesCounter > oldLineCount:
			reader = csv.reader([line], skipinitialspace=True)
			for r in reader:
				# Map the moods to their values
				your_mood = MoodDict[r[2]]
				team_work = MoodDict[r[4]]
				deadline = MoodDict[r[5]]
				process = MoodDict[r[6]]
				leadership = MoodDict[r[7]]

				# Now create the csv entry
				entry = 'timestamp="%s" project="%s" your_mood="%s" comments="%s" team_work="%s" deadline="%s" process="%s" leadership="%s"\n' % (r[0], r[1], your_mood, r[3], team_work, deadline, process, leadership)
				
				# Now add it to the splunk output doc
				# First test to compare the computed paths to local files
				if os.path.abspath(scriptLocal).startswith(appDir):
					f = open(outFile, "a")
					f.write(entry)
					f.close()
				else:
					print "ERROR - your computed path and local files are in different directories"
					sys.exit(1)
		linesCounter += 1
	dataFile.close()

	# Then update the linecount.log file with the new line count
	if os.path.abspath(scriptLocal).startswith(appDir):
		f = open("linecount.log", "w")
		f.write(str(newLineCount))
		f.close()
