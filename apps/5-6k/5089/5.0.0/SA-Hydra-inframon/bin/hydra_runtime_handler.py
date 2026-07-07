#!/usr/bin/env python
# coding=utf-8
#
# Copyright (C) 2005-2024 Splunk Inc. All Rights Reserved.

import datetime
import json
import os
import sys
import threading
import time
from queue import Empty, PriorityQueue
from urllib.parse import parse_qs, unquote_plus

from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.persistconn.application import PersistentServerConnectionApplication

# persistconn loads this file directly via importlib; ensure app bin/ is importable.
try:
    _APP_BIN_DIR = make_splunkhome_path(["etc", "apps", "SA-Hydra-inframon", "bin"])
except Exception:
    # Fallback for local/unit test contexts that do not initialize full Splunk env vars.
    _APP_BIN_DIR = os.path.dirname(os.path.abspath(__file__))
if _APP_BIN_DIR not in sys.path:
    sys.path.append(_APP_BIN_DIR)

from hydra_inframon import get_hydra_log_level, setupLogger
from hydra_inframon.logging_utils import format_log_message


logger = setupLogger(
    log_format="%(asctime)s %(levelname)s [HydraRuntimeREST] %(message)s",
    level=get_hydra_log_level("runtime_rest"),
    log_name="hydra_inframon_runtime_rest.log",
    logger_name="hydra_inframon_runtime_rest",
)


def _now():
    return time.time()


def _ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def _job_category_key(job_string):
    # expected format:
    # name|target|task|metadata_id|create_time|last_time|expiration|special
    _, target, task, metadata_id, _ = job_string.split("|", 4)
    return target + "|" + task + "|" + metadata_id


def _parse_json(value, default):
    try:
        return json.loads(value)
    except Exception:
        return default


def _first(value, default=None):
    if isinstance(value, list):
        return value[0] if len(value) > 0 else default
    if value is None:
        return default
    return value


def _path_parts(path_info):
    if path_info is None:
        return []
    if isinstance(path_info, bytes):
        path_info = path_info.decode("utf-8")
    path_info = str(path_info).strip("/")
    if path_info == "":
        return []
    return [unquote_plus(part) for part in path_info.split("/")]


def _job_fields_from_string(job_string):
    if not job_string:
        return {}
    try:
        job_id, target, task, metadata_id, _, _, _, _ = job_string.split("|", 7)
    except Exception:
        return {"job": job_string}
    return {
        "job_id": job_id,
        "task": task,
        "vcenter": target,
        "metadata_id": metadata_id,
    }


def _extract_args(request):
    args = {}

    form = request.get("form", {})
    if isinstance(form, dict):
        for key, value in form.items():
            args[key] = _first(value)

    query = request.get("query", {})
    if isinstance(query, dict):
        for key, value in query.items():
            args[key] = _first(value)
    elif isinstance(query, list):
        for item in query:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                args[item[0]] = _first(item[1])
    elif isinstance(query, str) and query != "":
        query_args = parse_qs(query, keep_blank_values=True)
        for key, value in query_args.items():
            args[key] = _first(value)

    payload = request.get("payload", "")
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")

    if isinstance(payload, str) and payload != "":
        form_args = parse_qs(payload, keep_blank_values=True)
        for key, value in form_args.items():
            args[key] = _first(value)

        # Support JSON payload in case callers POST JSON bodies.
        if len(form_args) == 0 and payload.startswith("{"):
            json_payload = _parse_json(payload, {})
            if isinstance(json_payload, dict):
                for key, value in json_payload.items():
                    args[key] = value

    return args


def _response(status, message, payload=None):
    body = {
        "status": int(status),
        "message": message,
        "payload": payload if payload is not None else {},
    }
    return {
        "status": int(status),
        "headers": {"Content-Type": "application/json"},
        "payload": json.dumps(body),
    }


