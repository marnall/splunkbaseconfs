#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sys
import csv,json
import platform
import urllib
import time,datetime
import os
import random
import HTMLParser
import re
from xml.dom import minidom
import logging
import logging.handlers
#
#from logging import handlers

TOPDIR = ''
appdir = 'etc/apps'
rundir = 'var/run/splunk'
vardir = 'var/log/splunk'
xmldir = 'local/data/ui/views'
output_file = 'splunk_apps.csv'
httproot = ''
version = '2.1.4'

exten = 'default.xml'
list_files = []
#list_apps = ['SplunkEnterpriseSecuritySuite']
#list_apps = ['fireeye','splunk_app_stream','Splunk_CiscoSecuritySuite','SplunkforPaloAltoNetworks','SplunkforBlueCoat','SplunkEnterpriseSecuritySuite']
list_apps = []

## Setup the logger
LOG_NAME="get_splunk_apps"
def setup_logger(splunk_home, log_file):
	LOG_FILE = os.path.join(splunk_home, vardir, log_file + ".log")
	LOG_MAX_BYTES = 10*(1024*1024) # 10MB
	LOG_COUNT = 3
	logger = logging.getLogger(__name__)
	logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
	logger.setLevel(logging.DEBUG)

#	file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', '%s.log' % name]), maxBytes=25000000, backupCount=5)
	file_handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_COUNT)
	formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
	file_handler.setFormatter(formatter)

	logger.addHandler(file_handler)

	return logger

#def get_pid(splunk_home):
#	PID_FILE = os.path.join(splunk_home, rundir, LOG_NAME + ".pid")
#	LOGGER.info("...CRE...%s...\n" % (PID_FILE))
#	pid = str(os.getpid())
#	if os.path.isfile(PID_FILE):
#		pre_pid = open(PID_FILE).readline()
#		try:
#			os.kill(int(pre_pid), 0)
#			# pre_pid is running...
#			ret = 0
#		except:	
#			ret = 1		
#	else:
#		file(PID_FILE, 'w').write(pid)
#		ret = 1
#	return ret

#def del_pid(splunk_home):
#	PID_FILE = os.path.join(splunk_home, rundir, LOG_NAME + ".pid")
#	try:
#		os.unlink(PID_FILE)
#		LOGGER.info("...DEL...%s...\n" % (PID_FILE))
#		ret = 0
#	except:
#		LOGGER.info("No such file or directory: %s " % (PID_FILE))
#		ret = 1
#	return ret

def getToday():
	os.environ['LANG'] = "C"
	return (datetime.datetime.now().strftime("%Y/%m/%d %T"))

#def step(ext, dirname, names):
#	ext = ext.lower()
#
#	for name in names:
#		if name.lower().endswith(ext):
#			list_files.append(os.path.join(dirname, name))
#			print(os.path.join(dirname, name))

#def detect_platform():
#	os_type=platform.system()
#	if os_type=="Linux":
#		homedir="/opt/splunk"
#	elif os_type=="Darwin":
#		homedir="/Applications/splunk"
#	elif os_type=="Windows":
#		homedir="C:\Program Files\Splunk"
#	else:
#		homedir="Unknown OS"
#		LOGGER.info("Detected platform %s isn't support now." % (homedir))
#
#	return homedir

def file_open(file_name):
	rfp = open(os.path.abspath(file_name), 'r')
	return (rfp)

def file_write(file_name, write_line):
	wfp = open(os.path.abspath(file_name),'a')
	wfp.write(write_line)
	wfp.close()

def file_create(file_name, write_line):
	wfp = open(os.path.abspath(file_name),'w')
	wfp.write(write_line)
	wfp.close()

def read_splunk_addr_port(app_dir):
	file_name = os.path.join(app_dir, 'fabrix/lookups', 'splunk_info.csv')
	rfp = open(os.path.abspath(file_name), 'r')
	try:
		line = csv.reader(rfp)
		for row in line:
			splk_web = row[0]
			splk_addr = row[1]
			splk_port = row[2]
	finally:
		rfp.close()

	return (splk_web, splk_addr, splk_port)

def get_enabled_apps(app_dir):
	file_name = os.path.join(app_dir, 'fabrix/lookups', 'splunk_enabled_apps.csv')
	rfp = open(os.path.abspath(file_name), 'r')
	row_num = 0
	try:
		line = csv.reader(rfp)
		row_num += 1
		for row in line:
			app_title = row[0]
			app_apply = row[3]
			if (app_apply == "1"):
				list_apps.append(app_title)
				LOGGER.info("title=%s, viz=%s list_apps ADDED" % (app_title, app_apply))
			else:
				LOGGER.info("title=%s, viz=%s list_apps EXCEPTED" % (app_title, app_apply))
	finally:
		rfp.close()

