import sys, traceback
from ds_utils import log  
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
from splunk.clilib.bundle_paths import make_splunkhome_path
import splunk.appserver.mrsparkle.lib.util as splunk_lib_util
from setup import  copy_apps, set_app_checkpoint, convert_conf_to_csv  

@Configuration()
class MigrateDS(GeneratingCommand):
    serverclass = Option(require=True)
    apps=Option(require=True)
    override=Option(require=True)

    def generate(self):

        try:
            log("INFO", "DS migrate is started ...")
            override=self.override.lower()
            apps=self.apps.lower()
            serverclass=self.serverclass.lower()
            if apps=="true":
                copy_apps(override)
                set_app_checkpoint()
            if serverclass=="true":
                convert_conf_to_csv(override)   
                  
            log("INFO", "DS migrate completed")
            yield {"status": "success", "message" : "Migration Completed"}

        except Exception as e:
            # Handle errors and return error result to JavaScript
            log("ERROR", f"Error during dsmigrate execution: {str(e)}")
            log("ERROR",traceback.format_exc())
            result = {"status": "error", "message": f"An error occurred: {str(e)}"}
            yield result

dispatch(MigrateDS, sys.argv, sys.stdin, sys.stdout, __name__)