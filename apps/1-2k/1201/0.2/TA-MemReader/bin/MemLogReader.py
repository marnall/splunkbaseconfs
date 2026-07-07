import os
import re
import sys
from proc_list import *
from memread import *
from line_handler import *
import splunk.clilib.cli_common as cli_common
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import traceback

def check_args():
	try:
		if not len(sys.argv) == 3:
			raise 
	except:
		print "Usage: MemLogReader.py <name of .conf> <name of stanza>"
		exit(1)
		
def setup_conf():
	""" Used to setup any conf file passed into the script.
		returns variable conf_file and stanza_target
	"""
	try:
		global conf_file
		global stanza_target
		conf_file = ""
		stanza_target = ""
		if sys.argv[1].endswith(".conf"):
			conf_file = sys.argv[1]
			stanza_target = sys.argv[2]
		elif sys.argv[2].endswith(".conf"):
			stanza_target = sys.argv[1]
			conf_file = sys.argv[2]
		else:
			raise
		
	except:
		print "Failed to set target configuration file. Make sure filename ends with .conf"
		exit(1)
	

def load_conf(app,conf_file):
	""" Loads copies of a specified configuration file into 2
		dictionaries, default_conf_file and local_conf_file
	"""
	try:
		global default_conf_file
		global local_conf_file
		target_default_conf = make_splunkhome_path(["etc", "apps", app, "default", conf_file])
		target_local_conf = make_splunkhome_path(["etc", "apps", app, "local", conf_file])
		default_conf_file = cli_common.readConfFile(target_default_conf)
		local_conf_file = cli_common.readConfFile(target_local_conf)
	except:
		print "Error trying to load conf files"
		if verbose:
			traceback.print_exc(file=sys.stdout)

def combine_conf_files(default_conf,local_conf):
	""" Combines default and local directory conf files into a master
		configuration file, containing the union of the two where "local"
		will overwrite "default"
	"""
	try:
		global combined_conf
		combined_conf = {}
		set_stanzas = set(default_conf.keys()+local_conf.keys())
		for k in set_stanzas:
			if k in default_conf_file and k in local_conf_file:
				combined_conf[k] = dict(default_conf_file[k].items() + local_conf_file[k].items())
			elif k in default_conf_file and k not in local_conf_file:
				combined_conf[k] = dict(default_conf_file[k].items())
			elif k in local_conf_file and k not in default_conf_file:
				combined_conf[k] = dict(local_conf_file[k].items())
		return combined_conf
	except:
		print "Could not combine conf files."
		if verbose:
			traceback.print_exc(file=sys.stdout)

def combine_stanza(combined_conf,target_stanza):
	""" Combines default stanza with the target stanza, 
		returns a single dict of the union
	"""
	try:
		combined_stanza = {}
		combined_stanza = dict(combined_conf['default'].items() + combined_conf[target_stanza].items())
		return combined_stanza
	except:
		print "Could not combine stanzas"
		if verbose:
			traceback.print_exc(file=sys.stdout)
		
def build_offset_list(stanza):
	""" builds a list offsets
	"""
	try:
		offsetlist = {}
		memregex = re.compile('offset\.\d+')
		for key,value in stanza.items():
			if memregex.match(key):
				offsetlist[key.split(".",1)[1]] = value
		return offsetlist
	except:
		print "Could not find a target memory loc block"
		if verbose:
			traceback.print_exc(file=sys.stdout)
		
def convert_to_hex(target,bit,mode,base_process_pid):
	""" builds a list offsets
	"""
	try:
		# Handle offset addition 
		templist = target.split('+')
		zerooffset = int(bit)/4
		targetoffset = "0x%0." + str(zerooffset) + "x"
		temphex = targetoffset % 0
		baseprogregex = re.compile('.+\.dll|.+\.exe')
		for item in templist:
			if baseprogregex.match(item):
				try:
					target_base_hex=ListProcessModules(base_process_pid,item)
					if target_base_hex:
						temphex = targetoffset % target_base_hex
				except:
					print "Can't find DLL or EXE"
			else:
				if mode == "hex":
					target = int(str(item),16)
					hexvalue = targetoffset % target
					temphex = int(temphex,16) + int(hexvalue,16)
					temphex = targetoffset % temphex
		return temphex
	except:
		print "Failed on Hex Conversion"
		if verbose:
			traceback.print_exc(file=sys.stdout)
		
def get_pid(process_name):
	''' Returns the pid of a process by name
	'''
	pid=ListProcessPid(process_name)
	return pid

def toBool(strVal):
	''' This method is used to convert standard .conf boolean entries
		into a straight True or False
	'''
	if strVal == None:
		return False
	lStrVal = strVal.lower()
	if lStrVal in ["true", "t", "1", 1, "yes", "y"] :
		return True 
	return False


def offset_read_ram(offset_dict, read_bytes, query_mode):		
	''' Follows offsets attempting to find the memory address.
		Used to follow pointers.
	'''
	try:
		sorted_list = sorted(offset_dict)
		baseaddress = 0
		for item in sorted_list:
			if item == sorted_list[0]:
				baseaddress = offset_dict[item]
			elif item == sorted_list[-1]:
				current_pointer_address = GetPointerAddress(main_pid,baseaddress,offset_dict[item],HexOrDec="Hex")
				baseaddress = current_pointer_address
			else:
				current_pointer_address = GetPointerAddress(main_pid,baseaddress,offset_dict[item],HexOrDec="Hex")
				baseaddress = current_pointer_address
		MemDump = ReadMemory(main_pid, baseaddress, Bytes=read_bytes, BufferType=query_mode, HexOrDec="Hex")
		return MemDump
	except:
		print "Failed tracing pointers / reading memory"
		if verbose:
			traceback.print_exc(file=sys.stdout)
		
