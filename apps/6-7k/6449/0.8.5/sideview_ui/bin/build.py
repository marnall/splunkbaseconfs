# -*- coding: utf-8 -*-
# Copyright 2014-2023 Sideview, LLC. all rights reserved
import os
import pathlib
import shutil
from subprocess import Popen, PIPE
import sys
import tempfile

#Arrange to load module from canary bin
script_path = pathlib.Path(sys.argv[0]).resolve()
apps_dir =  script_path.parent.parent.parent
canary_bin = apps_dir / "canary" / "bin"
sys.path.append(str(canary_bin))
import build_util

APP_NAME = build_util.get_appname()


# REMEMBER
#1) build and version   (app.conf)
#2) release notes,      (appserver/default/data/ui/release_notes.xml)
#3) python unit tests pass
#4) qunit tests pass on firefox, chrome (IE?)
#5) AppInspect - only has passes and any known failures.
#6) run build.py in source.

def build(args):
    with tempfile.TemporaryDirectory(prefix=f"{APP_NAME}-build") as temp_build_dir:
        target_dir = os.path.join(temp_build_dir, APP_NAME)

        build_util.svn_export(args.svn_trunk, target_dir)

        print("deleting bin/test subdirectory")
        shutil.rmtree(os.path.join(target_dir, "bin", "test"))

        #print("deleting all the qunit code")
        #shutil.rmtree(os.path.join(target_dir, "appserver","static","lib","qunit"))

        #print("deleting the saved searches")
        #os.chdir(os.path.join(target_dir, "default"))
        #os.remove("savedsearches.conf")

        #print("deleting any html dashboards")
        #shutil.rmtree(os.path.join(target_dir, "default","data","ui","html"))

        os.chdir(os.path.join(target_dir, "default", "data", "ui", "views"))
        for f in os.listdir('.'):
            if f.startswith("dev_"):
                print("deleting dev view -- %s" % f)
                os.remove(f)

        print("deleting build.py")
        os.chdir(os.path.join(target_dir, "bin"))
        os.remove("build.py")
        #print("deleting es_proxy.py, just because we don't really test it.")
        #os.remove("es_proxy.py")

        build_util.tar_it_up(temp_build_dir, args.output_dir, args.version)

    # find . -name '*.js' | grep -v "jquery" | grep -v "chartjs" | grep -v "json2" | grep -v "sprintf" | grep -v "qunit" | grep -v "strftime" | grep -v "moment_" | grep -v "google_palette" | grep -v "require" | grep -v "twix" | xargs wc -l
    #  17,396 lines js 9/14/19
    #  20,553 lines 3/9/2021
    # find . -name '*.py' | grep -v "yaml2" | grep -v "yaml3" | grep -v "/test/" | xargs wc -l
    # 2,687 lines 9/14/2019
    # 3,675 lines 3/9/2021
if __name__ == '__main__':
    args = build_util.getargs()
    build(args)
