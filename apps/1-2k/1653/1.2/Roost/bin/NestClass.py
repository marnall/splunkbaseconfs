#! /usr/bin/python

# nest.py -- a python interface to the Nest Thermostat
# by Scott M Baker, smbaker@gmail.com, http://www.smbaker.com/
#
# Usage:
#    'nest.py help' will tell you what to do and how to do it
#
# Licensing:
#    This is distributed unider the Creative Commons 3.0 Non-commecrial,
#    Attribution, Share-Alike license. You can use the code for noncommercial
#    purposes. You may NOT sell it. If you do use it, then you must make an
#    attribution to me (i.e. Include my name and thank me for the hours I spent
#    on this)
#
# Acknowledgements:
#    Chris Burris's Siri Nest Proxy was very helpful to learn the nest's
#       authentication and some bits of the protocol.
#
# File was modified to Fit with a Splunk Modular Input

import urllib
import urllib2
import time
import sys
import logging
from time import gmtime, strftime, localtime
from optparse import OptionParser

logging.root
logging.root.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)

try:
   import json
except ImportError:
   try:
       import simplejson as json
   except ImportError:
       logging.error("json_library not found")
       sys.exit(-1)

class Nest:
    def __init__(self, username, password, index=0, units="F"):
        self.username = username
        self.password = password
        self.units = units
        self.index = index

    def loads(self, res):
        if hasattr(json, "loads"):
            res = json.loads(res)
        else:
            res = json.read(res)
        return res

    def login(self):
        data = urllib.urlencode({"username": self.username, "password": self.password})
        logging.debug("%s"%data)
        req = urllib2.Request("https://home.nest.com/user/login",
                              data,
                              {"user-agent":"Nest/1.1.0.10 CFNetwork/548.0.4"})
        logging.debug("%s"%req)
        res = urllib2.urlopen(req).read()

        res = self.loads(res)

        self.transport_url = res["urls"]["transport_url"]
        self.weather_url = res["urls"]["weather_url"]
        self.access_token = res["access_token"]
        self.userid = res["userid"]
        self.status = self.get_status()
        self._load_objects()
        #self.structures = self._get_structures()
        #self.devices = self._get_devices()
        #self.schedules = self._get_schedules()

    def get_status(self):
        req = urllib2.Request(self.transport_url + "/v5/mobile/user." + self.userid,
                              headers={"user-agent":"Nest/1.1.0.10 CFNetwork/548.0.4",
                                       "Authorization":"Basic " + self.access_token,
                                       "X-nl-user-id": self.userid,
                                       "X-nl-protocol-version": "1"})

        res = urllib2.urlopen(req).read()
        res = self.loads(res)
        return res

    def temp_in(self, temp):
        if (self.units == "F"):
            return (temp - 32.0) / 1.8
        else:
            return temp

    def temp_out(self, temp):
        if (self.units == "F"):
            return temp*1.8 + 32.0
        else:
            return temp

    def get_devices(self): 
        return self.devices

    def get_schedules(self):
        return self.schedules

    def get_structures(self):
        return self.structures;

    def _load_objects(self):
        result = self.status
        schedules = {}
        devices = {}
        structures = {}
        daySched = [ "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday" ]
        for k in result["objects"]:
            obj_key = k["object_key"]
            if ("schedule" in obj_key ):
               sched_key = obj_key.replace("schedule.","")
               schedules[sched_key] = {}
               schedules[sched_key]["timestamp"] = "%s"%(strftime("%a, %d %b %Y %H:%M:%S %Z", localtime()))
               schedules[sched_key]["schedule_name"] = "%s"%(k["value"]["name"])
               schedules[sched_key]["schedule_version"] = "%s"%(k["value"]["ver"])
               schedules[sched_key]["schedule_mode"] = "%s"%(k["value"]["schedule_mode"])
               for day in k["value"]["days"]:
                   k["value"]["days"][day]["text"] = daySched[int(day)]
                   k["value"]["days"][day]["day_index"] = day
               schedules[sched_key]["schedule"] = k["value"]["days"]
               schedules[sched_key]["marker"] = "schedule"

            if ( 'structure' in obj_key ):
               struct_key = obj_key.replace("structure.","")
               structures[struct_key] = {}; 
               structures[struct_key]['timestamp'] = "%s "%(strftime("%a, %d %b %Y %H:%M:%S %Z", localtime()))
               for h in sorted(k["value"].keys()):
                   if ("swarm" in h or "devices" in h or "fabric_ids" in h):
                       val = "|".join(k["value"][h]).replace("device.","")
                   else:
                       val = k["value"][h]
                   structures[struct_key][h] = val
               zipCode = k["value"]["postal_code"]
               self.get_weather_ref(zipCode,structures[struct_key])
               structures[struct_key]["marker"] = "structure"
                 
            if ( "device" in obj_key and "dialog" not in obj_key):
                devices[k["value"]["serial_number"]] = { "timestamp" : "%s"%(strftime("%a, %d %b %Y %H:%M:%S %Z", localtime())) }
        for SN in devices:
            tmpDev = {}
            for k in result["objects"]:
               obj_key = k["object_key"]
               if ( ("shared" in obj_key or "device" in obj_key ) and "dialog" not in obj_key):
                  for h in sorted(k["value"].keys()):
                      tmpDev[h] = k["value"][h]
            for k in sorted(tmpDev.keys()):
                devices[SN][k] = "%s"%(tmpDev[k])    
            devices[SN]["marker"] = "status"

        self.devices = devices
        self.structures = structures
        self.schedules = schedules
    

    def get_weather(self, zip):
		req = urllib2.Request(
					self.weather_url + zip,
					headers = {
						"user-agent": "Nest/1.1.0.10 CFNetwork/548.0.4",
						"Authorization": "Basic " + self.access_token,
						"X-nl-user-id": self.userid,
						"X-nl-subscribe-timeout": "10",
						"X-nl-protocol-version": "1",
						"Connection": "close"
					}
				)

		res = urllib2.urlopen(req, timeout = 5).read()
		res = self.loads(res)
                weatherString = ""
		for zipcode in res:
			zipcodeData = res[zipcode]["current"]
                        for k in sorted(zipcodeData.keys()):
                            weatherString += " %s=\"%s\" "%(k,zipcodeData[k])
                return weatherString

    def get_weather_ref(self, zip, the_list):
                req = urllib2.Request(
                                        self.weather_url + zip,
                                        headers = {
                                                "user-agent": "Nest/1.1.0.10 CFNetwork/548.0.4",
                                                "Authorization": "Basic " + self.access_token,
                                                "X-nl-user-id": self.userid,
                                                "X-nl-subscribe-timeout": "10",
                                                "X-nl-protocol-version": "1",
                                                "Connection": "close"
                                        }
                                )

                res = urllib2.urlopen(req, timeout = 5).read()
                res = self.loads(res)
                for zipcode in res:
                        zipcodeData = res[zipcode]["current"]
                        for k in sorted(zipcodeData.keys()):
                            the_list[k] = zipcodeData[k]

    def show_energy(self,starttime=0):
        return
	shared = self.status["schedule"][self.serial]
	temp_out = {"name": shared["name"], "schedule_mode": shared["schedule_mode"], "touches":[] }
	for k in sorted(shared["days"].keys()):
		for j in sorted(shared["days"][k].keys()):
			if (int(shared["days"][k][j]["touched_at"]) > int(starttime)):
				temp_out["touches"].append(dict({ "day":k, "touch_id": j, "touch": shared["days"][k][j]}))
	return temp_out


    def show_curstat(self):
        return "%s m=\"status_check\" serial=\"%s\" %s %s"%(time.time(),self.serial,self.show_curtemp(),self.show_curhum())
        
    def show_curtemp(self):
        temp = self.status["shared"][self.serial]["current_temperature"]
        temp = self.temp_out(temp)

        return "current_temperature=%0.1f" % temp

    def show_curhum(self):
	hum =  self.status["device"][self.serial]["current_humidity"]
	return "current_humidity=%0.1f" % hum

    def set_temperature(self, temp):
        temp = self.temp_in(temp)

        data = '{"target_change_pending":true,"target_temperature":' + '%0.1f' % temp + '}'
        req = urllib2.Request(self.transport_url + "/v2/put/shared." + self.serial,
                              data,
                              {"user-agent":"Nest/1.1.0.10 CFNetwork/548.0.4",
                               "Authorization":"Basic " + self.access_token,
                               "X-nl-protocol-version": "1"})

        res = urllib2.urlopen(req).read()

        print res

    def set_fan(self, state):
        data = '{"fan_mode":"' + str(state) + '"}'
        req = urllib2.Request(self.transport_url + "/v2/put/device." + self.serial,
                              data,
                              {"user-agent":"Nest/1.1.0.10 CFNetwork/548.0.4",
                               "Authorization":"Basic " + self.access_token,
                               "X-nl-protocol-version": "1"})

        res = urllib2.urlopen(req).read()

        print res

