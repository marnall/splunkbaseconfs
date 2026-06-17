#
#

import os
import csv
from splunk.clilib.bundle_paths import make_splunkhome_path
from .modularinput import ModularInput as ModularInput
from aplspl.utilities.thanos import Thanos as Thanos
import hashlib
from splunk.util import normalizeBoolean

__author__ = 'ksmith'


class Upgrader(ModularInput):

    def __init__(self, logger=None, **kwargs):
        ModularInput.__init__(self, **kwargs)
        self.app_name = kwargs.get("app_name")
        self._manifest = []
        self._raw_manifest = []
        self._log = logger
        self.thanos = Thanos(app_name=self.app_name,
                             session_key=self.get_config("session_key"),
                             logger=self._log,
                             files_to_remove=[])
        self._load_manifest()

    def _load_manifest(self):
        manifest_file = make_splunkhome_path(["etc", "apps", self.app_name, "file.manifest"])
        if os.path.isfile(manifest_file):
            self._log.debug(f"action=found_manifest location={manifest_file}")
            with open(manifest_file, mode='r') as file:
                # reading the CSV file
                csvFile = csv.reader(file)

                # displaying the contents of the CSV file
                for lines in csvFile:
                    filename = lines[1]
                    md5sum = lines[0]
                    self._log.debug(f"action=manifest_file file={filename} md5sum={md5sum}")
                    self._manifest.append({"name": filename, "hash": md5sum})
                    self._raw_manifest.append(make_splunkhome_path(["etc", "apps", self.app_name, filename]))
        else:
            self._log.warn(f"action=manifest_not_found location={manifest_file}")

    def perform_check(self):
        for lines in self._manifest:
            filename = lines.get("name", "app.manifest")
            md5sum = lines.get("hash", "s")
            check_file = make_splunkhome_path(["etc", "apps", self.app_name, filename])
            if os.path.isfile(check_file):
                check_file_hash = hashlib.md5(open(check_file, 'rb').read()).hexdigest()
                if md5sum == check_file_hash:
                    self._log.debug(
                        f"action=check_file_hash file={check_file} manifest_hash={md5sum} check_hash={check_file_hash} are_equal={md5sum == check_file_hash}")
                else:
                    self._log.warn(
                        f"action=check_file_hash file={check_file} manifest_hash={md5sum} check_hash={check_file_hash} are_equal={md5sum == check_file_hash}")
            else:
                self._log.warn(
                    f"action=invalid_file_in_manifest msg=file_not_found filename={check_file} hash={md5sum}")
        self._log.debug("action=settings settings={}".format(self.get_config("destructive_walk")))
        app_home = make_splunkhome_path(["etc", "apps", self.app_name])
        # if self.get_config("destructive_walk"):
        exclude_prefixes = ['node_modules',
                            "__pycache__",
                            ".idea",
                            ".gitignore",
                            "file.manifest",
                            "local.meta",
                            os.path.join(app_home, "appserver", "build"),
                            os.path.join(app_home, "appserver", "addons"),
                            os.path.join(app_home, "local"),
                            os.path.join(app_home, "lib")]
        self._log.debug(f"action=walk_the_line exclude={exclude_prefixes}")

        do_removal = normalizeBoolean(self.get_config("destructive_walk"))

        def do_dir(d):
            dir_list = os.listdir(d)
            self._log.debug(f"action=walk_the_line dir={d} list={dir_list}")
            for fd in dir_list:
                item = os.path.join(d, fd)
                if item in exclude_prefixes or fd in exclude_prefixes:
                    self._log.debug(f"action=walk_the_line item={item} status=skipping")
                    continue
                if os.path.isfile(item):
                    self._log.debug(f"action=walk_the_line path={item} is_file=true is_dir=false")
                    if item in self._raw_manifest:
                        self._log.debug(f"action=walk_the_line filename={item} status=found_in_manifest")
                    else:
                        self._log.warn(
                            f"action=walk_the_line filename={item} status=not_found_in_manifest do_removal={do_removal}")
                        if do_removal:
                            self._log.info(f"action=walk_the_line filename={item} status=deleting")
                            # os.remove(item)

                if os.path.isdir(item) and item not in exclude_prefixes:
                    self._log.debug(f"action=walk_the_line path={item} is_file=false is_dir=true")
                    do_dir(item)

            # Do the recursion, skipping the raw_manifest ones

        do_dir(app_home)

        self._log.debug(f"action=walk_the_line status=complete")

