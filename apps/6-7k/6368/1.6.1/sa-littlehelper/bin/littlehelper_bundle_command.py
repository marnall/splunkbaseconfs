#!/usr/bin/env python

import os
import json
import sys
from datetime import datetime, timezone

app_lib_folder = os.path.join(os.path.dirname(__file__), "..", "lib")
sys.path.insert(0, app_lib_folder)
from sa_littlehelper import LittleHelperCommand, Target, Bundle, Distribution, splunk_json_get, bundle_path_info, LocalBundleWalker
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators

CAP = "run_bundlefiles"
UNKNOWN = "UNK"

@Configuration(distributed=False)
class BundleInfoCommand(GeneratingCommand, LittleHelperCommand):
    target = Option(require=False, default=Target.CAPTAIN, validate=validators.Set(*list(Target)))
    bundle = Option(require=False, default=Bundle.LATEST, validate=validators.Set(*list(Bundle)))
    distribute = Option(require=False, default=Distribution.LOCAL, validate=validators.Set(*list(Distribution)))


    def prepare(self):
        self.check_capability(CAP)

        if Distribution(self.distribute).include_remote:
            self._configuration.distributed = True

    def write_result(self,result):
        path = result.get('path',UNKNOWN)
        size = result.get('bytes',UNKNOWN)
        epoch = result.pop('mtime')

        #if available, fall back to the bundle time
        if not epoch:
            try:
                epoch = float(result.get('bundle_epoch'))
            except (TypeError,ValueError):
                pass

        #otherwise fall back to the search time
        if not epoch:
            epoch = self.search_now

        try:
            time = datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%FT%T%z")
        except (ValueError,OSError,TypeError) as e:
            self.message_writer("ERROR",f'Error converting "{epoch}" to timestamp: {e}')
            time = UNKNOWN
        return self.gen_record(_time=epoch, _raw=f"{time}\t{size}\t{path}", **result)


    def generate(self):
        if not self.is_remote and Bundle(self.bundle).is_computed():
            self.message_writer("INFO",f"bundle={self.bundle} is only an approximation.")

        # Only generate records if (local AND distribute includes local) OR if remote.
        if not self.is_remote and not Distribution(self.distribute).include_local:
            return

        walker = LocalBundleWalker(self.service, self.target, self.message_writer, self.logger)
        for filedata in walker.walk(self.bundle):
            yield self.write_result(filedata)

        # Only call the REST API if local and the target means that we have more to include. 
        if self.is_remote or not walker.call_rest:
            return

        data = splunk_json_get(client=self.service, path=f"/services/littlehelper-bundle",
                               target=self.target, bundle=self.bundle, skip_local="yes")

        for msg in data['messages']:
            self.message_writer(*msg)

        for result in data['results']:
            yield self.write_result(result)

dispatch(BundleInfoCommand, sys.argv, sys.stdin, sys.stdout, __name__)
