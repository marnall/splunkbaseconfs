#
# SPDX-FileCopyrightText: 2026 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import import_declare_test
import os
import subprocess
import json
import base64
import sys
import os.path as op
import time
import traceback

import splunktalib.common.log as log
from splunktalib.state_store import get_state_store
from splunktalib.timer_queue import TimerQueue

import jboss_consts as c
import java_args_gen as jag


class JMXOpInvoker:

    _LOGGER = log.Logs().get_logger(c.JBOSS_LOG)

    _OP_INVOKE_HOME_ARG = "jmx_op_invoke_home"

    _DIR_NAME = "jmx-op-invoke-1.2.0"

    _OP_INVOKE_HOME = op.join(op.dirname(op.abspath(__file__)), "java", _DIR_NAME)

    _MAIN_CLASS = "com.splunk.jmxopinvoke.JMXOpInvokeBootstrap"

    _INVOKE_JOBS_ARG = "invoke_jobs"

    _FILE_CONTENT = dict()

    def __init__(self, meta, stanzas):
        self._meta = meta
        self._stanzas = stanzas
        self._checkpoint_dir = None
        self._state_store = None
        self._timer_queue = None
        self._process = None
        self._task_files = list()

    def start(self):
        self._LOGGER.info("Starting JMXOpInvoker...")
        self._checkpoint_dir = self._meta.get(c.CHECKPOINT_DIR)
        if not self._checkpoint_dir:
            self._LOGGER.error(c.CHECKPOINT_DIR + " is null")
            return
        self._stanzas = self._get_valid_stanzas(self._stanzas)
        if not self._stanzas:
            return
        self._state_store = self._create_state_store()
        self._generate_task_files()
        self._start_scheduler()
        program_inputs = self._generate_program_input()
        for program_input in program_inputs:
            input_json = json.dumps(program_input)
            # Path to the log file for Java code to refer the configs from
            log4j2_xml_path = os.path.sep.join(
                [self._OP_INVOKE_HOME, "config", "log4j2.xml"]
            )

            vm_arguments = {
                c.LOG_PATH_PARAMS: c.LOG_PATH,
                c.LOG_LEVEL_PARAMS: c.LOG_LEVEL_VALUE,
                c.LOG4J_2_PROP_FILE: log4j2_xml_path,
            }
            args_generator = jag.JavaArgsGenerator(
                app_home=self._OP_INVOKE_HOME,
                vm_arguments=vm_arguments,
                main_class=self._MAIN_CLASS,
            )
            java_args = args_generator.generate()
            self._process = subprocess.Popen(
                java_args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,  # nosemgrep false-positive : The value java_args is static value from java_args_gen.py file. It doesn't take any external/user inputs.
                stderr=subprocess.PIPE,
            )
            self._process.stdin.write(input_json.encode("utf-8"))
            self._process.stdin.close()
            self._get_output()

    def stop(self):
        self._LOGGER.info("Stopping JMXOpInvoker...")
        if self._process is not None:
            self._process.kill()
        if self._timer_queue is not None:
            self._timer_queue.tear_down()
        for task_file in self._task_files:
            self._state_store.delete_state(task_file)
        self._LOGGER.info("JMXOpInvoker stopped")

    @classmethod
    def _get_valid_stanzas(cls, stanzas):
        valid_stanzas = list()
        for stanza in stanzas:
            if not cls._validate_stanza(stanza):
                cls._LOGGER.error(
                    "Stanza " + stanza.get(c.NAME, "None") + " is invalid"
                )
                continue
            stanza[c.NAME] = cls._generate_format_name(stanza.get(c.NAME))
            valid_stanzas.append(stanza)
        return valid_stanzas

    @classmethod
    def _validate_stanza(cls, stanza):
        if any(
            (
                not stanza[k]
                for k in (
                    c.DURATION,
                    c.NAME,
                    c.JMX_URL,
                    c.OBJECT_NAME,
                    c.OPERATION_NAME,
                )
            )
        ):
            return False
        return True

    @classmethod
    def _generate_format_name(cls, name):
        return base64.b64encode(name.encode("utf-8")).decode("ascii")

    def _create_state_store(self):
        state_store = get_state_store(
            meta_configs=self._meta, appname=c.APP_NAME, use_kv_store=False
        )
        return state_store

    def _generate_task_files(self):
        for stanza in self._stanzas:
            name = stanza.get(c.NAME)
            if not name:
                continue
            file_path = os.path.sep.join([self._checkpoint_dir, name])
            self._state_store.update_state(file_path, self._FILE_CONTENT)

    def _generate_program_input(self):
        program_inputs = list()
        invoke_jobs = list()
        for stanza in self._stanzas:
            program_input = dict()
            program_input[c.CHECKPOINT_DIR] = self._checkpoint_dir
            program_input[self._OP_INVOKE_HOME_ARG] = self._OP_INVOKE_HOME
            invoke_job = dict()
            invoke_job[c.NAME] = stanza.get(c.NAME)
            # get index
            index = stanza.get(c.INDEX)
            if index:
                invoke_job[c.INDEX] = index
            invoke_job[c.JMX_URL] = stanza.get(c.JMX_URL)
            # get username
            username = stanza.get(c.USERNAME)
            if username:
                invoke_job[c.USERNAME] = username
            # get password
            password = stanza.get(c.PASSWORD)
            if password:
                invoke_job[c.PASSWORD] = password
            #
            invoke_job[c.OBJECT_NAME] = stanza.get(c.OBJECT_NAME)
            invoke_job[c.OPERATION_NAME] = stanza.get(c.OPERATION_NAME)
            # get params
            params = stanza.get(c.PARAMS)
            if params:
                params = "[" + params + "]"
                invoke_job[c.PARAMS] = json.loads(params)
            # get signature
            signature = stanza.get(c.SIGNATURE)
            if signature:
                signature_lst = [elem.strip() for elem in signature.split(",")]
                invoke_job[c.SIGNATURE] = signature_lst
            # get split_array
            split_array = stanza.get(c.SPLIT_ARRAY)
            if split_array:
                invoke_job[c.SPLIT_ARRAY] = json.loads(split_array)
            # set sourcetype
            sourcetype = stanza.get(c.SOURCETYPE)
            if sourcetype:
                invoke_job[c.SOURCETYPE] = sourcetype
            else:
                invoke_job[c.SOURCETYPE] = "jboss:jmx"
            invoke_jobs.append(invoke_job)
            program_input[self._INVOKE_JOBS_ARG] = invoke_jobs
            program_inputs.append(program_input)
        return program_inputs

    def _start_scheduler(self):
        self._timer_queue = TimerQueue()
        for stanza in self._stanzas:
            name = stanza.get(c.NAME)
            if not name:
                continue
            duration = stanza.get(c.DURATION)
            if not duration:
                continue
            file_path = os.path.sep.join([self._checkpoint_dir, name])
            self._task_files.append(file_path)
            write_file_task = self.WriteFileTask(file_path, self._state_store)
            self._timer_queue.add_timer(
                callback=write_file_task, when=time.time(), interval=int(duration)
            )
        self._timer_queue.start()

    class WriteFileTask:
        def __init__(self, file_path, state_store):
            self.file_path = file_path
            self.state_store = state_store

        def __call__(self):
            self.write_task_file()

        def write_task_file(self):
            self.state_store.update_state(self.file_path, JMXOpInvoker._FILE_CONTENT)

    def _get_output(self):
        self._LOGGER.info("start get output from jmx-op-invoke")
        p = self._process
        while True:
            output = p.stdout.readline()
            output = output.decode("utf-8")
            if output == "" and p.poll() is not None:
                break
            if output:
                try:
                    sys.stdout.write(output)
                    sys.stdout.flush()
                except Exception:
                    self._LOGGER.error(traceback.format_exc())
                    break
        rc = p.poll()
        self._LOGGER.info(
            "The jmx-op-invoke is finished, the return code is " + str(rc)
        )


class GlobalJMXOpInvoker:
    """Singleton, inited when started"""

    __instance = None

    @classmethod
    def get_jmx_op_invoker(cls, meta=None, stanzas=None):
        if cls.__instance is None:
            cls.__instance = JMXOpInvoker(meta, stanzas)
        return cls.__instance

    @classmethod
    def reset(cls):
        cls.__instance = None