def xml_label(file_name, xmldir, curr_name):
	appnm_f = file_name.find(appdir)
	appnm_e = file_name.find('/', appnm_f + 10)
	appname = file_name[appnm_f+10:appnm_e]
	full_nm = os.path.join(TOPDIR, appdir, appname + xmldir, curr_name + ".xml")
	#os.path.exists('/tmp/license.json')

	try:
		theFile = file_open(full_nm)
		label_str = ''
		line = theFile.readline()
		while line:
			if not line: break
			if (re.search('<label>', line)):
				fv=line.find(">")
				ev=line.find("<", fv + 2)
				if (ev > 1):
					label_str=line[fv+1:ev]
				break

			line = theFile.readline()
		theFile.close()

	except IOError as e:
#	LOGGER.info('# TIME: ' + time.strftime('%Y-%m-%d %T', time.localtime(time.time())) + '... Read File.. No meta files ' + meta_file)
		return ''

	except ValueError as e:
#	LOGGER.info('# TIME: ' + time.strftime('%Y-%m-%d %T', time.localtime(time.time())) + '... Read File.. Could not convert data to an int..')
		return ''

	except:
#	LOGGER.info('# TIME: ' + time.strftime('%Y-%m-%d %T', time.localtime(time.time())) + '... Read File.. Unexpected error')
		return ''

	return label_str

def run(num_start, num_repeat):

	file_cnt = 0
	total_line_cnt = 0
	start_date = "%s" % getToday()
	LOGGER.info("#########.....Starting Fabrix v%s...%s" % (version, start_date))

	app_dir = os.path.join(TOPDIR, appdir)
	get_enabled_apps(app_dir)

	splunk_web, splunk_addr, splunk_port = read_splunk_addr_port(app_dir)
	httproot = "%s://%s:%s/app" % (splunk_web, splunk_addr, splunk_port)

	wr_file = os.path.join(TOPDIR, appdir, 'fabrix/lookups', output_file)
	wr_line = "title,lv_cnt,prev_lv_cnt,lv_node_cnt,coll_cnt,xml_tag,tag_name,tag_label,coll_name,tag_pname,url\n"
	file_create(wr_file, wr_line)

	for apptitle in list_apps:
		file_name = TOPDIR + "/etc/apps/" + apptitle +  "/local/data/ui/nav/" + exten
		if (os.path.exists(file_name) == True):
			xmldir = 'local/data/ui/views'
		else:
			file_name = TOPDIR + "/etc/apps/" + apptitle +  "/default/data/ui/nav/" + exten
			xmldir = 'default/data/ui/views'

#		print "1..%s -> %s...%s" % (file_name, apptitle, xmldir)

		try:
			theFile = file_open(file_name)

		except:
			LOGGER.warning("Unexpected error:%s, app:%s, %s" % (sys.exc_info()[0], apptitle, file_name))
#			print "try - except %s" % (file_name)
			continue

#	os.path.walk(app_dir, step, exten)
#	for file_name in list_files:
#		if (re.search('default/data/ui/nav', file_name)):
#			appnm_f = file_name.find(appdir)
#			appnm_e = file_name.find('/', appnm_f + 9)
#			apptitle = file_name[appnm_f+9:appnm_e]
#			print "1..%s -> %s..." % (file_name, apptitle)
			
#			res = apptitle in list_apps
#			if (res != True): continue

#			theFile = file_open(file_name)
#		else:
#			continue

#		if (apptitle == "SplunkEnterpriseSecuritySuite"):
#			httproot = "xxx:4500/app"
#		else:
#			httproot = "xxx:7080/app"

