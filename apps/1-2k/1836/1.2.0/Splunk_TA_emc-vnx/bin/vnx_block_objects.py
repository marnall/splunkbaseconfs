import logging
from re import search
from re import compile as reco
from storage_object import (StorageObject, VnxProxy)

_LOGGER = logging.getLogger("ta_vnx")


class Device(StorageObject):

    def __init__(self, agent, section_info, metric_time):
        super(Device, self).__init__(metric_time)
        self.id = None
        self.name = None
        self.capacity = None
        self.is_private = None
        self.state = None
        self.drive_type = None
        self.current_owner = None
        self.default_owner = None
        self.raid_group = None
        self.raid_type = None
        self.uid = None
        self.is_meta = None
        self.is_thin = None
        self.is_pool_based = None
        self._agent = agent
        self.parse(section_info)

    def parse(self, section_info):
        reg_strs = {
            "id": r"^\s*LOGICAL UNIT NUMBER\s+(\d+)",
            "name": r"^\s*Name\s+(.+)",
            "capacity": r"^\s*LUN Capacity\(Megabytes\):\s+(\d+)",
            "is_private": r"^\s*Is Private:\s+(.+)",
            "state": r"^\s*State:\s+(.+)",
            "drive_type": r"^\s*Drive Type:\s+(.+)",
            "current_owner": r"^\s*Current owner:\s+(.+)",
            "default_owner": r"^\s*Default Owner:\s+(.+)",
            "raid_group": r"^\s*RAIDGroup ID:\s+(\d+)",
            "raid_type": r"^\s*RAID Type:\s+(.+)",
            "uid": r"^\s*UID:\s+([\dA-Z:]+)",
            "is_meta": r"^\s*Is Meta LUN:\s+(.+)",
            "is_thin": r"^\s*Is Thin LUN:\s+(.+)",
            "is_pool_based": r"^\s*Is Pool LUN:\s+(.+)",
        }
        self._do_parse(section_info, reg_strs)

        if self.is_private is not None:
            if self.is_private.upper().find("YES") >= 0:
                self.is_private = "True"
            else:
                self.is_private = "False"

        if self.is_meta is not None:
            if self.is_meta.upper().find("YES") >= 0:
                self.is_meta = "True"
            else:
                self.is_meta = "False"

        if self.is_thin is not None and self.is_thin.upper().find("YES") >= 0:
            self.is_thin = "True"
        else:
            self.is_thin = "False"

        pool_based = self.is_pool_based
        if pool_based is not None and pool_based.upper().find("YES") >= 0:
            self.is_pool_based = "True"
        else:
            self.is_pool_based = "False"

        if self.raid_group is None:
            self.raid_group = "-1"

        if self.raid_type == "Hot Spare":
            self.is_private = "False"
            self.is_pool_based = "False"
            self.is_meta = "False"
            self.is_thin = "False"

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:block:device")


class Drive(StorageObject):

    def __init__(self, agent, section_info, metric_time):
        super(Drive, self).__init__(metric_time)
        self.id = None
        self.capacity = None
        self.state = None
        self.is_hotspare = None
        self.vendor = None
        self.raid_group = None
        self.drive_type = None
        self.product_id = None
        self.product_revision = None
        self.current_speed = None
        self.max_speed = None
        self.parse(section_info)
        self._agent = agent

    def parse(self, section_info):
        reg_strs = {
            "id": r"^\s*Bus\s+(\d+)\s+Enclosure\s+(\d+)\s+Disk\s+(\d+)",
            "capacity": r"^\s*Capacity:\s+(\d+)",
            "state": r"^\s*State:\s+(.+)",
            "is_hotspare": r"^\s*Hot Spare:\s+(.+)",
            "vendor": r"^\s*Vendor Id:\s+(.+)",
            "raid_group": r"^\s*Raid Group ID:\s+(\d+)",
            "drive_type": r"^\s*Drive Type:\s+(.+)",
            "product_id": r"^\s*Product Id:\s+(.+)",
            "product_revision": r"^\s*Product Revision:\s+(.+)",
            "current_speed": r"^\s*Current Speed:\s+(.+)",
            "max_speed": r"^\s*Maximum Speed:\s+(.+)",
        }
        self._do_parse(section_info, reg_strs)

        if self.is_hotspare is not None:
            if self.is_hotspare.upper().find("YES") >= 0:
                self.is_hotspare = "True"
            else:
                self.is_hotspare = "False"

        if self.raid_group is None:
            self.raid_group = "-1"

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:block:drive")


