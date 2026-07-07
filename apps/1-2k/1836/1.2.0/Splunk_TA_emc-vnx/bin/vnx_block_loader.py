import logging
import time
import random
import threading
import os.path as op

import vnx_block_objects as vbo
from timed_popen import timed_popen


__all__ = ["VnxBlock"]

_LOGGER = logging.getLogger("ta_vnx")


class VnxBlock(object):
    _NAVISECCLI = "naviseccli"
    _log_template = "platform=Vnx Block,ip=%s,cmd=%s,reason=%s"
    _this_dir = op.dirname(op.abspath(__file__))

    def __init__(self, ip, ip2, username, password, site="", scope="0"):
        self.site = site
        self.ip = ip.strip()
        self.ip2 = ip2.strip()
        self.username = username
        self.password = password
        self.scope = scope.strip()
        self.agents = []
        self.cli_common = [self._NAVISECCLI, "-user", self.username,
                           "-password", self.password, "-scope", self.scope, "-h"]
        self._timed_out_count = 0

    def is_valid(self):
        if self.agents:
            for agent in self.agents:
                if not agent.is_valid():
                    return False
            return True
        else:
            return False

    def is_alive(self):
        return self._timed_out_count < 300

    @staticmethod
    def platform():
        return "Vnx Block"

    def collect_perf_metrics(self):
        perf_metrics = {}
        self._get_agents()
        if not self.is_valid():
            _LOGGER.warn("VNX Block %s is not valid, ignore", self.ip)
            return perf_metrics

        sp_perf = self.collect_sp_perf_metrics()
        drive_perf = self.collect_drive_perf_metrics()
        rg_device_perf = self.collect_rg_device_perf_metrics()
        pool_device_perf = self.collect_pool_device_perf_metrics()
        rg_device_perf["device_perf"].extend(pool_device_perf["device_perf"])

        perf_metrics.update(sp_perf)
        perf_metrics.update(drive_perf)
        perf_metrics.update(rg_device_perf)
        return perf_metrics

    def collect_inventory_info(self):
        inventories = {}
        self._get_agents(force_refresh=True)
        if not self.is_valid():
            _LOGGER.warn("VNX Block %s is not valid, ignore", self.ip)
            return inventories

        devices = self.get_devices()
        drives = self.get_drives()
        raid_groups = self.get_raid_groups()
        storage_pools = self.get_storage_pools()
        storage_groups = self.get_storage_groups()
        nas_devices = self._get_nas_control_devices(
                                         storage_groups["storage_groups"],
                                         devices["devices"])
        devices["devices"].extend(nas_devices["devices"])
        inventories.update(devices)
        inventories.update(drives)
        inventories.update(raid_groups)
        inventories.update(storage_pools)
        inventories.update(storage_groups)
        inventories.update({"agents": self.agents})
        return inventories

    def collect_array_states(self):
        states = {}
        self._get_agents()
        if not self.is_valid():
            _LOGGER.warn("VNX Block %s is not valid, ignore", self.ip)
            return states

        sfpstates = self.get_backend_sfpstates()
        crus_states = self.get_crus_states()
        drive_states = self.get_drive_states()
        device_states = self.get_device_states()
        rg_states = self.get_raidgroup_states()
        pool_states = self.get_storagepool_states()
        states.update(sfpstates)
        states.update(crus_states)
        states.update(drive_states)
        states.update(device_states)
        states.update(rg_states)
        states.update(pool_states)
        return states

    def collect_sp_perf_metrics(self):
        self._get_agents()
        if not self.is_valid():
            _LOGGER.warn("VNX Block %s is not valid, ignore", self.ip)
            return {}

        _LOGGER.info("start collect sp perf for %s", self.ip)
        perf_metrics = []
        random.shuffle(self.agents)
        for agent in self.agents:
            cli = self.cli_common + [agent.ip, "-np", "getcontrol", "-all"]
            begin = time.time()
            output = timed_popen(cli, 10)
            if self._timed_out(output, agent.ip, "getcontrol"):
                continue

            self._dump(agent, "getcontrol", output[0])
            self._timed_out_count = 0
            metric_time = begin + (time.time() - begin) / 2
            perf = vbo.ProcessorPerfMetrics(agent, output[0].split("\n"),
                                            metric_time)
            if perf.is_valid():
                perf_metrics.append(perf)
            else:
                _LOGGER.error(self._log_template,
                              agent.ip, "getcontrol", output[0])
        _LOGGER.info("end collect sp perf for %s", self.ip)
        return {"sp_perf": perf_metrics}

    def collect_drive_perf_metrics(self):
        opts = ["", "-np", "getdisk", "-bytrd", "-bytwrt", "-busyticks",
                "-idleticks", "-read", "-write"]
        _LOGGER.info("start collect drive perf for %s", self.ip)
        perf = self._do_collect(opts, r"^\s*Bus\s+\d+",
                                vbo.DrivePerfMetrics, 240)
        _LOGGER.info("end collect drive perf for %s", self.ip)
        return {"drive_perf": perf}

    def collect_rg_device_perf_metrics(self):
        opts = ["", "-np", "getlun", "-name", "-disk", "-bread", "-bwrite",
                "-busy", "-idle", "-busyticks", "-idleticks"]
        _LOGGER.info("start collect rg device perf for %s", self.ip)
        perf = self._do_collect(opts, r"^\s*LOGICAL UNIT NUMBER\s+",
                                vbo.DevicePerfMetrics, 600)
        _LOGGER.info("end collect rg device perf for %s", self.ip)
        return {"device_perf": perf}

    def collect_pool_device_perf_metrics(self):
        opts = ["", "-np", "lun", "-list", "-perfData", "-poolName"]
        _LOGGER.info("start collect pool device perf for %s", self.ip)
        perf = self._do_collect(opts, r"^\s*LOGICAL UNIT NUMBER\s+",
                                vbo.DevicePerfMetrics, 600)
        _LOGGER.info("end collect pool device perf for %s", self.ip)
        return {"device_perf": perf}

    def get_drives(self):
        opts = ["", "-np", "getdisk", "-messner", "-capacity", "-state", "-hs",
                "-vendor", "-rg", "-drivetype", "-product", "-rev", "-speeds"]
        _LOGGER.info("start collect drive inventory for %s", self.ip)
        drives = self._do_collect(opts, r"^\s*Bus\s+\d+", vbo.Drive, 240)
        _LOGGER.info("end collect drive inventory for %s", self.ip)
        return {"drives": drives}

    def get_raid_groups(self):
        opts = ["", "-np", "getrg", "-tcap", "-ucap",
                "-type", "-state", "-disks"]
        _LOGGER.info("start collect raid group inventory for %s", self.ip)
        rgs = self._do_collect(opts, r"^\s*RaidGroup ID:\s+", vbo.RaidGroup)
        _LOGGER.info("end collect raid group inventory for %s", self.ip)
        return {"raid_groups": rgs}

    def get_storage_pools(self):
        if not self._support_virtual_provisioning():
            return {}

        opts = ["", "-np", "storagepool", "-messner", "-list", "-status",
                "-rawCap", "-userCap", "-consumedCap", "-availableCap",
                "-rtype", "-diskType", "-disks", "-luns"]
        _LOGGER.info("start collect storage pools inventory for %s", self.ip)
        sps = self._do_collect(opts, r"^\s*(Thin )?Pool Name:\s+",
                               vbo.StoragePool)
        _LOGGER.info("end collect storage pools inventory for %s", self.ip)
        return {"storage_pools": sps}

    def get_devices(self):
        opts = ["", "-np", "getlun", "-name", "-capacity", "-private",
                "-state", "-drivetype", "-owner", "-default", "-rg",
                "-type", "-uid", "-ismetalun"]

        if self._support_virtual_provisioning():
            opts.extend(("-isthinlun", "-ispoollun"))

        _LOGGER.info("start collect device inventory for %s", self.ip)
        devices = self._do_collect(opts, r"^\s*LOGICAL UNIT NUMBER\s+",
                                   vbo.Device, 600)
        _LOGGER.info("end collect device inventory for %s", self.ip)
        return {"devices": devices}

    def get_storage_groups(self):
        opts = ["", "-np", "storagegroup", "-messner", "-list", "-host"]
        _LOGGER.info("start collect device inventory for %s", self.ip)
        sgs = self._do_collect(opts, r"^\s*Storage Group Name:\s+",
                               vbo.StorageGroup)
        _LOGGER.info("end collect device inventory for %s", self.ip)
        return {"storage_groups": sgs}

    def get_sp_ports(self):
        opts = ["", "-np", "port", "-list", "-sp"]
        _LOGGER.info("start collect port inventory for %s", self.ip)
        ports = self._do_collect(opts, r"^\s*SP Name:\s+", vbo.SPPort)
        _LOGGER.info("end collect port inventory for %s", self.ip)
        return {"storage_ports": ports}

    def get_backend_sfpstates(self):
        opts = ["", "-np", "backendbus", "-get", "-sfpstate"]
        sfpstates = self._do_collect(opts, r"^\s*Bus \d+\s*$", vbo.BusSFPState)
        return {"sfp_states": sfpstates}

    def get_crus_states(self):
        opts = ["", "-np", "getcrus", "-cpua",
                "-cpub", "-dimma", "-dimmb", "-fana", "-fanb", "-ioa",
                "-iob", "-lcca", "-lccb", "-spsa", "-spsb", "-spa", "-spb",
                "-vsca", "-vscb"]
        crus = self._do_collect(opts, r"^\s*D[A|P]E.*Enclosure\s+\d+\s*$",
                                vbo.CrusState)
        return {"crus_states": crus}

    def get_drive_states(self):
        opts = ["", "-np", "getdisk", "-state", "-hr", "-hw", "-sr", "-sw"]
        drive_states = self._do_collect(opts, r"^\s*Bus\s+\d+", vbo.DriveState)
        return {"drive_states": drive_states}

    def get_device_states(self):
        opts = ["", "-np", "getlun", "-name", "-state"]
        device_states = self._do_collect(opts, r"^\s*LOGICAL UNIT NUMBER\s+",
                                         vbo.DeviceState)
        return {"device_states": device_states}

    def get_raidgroup_states(self):
        opts = ["", "-np", "getrg", "-state"]
        rg_states = self._do_collect(opts, r"^\s*RaidGroup ID:\s+",
                                     vbo.RaidGroupState)
        return {"raidgroup_states": rg_states}

    def get_storagepool_states(self):
        opts = ["", "-np", "storagepool", "-list", "-state"]
        pool_states = self._do_collect(opts, r"^\s*(Thin )?Pool Name:\s+",
                                       vbo.StoragePoolState)
        return {"storagepool_states": pool_states}

    def _get_nas_control_devices(self, storage_groups, devices):
        sg_devs = set((dev_id for sg in storage_groups
                       for dev_id in sg.device_ids))
        all_devs = set((dev.id for dev in devices))
        nas_control_devs = sg_devs - all_devs

        opts = ["", "-np", "getlun", "-messner", "", "-name", "-capacity",
                "-private", "-state", "-drivetype", "-owner", "-default",
                "-rg", "-type", "-uid", "-ismetalun"]

        if self._support_virtual_provisioning():
            opts.extend(("-isthinlun", "-ispoollun"))

        _LOGGER.info("start collect nas device inventory for %s", self.ip)
        devs = []
        random.shuffle(self.agents)
        for dev_id in nas_control_devs:
            opts[4] = dev_id
            for agent in self.agents:
                opts[0] = agent.ip
                cli = self.cli_common + opts
                begin = time.time()
                output = timed_popen(cli, 10)
                if self._timed_out(output, agent.ip, "getlun"):
                    continue

                self._dump(agent, "getlun", output[0])
                self._timed_out_count = 0
                metric_time = begin + (time.time() - begin) / 2
                output = "LOGICAL UNIT NUMBER %s\n%s" % (dev_id, output[0])
                devs.extend(vbo.parse_block_objects(agent, output,
                            r"^\s*LOGICAL UNIT NUMBER\s+",
                            vbo.Device, metric_time))
                break
        _LOGGER.info("end collect nas device inventory for %s", self.ip)
        return {"devices": devs}

    def _dump(self, agent, cli, output):
        if _LOGGER.level == logging.DEBUG:
            agent_rev = agent.agent_rev if agent.agent_rev is not None else ""
            idx = agent_rev.find("(")
            if idx > 0:
                agent_rev = agent_rev[:idx].strip()

            model = agent.model if agent.model is not None else ""
            file_name = "_".join(("vnx_block", agent_rev, model,
                                  str(threading.current_thread().ident)))
            file_name = op.join(self._this_dir, file_name)
            with open(file_name, "a") as f:
                f.write("\n***%s %s %s\n%s\n"
                        % (time.ctime(), self.ip, cli, output))

    def _do_collect(self, cli_opts, start_tag, StorageClass, timeout=90):
        self._get_agents()
        if not self.is_valid():
            _LOGGER.warn("VNX Block %s is not valid, ignore", self.ip)
            return []

        random.shuffle(self.agents)
        for agent in self.agents:
            cli_opts[0] = agent.ip
            cli = self.cli_common + cli_opts
            begin = time.time()
            output = timed_popen(cli, timeout)
            if self._timed_out(output, agent.ip, cli_opts[2]):
                continue

            self._dump(agent, cli, output[0])
            self._timed_out_count = 0
            metric_time = begin + (time.time() - begin) / 2
            return vbo.parse_block_objects(agent, output[0], start_tag,
                                           StorageClass, metric_time)
        return []

    def _get_agents(self, force_refresh=False):
        if not force_refresh and self.agents:
            return

        del self.agents[:]
        for ip in (self.ip, self.ip2):
            if not ip:
                continue

            cli = [ip, "-np", "getagent", "-ver", "-name", "-node", "-rev",
                   "-model", "-type", "-mem", "-serial", "-spid", "-cabinet",
                   "-os"]
            begin = time.time()
            output = timed_popen(self.cli_common + cli, 15)
            if self._timed_out(output, ip, "getagent"):
                continue

            self._timed_out_count = 0
            metric_time = begin + (time.time() - begin) / 2
            agent = vbo.Agent(self.site, ip, output[0].split("\n"),
                              metric_time)
            if agent.is_valid():
                self.agents.append(agent)
            else:
                _LOGGER.error(self._log_template, ip, "getagent", output[0])
            self._dump(agent, cli, output[0])

    def _timed_out(self, output, ip, cmd):
        if output[1] and output[1].strip():
            _LOGGER.error(self._log_template, ip, cmd, output[1])

        if output[-1] and not output[0]:
            self._timed_out_count += 1
            _LOGGER.error(self._log_template, ip, cmd, "timed_out")
            return True
        return False

    def _support_virtual_provisioning(self):
        if not self.is_valid():
            return False

        model = self.agents[0].model
        if (model.startswith("CX3") or
                model.startswith("CX200") or
                model.startswith("CX400") or
                model.startswith("CX500") or
                model.startswith("CX600") or
                model.startswith("CX700")):
            return False
        return True