def create_parser():
   parser = OptionParser(usage="nest [options] command [command_options] [command_args]",
        description="Commands: fan temp",
        version="unknown")

   parser.add_option("-u", "--user", dest="user",
                     help="username for nest.com", metavar="USER", default=None)

   parser.add_option("-p", "--password", dest="password",
                     help="password for nest.com", metavar="PASSWORD", default=None)

   parser.add_option("-c", "--celsius", dest="celsius", action="store_true", default=False,
                     help="use celsius instead of farenheit")

   parser.add_option("-s", "--serial", dest="serial", default=None,
                     help="optional, specify serial number of nest thermostat to talk to")

   parser.add_option("-i", "--index", dest="index", default=0, type="int",
                     help="optional, specify index number of nest to talk to")


   return parser

def help():
    print "syntax: nest [options] command [command_args]"
    print "options:"
    print "   --user <username>      ... username on nest.com"
    print "   --password <password>  ... password on nest.com"
    print "   --celsius              ... use celsius (the default is farenheit)"
    print "   --serial <number>      ... optional, specify serial number of nest to use"
    print "   --index <number>       ... optional, 0-based index of nest"
    print "                                (use --serial or --index, but not both)"
    print
    print "commands: temp, fan, show, curtemp, curhumid"
    print "    temp <temperature>    ... set target temperature"
    print "    fan [auto|on]         ... set fan state"
    print "    show                  ... show everything"
    print "    curtemp               ... print current temperature"
    print "    curhumid              ... print current humidity"
    print
    print "examples:"
    print "    nest.py --user joe@user.com --password swordfish temp 73"
    print "    nest.py --user joe@user.com --password swordfish fan auto"

