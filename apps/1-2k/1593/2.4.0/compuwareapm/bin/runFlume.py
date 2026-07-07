import sys
import os
import subprocess

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)


try:
	retcode = subprocess.call(["java", "-version"])
	if retcode < 0:
		print >> sys.stderr, "Java not in Path", -retcode
	else:
		print >> sys.stdout, "Child returned", retcode
except OSError as e:
    print >>sys.stderr, "Execution failed:", e

appdir = os.path.abspath(os.path.join(os.path.dirname(__file__),".."))

if not appdir:
    appdir = os.getcwd();
else:
    print >> sys.stdout, "App directory:", appdir




c1 = os.path.join(appdir, "bin", "apache-flume-1.7.0-bin", "lib", "*")
c2 = os.path.join(appdir, "bin", "apache-flume-1.7.0-bin", "lib", "flume-ng-node-1.7.0.jar")
c3 = os.path.join(appdir, "bin", "dtFlume.jar")

javapath = os.path.join(os.sep, "usr", "bin", "java")

classpath = c1 + os.pathsep + c2 + os.pathsep + c3

print >> sys.stdout, "Class path:", classpath

log4j = os.path.join(appdir,"bin", "apache-flume-1.7.0-bin", "conf", "log4j.properties")

flumeconf = os.path.join(appdir,"bin","flume-conf.properties");

pidfilename = os.path.join(appdir, 'flume.pid')

cmdline = javapath + " -Xmx20m -Dlog4j.configuration=file:" + log4j + " -cp " + classpath + " org.apache.flume.node.Application -f " + flumeconf + " -n agent1"

# check current OS for process detection
currentOS = os.name

# OS detection drives process for detecting running Flume instances based on pid file	
if currentOS == 'posix':
	if os.access(pidfilename, os.F_OK):
		flumeFilepid = int(open(pidfilename).read())
		if os.path.exists("/proc/%s" % flumeFilepid): 
			print >>sys.stderr, "Process already running as PID ", flumeFilepid
			sys.exit(1)
		else:
			print >>sys.stderr, "PID file exists but process is no longer running. Removing pidfile"
			os.remove(pidfilename)
	try:
		p = subprocess.Popen(['java', '-Xmx20m', '-Dlog4j.configuration=file:%s' % log4j,'-cp', classpath, 'org.apache.flume.node.Application', '-f', flumeconf, '-n', 'agent1'], stdout=subprocess.PIPE)
		flumepid = p.pid
		pidfile = open(pidfilename, 'w')
		pidfile.write(str(p.pid))
		pidfile.close()
		cmdout,cmderr =  p.communicate()
		retcode = p.wait()
		if retcode < 0:
			print >>sys.stderr, "Child was terminated by signal", -retcode
		else:
			print >>sys.stdout, "Child returned", retcode
	except OSError as e:
			print >>sys.stderr, "Execution failed:", e
else:
	if currentOS == 'nt':
		print "Windows based OS"
		if os.access(pidfilename, os.F_OK):
			flumeFilepid = int(open(pidfilename).read())
			tasklistcmd = 'tasklist /fi \"PID eq %i\"' % flumeFilepid		
			tasklist = subprocess.check_output(tasklistcmd).strip()
			if "INFO" not in tasklist:
				print >>sys.stderr, "Flume or process with same PID already running"
				sys.exit(1)
		try:
			p = subprocess.Popen(['java', '-Xmx20m', '-Dlog4j.configuration=file:%s' % log4j,'-cp', classpath, 'org.apache.flume.node.Application', '-f', flumeconf, '-n', 'agent1'], stdout=subprocess.PIPE)
			flumepid = p.pid
			pidfile = open(pidfilename, 'w')
			pidfile.write(str(p.pid))
			pidfile.close()
			cmdout,cmderr =  p.communicate()
			retcode = p.wait()
			if retcode < 0:
				print >>sys.stderr, "Child was terminated by signal", -retcode
			else:
				print >>sys.stdout, "Child returned", retcode
		except OSError as e:
			print >>sys.stderr, "Execution failed:", e	
	else:
		print >>sys.stdout, "Unsupported OS"
		sys.exit(1)
		