#		print "2..%s -> %s..." % (file_name, apptitle)
		file_cnt += 1
		file_line_cnt = 0
		LOGGER.info("Starting...%s FILE=%s, file_cnt=#%d" % (getToday(), file_name, file_cnt))

		fv = 0
		ev = 0
		line_cnt = 0
		lv_cnt = 0
		lv_node_cnt = 0
		coll_cnt = 0
		curr_tag = ''
		prev_tag = ''
		curr_tag_name = ''
		coll_name = ['']*10
		tag_pname = ''
		coll_save_name = ''
		line_skipped = 0
		prev_lv_cnt = 0
		prev_tag_name = ''
		prev_tag_pname = ''
		prev_tag_label = ''
		prev_url = ''

		line = "Go."
		while line:
			line = theFile.readline()
			if (len(line) < 4):
				continue

			fv = 0
			ev = 0
			xml_label_str = ''

			line_cnt += 1
			if (re.search('<!--', line)):
				line_skipped = 1

			if (re.search('-->', line)):
				line_skipped = 0
			
			if (line_skipped == 1): continue

			if (re.search('<nav', line)):
				lv_cnt = 0
				lv_node_cnt = 0
				curr_tag = 'nav'
				tag_pname = 'Fabrix'

			if (re.search('<view ', line)):
				curr_tag = 'view'
				if (prev_tag != 'view') & (prev_tag != 'div') & (prev_tag != 'saved') & (prev_tag != 'href'):
					lv_cnt += 1
					lv_node_cnt = 0
				fv=line.find("=\"")
				ev=line.find("\"", fv+2)
				curr_tag_name=HTMLParser.HTMLParser().unescape(line[fv+2:ev])

				if (lv_cnt != 1):
					tag_pname = coll_name[coll_cnt]
				else:
					tag_pname = 'Fabrix'

			if (re.search('<saved ', line)):
				curr_tag = 'saved'
				if (prev_tag != 'saved') & (prev_tag != 'href') & (prev_tag != 'view'):
					lv_cnt += 1
					lv_node_cnt = 0

				fv=line.find("=\"")
				ev=line.find("\"", fv+2)
				curr_tag_name=HTMLParser.HTMLParser().unescape(line[fv+2:ev])

				tag_pname = coll_name[coll_cnt]

			if (re.search('href=', line)):
				curr_tag = 'href'
				if (prev_tag != 'href') & (prev_tag != 'view'):
					lv_cnt += 1
					lv_node_cnt = 0

				tag_pname = coll_name[coll_cnt]

				fv=line.find("href=\"")
				if (fv == -1):
					fv=line.find("href=\'")

				ev=line.find('\"', fv+6)
				if (ev == -1):
					ev=line.find('\'', fv+6)

				curr_tag_name=line[fv+6:ev]
				fv=line.find('>')
				ev=line.find('<', fv+1)
				xml_label_str=HTMLParser.HTMLParser().unescape(line[fv+1:ev])

			if (re.search('<collection ', line)):
				if (prev_tag != 'view') & (prev_tag != 'div') & (prev_tag != 'href') & (prev_tag != 'saved'):
					lv_cnt += 1
					lv_node_cnt = 0

				coll_cnt += 1
				curr_tag = 'coll'

				fv=line.find("label=\"")
				ev=line.find("\"", fv+7)
				curr_tag_name=HTMLParser.HTMLParser().unescape(line[fv+7:ev])
				
				coll_name[coll_cnt] = curr_tag_name
				coll_save_name = curr_tag_name

				if (lv_cnt != 1):
					tag_pname = coll_name[coll_cnt - 1]
				else:
					tag_pname = 'Fabrix'

			if (re.search('</collection', line)):
				if (prev_tag == 'view') | (prev_tag == 'div') | (prev_tag == 'href') | (prev_tag == 'saved'):
					lv_cnt -= 2
				else:
					lv_cnt -= 1

				lv_node_cnt =0
				coll_cnt -= 1
				curr_tag = 'end_coll'

			if (re.search('<divider', line)):
				curr_tag = 'div'

			if (len(curr_tag_name) != 0) & (curr_tag != 'href'):
				xml_label_str=HTMLParser.HTMLParser().unescape(xml_label(file_name, xmldir, curr_tag_name))
				if (len(xml_label_str) == 0):
					xml_label_str = curr_tag_name

			in_apptitle = curr_tag_name.find(apptitle)
			if (in_apptitle > 0):
				apptitle_len = len(apptitle)
				tmp_tag_name = curr_tag_name[in_apptitle+apptitle_len:]
				if (len(tmp_tag_name) > 0):
					if (tmp_tag_name[0] == '/'):
						curr_tag_name = tmp_tag_name[1:]	

			if (curr_tag == 'nav'):
				curr_tag_name = 'Fabrix'
				xml_label_str = 'Fabrix'
				tag_pname = 'Fabrix'
				url = "%s/%s" % (httproot, apptitle)
			elif (curr_tag_name == 'unclassified') | (curr_tag_name == 'all'):
				url = "%s/%s" % (httproot, apptitle)
			elif ((curr_tag == 'view') | (curr_tag == 'href') | (curr_tag == 'saved')):
				url = "%s/%s/%s" % (httproot, apptitle, curr_tag_name)
			else:
				url = ""

			if (curr_tag_name == 'Search') | (curr_tag_name == 'search'):
				curr_tag_name = "%s_%s" % (apptitle, curr_tag_name)

			if (curr_tag_name == 'all') | (curr_tag_name == 'unclassified'):
				curr_tag_name = "%s_%d_%s" % (apptitle, line_cnt, curr_tag_name)

			if (curr_tag != 'end_coll') & (curr_tag != 'div'):
				if (tag_pname != 'Documentation') & (tag_pname != 'Help') & (curr_tag_name != 'Help'):
					if (re.search('Documentation', curr_tag_name) == None) \
						& (re.search('/manager|mailto|http://', curr_tag_name) == None):
