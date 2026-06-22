# Copyright 2014-2024 Sideview, LLC. all rights reserved
import os
import pathlib
import glob
import shutil
from subprocess import Popen, PIPE
import sys
import tempfile
import time

#Arrange to load module from canary bin
script_path = pathlib.Path(sys.argv[0]).resolve()
apps_dir =  script_path.parent.parent.parent
canary_bin = apps_dir / "canary" / "bin"
sys.path.append(str(canary_bin))
import build_util

APP_NAME = build_util.get_appname()

# REMEMBER
#1) build and version   (app.conf)
#2) text on homepage,   (default/data/ui/views/home.xml)
#3) release notes,      (appserver/static/release_notes.txt)
#4) python unit tests pass
#5) AppInspect - only has passes and any known failures.
#6) run build.py in source.

def build(args):
    with tempfile.TemporaryDirectory(prefix=f"{APP_NAME}-build") as temp_build_dir:
        target_dir = os.path.join(temp_build_dir, APP_NAME)

        build_util.svn_export(args.svn_trunk, target_dir)

        #print("deleting bin/test subdirectory")
        #shutil.rmtree(os.path.join(target_dir, "bin", "test"))

        os.chdir(os.path.join(target_dir, "bin"))
        print("deleting build.py")
        os.remove("build.py")

        time.sleep(1)
        build_util.tar_it_up(temp_build_dir, args.output_dir, args.version)


if __name__ == '__main__':
    args = build_util.getargs()
    build(args)