class StoragePool(StorageObject):

    def __init__(self, agent, section_info, metric_time):
        super(StoragePool, self).__init__(metric_time)
        self.name = None
        self.id = None
        self.status = None
        self.raw_cap = None
        self.user_cap = None
        self.used_cap = None
        self.free_cap = None
        self.rtype = None
        self.disk_type = None
        self._drive_ids = []
        self._device_ids = []
        self._agent = agent
        self.parse(section_info)

    def parse(self, section_info):
        reg_strs = {
            "name": r"^\s*Pool Name:\s+(.+)",
            "id": r"^\s*Pool ID:\s+(\d+)",
            "status": r"^\s*Status:\s+(.+)",
            "raw_cap": r"^\s*Raw Capacity \(Blocks\):\s+(\d+)",
            "user_cap": r"^\s*User Capacity \(Blocks\):\s+(\d+)",
            "used_cap": r"^\s*Consumed Capacity \(Blocks\):\s+(\d+)",
            "free_cap": r"^\s*Available Capacity \(Blocks\):\s+(\d+)",
            "rtype": r"^\s*Raid Type:\s+(.+)",
            "disk_type": r"^\s*Disk Type:\s+(.+)",
            "_drive_ids": r"^\s*Bus\s+(\d+)\s+Enclosure\s+(\d+)\s+Disk\s+(\d+)",
            "_device_ids": r"^\s*LUNs:([\d|,|\s]+)",
        }
        self._do_parse(section_info, reg_strs)

        if self.raw_cap is not None:
            self.raw_cap = str(int(self.raw_cap) / 2048)

        if self.user_cap is not None:
            self.user_cap = str(int(self.user_cap) / 2048)

        if self.used_cap is not None:
            self.used_cap = str(int(self.used_cap) / 2048)

        if self.free_cap is not None:
            self.free_cap = str(int(self.free_cap) / 2048)

        devs = []
        for dev_ids in self._device_ids:
            devs.extend((dev.strip() for dev in dev_ids.split(",")))
        self._device_ids = devs

    def to_string(self, timestamp, idx):
        sp = self._to_tag_value(timestamp, idx, "vnx:block:storagePool")
        drive = self.drive_to_string(timestamp, idx)
        device = self.device_to_string(timestamp, idx)
        return "".join((sp, drive, device))

    def drive_to_string(self, timestamp, idx):
        timestamp = self._metric_time
        array_no = self._agent.array_serial_no
        evt_fmt = ("<event><time>%s</time><source>vnx</source>"
                   "<sourcetype>vnx:block:poolDrive</sourcetype>"
                   "<index>%s</index><data>%s</data></event>")
        data_fmt = "pool_name=%s,pool_id=%s,drive_id=%s,array_serial_no=%s"
        return "".join((evt_fmt % (timestamp, idx,
                        data_fmt % (self.name, self.id, drive_id, array_no))
                        for drive_id in self._drive_ids))

    def device_to_string(self, timestamp, idx):
        timestamp = self._metric_time
        array_no = self._agent.array_serial_no
        evt_fmt = ("<event><time>%s</time><source>vnx</source>"
                   "<sourcetype>vnx:block:poolDevice</sourcetype>"
                   "<index>%s</index><data>%s</data></event>")
        data_fmt = "pool_name=%s,pool_id=%s,device_id=%s,array_serial_no=%s"
        return "".join((evt_fmt % (timestamp, idx,
                        data_fmt % (self.name, self.id, device_id, array_no))
                        for device_id in self._device_ids))


