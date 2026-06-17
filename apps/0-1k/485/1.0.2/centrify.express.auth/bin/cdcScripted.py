'''
 This a simple authentication script which uses adinfo and adquery to 
 authenticate a DirectControl user and get their group information.  

'''
# Set this to the name of the group you want to control Splunk access
# Set the value to "" to allow all zone users access
SPLUNKGROUP = "splunk-users"


# commonAuthBase contains constants and a basic mapping framework for users.
# plus any common imports to all scripts.
################# BEGIN commonAuth.py ##################################3
import sys, subprocess, getopt

# keys we'll be using when talking with splunk.
USERNAME    = "username"
USERTYPE    = "role"
SUCCESS     = "--status=success"
FAILED      = "--status=fail"

# read the inputs coming in and put them in a dict for processing.
def readInputs():
   optlist, args = getopt.getopt(sys.stdin.readlines(), '', ['username=', 'password='])

   returnDict = {}
   for name, value in optlist:
      returnDict[name[2:]] = value.strip()

   return returnDict

################# END commonAuth.py ##################################3
import os

DEVNULL = open('/dev/null', 'w');
#DEBUG = open('/tmp/debug.splunk', 'w');

'''
 This function will be called when a user enters their credentials in the login page in UI.
 Input:
       --username=<user> --password=<pass> 
 Output:
       On Success:
                    --status=success
       On Failure:
                   Anything but --status=success
'''
def userLogin( infoIn  ):




   # Validate this user is enabled in the current zone
   command = ['/usr/bin/adquery', 'user', str(infoIn['username'])]
   retCode = subprocess.call(command, stdout=DEVNULL, stderr=DEVNULL)
   if retCode != 0:
       print FAILED
       return

   command = ['/usr/bin/adquery', 'user', '-M', str(infoIn['username'])]

   # This will throw on failure, but certainly shouldn't if the first
   # adquery worked
   samname = subprocess.Popen(command, stdout=subprocess.PIPE).communicate()[0].strip()

   # Get the domain for this user
   command = ['/usr/bin/adquery', 'user', '-C', str(infoIn['username'])]
   cName = subprocess.Popen(command, stdout=subprocess.PIPE).communicate()[0]
   slash = str.find(cName, '/')
   if slash != -1:
       domain = cName[0:slash]
   else:
       # This should really never happen....
       domain = subprocess.Popen(['adinfo', '-d'], stdout=subprocess.PIPE).communicate()[0]
       

   command = ['/usr/bin/adinfo', '-A', str(domain), '-u', str(samname)]
   
   # adinfo -A allows the password to be entered through a pipe (stdin)
   proc = subprocess.Popen( command,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE
                            )
   
   output = proc.communicate( infoIn['password'] )

   retCode = proc.wait()

   if retCode != 0:
       print FAILED
       return


   # Not mac and we got a good return code: success
   print SUCCESS


'''
 This function prints out the details of the userId supplied.
 Input :
         --username=<user>
 Output:
         --status=success --userInfo=<userId>;<username>;<realname>;<role>:<role>:<role>    Note roles delimited by :
'''
def getUserInfo( infoIn ):
   command = ['/usr/bin/adquery', 'user', '--display', str(infoIn['username'])]
   displayName = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=DEVNULL).communicate()[0].strip()

   if len(displayName) < 1:
	print FAILED
	return

   roleList = getUsersRole( infoIn['username'] )

   # XXX: Are role names with spaces supported?
   outStr = SUCCESS + " --userInfo=" + infoIn["username"] + ";" + infoIn["username"] + ";" + displayName + ";"
   first = 1
   for roleItem in roleList:
      if first:
	  outStr = outStr + roleItem
	  first = 0
      else:
	  outStr = outStr + ":" + roleItem

   print outStr




'''
 This function gets all the users in the system that scripted auth will work for.
 Input :
         N/A
 Output :
           --status=success --userInfo=<userId>;<username>;<realname>;<role>:<role>:<role> --userInfo=<userId>;<username>;<realname>;<role>:<role>:<role>  ...
'''
def getUsers( infoIn ):

       command = ["adquery", "user", "--prefix", "--display"]

       if len(SPLUNKGROUP) > 0:
	       splunkUsers = subprocess.Popen(["adquery", "group", "--members", SPLUNKGROUP], stdout=subprocess.PIPE).communicate()[0]

	       command += splunkUsers.split('\n')

       results = subprocess.Popen(command, stdout=subprocess.PIPE).communicate()[0]

       outStr = SUCCESS

       users = results.split('\n')
       for user in users:
	   names = user.strip().split(':')
	   if len(names) < 2:
	      continue
	   uname = str(names[0])
	   outStr = outStr + " --userInfo=" + uname + ';' + uname + ";" + str(names[1]) + ";"
		
	   roleList = getUsersRole( uname )
	   first = 1
	   for roleItem in roleList:
	      if first:
		  outStr = outStr + roleItem
		  first = 0
	      else:
		  outStr = outStr + ":" + roleItem


       # DEBUG.write(outStr)
       print outStr


def getUsersRole( username ):
    groups = subprocess.Popen(["adquery", "user", "-G", str(username)], stdout=subprocess.PIPE).communicate()[0].strip()

    if groups:
        roles = groups.split('\n')
        return roles
    else:
        print "Unable to find user " + username
        print "Returning lowest role of user"
        return [ "user" ]


  
if __name__ == "__main__":
   callName = sys.argv[1]
   dictIn = readInputs()
   
   returnDict = {}
   if callName == "userLogin":
      userLogin( dictIn )
   elif callName == "getUsers":
      getUsers( dictIn )
   elif callName == "getUserInfo":
      getUserInfo( dictIn )
   elif callName == "getSearchFilter":
      print "ERROR " + callName + " not implemented"
   else:
      print "ERROR unknown function call: " + callName
