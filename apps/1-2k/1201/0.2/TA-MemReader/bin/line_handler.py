import time
from datetime import date
import platform
import socket
import sys

def AddTimeStamp():
	current="[" + time.strftime("%Y-%m-%dT%H:%M:%S") + "]" 
	return current

def BuildLogLine( StoredLog, PrntLineNumber=False ):
	""" This fuction takes a ctypes object that is dumped from memory,
		appends a timestamp to the front of the line and an optional line number.
		If no line number is supplied, only a timestamp will be appended.
		This function will also create a new line anytime there is a null 
		returned in the ctype object.  This function will not return partial lines
		and must have atleast 1 null char in the string.
		
		This method will output as a list object.
	"""
	try:
		ListLineNumber=1
		LogLineContents = []
		current = AddTimeStamp()
		if PrntLineNumber:
			current = current + "[" + str(ListLineNumber) +"] "
		for value in StoredLog.raw:
			if ord(value) != 0:
				current=current+value
			else:
				LogLineContents.insert(ListLineNumber-1, current)
				ListLineNumber=ListLineNumber + 1
				current = AddTimeStamp()
				if PrntLineNumber:
					current = current + "[" + str(ListLineNumber) +"] "
		return LogLineContents
		
	except:
		print "Failure in line printing"

def PrintLines( ArrayToPrint, LineToStartOn, LinesToPrint, WriteStdOut=1, SendUDP=0, Ip="127.0.0.1", Port="5005" ):
	""" This function takes a list, and iterates through it's objects and 
		will print the output to standard out or UDP.  Usage is to supply a line number to start
		on, and then a count of how many lines to print.  By default standard out 
		is enabled, while UDP is disabled.
	"""
	try:
		PrintLine=0
		while PrintLine < LinesToPrint: 
			if LineToStartOn == 0:
				if WriteStdOut == 1:
					print ArrayToPrint[0]
				if SendUDP == 1:
					try:
						SendUDPLines(Ip=Ip, Port=Port, Message=ArrayToPrint[0])
					except:
						print "There was a failure from the SendUDPLines method"
				LinesToPrint=LinesToPrint-1
				LineToStartOn=1
			else:
				CurrentLineToPrint = LineToStartOn + PrintLine
				if WriteStdOut == 1:
					print ArrayToPrint[CurrentLineToPrint]
				if SendUDP == 1:
					SendUDPLines(Message=ArrayToPrint[CurrentLineToPrint])
				PrintLine=PrintLine+1
	except:
		print "blah"

def SendUDPLines(Ip="127.0.0.1",Port="5005",Message=""):
	""" This function takes a list, and iterates through it's objects and 
		will print the output to UDP.  Usage is to supply a line number to start
		on, and then a count of how many lines to print.
	"""
	try:
		if Message != "":
			Udp_Message=Message
		else:
			raise Missing_Message
		sock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM ) # UDP
		sock.sendto( Udp_Message, (Udp_Ip, Udp_Port) )
		
	except Missing_Message:
			print "Missing message to send to UDP"
			
	except:
			print "An error occured when trying to send UDP"
		

def FlushSysOut():
	try:
		sys.stdout.flush()
	
	except:
			print "Failed to flush standard out."
		