class RaidGroup(StorageObject):

    def __init__(self, agent, section_info, metric_time):
        super(RaidGroup, self).__init__(metric_time)
        self.id = None
        self.raw_cap = None
        self.logical_cap = None
        self.free_cap = None
        self.rtype = None
        self.state = None
        self._drive_ids = []
        self._agent = agent
        self.parse(section_info)

    def parse(self, section_info):
        reg_strs = {
            "id": r"^\s*RaidGroup ID:\s+(\d+)",
            "raw_cap": r"^\s*Raw Capacity \(Blocks\):\s+(\d+)",
            "logical_cap": r"^\s*Logical Capacity \(Blocks\):\s+(\d+)",
            "free_cap": r"Free Capacity \(Blocks,non-contiguous\):\s+(\d+)",
            "rtype": r"RaidGroup Type:\s+(.+)",
            "state": r"RaidGroup State:\s+(.+)",
            "_drive_ids": r"\s+Bus\s+(\d+)\s+Enclosure\s+(\d+)\s+Disk\s+(\d+)",
        }
        self._do_parse(section_info, reg_strs)

        if self.raw_cap is not None:
            self.raw_cap = str(int(self.raw_cap) / 2048)

        if self.logical_cap is not None:
            self.logical_cap = str(int(self.logical_cap) / 2048)

        if self.free_cap is not None:
            self.free_cap = str(int(self.free_cap) / 2048)

    def to_string(self, timestamp, idx):
        rg = self._to_tag_value(timestamp, idx, "vnx:block:raidGroup")
        drive = self.drive_to_string(timestamp, idx)
        return "".join((rg, drive))

    def drive_to_string(self, timestamp, idx):
        timestamp = self._metric_time
        evt_fmt = ("<event><time>%s</time><source>vnx</source>"
                   "<sourcetype>vnx:block:rgDrive</sourcetype>"
                   "<index>%s</index><data>%s</data></event>")
        data_fmt = "drive_id=%s,rg_id=%s,array_serial_no=%s"
        array_no = self._agent.array_serial_no
        return "".join((evt_fmt % (timestamp, idx,
                        data_fmt % (drive_id, self.id, array_no))
                        for drive_id in self._drive_ids))

    def is_valid(self):
        return super(RaidGroup, self).is_valid() and self._drive_ids


class StorageGroup(StorageObject):

    def __init__(self, agent, section_info, metric_time):
        super(StorageGroup, self).__init__(metric_time)
        self.name = None
        self.hba_spports = []
        self.hostnames = []
        self.device_ids = []
        self._agent = agent
        self.parse(section_info)

    def parse(self, section_info):
        done_with_hba_spports = False
        for lin in section_info:
            if self.name is None:
                match = search(r"^\s*Storage Group Name:\s+(.+)", lin)
                if match:
                    self.name = match.group(1).strip()
                    continue

            if not done_with_hba_spports:
                match = search(r"([^\s]+)\s+(SP\s+[A|B])\s+(\d+)", lin)
                if match:
                    self.hba_spports.append((match.group(1), match.group(2),
                                             match.group(3)))
                    continue
                else:
                    match = search(r"Host name:\s+(.+)", lin)
                    if match:
                        self.hostnames.append(match.group(1).strip())
                        continue

            match = search(r"^\s+\d+\s+(\d+)", lin)
            if match:
                self.device_ids.append(match.group(1))
                if self.hba_spports:
                    done_with_hba_spports = True

    def has_host_attached(self):
        return len(self.hba_spports) > 0

    def to_string(self, timestamp, idx):
        timestamp = self._metric_time
        assert len(self.hostnames) == len(self.hba_spports)
        array_no = self._agent.array_serial_no
        evt_fmt = ("<event><time>%s</time><source>vnx</source>"
                   "<sourcetype>vnx:block:storageGroup</sourcetype>"
                   "<index>%s</index><data>%s</data></event>")
        data_fmt = "HBA=%s,spid=%s,spport=%s,hostname=%s,array_serial_no=%s"
        sg = "".join((evt_fmt % (timestamp, idx,
                      data_fmt % (hba[0], hba[1], hba[2], host, array_no))
                      for hba, host in zip(self.hba_spports, self.hostnames)))
        device = self.device_to_string(timestamp, idx)
        return "".join((sg, device))

    def device_to_string(self, timestamp, idx):
        timestamp = self._metric_time
        evt_fmt = ("<event><time>%s</time><source>vnx</source>"
                   "<sourcetype>vnx:block:sgDevice</sourcetype>"
                   "<index>%s</index><data>%s</data></event>")
        array_no = self._agent.array_serial_no
        data_fmt = "device_id=%s,storagegroup_name=%s,array_serial_no=%s"
        return "".join((evt_fmt % (timestamp, idx, data_fmt
                        % (dev, self.name, array_no))
                        for dev in self.device_ids))

    def is_valid(self):
        return self.name is not None and self.hba_spports and self.device_ids


