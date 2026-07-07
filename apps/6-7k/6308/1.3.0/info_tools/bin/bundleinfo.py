import glob,os,sys,tarfile

from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators

@Configuration(type='reporting')

class BundleInfo(GeneratingCommand):
	
	def generate(self):

		filter = "*.bundle"
		bundles = os.sep.join([os.environ['SPLUNK_HOME'], "var", "run", filter])
		latest_mtime=int(0)
		latest_bundle=""
		for name in glob.glob(bundles):
			entry=os.stat(name)
			mtime=int(entry.st_mtime)
			if mtime>latest_mtime:
				latest_mtime=mtime
				latest_bundle=name
		tball=tarfile.open(latest_bundle,"r")
		for tfile in tball.getmembers():
			yield self.gen_record(bundle=latest_bundle, file=tfile.name, size=tfile.size, mtime=tfile.mtime)
		tball.close()
dispatch(BundleInfo, sys.argv, sys.stdin, sys.stdout, __name__)
