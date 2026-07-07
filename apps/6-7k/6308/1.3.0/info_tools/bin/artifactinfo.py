import re,os,csv,sys,time,glob

from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators

@Configuration(type='reporting')

class ArtifactInfo(GeneratingCommand):

	sid = Option(require=False)
	search = Option(require=False)
	regex = Option(require=False)

	def generate(self):
		dispatchdir = os.sep.join([os.environ['SPLUNK_HOME'], "var", "run", "splunk", "dispatch"])
		if self.sid:
			artifact = os.sep.join([dispatchdir,self.sid,"info.csv"])
			with open(artifact, mode='r') as file:
				csv_file = csv.DictReader(file)
				for row in csv_file:
					yield dict(row)
		elif self.search:
			sid = self._metadata.searchinfo.sid
			cur_path = os.sep.join([dispatchdir,"*","info.csv"])
			for name in glob.glob(cur_path):
				with open(name, 'r') as file:
					if self.search in file.read():
						if sid not in name:
							yield self.gen_record(result="found", artifact=name)
		elif self.regex:
			sid = self._metadata.searchinfo.sid
			cur_path = os.sep.join([dispatchdir,"*","info.csv"])
			for name in glob.glob(cur_path):
				with open(name, 'r') as file:
					m=re.search(rf"{self.regex}",file.read())
					if m is not None:
						if sid not in name:
							yield self.gen_record(result=m.group(), artifact=name)
dispatch(ArtifactInfo, sys.argv, sys.stdin, sys.stdout, __name__)