class SPPort(object):

    def __init__(self, agent, section_info, metric_time):
        super(SPPort, self).__init__(metric_time)
        self.sp_name = None
        self.port_id = None
        self.uid = None
        self.link_status = None
        self.port_status = None
        self.switch_present = None
        self._agent = agent
        self.parse(section_info)

    def parse(self, section_info):
        reg_strs = {
            "sp_name": r"^\s*SP Name:\s+(.+)",
            "port_id": r"^\s*SP Port ID:\s+(\d+)",
            "uid": r"^\s*SP UID:\s+(.+)",
            "link_status": r"^\s*Link Status:\s+(.+)",
            "port_status": r"^\s*Port Status:\s+(.+)",
            "switch_present": r"^\s*Switch Present:\s+(.+)",
        }
        self._do_parse(section_info, reg_strs)

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:block:spPort")


class Agent(StorageObject):

    def __init__(self, site, ip, section_info, metric_time):
        super(Agent, self).__init__(metric_time)
        self.site = site
        self.ip = ip
        self.agent_rev = None
        self.agent_name = None
        self.node = None
        self.physical_node = None
        self.revision = None
        self.model = None
        self.model_type = None
        self.sp_memory = None
        self.array_serial_no = None
        self.sp_id = None
        self.cabinet = None
        self.os = None
        self.parse(section_info)

    def parse(self, section_info):
        reg_strs = {
            "agent_rev": r"^\s*Agent Rev:\s+(.+)",
            "agent_name": r"^\s*Name:\s+(.+)",
            "node": r"^\s*Node:\s+(.+)",
            "physical_node": r"^\s*Physical Node:\s+(.+)",
            "revision": r"^\s*Revision:\s+(.+)",
            "model": r"^\s*Model:\s+(.+)",
            "model_type": r"^\s*Model Type:\s+(.+)",
            "sp_memory": r"^\s*SP Memory:\s+(.+)",
            "array_serial_no": r"^\s*Serial No:\s+(.+)",
            "sp_id": r"^\s*SP Identifier:\s+(.+)",
            "cabinet": r"^\s*Cabinet:\s+(.+)",
            "os": r"^\s*Operating System:\s+(.+)",
        }
        self._do_parse(section_info, reg_strs)

    def to_string(self, timestamp, idx):
        self._agent = VnxProxy("array_serial_no", self.array_serial_no)
        res = self._to_tag_value(timestamp, idx, "vnx:block:agent")
        del self._agent
        return res


def _to_int(int_str, default=0):
    try:
        return int(int_str)
    except (TypeError, ValueError):
        return default


