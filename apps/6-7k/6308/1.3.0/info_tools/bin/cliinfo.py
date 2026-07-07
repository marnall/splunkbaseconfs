import re,os,subprocess,sys
from subprocess import run,PIPE

from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators

@Configuration(type='reporting')

class CliInfo(GeneratingCommand):

	clicmd = Option(require=True)

	def generate(self):
		splunkhome=os.environ['SPLUNK_HOME']
		splunkcmd = os.sep.join([os.environ['SPLUNK_HOME'], "bin", "splunk"])
		args = re.split("\s",self.clicmd)
		allowed = re.search("status|list|show|display|help", args[0])
		auth_needed =  re.search("list|show|display", args[0])
		if auth_needed:
			args.append("-token")
			args.append(self._metadata.searchinfo.session_key)
		if allowed:
			if len(args) == 1:
				cmd = subprocess.run([splunkcmd, args[0]], stdout=PIPE, stderr=subprocess.STDOUT).stdout.decode("utf-8").splitlines()
			elif len(args) == 2:
				cmd = subprocess.run([splunkcmd, args[0], args[1]], stdout=PIPE, stderr=subprocess.STDOUT).stdout.decode("utf-8").splitlines()
			elif len(args) == 3:
				cmd = subprocess.run([splunkcmd, args[0], args[1], args[2]], stdout=PIPE, stderr=subprocess.STDOUT).stdout.decode("utf-8").splitlines()
			elif len(args) == 4:
				cmd = subprocess.run([splunkcmd, args[0], args[1], args[2], args[3]], stdout=PIPE, stderr=subprocess.STDOUT).stdout.decode("utf-8").splitlines()
			elif len(args) == 5:
				cmd = subprocess.run([splunkcmd, args[0], args[1], args[2], args[3], args[4]], stdout=PIPE, stderr=subprocess.STDOUT).stdout.decode("utf-8").splitlines()
			for s in cmd:
				if len(s) > 0:
					yield self.gen_record(cmdout=s)		
		else:
			yield self.gen_record(cmdout="not allowed")

dispatch(CliInfo, sys.argv, sys.stdin, sys.stdout, __name__)
