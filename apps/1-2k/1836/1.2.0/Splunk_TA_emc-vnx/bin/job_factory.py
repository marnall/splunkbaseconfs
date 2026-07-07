"""
Create scheduling jobs
"""

import logging
import time

from vnx_file_loader import VnxFiler
from vnx_block_loader import (VnxBlock, VnxBlockPerfLoader)


__all__ = ["JobFactory"]

_LOGGER = logging.getLogger("ta_vnx")


class _CollectionJob(object):

    def __init__(self, config, endpoint, data_collect_func):
        self._config = config
        self._func = data_collect_func
        self._endpoint = endpoint

    def __call__(self):
        _LOGGER.info("Start %s. Metric=%s",
                     self._config["name"], self._config["metric_type"])
        results = self._func()
        tim = time.time()
        idx = self._config.get("index", "main")
        if results:
            event_queue = self._config["event_queue"]
            for _, data_objs in results.iteritems():
                if data_objs:
                    events = "".join(("<stream>%s</stream>"
                                      % obj.to_string(tim, idx)
                                      for obj in data_objs))
                    event_queue.put(events)
        _LOGGER.info("End %s. Metric=%s",
                     self._config["name"], self._config["metric_type"])

    def is_alive(self):
        return self._endpoint.is_alive()

    def get(self, key):
        return self._config[key]


class JobFactory(object):

    def __init__(self):
        self.platform_dispatch_tbl = {
            "VNX Block": self._create_vnx_job,
            "VNX File": self._create_vnx_job,
        }

        self.supported_metric_types = {
            "vnx_block_inventory": self._create_vnx_block_inventory_job,
            "vnx_block_performance": self._create_vnx_block_perf_job,
            "vnx_block_status": self._create_vnx_block_status_job,
            "vnx_file_inventory": self._create_vnx_file_inventory_job,
            "vnx_file_performance": self._create_vnx_file_perf_job,
            "vnx_file_sys_performance": self._create_vnx_file_sys_perf_job,
            "vnx_file_cifs_performance": self._create_vnx_file_cifs_perf_job,
            "vnx_file_nfs_performance": self._create_vnx_file_nfs_perf_job,
        }

    @staticmethod
    def get_supported_metric_types(platform):
        platform_metrics = {
            "VNX Block": ("vnx_block_inventory", "vnx_block_performance",
                          "vnx_block_status"),
            "VNX File": ("vnx_file_inventory", "vnx_file_sys_performance",
                         "vnx_file_nfs_performance",
                         "vnx_file_cifs_performance"),
        }

        if platform == "ALL":
            return platform_metrics
        else:
            return {platform: platform_metrics.get(platform,
                                                   ("Not Supported",))}

    def create_job(self, config):
        """
        Create a job according to the config. The job object shall
        be callable and implement is_alive() interface which returns
        True if it is still valid else False
        """

        _LOGGER.info("creating job for %s", config["name"])
        platform = config["platform"]
        if platform not in self.platform_dispatch_tbl:
            _LOGGER.error("Not supported platform: %s", platform)
            return None
        return self.platform_dispatch_tbl[platform](config)

    def _create_vnx_job(self, config):
        metric_type = config["metric_type"]
        if metric_type not in self.supported_metric_types:
            _LOGGER.error("Unsupported metric type %s", metric_type)
            return None
        return self.supported_metric_types[metric_type](config)

    @staticmethod
    def _create_vnx_block_inventory_job(config):
        vb = VnxBlock(config["network_addr"], config.get("network_addr2", ""),
                      config["username"], config["password"],
                      config.get("site", ""), config.get("scope", "0"))
        return _CollectionJob(config, vb, vb.collect_inventory_info)

    @staticmethod
    def _create_vnx_block_perf_job(config):
        vb = VnxBlockPerfLoader(config["network_addr"],
                                config.get("network_addr2", ""),
                                config["username"],
                                config["password"],
                                config.get("site", ""), config.get("scope", "0"))
        return _CollectionJob(config, vb, vb.collect_perf_metrics)

    @staticmethod
    def _create_vnx_block_status_job(config):
        vb = VnxBlock(config["network_addr"], config.get("network_addr2", ""),
                      config["username"], config["password"],
                      config.get("site", ""), config.get("scope", "0"))
        return _CollectionJob(config, vb, vb.collect_array_states)

    @staticmethod
    def _create_vnx_file_inventory_job(config):
        vf = VnxFiler(config["network_addr"], config.get("network_addr2", ""),
                      config["username"], config.get("password", ""),
                      config.get("site", ""))
        return _CollectionJob(config, vf, vf.collect_inventory_info)

    @staticmethod
    def _create_vnx_file_perf_job(config):
        vf = VnxFiler(config["network_addr"], config.get("network_addr2", ""),
                      config["username"], config.get("password", ""),
                      config.get("site", ""))
        return _CollectionJob(config, vf, vf.collect_perf_metrics)

    @staticmethod
    def _create_vnx_file_sys_perf_job(config):
        vf = VnxFiler(config["network_addr"], config.get("network_addr2", ""),
                      config["username"], config.get("password", ""),
                      config.get("site", ""))
        return _CollectionJob(config, vf, vf.collect_system_perf_metrics)

    @staticmethod
    def _create_vnx_file_cifs_perf_job(config):
        vf = VnxFiler(config["network_addr"], config.get("network_addr2", ""),
                      config["username"], config.get("password", ""),
                      config.get("site", ""))
        return _CollectionJob(config, vf, vf.collect_all_cifs_perf_metrics)

    @staticmethod
    def _create_vnx_file_nfs_perf_job(config):
        vf = VnxFiler(config["network_addr"], config.get("network_addr2", ""),
                      config["username"], config.get("password", ""),
                      config.get("site", ""))
        return _CollectionJob(config, vf, vf.collect_all_nfs_perf_metrics)