class ProcessorPerfMetrics(StorageObject):

    def __init__(self, agent, output, metric_time):
        super(ProcessorPerfMetrics, self).__init__(metric_time)
        self.sys_fault_led = None
        self.statistics_logging = None
        self.sp_read_cache_state = None
        self.sp_write_cache_state = None
        self.max_requests = None
        self.average_requests = None
        self.total_reads = None
        self.total_writes = None
        self.prct_busy = None
        self.prct_idle = None
        #self.sys_date = None
        #self.sys_time = None
        self.read_requests = None
        self.write_requests = None
        self.blocks_read = None
        self.blocks_written = None
        self.sum_queue_lengths_by_arrivals = None
        self.arrivals_to_non_zero_queue = None
        self.hw_flush_on = None
        self.idle_flush_on = None
        self.lw_flush_off = None
        self.write_cache_flushes = None
        self.write_cache_blocks_flushed = None
        self.controller_busy_ticks = None
        self.controller_idle_ticks = None
        self.serial_no_for_the_sp = None
        self.internal_bus_1_busy_ticks = None
        self.internal_bus_1_idle_ticks = None
        self.internal_bus_2_busy_ticks = None
        self.internal_bus_2_idle_ticks = None
        self.internal_bus_3_busy_ticks = None
        self.internal_bus_3_idle_ticks = None
        self.internal_bus_4_busy_ticks = None
        self.internal_bus_4_idle_ticks = None
        self.internal_bus_5_busy_ticks = None
        self.internal_bus_5_idle_ticks = None
        self._agent = agent
        self.sp_id = self._agent.sp_id
        self.parse(output)

    def parse(self, output):
        reg_strs = {
            "sys_fault_led": r"^\s*System Fault LED:\s+(.+)",
            "statistics_logging": r"^\s*Statistics Logging:\s+(.+)",
            "sp_read_cache_state": r"^\s*SP Read Cache State:?\s+(.+)",
            "sp_write_cache_state": r"^\s*SP Write Cache State:?\s+(.+)",
            "max_requests": r"^\s*Max Requests:\s+(.+)",
            "average_requests": r"^\s*Average Requests:\s+(.+)",
            "total_reads": r"^\s*Total Reads:\s+(\d+)",
            "total_writes": r"^\s*Total Writes:\s+(\d+)",
            "prct_busy": r"^\s*Prct Busy:\s+([\d\.]+)",
            "prct_idle": r"^\s*Prct Idle:\s+([\d\.]+)",
            #"sys_date": r"^\s*System Date:\s+(.+)",
            #"sys_time": r"^\s*System Time:\s+(.+)",
            "read_requests": r"^\s*Read_requests:\s+(\d+)",
            "write_requests": r"^\s*Write_requests:\s+(\d+)",
            "blocks_read": r"^\s*Blocks_read:\s+(\d+)",
            "blocks_written": r"^\s*Blocks_written:\s+(\d+)",
            "sum_queue_lengths_by_arrivals": r"^\s*Sum_queue_lengths_by_arrivals:\s*(.+)",
            "arrivals_to_non_zero_queue": r"^\s*Arrivals_to_non_zero_queue:\s+(.+)",
            "hw_flush_on": r"^\s*Hw_flush_on:\s+(.+)",
            "idle_flush_on": r"^\s*Idle_flush_on:\s+(.+)",
            "lw_flush_off": r"^\s*Lw_flush_off:\s+(.+)",
            "write_cache_flushes": r"^\s*Write_cache_flushes:\s+(.+)",
            "write_cache_blocks_flushed": r"^\s*Write_cache_blocks_flushed:\s+(.+)",
            "controller_busy_ticks": r"^\s*Controller busy ticks:\s+(\d+)",
            "controller_idle_ticks": r"^\s*Controller idle ticks:\s+(\d+)",
            "serial_no_for_the_sp": r"^\s*Serial Number For The SP:\s+(.+)",
            "internal_bus_1_busy_ticks": r"^\s*Internal bus 1 busy ticks:\s+(.+)",
            "internal_bus_1_idle_ticks": r"^\s*Internal bus 1 idle ticks:\s+(.+)",
            "internal_bus_2_busy_ticks": r"^\s*Internal bus 2 busy ticks:\s+(.+)",
            "internal_bus_2_idle_ticks": r"^\s*Internal bus 2 idle ticks:\s+(.+)",
            "internal_bus_3_busy_ticks": r"^\s*Internal bus 3 busy ticks:\s+(.+)",
            "internal_bus_3_idle_ticks": r"^\s*Internal bus 3 idle ticks:\s+(.+)",
            "internal_bus_4_busy_ticks": r"^\s*Internal bus 4 busy ticks:\s+(.+)",
            "internal_bus_4_idle_ticks": r"^\s*Internal bus 4 idle ticks:\s+(.+)",
            "internal_bus_5_busy_ticks": r"^\s*Internal bus 5 busy ticks:\s+(.+)",
            "internal_bus_5_idle_ticks": r"^\s*Internal bus 5 idle ticks:\s+(.+)",
        }
        self._do_parse(output, reg_strs)
        if self.is_valid():
            self.total_reads = _to_int(self.total_reads)
            self.total_writes = _to_int(self.total_writes)
            self.read_requests = _to_int(self.read_requests)
            self.write_requests = _to_int(self.write_requests)
            self.blocks_read = _to_int(self.blocks_read)
            self.blocks_written = _to_int(self.blocks_written)
            self.write_cache_flushes = _to_int(self.write_cache_flushes)
            self.write_cache_blocks_flushed = _to_int(self.write_cache_blocks_flushed)
            self.sum_queue_lengths_by_arrivals = _to_int(self.sum_queue_lengths_by_arrivals)
            self.arrivals_to_non_zero_queue = _to_int(self.arrivals_to_non_zero_queue)
            self.hw_flush_on = _to_int(self.hw_flush_on)
            self.idle_flush_on = _to_int(self.idle_flush_on)
            self.lw_flush_off = _to_int(self.lw_flush_off)
            self.internal_bus_1_busy_ticks = _to_int(self.internal_bus_1_busy_ticks)
            self.internal_bus_1_idle_ticks = _to_int(self.internal_bus_1_idle_ticks)
            self.internal_bus_2_busy_ticks = _to_int(self.internal_bus_2_busy_ticks)
            self.internal_bus_2_idle_ticks = _to_int(self.internal_bus_2_idle_ticks)
            self.internal_bus_3_busy_ticks = _to_int(self.internal_bus_3_busy_ticks)
            self.internal_bus_3_idle_ticks = _to_int(self.internal_bus_3_idle_ticks)
            self.internal_bus_4_busy_ticks = _to_int(self.internal_bus_4_busy_ticks)
            self.internal_bus_4_idle_ticks = _to_int(self.internal_bus_4_idle_ticks)
            self.internal_bus_5_busy_ticks = _to_int(self.internal_bus_5_busy_ticks)
            self.internal_bus_5_idle_ticks = _to_int(self.internal_bus_5_idle_ticks)
            self.controller_busy_ticks = _to_int(self.controller_busy_ticks)
            self.controller_idle_ticks = _to_int(self.controller_idle_ticks)
            self.max_requests = _to_int(self.max_requests)
            self.average_requests = _to_int(self.average_requests)

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:block:spPerf")


