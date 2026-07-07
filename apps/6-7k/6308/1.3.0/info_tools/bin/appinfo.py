import glob,os,sys

from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators

@Configuration(type='reporting')

class AppInfo(GeneratingCommand):

	app = Option(require=False)

	def generate(self):
		if self.app:
			if ".." in self.app:
				sdir="zyxw"
			else:
				sdir=self.app
		else:
			sdir="*"
		appdir = os.sep.join([os.environ['SPLUNK_HOME'], "etc", "apps", sdir, "**"])
		for name in glob.glob(appdir, recursive=True):
			if os.path.isfile(name):
				info=os.stat(name)
				size=info.st_size
				mtime=int(info.st_mtime)
				yield self.gen_record(file=name, size=info.st_size, mtime=mtime)

dispatch(AppInfo, sys.argv, sys.stdin, sys.stdout, __name__)
