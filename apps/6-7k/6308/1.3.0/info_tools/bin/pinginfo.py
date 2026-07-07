import re,os,subprocess,sys,time
from subprocess import run,PIPE

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators

@Configuration(type='reporting')

class PingInfo(GeneratingCommand):

	address = Option(require=True)
	count = Option(require=False)

	def generate(self):
		if self.count and int(self.count) > 0 and int(self.count) < 11:
			pcount="-c"+self.count
		else:
			pcount="-c3"
		ping = subprocess.run(['ping', '-n', pcount, self.address], capture_output=True)

		for p in ping.stdout.decode("utf-8").splitlines():
			x = re.search("time|ms", p)
			if x:
				yield {'pingdata': p}
dispatch(PingInfo, sys.argv, sys.stdin, sys.stdout, __name__)
