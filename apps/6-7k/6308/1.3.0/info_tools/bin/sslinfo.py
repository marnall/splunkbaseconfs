import re,os,subprocess,sys,time
from subprocess import run,PIPE

from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators

@Configuration(type='reporting')

class TestInfo(GeneratingCommand):

	hostport = Option(require=True)
	timeout = Option(require=False)

	def generate(self):
		if self.timeout and int(self.timeout) > 0 and int(self.timeout) < 31:
			timeout=int(self.timeout)
		else:
			timeout=5
		splunkhome=os.environ['SPLUNK_HOME']
		cmd = os.sep.join([os.environ['SPLUNK_HOME'], "bin", "openssl"])
		ssl = subprocess.Popen([cmd, "s_client",  "-connect", self.hostport], stdin=PIPE, stdout=PIPE)
		time.sleep(timeout)
		outs, errs = ssl.communicate(input=(b'Q\n'))
		for s in outs.decode("utf-8").splitlines():
			yield self.gen_record(data=s)

dispatch(TestInfo, sys.argv, sys.stdin, sys.stdout, __name__)