def read_ram(target_address, read_bytes, query_mode):
	""" reads a "target_address" without following offsets
	"""
	try:
		MemDump = ReadMemory(main_pid, target_address, Bytes=read_bytes, BufferType=query_mode, HexOrDec="Hex")
		return MemDump
	except:
		print "Failed to read ram"
		if verbose:
			traceback.print_exc(file=sys.stdout)
		
def convert_float(float_int, mode="int"):
	""" Converts int into floating point
	"""
	if not mode == "int":
		float_int = int(str(float_int), 16)								# convert from hex to a Python int
	convert_pointer = pointer(c_int(float_int))							# make this into a c integer
	convert_floating_point = cast(convert_pointer, POINTER(c_float))	# cast the int pointer to a float pointer
	return convert_floating_point.contents.value						# dereference the pointer, get the float

def send_line(line):
	''' Sends the line to UDP or stdout
	'''
	try:
		if SendUDP == True:
			SendUDPLines(UDPIP,UDPPort,line)
		if SendStdOut == True:
			print line
		if SendUDP == 0 and SendStdOut == 0:
			raise
	except:
		print "Could not send line to proper output."
		if verbose:
			traceback.print_exc(file=sys.stdout)
		
def output(memory_object, mode):	
	''' Controls all of the output modes supported by MemLogReader
		there is a case statement at the bottom that will call a function
		with the lines_to_print.  Each output mode will change the display
		of the contents in memory
	'''
	try:
		if not mode:
			raise
			
		def string_null_break(lines_to_print):
			formatted_output = BuildLogLine(memory_object, PrntLineNumber=False)
			line_printed=0
			for line in formatted_output:
				if line_printed < lines_to_print and not lines_to_print == 0:
					send_line(line)
					line_printed = line_printed + 1
				elif lines_to_print == 0:
					send_line(line)
			 	
		def string(lines_to_print):
			line_target = AddTimeStamp() + memory_object.raw
			send_line(line_target)
			
		def hex_address_4_byte(lines_to_print):
			address = ""
			BigEndianLineCount = 0
			address_book = []
			for l in memory_object.raw:
				ByteHexValue = "%0.2X" % ord(l)
				if BigEndianLineCount < 4:
					address = ByteHexValue + address
					BigEndianLineCount = BigEndianLineCount + 1
				if BigEndianLineCount >= 4:
					address_book.append("0x%0.8X" % int(address, 16))
					BigEndianLineCount = 1
					address = ByteHexValue
			line_printed=0
			for line in address_book:
				line_target = AddTimeStamp() + line
				if line_printed < lines_to_print and not lines_to_print == 0:
					send_line(line_target)
					line_printed = line_printed + 1
				elif lines_to_print == 0:
					send_line(line_target)
		
		def float_4_byte(lines_to_print):
			if final_settings["query_mode"].lower() == "string":
				address = ""
				BigEndianLineCount = 0
				address_book = []
				for l in memory_object.raw:
					ByteHexValue = "%0.2X" % ord(l)
					if BigEndianLineCount < 4:
						address = ByteHexValue + address
						BigEndianLineCount = BigEndianLineCount + 1
					if BigEndianLineCount >= 4:
						address_book.append("0x%0.8X" % int(address, 16))
						BigEndianLineCount = 1
						address = ByteHexValue
				line_printed=0
				for line in address_book:
					line_target = AddTimeStamp() + str(convert_float(line, "hex"))
					if line_printed < lines_to_print and not lines_to_print == 0:
						send_line(line_target)
						line_printed = line_printed + 1
					elif lines_to_print == 0:
						send_line(line_target)
			else:
					line_target = AddTimeStamp() + str(convert_float(memory_object.value))
					send_line(line_target)
		
		def none():
			raise
			
		commands = {
						"string_null_break": string_null_break,
						"string": string,
						"hex_address_4_byte": hex_address_4_byte,
						"float_4_byte": float_4_byte,
					}
		commands.get(mode, none)(NumLinesPrint)
	except:
		print "No mode selected, exiting"
		if verbose:
			traceback.print_exc(file=sys.stdout)
		


# Main script 		
if __name__ == "__main__":
	try:
		global verbose
		verbose = False
		global main_pid
		global SendUDP
		global SendStdOut
		global UDPIP
		global UDPPort
		global NumLinesPrint
		check_args()
		setup_conf()
		target_address = False
		load_conf("TA-MemReader",conf_file)
		combined = combine_conf_files(default_conf_file,local_conf_file)
		final_settings = combine_stanza(combined,stanza_target)
		main_pid = get_pid(final_settings["base_process"])
		SendUDP = toBool(final_settings["sendudp"])
		SendStdOut = toBool(final_settings["sendstdout"])
		UDPIP = final_settings["udpip"]
		UDPPort = final_settings["udpport"]
		NumLinesPrint = int(final_settings["print_x_lines"])
		offsets = build_offset_list(final_settings)
		target_address = final_settings.get("target_address")
		if len(offsets) >= 1 and not target_address:
			for key, value in offsets.items():
				offsets[key] = convert_to_hex(offsets[key],final_settings["bit"],final_settings["offset_mode"],main_pid)
			memory_object = offset_read_ram(offsets,final_settings["read_bytes"],final_settings["query_mode"])
		elif target_address:
			memory_object = read_ram(target_address,final_settings["read_bytes"],final_settings["query_mode"])
		output(memory_object, final_settings.get("output_mode"))
	except:
		print "Exiting, error in .conf or attaching to program"
		if verbose:
			traceback.print_exc(file=sys.stdout) 