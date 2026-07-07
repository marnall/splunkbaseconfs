import re,os,subprocess,sys
from subprocess import run,PIPE

from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option

@Configuration(type='reporting')

class BtoolInfo(GeneratingCommand):

	conf = Option(require=True)

	def generate(self):
		splunkhome=os.environ['SPLUNK_HOME']
		splunkcmd = os.sep.join([os.environ['SPLUNK_HOME'], "bin", "splunk"])
		btool = subprocess.run([splunkcmd, "btool", self.conf, "list", "--debug"], stdout=PIPE).stdout.decode("utf-8").splitlines()
		stanza=""
		value=""
		for s in btool:
			if splunkhome in s:
				if value:
					yield {'confpath': confpath, 'stanza': stanza, 'property': prop, 'value': value}
				m=re.search(r"^("+re.escape(splunkhome)+"\S+)"+"\s+(\[.+]|[^=]+)(?:\s*=\s*)*(.+)*",s)
				if m is not None:
					confpath=m.group(1)
					prop=m.group(2)
					if prop[0]=="[":
						stanza=prop
						prop=""
						value=""
					if m.lastindex==3:
						value=m.group(3)
					else:
						value=""
			else:
				value=value+s
		yield self.gen_record(confpath=confpath, stanza=stanza, property=prop, value=value)

dispatch(BtoolInfo, sys.argv, sys.stdin, sys.stdout, __name__)