class DrivePerfMetrics(StorageObject):

    def __init__(self, agent, output, metric_time):
        super(DrivePerfMetrics, self).__init__(metric_time)
        self.drive_id = None
        self.kbytes_read = None
        self.kbytes_written = None
        self.busy_ticks = None
        self.idle_ticks = None
        self.number_reads = None
        self.number_writes = None
        self._agent = agent
        self.parse(output)

    def parse(self, output):
        reg_strs = {
            "drive_id": r"^\s*Bus\s+(\d+)\s+Enclosure\s+(\d+)\s+Disk\s+(\d+)",
            "kbytes_read": r"^\s*Kbytes Read:\s+(\d+)",
            "kbytes_written": r"^\s*Kbytes Written:\s+(\d+)",
            "busy_ticks": r"^\s*Busy Ticks:\s+(\d+)",
            "idle_ticks": r"^\s*Idle Ticks:\s+(\d+)",
            "number_reads": r"^\s*Number of Reads:\s+(\d+)",
            "number_writes": r"^\s*Number of Writes:\s+(\d+)",
        }
        self._do_parse(output, reg_strs)
        if self.is_valid():
            self.kbytes_read = _to_int(self.kbytes_read)
            self.kbytes_written = _to_int(self.kbytes_written)
            self.busy_ticks = _to_int(self.busy_ticks)
            self.idle_ticks = _to_int(self.idle_ticks)
            self.number_reads = _to_int(self.number_reads)
            self.number_writes = _to_int(self.number_writes)

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:block:drivePerf")


