#
# SPDX-FileCopyrightText: 2026 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import os
import sys


class JavaArgsGenerator:
    CLASSPATH_ARG = "-classpath"

    # REMOVED_FILES list contains the 3rd party jar files that are
    # removed from add-on (as they are updated with available latest versions)
    # and will not be used in classpath of java process.
    REMOVED_FILES = [
        "log4j-1.2.17.jar",
        "guava-25.0-jre.jar",
        "fastjson-1.2.5.jar",
        "jmx-op-invoke-1.0.jar",
        "jmx-op-invoke-1.1.0.jar",
        "jmx-op-invoke-1.1.1.jar",
        "commons-collections-3.2.2.jar",
        "commons-configuration-1.10.jar",
        "commons-configuration2-2.7.jar",
        "commons-configuration2-2.8.jar",
        "commons-io-2.4.jar",
        "commons-lang-2.6.jar",
        "commons-lang3-3.9.jar",
        "commons-lang3-3.14.0.jar",
        "commons-text-1.8.jar",
        "commons-text-1.9.jar",
        "commons-logging-1.1.1.jar",
        "commons-pool2-2.3.jar",
        "fastjson-1.2.60.jar",
        "guava-30.1-jre.jar",
        "log4j-1.2.17.redhat-3.jar",
        "slf4j-api-1.7.5.jar",
        "slf4j-log4j12-1.7.5.jar",
        "log4j-api-2.14.1.jar",
        "log4j-core-2.14.1.jar",
        "log4j-api-2.15.0.jar",
        "log4j-core-2.15.0.jar",
        "log4j-api-2.16.0.jar",
        "log4j-core-2.16.0.jar",
        "log4j-api-2.18.0.jar",
        "log4j-core-2.18.0.jar",
        "fastjson-1.2.78.jar",
        "commons-io-2.11.0.jar",
        "commons-beanutils-1.9.4.jar",
        "fastjson-1.2.83.jar",
        "commons-configuration2-2.10.1.jar",
        "commons-io-2.18.0.jar",
        "commons-lang3-3.18.0.jar",
        "commons-logging-1.3.5.jar",
        "commons-pool2-2.11.1.jar",
        "commons-text-1.11.0.jar",
        "commons-beanutils-1.11.0.jar",
        "commons-collections4-4.4.jar",
        "log4j-api-2.25.3.jar",
        "log4j-core-2.25.3.jar",
    ]

    def __init__(
        self,
        app_home,
        jar_dirs=["bin", "lib"],
        vm_arguments=None,
        main_class=None,
    ):
        self._app_home = app_home
        self._jar_dirs = jar_dirs
        self._vm_arguments = vm_arguments
        self._main_class = main_class
        if sys.platform == "win32":
            self._classpath_sep = ";"
        else:
            self._classpath_sep = ":"
        if "JAVA_HOME" not in os.environ:
            self._java_executable = "java"
        else:
            self._java_executable = os.path.sep.join(
                [os.environ["JAVA_HOME"], "bin", "java"]
            )

    def generate(self):
        classpath = self._generate_classpath()
        vm_arguments_lst = self._generate_vm_arguments()
        java_args = [
            self._java_executable,
            JavaArgsGenerator.CLASSPATH_ARG,
            classpath,
        ]
        java_args.extend(vm_arguments_lst)
        if self._main_class is not None:
            java_args.append(self._main_class)
        return java_args

    def _generate_vm_arguments(self):
        vm_arguments_lst = []
        if self._vm_arguments is not None:
            for k, v in list(self._vm_arguments.items()):
                vm_arguments_lst.append(k + v)
        return vm_arguments_lst

    def _generate_classpath(self):
        classpath = ""
        for jar_dir in self._jar_dirs:
            dirpath = os.path.sep.join([self._app_home, jar_dir])
            for filename in os.listdir(dirpath):
                if (
                    filename.endswith(".jar")
                    and filename not in JavaArgsGenerator.REMOVED_FILES
                ):
                    filepath = os.path.join(dirpath, filename)
                    if os.path.isfile(filepath):
                        classpath = classpath + self._classpath_sep + filepath
        return classpath
