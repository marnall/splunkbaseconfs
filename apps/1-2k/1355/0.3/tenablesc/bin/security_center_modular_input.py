#!/usr/bin/python

# copyright Satisnet Ltd.   2013
# Licensed LGPL v3


import sys
import time
from splunk_modular_inputs import modular_inputs
from sc_connect import sc_connect


SCHEME = """<scheme>
    <title>Tenable Security Center</title>
    <description>Get data from Tenable Security Center</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>simple</streaming_mode>

    <endpoint>
        <args>
            <arg name="name">
                <title>Name</title>
                <description>Unique Name for the Security Center input
                </description>
            </arg>
	    <arg name="url">
                <title>URL</title>
                <description>The URL for the Security Center API
                   For example, for Security Center on IP 192.168.1.2 
                        type https://192.168.1.2/request.php
                </description>
            </arg>


            <arg name="username">
                <title>Username</title>
                <description>Username to login to Security Center (Orgainisation Head or Lower, NOT admin)</description>
            </arg>

            <arg name="password">
                <title>Password</title>
                <description>Password for the Username</description>
            </arg>

            <arg name="frequency">
                <title>Frequency</title>
                <description>Frequency in seconds to check Security Center for vulnerabilities</description>
        </args>
    </endpoint>
</scheme>
"""



if __name__ == '__main__':
	if len(sys.argv) > 1:
		if sys.argv[1] == "--scheme":
			modular_inputs.do_scheme(SCHEME)
		elif sys.argv[1] == "--validate-arguments":
			try:
				mi = modular_inputs()
		        	username = mi.get_config("username")
		        	password = mi.get_config("password")
				url  = mi.get_config("url")
		        	name = mi.get_config("name")
		        	checkpoint_dir  = mi.get_config("checkpoint_dir")
                                frequency = mi.get_config("frequency")
				sc = sc_connect(username, password, name)
			except Exception, e:
				modular_inputs.print_error("Error Validating Args : %s" % str(e))
	else:
		try:
			mi = modular_inputs()
		        username = mi.get_config("username")
		        password = mi.get_config("password")
			url  = mi.get_config("url")
		        name = mi.get_config("name")
		        checkpoint_dir  = mi.get_config("checkpoint_dir")
                        frequency = int(mi.get_config("frequency"))
			mi.load_checkpoint()

			# if collection has been run recently wait until scheduled to start again
			wait_till = mi.get_lastrun() + frequency
			wait = wait_till - time.time()
			if wait > 0:
				time.sleep(wait)

			while True:
				sc = sc_connect(username, password, url)
				sc.vulnipdetail()
				mi.save_checkpoint()
				sys.stdout.flush()
				time.sleep(frequency)

		except Exception, e:
			modular_inputs.print_error("Error Querying Security Center: %s" % str(e))
