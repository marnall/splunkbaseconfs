import os,sys,time

from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators

@Configuration(type='reporting')

class SpecInfo(GeneratingCommand):

	spec = Option(require=True)

	def generate(self):
		readmedir = os.sep.join([os.environ['SPLUNK_HOME'], "etc", "system", "README"])
		if self.spec:
			specfile = os.sep.join([readmedir,self.spec]) + ".conf.spec"
			try :
				with open(specfile, mode='r') as file:
					for line in file:
						yield self.gen_record(contents=line)
				file.close()
			except OSError:
				yield self.gen_record(contents=".spec file not found")
dispatch(SpecInfo, sys.argv, sys.stdin, sys.stdout, __name__)
