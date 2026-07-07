import glob,os,re,sys

from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators

@Configuration(type='reporting')

class UserInfo(GeneratingCommand):
	
	def generate(self):

		userdir = os.sep.join([os.environ['SPLUNK_HOME'], "etc", "users", "**"])
		for name in glob.glob(userdir, recursive=True):
			if os.path.isfile(name):
				info=os.stat(name)
				size=info.st_size
				mtime=int(info.st_mtime)
				m=re.search(r"users[\/\\]([^\/\\]+)[\/\\]([^\/\\]+)[\/\\](.+)$",name)
				if m is not None:
					if m.lastindex==3:
						user=m.group(1)
						app=m.group(2)
						fileobject=m.group(3)
						yield self.gen_record(user=user, app=app, fileobject=fileobject, size=info.st_size, mtime=mtime)
					else:
						continue

dispatch(UserInfo, sys.argv, sys.stdin, sys.stdout, __name__)