class RuntimeState(object):
    """
    Thread-safe in-memory runtime with selective cache checkpointing.
    """

    def __init__(self):
        self.job_queue = PriorityQueue()
        self.job_lock = threading.Lock()

        self.cache = {}
        self.cache_lock = threading.Lock()
        self.cache_expiration = 3600
        self.special_expirations = {}
        self.last_prune = _now()

        self.job_aggregate_execution_info = {}
        self.job_aggregate_lock = threading.Lock()

        self.active_job_category_count = {}
        self.active_job_category_lock = threading.Lock()

        self.completed_atomic_jobs = []
        self.failed_atomic_jobs = []
        self.atomic_job_lock = threading.Lock()

        self.checkpoint_path = make_splunkhome_path(
            ["etc", "apps", "SA-Hydra-inframon", "local", "run", "hydra_runtime_cache.json"]
        )
        self._load_checkpoint()

    def _checkpoint(self):
        """
        Persist special-expiration cache items only.
        """
        try:
            directory = os.path.dirname(self.checkpoint_path)
            _ensure_dir(directory)
            serializable = []
            now = _now()
            with self.cache_lock:
                for name, expiration_time in self.special_expirations.items():
                    if name in self.cache:
                        _, cache_value = self.cache[name]
                        remaining = max(0, expiration_time - now)
                        serializable.append((name, cache_value, remaining))
            with open(self.checkpoint_path, "w") as fd:
                fd.write(json.dumps(serializable))
            logger.debug(
                format_log_message(
                    "Runtime checkpoint saved",
                    {
                        "event": "runtime.checkpoint.save",
                        "status": "success",
                        "component": "runtime",
                        "entry_count": len(serializable),
                    },
                )
            )
        except Exception as exc:
            logger.exception(
                format_log_message(
                    "Runtime checkpoint save failed",
                    {
                        "event": "runtime.checkpoint.save",
                        "status": "fail",
                        "reason": "exception",
                        "component": "runtime",
                        "error": str(exc),
                    },
                )
            )

    def _load_checkpoint(self):
        try:
            if not os.path.exists(self.checkpoint_path):
                return
            with open(self.checkpoint_path, "r") as fd:
                content = fd.read()
            items = _parse_json(content, [])
            for name, value, remaining in items:
                self.set_cache(name, value, expiration=int(remaining))
            logger.info(
                format_log_message(
                    "Runtime checkpoint loaded",
                    {
                        "event": "runtime.checkpoint.load",
                        "status": "success",
                        "component": "runtime",
                        "entry_count": len(items),
                    },
                )
            )
        except Exception as exc:
            logger.exception(
                format_log_message(
                    "Runtime checkpoint load failed",
                    {
                        "event": "runtime.checkpoint.load",
                        "status": "fail",
                        "reason": "exception",
                        "component": "runtime",
                        "error": str(exc),
                    },
                )
            )

    def _prune_cache(self):
        if self.last_prune + self.cache_expiration > _now():
            return
        now = _now()
        remove_names = []
        for name, (touch_time, _) in self.cache.items():
            exp = self.special_expirations.get(name)
            if exp is not None:
                if exp < now:
                    remove_names.append(name)
            elif (touch_time + self.cache_expiration) < now:
                remove_names.append(name)
        for name in remove_names:
            self.cache.pop(name, None)
            self.special_expirations.pop(name, None)
        self.last_prune = now

    def get_cache(self, name):
        with self.cache_lock:
            self._prune_cache()
            cache_item = self.cache.get(name)
            if cache_item is None:
                return None
            _, value = cache_item
            self.cache[name] = (_now(), value)
            return value

    def set_cache(self, name, value, expiration=None):
        with self.cache_lock:
            now = _now()
            self.cache[name] = (now, value)
            if isinstance(expiration, int):
                self.special_expirations[name] = now + expiration
            elif name in self.special_expirations:
                self.special_expirations.pop(name, None)
            self._prune_cache()
        self._checkpoint()

    def set_cache_batch(self, items, expiration=None):
        with self.cache_lock:
            now = _now()
            for name, value in items:
                self.cache[name] = (now, value)
                if isinstance(expiration, int):
                    self.special_expirations[name] = now + expiration
            self._prune_cache()
        self._checkpoint()

    def _update_active_job_count(self, job_string, delta):
        try:
            key = _job_category_key(job_string)
        except Exception:
            return
        with self.active_job_category_lock:
            cur = self.active_job_category_count.get(key, 0)
            cur += delta
            self.active_job_category_count[key] = max(0, cur)

    def add_job_batch(self, serialized_jobs):
        with self.job_lock:
            for item in serialized_jobs:
                if ":" not in item:
                    continue
                priority, job_string = item.split(":", 1)
                self.job_queue.put((int(priority), job_string))
                self._update_active_job_count(job_string, 1)

    def pop_job(self, block=True):
        try:
            timeout = 3 if block else 0
            priority, job_string = self.job_queue.get(block=block, timeout=timeout)
            self._update_active_job_count(job_string, -1)
            return priority, job_string
        except Empty:
            return None, None

    def report_job_execution(self, job_string, execution_time):
        try:
            key = _job_category_key(job_string)
        except Exception:
            return
        with self.job_aggregate_lock:
            old = self.job_aggregate_execution_info.get(key, [0.0, 0])
            avg, count = old[0], old[1]
            count += 1
            avg = ((avg * (count - 1)) + float(execution_time)) / float(count)
            self.job_aggregate_execution_info[key] = [avg, count]

    def report_atomic_success(self, job_name):
        with self.atomic_job_lock:
            self.completed_atomic_jobs.append(job_name)

    def report_atomic_failure(self, job_name):
        with self.atomic_job_lock:
            self.failed_atomic_jobs.append(job_name)

    def get_atomic_job_info(self):
        with self.atomic_job_lock:
            payload = {
                "completed_atomic_jobs": self.completed_atomic_jobs,
                "failed_atomic_jobs": self.failed_atomic_jobs,
            }
            self.completed_atomic_jobs = []
            self.failed_atomic_jobs = []
            return payload

    def get_job_info(self):
        payload = {"count": self.job_queue.qsize()}
        with self.job_aggregate_lock:
            aggregate = {}
            for key, values in self.job_aggregate_execution_info.items():
                aggregate[key] = [values[0], values[1], 0]
            # mirror previous behavior: clear after exposing.
            self.job_aggregate_execution_info = {}
        with self.active_job_category_lock:
            for key, active_count in self.active_job_category_count.items():
                if key in aggregate:
                    aggregate[key][2] = active_count
                else:
                    aggregate[key] = [0.0, 0, active_count]
        payload["job_aggregate_execution_info"] = aggregate
        payload["atomic_job_info"] = self.get_atomic_job_info()
        return payload


