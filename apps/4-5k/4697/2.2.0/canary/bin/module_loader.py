# -*- coding: utf-8 -*-
#Copyright (C) 2015-2026 Sideview LLC.  All Rights Reserved.
"""
    Contains functions and classes used by Canary to deal with module classes
    and resource files.
"""

import logging
import os
import sys
import yaml

import sideview_canary as sv
from splunk.clilib import bundle_paths
import splunk.clilib.cli_common as cli_common

logger = sv.setup_logging(logging.DEBUG)

APP = "canary"


CONF_EXTENSION = ".conf"




def get_params(conf):
    """
    for a particular module, load the information about the params it can take.
    """
    assert "module" in conf
    assert conf["module"].get("className", False)

    params = {}
    for stanza_name, stanza in conf.items():
        if stanza_name.startswith("param:"):
            param_name = stanza_name[6:].strip()
            params[param_name] = {}

            if "default" in stanza and 'required' in stanza and stanza["required"] == "True":
                logger.error("%s lists param %s as required but then has a default key.",
                             stanza_name, param_name)
                return {}
            if "values" in stanza:
                clean_values = []
                for val in stanza["values"].split(","):
                    clean_values.append(val.strip())
                stanza["values"] = clean_values

            for key in stanza:
                params[param_name][key] = stanza[key]

    return params



def get_conf_file(module_dir):
    """ for each directory tell me if there's a conf file in it with the same name."""
    for directory, _subdirectory, files in os.walk(module_dir):
        for name in files:
            if name.endswith(CONF_EXTENSION):
                # TODO - remove this and replace with a non-cli-common conf reader.
                return (name, cli_common.readConfFile(os.path.join(directory, name)))
    return False, False



def path_to_url(app, path):
    """
    given a FS path of
        C:\\LOTS_OF_THINGS\\appserver\\static\\sideview\\modules\\NavBar\\NavBar.js
    returns a url of
        /static/app/canary/sideview/modules/NavBar/NavBar.js
    """
    static_file_path = sv.get_static_file_path(app)
    if path.index(static_file_path) == -1:
        raise ValueError("this path %s is not within appserver/static" % path)
    path = path.replace("%s%s" % (static_file_path, os.sep), "")
    path = path.split(os.sep)
    return "/".join(path)



def simple_memoize_by_app_and_theme(func):
    """Memoize function results by (app_name, theme) tuple"""
    cache = {}

    def memoized_func(app_name, theme="light"):
        key = (app_name, theme)
        if key not in cache:
            cache[key] = func(app_name, theme)
        return cache[key]

    return memoized_func

@simple_memoize_by_app_and_theme
def get_modules_for_app(app_name, theme="light"):
    """Returns a dict of dicts, each containing everything you need to know
    about a given Canary UI module (HTML, CSS files, etc.)"""

    root_module_dir = os.path.join(
        os.environ['SPLUNK_HOME'],
        "etc", "apps", app_name,
        "appserver", "static", "lib", "modules"
    )

    # Early exit if directory doesn't exist
    if not os.path.isdir(root_module_dir):
        logger.warning("Module directory not found: %s", root_module_dir)
        return {}

    modules = {}

    # Single directory walk - process everything in one pass
    for module_dir, _subdirectories, files in os.walk(root_module_dir):
        # Skip the root directory
        if module_dir == root_module_dir:
            continue

        # Find conf file (should be only one per module)
        conf_file = None
        conf_name = None
        for filename in files:
            if filename.endswith(CONF_EXTENSION):
                conf_file = filename
                conf_name = filename[:-len(CONF_EXTENSION)]
                break

        if not conf_file:
            continue

        # Read configuration
        conf_path = os.path.join(module_dir, conf_file)
        conf = cli_common.readConfFile(conf_path)

        if not conf or "module" not in conf:
            continue

        class_name = conf["module"].get("className")
        if not class_name:
            continue

        # Build module definition
        mod = {
            "params": get_params(conf),
            "class": class_name,
            "description": conf["module"].get("description"),
            "filePrefix": conf_name,
            "path": module_dir,
            "appName": app_name
        }

        # Add hierarchy directives
        for rule in sv.HIERARCHY_DIRECTIVES:
            rule_value = conf["module"].get(rule)
            if rule_value in ("True", "False"):
                mod[rule] = (rule_value == "True")

        # Process resource files
        for filename in files:
            if filename == conf_file:
                continue

            # Skip backup files (e.g., foo.js.bak)
            parts = filename.split(".")
            if len(parts) != 2:
                continue

            ext = parts[1]
            full_path = os.path.join(module_dir, filename)

            if ext == "js":
                # JS files get URL paths
                mod["js"] = path_to_url(app_name, full_path)

            elif ext == "css":
                # CSS files get URL paths, filtered by theme
                file_theme = "dark" if "dark" in filename else "light"
                if theme == file_theme:
                    mod["css"] = path_to_url(app_name, full_path)

            else:
                # All other files get filesystem paths
                mod[ext] = full_path

        modules[class_name] = mod

    return modules


def get_modules(session_key=None, theme="light"):
    """Returns a dict of dicts, each dict represents one module.
    Aggregates all valid modules in the system.

    NOTE: Currently only the canary app can provide custom modules.
    """

    if not session_key:
        raise ValueError("session_key is required")

    all_modules = {}

    # Currently only canary app is allowed to load custom modules
    # Future: extend to all non-disabled apps
    supported_apps = ["canary"]

    for app_name in supported_apps:
        app_modules = get_modules_for_app(app_name, theme)

        # Check for module name conflicts
        conflicts = set(app_modules.keys()) & set(all_modules.keys())
        if conflicts:
            raise ImportError(
                "Cannot import modules {} from {}. Another app already has these modules.".format(
                    ", ".join(conflicts), app_name
                )
            )

        all_modules.update(app_modules)

    return all_modules