class DevicePerfMetrics(StorageObject):

    def __init__(self, agent, output, metric_time):
        super(DevicePerfMetrics, self).__init__(metric_time)
        self.device_id = None
        self.device_name = None
        self.blocks_read = []
        self.blocks_written = []
        self.idle_ticks = []
        self.busy_ticks = []
        self.read_requests = []
        self.write_requests = []
        self.pool_name = None
        self._agent = agent
        self.parse(output)

    def parse(self, output):
        reg_strs = {
            "device_id": r"^\s*LOGICAL UNIT NUMBER\s+(\d+)",
            "device_name": r"^\s*Name:?\s+(.+)",
            "blocks_read": r"^\s*Blocks Read:\s+(\d+)",
            "blocks_written": r"^\s*Blocks Written:\s+(\d+)",
            "idle_ticks": r"^\s*Idle Ticks:\s+(\d+)",
            "busy_ticks": r"^\s*Busy Ticks:\s+(\d+)",
            "read_requests": r"^\s*Read Requests:\s+(\d+)",
            "write_requests": r"^\s*Write Requests:\s+(\d+)",
            "pool_name": r"^\s*Pool Name:\s+(.+)",
        }
        self._do_parse(output, reg_strs)
        if (self.is_valid() and self.blocks_read and self.blocks_written and
                self.idle_ticks and self.busy_ticks and self.read_requests and self.write_requests):
            total = sum((_to_int(blocks) for blocks in self.blocks_read))
            self.blocks_read = total / len(self.blocks_read)
            total = sum((_to_int(blocks) for blocks in self.blocks_written))
            self.blocks_written = total / len(self.blocks_written)
            total = sum((_to_int(ticks) for ticks in self.idle_ticks))
            self.idle_ticks = total / len(self.idle_ticks)
            total = sum((_to_int(ticks) for ticks in self.busy_ticks))
            self.busy_ticks = total / len(self.busy_ticks)
            total = sum((_to_int(requests) for requests in self.read_requests))
            self.read_requests = total / len(self.read_requests)
            total = sum((_to_int(requests) for requests in self.write_requests))
            self.write_requests = total / len(self.write_requests)
        else:
            self.device_id = None
            self.device_name = None

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:block:devicePerf")


class BusSFPState(StorageObject):

    def __init__(self, agent, output, metric_time):
        super(BusSFPState, self).__init__(metric_time)
        self.bus_id = None
        self.spa_sfp_state = None
        self.spb_sfp_state = None
        self._agent = agent
        self.parse(output)

    def parse(self, output):
        reg_strs = {
            "bus_id": r"^\s*(Bus\s+\d+)",
            "spa_sfp_state": r"SPA SFP State:\s+(.+)",
            "spb_sfp_state": r"SPB SFP State:\s+(.+)",
        }
        self._do_parse(output, reg_strs)

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:block:sfpState")


class CrusState(StorageObject):

    def __init__(self, agent, output, metric_time):
        super(CrusState, self).__init__(metric_time)
        self.location = None
        self.cpu_module_a_state = None
        self.cpu_module_b_state = None
        self.dimm_module_a_state = None
        self.dimm_module_b_state = None
        self.spa_state = None
        self.spb_state = None
        self.powera_state = None
        self.powerb_state = None
        self.spsa_state = None
        self.spsb_state = None
        self.spa_io_module_0_state = None
        self.spa_io_module_1_state = None
        self.spb_io_module_0_state = None
        self.spb_io_module_1_state = None
        self.lcc_a_state = None
        self.lcc_b_state = None
        self._agent = agent
        self.parse(output)

    def parse(self, output):
        reg_strs = {
            "location": r"^\s*(D[A|P]E.*Enclosure \d+)\s*$",
            "cpu_module_a_state": r"CPU Module A State:\s+(\w+)\s*$",
            "cpu_module_b_state": r"CPU Module B State:\s+(\w+)\s*$",
            "dimm_module_a_state": r"DIMM Module A State:\s+(\w+)\s*$",
            "dimm_module_b_state": r"DIMM Module B State:\s+(\w+)\s*$",
            "spa_state": r"SP A State:\s+(\w+)\s*$",
            "spb_state": r"SP B State:\s+(\w+)\s*$",
            "powera_state": r"Power A State:\s+(\w+)\s*$",
            "powerb_state": r"Power B State:\s+(\w+)\s*$",
            "spsa_state": r"SPS A State:\s+(\w+)\s*$",
            "spsb_state": r"SPS B State:\s+(\w+)\s*$",
            "spa_io_module_0_state": r"SP A I/O Module 0 State:\s+(\w+)\s*$",
            "spa_io_module_1_state": r"SP A I/O Module 1 State:\s+(\w+)\s*$",
            "spb_io_module_0_state": r"SP B I/O Module 0 State:\s+(\w+)\s*$",
            "spb_io_module_1_state": r"SP A I/O Module 1 State:\s+(\w+)\s*$",
            "lcc_a_state": r"LCC A State:\s+(\w+)\s*$",
            "lcc_b_state": r"LCC B State:\s+(\w+)\s*$",
        }
        self._do_parse(output, reg_strs)
        for name, value in self.__dict__.iteritems():
            if value is None:
                setattr(self, name, "N/A")

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:block:crusState")