RUNTIME_STATE = RuntimeState()


def _resource_from_path(path_info):
    parts = _path_parts(path_info)
    if len(parts) == 0:
        return None, ""

    if parts[0] == "cache":
        if len(parts) > 1 and parts[1] == "batch":
            return "cache_batch", "/" + "/".join(parts[2:])
        return "cache", "/" + "/".join(parts[1:])

    if parts[0] == "job":
        if len(parts) < 2:
            return None, ""
        if parts[1] == "info":
            return "job_info", "/" + "/".join(parts[2:])
        if parts[1] == "pop":
            return "job_pop", "/" + "/".join(parts[2:])
        if parts[1] == "batch":
            return "job_batch", "/" + "/".join(parts[2:])
        if parts[1] == "exec":
            if len(parts) > 2 and parts[2] == "failure":
                return "job_exec_failure", "/" + "/".join(parts[3:])
            if len(parts) > 2 and parts[2] == "expired":
                return "job_exec_expired", "/" + "/".join(parts[3:])
            return "job_exec", "/" + "/".join(parts[2:])
        return None, ""

    if parts[0] == "health":
        return "health", "/" + "/".join(parts[1:])

    return None, ""


class HydraRuntimeHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line=None, command_arg=None, *args, **kwargs):
        super(HydraRuntimeHandler, self).__init__()
        self.command_line = command_line
        self.command_arg = command_arg

    def handle(self, in_string):
        try:
            if isinstance(in_string, bytes):
                in_string = in_string.decode("utf-8")
            if isinstance(in_string, dict):
                request = in_string
            else:
                request = json.loads(in_string)
        except Exception:
            return _response(400, "invalid request payload", {})

        method = str(request.get("method", "GET")).upper()
        path_info = request.get("path_info", "")
        args = _extract_args(request)
        resource, resource_path = _resource_from_path(path_info)
        if resource is None:
            return _response(404, "unknown runtime resource", {})

        logger.debug(
            format_log_message(
                "Runtime request started",
                {
                    "event": "runtime.request",
                    "status": "start",
                    "component": "runtime",
                    "resource": resource,
                    "method": method,
                    "path_info": path_info,
                    "resource_path": resource_path,
                    "args": args,
                },
            )
        )

        try:
            response = self._dispatch(resource, method, resource_path, args)
        except Exception as exc:
            logger.exception(
                format_log_message(
                    "Runtime request failed",
                    {
                        "event": "runtime.request",
                        "status": "fail",
                        "reason": "exception",
                        "component": "runtime",
                        "resource": resource,
                        "method": method,
                        "error": str(exc),
                    },
                )
            )
            return _response(500, str(exc), {})

        logger.debug(
            format_log_message(
                "Runtime request completed",
                {
                    "event": "runtime.request",
                    "status": response.get("status", "unknown"),
                    "component": "runtime",
                    "resource": resource,
                    "method": method,
                },
            )
        )
        return response

    def _dispatch(self, resource, method, resource_path, args):
        parts = _path_parts(resource_path)

        if resource == "cache":
            cache_name = parts[0] if len(parts) > 0 else ""
            if cache_name == "":
                return _response(400, "cache name is required", {})
            if method == "GET":
                value = RUNTIME_STATE.get_cache(cache_name)
                if value is None:
                    return _response(404, "cache entry not found", {})
                return _response(200, "ok", {"value": value})
            if method == "POST":
                value_raw = args.get("value", "{}")
                value = _parse_json(value_raw, value_raw)
                expiration = args.get("expiration", None)
                expiration = int(expiration) if expiration not in (None, "") else None
                RUNTIME_STATE.set_cache(cache_name, value, expiration=expiration)
                return _response(200, "ok", {})
            return _response(405, "method not supported", {})

        if resource == "cache_batch":
            if method != "POST":
                return _response(405, "method not supported", {})
            items_raw = args.get("items", "[]")
            items = _parse_json(items_raw, [])
            expiration = args.get("expiration", None)
            expiration = int(expiration) if expiration not in (None, "") else None
            RUNTIME_STATE.set_cache_batch(items, expiration=expiration)
            return _response(200, "ok", {"count": len(items)})

        if resource == "job_info":
            if method != "GET":
                return _response(405, "method not supported", {})
            return _response(200, "ok", RUNTIME_STATE.get_job_info())

        if resource == "job_pop":
            if method != "GET":
                return _response(405, "method not supported", {})
            block = args.get("block", "1")
            block = False if str(block) == "0" else True
            _, job_string = RUNTIME_STATE.pop_job(block=block)
            if job_string is None:
                return _response(404, "no job available", {})
            logger.info(
                format_log_message(
                    "Job dequeued from runtime queue",
                    dict(
                        {
                            "event": "runtime.job.dequeue",
                            "status": "success",
                            "component": "runtime",
                            "queue_count": RUNTIME_STATE.job_queue.qsize(),
                        },
                        **_job_fields_from_string(job_string)
                    ),
                )
            )
            return _response(200, "ok", {"job": job_string})

        if resource == "job_batch":
            if method != "POST":
                return _response(405, "method not supported", {})
            jobs_raw = args.get("jobs", "[]")
            jobs = _parse_json(jobs_raw, [])
            RUNTIME_STATE.add_job_batch(jobs)
            logger.info(
                format_log_message(
                    "Job batch queued in runtime",
                    {
                        "event": "runtime.job.enqueue",
                        "status": "success",
                        "component": "runtime",
                        "count": len(jobs),
                        "queue_count": RUNTIME_STATE.job_queue.qsize(),
                    },
                )
            )
            return _response(200, "ok", {"count": len(jobs)})

        if resource == "job_exec":
            if method != "POST":
                return _response(405, "method not supported", {})
            job_string = args.get("job", "")
            exec_time = float(args.get("time_spent", "0"))
            atomic_job = args.get("atomic_job", "")
            if atomic_job:
                RUNTIME_STATE.report_atomic_success(atomic_job)
            if job_string:
                RUNTIME_STATE.report_job_execution(job_string, exec_time)
            logger.info(
                format_log_message(
                    "Job execution reported to runtime",
                    dict(
                        {
                            "event": "runtime.job.exec",
                            "status": "success",
                            "component": "runtime",
                            "duration_seconds": round(exec_time, 3),
                            "atomic_job": atomic_job,
                        },
                        **_job_fields_from_string(job_string)
                    ),
                )
            )
            return _response(200, "ok", {})

        if resource == "job_exec_failure":
            if method != "POST":
                return _response(405, "method not supported", {})
            atomic_job = args.get("atomic_job", "")
            if atomic_job == "":
                parts = _path_parts(resource_path)
                atomic_job = parts[0] if len(parts) > 0 else ""
            if atomic_job == "":
                return _response(400, "atomic_job is required", {})
            RUNTIME_STATE.report_atomic_failure(atomic_job)
            logger.warning(
                format_log_message(
                    "Atomic job failure reported to runtime",
                    {
                        "event": "runtime.job.exec",
                        "status": "fail",
                        "reason": "atomic_failure",
                        "component": "runtime",
                        "job_id": atomic_job,
                    },
                )
            )
            return _response(200, "ok", {})

        if resource == "job_exec_expired":
            if method != "POST":
                return _response(405, "method not supported", {})
            count = int(args.get("count", "1"))
            logger.info(
                format_log_message(
                    "Expired job count reported to runtime",
                    {
                        "event": "runtime.job.expired",
                        "status": "success",
                        "component": "runtime",
                        "count": count,
                    },
                )
            )
            return _response(200, "ok", {"expired_count": count})

        if resource == "health":
            if method != "GET":
                return _response(405, "method not supported", {})
            return _response(
                200,
                "ok",
                {"service": "hydra_runtime_rest", "time": datetime.datetime.utcnow().isoformat()},
            )

        return _response(404, "unknown runtime resource", {})
