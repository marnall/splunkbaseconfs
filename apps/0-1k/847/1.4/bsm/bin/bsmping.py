
__doc__ = """

#-- Copyright 2007 Erik Swan and Splunk, Inc. - erikswan@dogandbone.com
#-- Updated by Stephan Buys - sbuys@exponant.com (2011)
"""

# Copyright (C) 2005-2008 Splunk Inc.  All Rights Reserved.  Version 3.0
import getopt, sys, ConfigParser, os, cStringIO, time, traceback, datetime
import splunk.Intersplunk as si
import splunk.clilib.cli_common as comm

splunk_home = os.getenv('SPLUNK_HOME')
if not splunk_home:
    si.generateErrorResults('Environment variable SPLUNK_HOME must be set')

VERSION = '1.4'

#
# This is the list of configuration options that can be set either on the 
# command line or via the imap.conf file.  Note that these names must 
# correspond exactly to field names in the IMAPProcessor class and the names 
# specified in the optlist near the bottom of this file.
#
# The imap.ini configuration file provides more detailed documentation about 
# the effects of each of the options.
#
configOptions = [ 
  "reduceFilter", 
  "prFlags", 
  "logPath",
  "cachePath",
  "earliestTime",
  "prauditScript",
  "auditreduceScript",
  "enableSinkHole",
  "sinkHolePath",
  "debug", 
  "noCache",
]

# path to the confguration conf file
scriptDir = sys.path[0] # find it relative to getimap.py file
configDefaultFileName = os.path.join(scriptDir,'..','default','bsm.conf')
configLocalFileName = os.path.join(scriptDir,'..','local','bsm.conf')

# name of the only section in the config file
configSectionName = "BSM Configuration"