class DriveState(StorageObject):

    def __init__(self, agent, output, metric_time):
        super(DriveState, self).__init__(metric_time)
        self.drive_id = None
        self.state = None
        self.hard_read_error = None
        self.hard_write_error = None
        self.soft_read_error = None
        self.soft_write_error = None
        self._agent = agent
        self.parse(output)

    def parse(self, output):
        reg_strs = {
            "drive_id": r"^\s*Bus\s+(\d+)\s+Enclosure\s+(\d+)\s+Disk\s+(\d+)",
            "state": r"^\s*State:\s+(\w+)",
            "hard_read_error": r"^\s*Hard Read Errors:\s+(\d+)",
            "hard_write_error": r"^\s*Hard Write Errors:\s+(\d+)",
            "soft_read_error": r"^\s*Soft Read Errors:\s+(\d+)",
            "soft_write_error": r"^\s*Soft Write Errors:\s+(\d+)",
        }
        self._do_parse(output, reg_strs)

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:block:driveState")


class DeviceState(StorageObject):

    def __init__(self, agent, output, metric_time):
        super(DeviceState, self).__init__(metric_time)
        self.device_id = None
        self.device_name = None
        self.state = None
        self._agent = agent
        self.parse(output)

    def parse(self, output):
        reg_strs = {
            "device_id": r"^\s*LOGICAL UNIT NUMBER\s+(\d+)",
            "device_name": r"^\s*Name:?\s+(.+)",
            "state": r"^\s*State:\s+(\w+)",
        }
        self._do_parse(output, reg_strs)

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:block:deviceState")


class RaidGroupState(StorageObject):

    def __init__(self, agent, output, metric_time):
        super(RaidGroupState, self).__init__(metric_time)
        self.raidgroup_id = None
        self.state = None
        self._agent = agent
        self.parse(output)

    def parse(self, output):
        reg_strs = {
            "raidgroup_id": r"^\s*RaidGroup ID:\s+(\d+)",
            "state": r"^\s*RaidGroup State:\s+(\w+)",
        }
        self._do_parse(output, reg_strs)

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:block:rgState")


class StoragePoolState(StorageObject):

    def __init__(self, agent, section_info, metric_time):
        super(StoragePoolState, self).__init__(metric_time)
        self.name = None
        self.id = None
        self.state = None
        self._agent = agent
        self.parse(section_info)

    def parse(self, section_info):
        reg_strs = {
            "name": r"^\s*(?:Thin )?Pool Name:\s+(.+)",
            "id": r"^\s*(?:Thin )?Pool ID:\s+(\d+)",
            "state": r"^\s*State:\s+(.+)",
        }
        self._do_parse(section_info, reg_strs)

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx,
                                  "vnx:block:storagePoolState")


def _parse_block_objects(agent, output, start_tag, StorageClass, metric_time):
    container = []
    section_info = []
    start_collect = False
    pat = reco(start_tag)

    for lin in output.split("\n"):
        match = pat.search(lin)
        if match:
            if section_info:
                obj = StorageClass(agent, section_info, metric_time)
                if obj.is_valid():
                    container.append(obj)
                else:
                    _LOGGER.debug("%s Ignore: %s", StorageClass.__name__,
                                  "\n".join(section_info))
                del section_info[:]
            start_collect = True
            section_info.append(lin)
        elif start_collect:
            section_info.append(lin)

    if section_info:
        obj = StorageClass(agent, section_info, metric_time)
        if obj.is_valid():
            container.append(obj)
        else:
            _LOGGER.debug("%s Ignore: %s", StorageClass.__name__,
                          "\n".join(section_info))
    return container


def parse_block_objects(agent, output, start_tag, StorageClass, metric_time,
                        use_computing_service=True):
    if use_computing_service:
        # use data_loader's computing service for calculating
        import data_loader
        loader = data_loader.GlobalDataLoader.get_data_loader(None, None, None)
        return loader.run_computing_job(_parse_block_objects,
                                        (agent, output, start_tag,
                                         StorageClass, metric_time))
    else:
        return _parse_block_objects(agent, output, start_tag, StorageClass,
                                    metric_time)