class VnxBlockPerfLoader(object):
    """
    The metrics of VNX Block are accumulative. This helper class does the
    metrics diff for sp_perf, device_perf, drive_perf between the calls.
    Splunk Enterprise doesn't scale well for calculating metrics difference
    between events when the data is large
    """

    def __init__(self, ip, ip2, username, password, site="", scope=0):
        self.block = VnxBlock(ip, ip2, username, password, site, scope)
        self.last_perf_metrics = None
        self._lock = threading.Lock()

    def is_alive(self):
        return self.block.is_alive()

    def collect_perf_metrics(self):
        if self.last_perf_metrics is None:
            metrics = self.block.collect_perf_metrics()
            if not metrics:
                return metrics

            if all((not v for v in metrics.itervalues())):
                _LOGGER.info("Got no perf metrics for %s", self.block.ip)
                return {}

            sp_metrics = {p.sp_id: p for p in metrics["sp_perf"]}
            drive_metrics = {p.drive_id: p for p in metrics["drive_perf"]}
            device_metrics = {p.device_id: p for p in metrics["device_perf"]}
            with self._lock:
                self.last_perf_metrics = {
                    "sp_perf": sp_metrics,
                    "drive_perf": drive_metrics,
                    "device_perf": device_metrics,
                }
            return {}
        else:
            now_metrics = self.block.collect_perf_metrics()
            if all((not v for v in now_metrics.itervalues())):
                _LOGGER.info("Got no perf metrics for %s", self.block.ip)
                return {}

            with self._lock:
                diff_metrics = self._do_perf_metrics_diff(now_metrics)
            return diff_metrics

    def _do_perf_metrics_diff(self, now_metrics):
        now_sp_metrics = now_metrics["sp_perf"]
        sp_metrics = self.last_perf_metrics["sp_perf"]
        sps_diff = []
        for now_metric in now_sp_metrics:
            if now_metric.sp_id in sp_metrics:
                prev_metric = sp_metrics[now_metric.sp_id]
                prev_metric = self._diff_sp_metrics(now_metric, prev_metric)
                sps_diff.append(prev_metric)
            sp_metrics[now_metric.sp_id] = now_metric

        now_drive_metrics = now_metrics["drive_perf"]
        drive_metrics = self.last_perf_metrics["drive_perf"]
        drives_diff = []
        for now_metric in now_drive_metrics:
            if now_metric.drive_id in drive_metrics:
                prev_metric = drive_metrics[now_metric.drive_id]
                prev_metric = self._diff_drive_metrics(now_metric,
                                                       prev_metric)
                drives_diff.append(prev_metric)
            drive_metrics[now_metric.drive_id] = now_metric

        now_device_metrics = now_metrics["device_perf"]
        device_metrics = self.last_perf_metrics["device_perf"]
        devices_diff = []
        for now_metric in now_device_metrics:
            if now_metric.device_id in device_metrics:
                prev_metric = device_metrics[now_metric.device_id]
                prev_metric = self._diff_device_metrics(now_metric,
                                                        prev_metric)
                devices_diff.append(prev_metric)
            device_metrics[now_metric.device_id] = now_metric

        return {
            "sp_perf": sps_diff,
            "drive_perf": drives_diff,
            "device_perf": devices_diff,
        }

    @staticmethod
    def _diff_sp_metrics(now, prev):
        diff = now._metric_time - prev._metric_time
        diff = diff if diff != 0 else 1
        prev.total_reads = (now.total_reads - prev.total_reads) / diff
        prev.total_writes = (now.total_writes - prev.total_writes) / diff
        prev.read_requests = (now.read_requests - prev.read_requests) / diff
        prev.write_requests = (now.write_requests - prev.write_requests) / diff
        prev.blocks_read = (now.blocks_read - prev.blocks_read) / diff
        prev.blocks_written = (now.blocks_written - prev.blocks_written) / diff
        prev.controller_busy_ticks = (now.controller_busy_ticks -
                                      prev.controller_busy_ticks) / diff
        prev.controller_idle_ticks = (now.controller_idle_ticks -
                                      prev.controller_idle_ticks) / diff
        prev.write_cache_flushes = (now.write_cache_flushes -
                                    prev.write_cache_flushes) / diff
        prev.write_cache_blocks_flushed = (now.write_cache_blocks_flushed -
                                        prev.write_cache_blocks_flushed) / diff
        prev.internal_bus_1_busy_ticks = (now.internal_bus_1_busy_ticks -
                                        prev.internal_bus_1_busy_ticks) / diff
        prev.internal_bus_1_idle_ticks = (now.internal_bus_1_idle_ticks -
                                        prev.internal_bus_1_idle_ticks) / diff
        prev.internal_bus_2_busy_ticks = (now.internal_bus_2_busy_ticks -
                                        prev.internal_bus_2_busy_ticks) / diff
        prev.internal_bus_2_idle_ticks = (now.internal_bus_2_idle_ticks -
                                        prev.internal_bus_2_idle_ticks) / diff
        prev.internal_bus_3_busy_ticks = (now.internal_bus_3_busy_ticks -
                                        prev.internal_bus_3_busy_ticks) / diff
        prev.internal_bus_3_idle_ticks = (now.internal_bus_3_idle_ticks -
                                        prev.internal_bus_3_idle_ticks) / diff
        prev.internal_bus_4_busy_ticks = (now.internal_bus_4_busy_ticks -
                                        prev.internal_bus_4_busy_ticks) / diff
        prev.internal_bus_4_idle_ticks = (now.internal_bus_4_idle_ticks -
                                        prev.internal_bus_4_idle_ticks) / diff
        prev.internal_bus_5_busy_ticks = (now.internal_bus_5_busy_ticks -
                                        prev.internal_bus_5_busy_ticks) / diff
        prev.internal_bus_5_idle_ticks = (now.internal_bus_5_idle_ticks -
                                        prev.internal_bus_5_idle_ticks) / diff
        prev.max_requests = now.max_requests
        prev.average_requests = now.average_requests
        prev.prct_busy = now.prct_busy
        prev.pcrt_idle = now.prct_idle
        prev.sum_queue_lengths_by_arrivals = (now.sum_queue_lengths_by_arrivals
                                - prev.sum_queue_lengths_by_arrivals) / diff
        prev.arrivals_to_non_zero_queue = (now.arrivals_to_non_zero_queue -
                                       prev.arrivals_to_non_zero_queue) / diff
        prev.hw_flush_on = (now.hw_flush_on - prev.hw_flush_on) / diff
        prev.idle_flush_on = (now.idle_flush_on - prev.idle_flush_on) / diff
        prev.lw_flush_off = (now.lw_flush_off - prev.lw_flush_off) / diff
        #prev.sys_date = now.sys_date
        #prev.sys_time = now.sys_time
        return prev

    @staticmethod
    def _diff_drive_metrics(now, prev):
        diff = now._metric_time - prev._metric_time
        diff = diff if diff != 0 else 1
        prev.kbytes_read = (now.kbytes_read - prev.kbytes_read) / diff
        prev.kbytes_written = (now.kbytes_written - prev.kbytes_written) / diff
        prev.busy_ticks = (now.busy_ticks - prev.busy_ticks) / diff
        prev.idle_ticks = (now.idle_ticks - prev.idle_ticks) / diff
        prev.number_reads = (now.number_reads - prev.number_reads) / diff
        prev.number_writes = (now.number_writes - prev.number_writes) / diff
        return prev

    @staticmethod
    def _diff_device_metrics(now, prev):
        diff = now._metric_time - prev._metric_time
        diff = diff if diff != 0 else 1
        prev.read_requests = (now.read_requests - prev.read_requests) / diff
        prev.write_requests = (now.write_requests - prev.write_requests) / diff
        prev.blocks_read = (now.blocks_read - prev.blocks_read) / diff
        prev.blocks_written = (now.blocks_written - prev.blocks_written) / diff
        prev.busy_ticks = (now.busy_ticks - prev.busy_ticks) / diff
        prev.idle_ticks = (now.idle_ticks - prev.idle_ticks) / diff
        return prev