#--------------------------------------------------------------
class BSMProcessor(object):

    """
    """

    # -------------------
    # -------------------
    def __init__(self):
        # initialize all of the configuration fields with default values that
        # will be used on the off chance that they don't appear in imap.ini
        self.reduceFilter = ""        # filter to pass to auditreduce
        self.prFlags = ""       # flags to pass to praudit
        self.logPath = "/var/audit"
        self.earliestTime = '20010101'
        self.cachePath = splunk_home+"/etc/apps/bsm/local/"
        self.cacheFile = "getbsm.cache"
        self.noCache = False
        self.debug = False 
        self.auditreduceScript = 'auditreduce'
        self.prauditScript = 'praudit'
        self.enableSinkHole = False
        self.sinkHolePath = ""


    # -----------------------------------
    # -----------------------------------
    def initFromOptlist(self, optlist):
        # First read settings in config.ini, if it exists...
        self.readConfig()
        # ...now, for debugging and backward compat, allow command line 
        # settings to override...
 
        self.readOptlist(optlist)
 

        if self.debug:
          keys = self.__dict__.keys();
          keys.sort();
          for k in keys:
            if k.startswith("_"): continue
            print k + "=" + str(self.__dict__[k])

        # check min required args
        if self.prFlags == "":
            self.usage()
            #sys.exit()
            si.generateErrorResults("Too few arguments")

    #----------------------
    # ---------------------
    def readConfig(self):
      """  read settings from config.ini, if it exists. """
      path = ''
      if os.path.exists(configLocalFileName):
        path = configLocalFileName
        self.logger("readConfig : reading local config :" + path)
      elif os.path.exists(configDefaultFileName):
        path = configDefaultFileName
        self.logger("readConfig : reading defult config :" + path)
      else:
        self.logger("readConfig : could not find config file")
        return
      config = ConfigParser.ConfigParser()
      config.read(path)
      for o in configOptions:
        if config.has_option(configSectionName, o):
          val = getattr(self, o)
          newVal = config.get(configSectionName, o)
          # check to see if the current/default value is a boolean; if so,
          # perform a forgiving conversion from string to bool.
          if val.__class__ == bool:
            newVal = (newVal.strip().lower() == "true")
          setattr(self, o, newVal)

    #-------------------------------
    # ------------------------------
    def readOptlist(self, optlist):
      """
      Read settings from the command line.  We support command
      line args mainly for backwards compat and for quick debugging;
      users should be encouraged to use the imap.ini file instead.
      """
      for o, a in optlist:
        o = o[2:] # strip the leading --

        if o in configOptions:
          val = getattr(self, o)
          # check to see if the current/default value is a boolean. If so,
          # then the value is true if specified as a flag; otherwise, convert
          # the option value to a bool.
          if val.__class__ == bool:
            if (a == None or len(a) == 0) :
              val 
            else:
              val = (a.strip().lower() == "true")
          else: 
            val = a
          setattr(self, o, val)

    #----------------
    # ---------------
    def usage(self):
        """ usage text for help """
        
        print "The required fields are: prFlasgs"
        print "eg:"
        print "python bsmping.py prflags -r reduceFilter -"
        print "Other parameters that can also be supplied. Refer the default/bsm.conf file for details"
        
    #-------------------------
    # ------------------------
    def logger(self, string):
        """ helper function for logging """
        if self.debug:
            print string

    #-------------------------------------
    #------------------------------------
    def getCache(self):
        """  
        """
        self.logger("getcache:: about to getCache ")

        if self.earliestTime == 'now':
            now = datetime.datetime.now()
            td = datetime.timedelta(minutes=1)
            now = now - td
            self.earliestTime = now.strftime("%Y%m%d%H%M")

        results = self.earliestTime
        f = None
        try:
            if self.noCache:
                return results         
            else:
    
                try:
                    os.stat(self.cachePath+self.cacheFile)
                except:
                    self.logger("getcache:: cache does not exist, using default")
                    return results

                # open cache file
                f=open(self.cachePath+self.cacheFile, 'r')

                # read the cache string
                cacheValue = f.readline()
                if ( cacheValue != None ):
                    results = cacheValue

        except Exception, e:
            print "ERROR - could not read bsm cache"
            print traceback.print_exc(file=sys.stdout)


        if ( f != None ):
            f.close()

        self.logger("getCache:: got the cache vaule: " + results )
        return results

    #-------------------------------------
    #------------------------------------
    def setCache(self, cachestr):
        """  
        """
        self.logger("setCache:: about to set cache to :" + cachestr )
        
        f = None
        try:
            # see if our cache dir exists
            try:
                os.stat(self.cachePath)
            except:
                try:
                    os.makedirs(self.cachePath)
                except:
                    print "ERROR counld not create bsm cache path"
                    print traceback.print_exc(file=sys.stdout)
                    return

            # open cache file
            f = open(self.cachePath+self.cacheFile, 'w')

            # write cachestr
            f.write(cachestr)

        except:
            print "ERROR could not write bsm cache file"
            print traceback.print_exc(file=sys.stdout)
        
        if ( f != None ):
            f.close()

        self.logger("setcache:: successfully set cache")
    
           

    #-------------------------------
    #-------------------------------
    def nukedir(self, dir):
        self.logger("About to remove files in " + dir )
        if dir[-1] == os.sep: dir = dir[:-1]
        files = os.listdir(dir)
        for file in files:
            if file == '.' or file == '..': continue
            path = dir + os.sep + file
            if os.path.isdir(path):
                nukedir(path)
            else:
                os.unlink(path)


    #-------------------------------
    # ------------------------------
    def eatSinkHole(self):
        """ consume any files in the sinkhole and then delete them """

        if self.enableSinkHole == False:
            return

        if self.noCache:
            return

        self.logger("eatSinkHole:: about to eat everything in : " + self.sinkHolePath)

        try:
            path = self.sinkHolePath.replace("$SPLUNK_HOME",splunk_home)
            dirList=os.listdir(path)
            if ( len(dirList ) < 1):
                self.logger("eatSinkHole : no files in sink hole")
                return


            cmd = self.auditreduceScript + self.reduceFilter
            cmd = cmd + ' -A ' + path + '/* | ' + self.prauditScript + ' ' + self.prFlags
            self.logger("eatSinkHole:: about to call " + cmd )

            for line in os.popen(cmd).readlines():     # run find command 
                num  = 1
                print str(num) + line
              
            self.nukedir(path)

        except:
            print "ERROR - error calling audit script"
            print traceback.print_exc(file=sys.stdout)




    #-------------------------------
    # ------------------------------
    def getLogs(self):
        """ Print out all the mail for folder box """
  
        lastTime = self.getCache()

        # we set the max time to a minute  ago this will be set as the next cache time
        now = datetime.datetime.now()
        td = datetime.timedelta(minutes=1)
        now = now - td
        nowstr = now.strftime("%Y%m%d%H%M")
        
        self.logger("getLogs:: now string is " + nowstr )

        try:
            if nowstr == lastTime:
                self.logger("now and last time are the same, will exit this run")
                return

            cmd = self.auditreduceScript + ' -a ' + lastTime    # add after arg
            cmd = cmd + ' -b ' + nowstr                         # add before arg
            cmd = cmd + ' ' + self.logPath + ' | ' + self.prauditScript + ' ' + self.prFlags 
            self.logger("getLogs:: about to call " + cmd )

            for line in os.popen(cmd).readlines():     # run find command 
                num  = 1 
                print str(num) + line 

            self.setCache(nowstr)
        except:
            print "ERROR - error calling audit script"
            print traceback.print_exc(file=sys.stdout) 

            
# ----------------
# ----------------
def main():
    bsmProc = BSMProcessor()

    optlist = None
    try:
      optlist, args = getopt.getopt(sys.argv[1:], '?',['noCache=', 'filter='])
      bsmProc.initFromOptlist(optlist)
    except getopt.error, val:
      print str(val) # tell them what was wrong
      bsmProc.usage()
      si.generateErrorResults("Incorrect usage...")
      
    # Do the work....    
    bsmProc.getLogs()
    bsmProc.eatSinkHole()

if __name__ == '__main__':
    main()