def main():
    parser = create_parser()
    (opts, args) = parser.parse_args()

    if (len(args)==0) or (args[0]=="help"):
        help()
        sys.exit(-1)

    if (not opts.user) or (not opts.password):
        print "how about specifying a --user and --password option next time?"
        sys.exit(-1)

    if opts.celsius:
        units = "C"
    else:
        units = "F"

    n = Nest(opts.user, opts.password, opts.serial, opts.index, units=units)
    n.login()
    n.get_status()

    cmd = args[0]

    if (cmd == "temp"):
        if len(args)<2:
            print "please specify a temperature"
            sys.exit(-1)
        n.set_temperature(int(args[1]))
    elif (cmd == "fan"):
        if len(args)<2:
            print "please specify a fan state of 'on' or 'auto'"
            sys.exit(-1)
        n.set_fan(args[1])
    elif (cmd == "show_struct"):
	print "\n\n\n\n"
        print n.show_structure()
    elif (cmd == "show_energy"):
	print n.show_energy()
    elif (cmd == "show"):
        print n.show_status()
    elif (cmd == "curtemp"):
        print n.show_curtemp()
    elif (cmd == "curhumid"):
	print n.show_curhum()
    else:
        print "misunderstood command:", cmd
        print "do 'nest.py help' for help"

if __name__=="__main__":
   main()





