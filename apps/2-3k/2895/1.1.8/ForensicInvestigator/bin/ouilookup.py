#!/usr/bin/python 
# MAC address OUI Lookup
# For questions ask anlee2 -at- vt.edu or Dan Dumond
# Takes a MAC address
# Returns vendor information tied to that MAC

import sys,csv,splunk.Intersplunk,string,base64,urllib

def main():
	(isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
	if len(sys.argv) < 2:
		splunk.Intersplunk.parseError("No arguments provided")
		sys.exit(0)

	input_mac = sys.argv[1]
	OUI_file = "oui-lite.txt"
	input_mac = input_mac.replace('-','')
	input_mac = input_mac.replace(':','')
	input_mac = input_mac.replace(' ','')
	if len(input_mac) > 12:
		line = 'Invalid MAC address. (too many characters)'
		print line
		#sys.exit()
	try: # validate that it is a hexadecimal string
		int(input_mac, 16)
	except:
		line = 'Invalid MAC address. (Not a valid hex string)'
		print line
		#sys.exit()
	input_mac = input_mac[0:6]

	try: # try to open the file
		f = open(OUI_file, 'r')
		oui_lines = f.read().split('\n')
		answer_lines = ''
		for line in oui_lines:
			if line.find(input_mac.upper())==0:
				line = line.replace('     (base 16)\t\t','<,>')
				# also supports a reduced size oui-lite.txt
				# oui-lite.txt is generated from the oui.txt and the following command
				# grep "(base 16)" oui.txt |sed 's/     (base 16)\t\t/<,>/g'>oui-lite.txt
				
				#line = line.replace('<,>','=')
				if len(answer_lines) == 0:
					answer_lines = line
				else:
					answer_lines = answer_lines + '<b>' + line
	
				#print line
				output = csv.writer(sys.stdout)
				data = [['answer'],[line]]
				output.writerows(data)
	except IOError:
		print "An error occurred."
	finally:
		f.close()
main()
