
import glob,os,sys

from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators

@Configuration(type='reporting')

class VarInfo(GeneratingCommand):

	subdir = Option(require=False)

	def generate(self):
		if self.subdir:
			if ".." in self.subdir:
				sdir="zyxw"
			else:
				sdir=self.subdir
		else:
			sdir="*"
		vardir = os.sep.join([os.environ['SPLUNK_HOME'], "var", sdir, "**"])
		for name in glob.glob(vardir, recursive=True):
			if os.path.isfile(name):
				info=os.stat(name)
				size=info.st_size
				mtime=int(info.st_mtime)
				yield self.gen_record(file=name, size=info.st_size, mtime=mtime)

dispatch(VarInfo, sys.argv, sys.stdin, sys.stdout, __name__)