#						wr_line = "title,lv_cnt,lv_node_cnt,coll_cnt,xml_tag,tag_name,tag_label,coll_name,tag_pname,url\n"

						lv_node_cnt += 1
						if ((prev_lv_cnt == 1) & (lv_cnt == 1)):
							tmp_lv_cnt = lv_cnt + 1
							tmp_name = '%d_%s' % (tmp_lv_cnt, prev_tag_name)
							tmp_pname = '%s' % (prev_tag_name)
							tmp_label = '%s' % (prev_tag_label)
							tmp_url = prev_url
							wr_line = "%s,%d,%d,%d,%d,%s,%s,%s,%s,%s,%s\n" % (apptitle, tmp_lv_cnt, prev_lv_cnt, lv_node_cnt, coll_cnt, curr_tag, tmp_name, tmp_label, coll_name[coll_cnt], tmp_pname, tmp_url)
							file_write(wr_file, wr_line)

							tmp_lv_cnt = lv_cnt + 2
							tmp_name = '%d_%s' % (tmp_lv_cnt, prev_tag_name)
							tmp_pname = '%d_%s' % (tmp_lv_cnt - 1, prev_tag_name)
							tmp_label = '%s' % (prev_tag_label)
							tmp_url = prev_url
							wr_line = "%s,%d,%d,%d,%d,%s,%s,%s,%s,%s,%s\n" % (apptitle, tmp_lv_cnt, prev_lv_cnt, lv_node_cnt, coll_cnt, curr_tag, tmp_name, tmp_label, coll_name[coll_cnt], tmp_pname, tmp_url)
							file_write(wr_file, wr_line)

							tmp_lv_cnt = lv_cnt + 3
							tmp_name = '%d_%s' % (tmp_lv_cnt, prev_tag_name)
							tmp_pname = '%d_%s' % (tmp_lv_cnt - 1, prev_tag_name)
							tmp_label = '%s' % (prev_tag_label)
							tmp_url = prev_url
							wr_line = "%s,%d,%d,%d,%d,%s,%s,%s,%s,%s,%s\n" % (apptitle, tmp_lv_cnt, prev_lv_cnt, lv_node_cnt, coll_cnt, curr_tag, tmp_name, tmp_label, coll_name[coll_cnt], tmp_pname, tmp_url)
							file_write(wr_file, wr_line)
							
						wr_line = "%s,%d,%d,%d,%d,%s,%s,%s,%s,%s,%s\n" % (apptitle, lv_cnt, prev_lv_cnt, lv_node_cnt, coll_cnt, curr_tag, curr_tag_name, xml_label_str, coll_name[coll_cnt], tag_pname, url)
						file_write(wr_file, wr_line)
						prev_lv_cnt = lv_cnt
						prev_tag_name = curr_tag_name
						prev_tag_pname = tag_pname
						prev_tag_label = xml_label_str
						prev_url = url
#						time.sleep(1)

			LOGGER.info("%2d, %2d, %2d, %8s, %8s, %-30s, %-30s, %-30s, %-30s" % (line_cnt, lv_cnt, coll_cnt, curr_tag, prev_tag, curr_tag_name, xml_label_str, coll_name[coll_cnt], tag_pname))

			if (curr_tag != 'div'):
				prev_tag = curr_tag

			if (curr_tag == 'end_coll'):
				coll_save_name = ''

		theFile.close()
		LOGGER.info("     ......%s FILE=%s, line_cnt=#%d\n" % (getToday(), file_name, file_line_cnt))
#		time.sleep(10)

	end_date = "%s" % getToday()
	LOGGER.info("Finish.....%s START=%s -> END=%s, Files=%d, Total_lines=%d\n" % (getToday(), start_date, end_date, file_cnt, total_line_cnt))

if __name__ == "__main__":
	if (len(sys.argv) < 2):
		print "Usage: %s {splunk_home_dir_full_path}\n" % (__file__)
		sys.exit(0)

	try:
		TOPDIR = os.environ['SPLUNK_HOME']

	except:	
		if (len(TOPDIR) == 0):
			TOPDIR = sys.argv[1]
#			print ">>>>>> undefined SPLUNK_HOME environ <<<<<<\n"	

#	print "argv[0] = %s, argv[1] = %s, TOP=%s\n" % (sys.argv[0], sys.argv[1], TOPDIR)
	LOGGER = setup_logger(TOPDIR, LOG_NAME)

#	if (get_pid(TOPDIR) == 0):
#		LOGGER.info("%s is running...!" % (LOG_NAME))
#		print "%s is running...!" % (LOG_NAME) 
#		sys.exit()

	num_start = 1
	num_repeat = 0
	run(num_start, num_repeat)

#	del_pid(TOPDIR)
	sys.exit()
