#
# SPDX-FileCopyrightText: 2026 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import base64
import json
import os
import subprocess
import sys
import time
import traceback

import java_args_gen as jag
from solnlib import log
import tomcat_consts as c
from solnlib.timer_queue import TimerQueue
from solnlib.modular_input.checkpointer import FileCheckpointer


class JMXOpInvoker:

    _LOGGER = log.Logs().get_logger(c.TOMCAT_LOG)

    _OP_INVOKE_HOME_ARG = "jmx_op_invoke_home"

    _DIR_NAME = "jmx-op-invoke-1.2.0"

    _APP_PATH = os.path.dirname(os.path.abspath(__file__))

    _OP_INVOKE_HOME = os.path.join(_APP_PATH, "java", _DIR_NAME)

    _MAIN_CLASS = "com.splunk.jmxopinvoke.JMXOpInvokeBootstrap"

    _INVOKE_JOBS_ARG = "invoke_jobs"

    _FILE_CONTENT: dict = {}

    def __init__(self, meta, stanzas):
        self._meta = meta
        self._stanzas = stanzas
        self._checkpoint_dir = None
        self._state_store = None
        self._timer_queue = None
        self._process = None
        self._task_files = list()
        self._is_process_terminated = False

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

        # Adding a short delay before scheduling the job to handle quick enable/disable actions on the input.
        # Without this delay, if the input is quickly enable and disable (or if multiple inputs are enabled in quick succession),
        # the sub-process (Java process) created by the initial input may not terminate properly.
        # This can happen because the parent process is killed too quickly before it has a chance to clean up its child process.
        # As a result, zombie sub-processes may remain running in the background.
        # This delay helps ensure that the first process has time to terminate cleanly before a new sub-process is spawned.
        self._LOGGER.debug(
            "Sleeping for 5 seconds to allow clean shutdown of previous sub-processes."
        )
        time.sleep(5)

        if self._is_process_terminated:
            return

        self._start_scheduler()
        program_inputs = self._generate_program_input()
        if program_inputs:
            input_json = json.dumps(program_inputs[0])
            # Path to the log file for Java code to refer the configs from
            log4j2_xml_path = os.path.sep.join(
                [self._OP_INVOKE_HOME, "config", "log4j2.xml"]
            )
            vm_arguments = {
                c.LOG4J_2_PROP_FILE: log4j2_xml_path,
                c.LOG_LEVEL_PARAMS: c.LOG_LEVEL_VALUE,
            }
            mx4j_path = self._APP_PATH + os.path.sep + "mx4j.ks"
            if os.path.isfile(mx4j_path):
                vm_arguments[c.TRUSTSTORE_LOCATION_PROP] = mx4j_path
            args_generator = jag.JavaArgsGenerator(
                app_home=self._OP_INVOKE_HOME,
                vm_arguments=vm_arguments,
                main_class=self._MAIN_CLASS,
            )
            java_args = args_generator.generate()
            try:
                self._process = subprocess.Popen(  # nosemgrep false-positive : The value java_args is
                    # static value from java_args_gen.py file. It doesn't take any external/user inputs.
                    java_args,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            except FileNotFoundError as e:
                error_msg = (
                    "Java execution failed. The specified Java binary was not found. "
                    "Please ensure JAVA_HOME is correctly set in splunk-launch.conf, or that the Java binary path is added to the system PATH."
                )
                self._LOGGER.exception(error_msg)
                return
            except Exception:
                self._LOGGER.exception(
                    "Failed to create sub-process for Java execution."
                )
                return
            self._process.stdin.write(input_json.encode("utf-8"))
            self._process.stdin.close()
            self._get_output()

    def stop(self):
        self._is_process_terminated = True

        self._LOGGER.info("Stopping JMXOpInvoker...")
        if self._process is not None:
            self._process.kill()
        if self._timer_queue is not None:
            self._timer_queue.stop()
        for task_file in self._task_files:
            self._state_store.delete(task_file)
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
            not stanza[k]
            for k in (
                c.DURATION,
                c.NAME,
                c.JMX_URL,
                c.OBJECT_NAME,
                c.OPERATION_NAME,
            )
        ):
            return False
        return True

    @classmethod
    def _generate_format_name(cls, name):
        return base64.b64encode(name.encode("utf-8")).decode("ascii")

    def _create_state_store(self):
        state_store = FileCheckpointer(self._checkpoint_dir)
        return state_store

    def _generate_task_files(self):
        for stanza in self._stanzas:
            if not stanza.get(c.NAME):
                continue
            self._state_store.update(stanza.get("account"), self._FILE_CONTENT)

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
                invoke_job[c.SOURCETYPE] = "tomcat:jmx"
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
            file_path = stanza.get("account")
            self._task_files.append(file_path)
            write_file_task = self.WriteFileTask(file_path, self._state_store)
            self._timer_queue.add_timer(
                callback=write_file_task,
                when=time.time()
                + 5,  # Adding a 5-second buffer to allow the JMXOpInvokeBootstrap class to complete setup before invoking the first execution
                interval=int(duration),
            )
        self._timer_queue.start()

    class WriteFileTask:
        def __init__(self, file_path, state_store):
            self.file_path = file_path
            self.state_store = state_store

        def __call__(self):
            self.write_task_file()

        def write_task_file(self):
            self.state_store.update(self.file_path, JMXOpInvoker._FILE_CONTENT)

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
                except (BrokenPipeError, OSError):
                    self._LOGGER.info(
                        f"stdout stream was interrupted likely due to enabling/disabling the inputs. {traceback.format_exc()}"
                    )
                    break
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
