import logging
from re import compile as reco
from itertools import izip
from re import search

from storage_object import StorageObject

_LOGGER = logging.getLogger("ta_vnx")


class FileSystem(StorageObject):

    def __init__(self, filer, output, metric_time):
        super(FileSystem, self).__init__(metric_time)
        self.name = None
        self.id = None
        self.raw_capacity = None
        self.logical_capacity = None
        self.used_capacity = None
        self.max_size = None
        self.is_virtual_provisioned = None
        self.type = None
        self.ro_servers = None
        self.rw_servers = None
        self._filer = filer
        self.parse(output)

    def parse(self, output):
        """
        output => name,id,rawcapacity,logicalcapacity,usedcapacity,
                  maxsize,virtuallyprovisioned,type,ROServers,RWServers
        """

        fs_fields = output.split("|")
        if len(fs_fields) == 10:
            fs_fields[2] = fs_fields[2] and fs_fields[2] or "0"
            fs_fields[3] = fs_fields[3] and fs_fields[3] or "0"
            fs_fields[4] = fs_fields[4] and fs_fields[4] or "0"
            fs_fields[2] = str(int(fs_fields[2]) / 2048)
            fs_fields[3] = str(int(fs_fields[3]) / 2048)
            fs_fields[4] = str(int(fs_fields[4]) / 2048)
        elif len(fs_fields) == 8:
            fs_fields = fs_fields[:-5] + ["0", "0"] + fs_fields[-5:]
        else:
            _LOGGER.warn("invalid fs info : %s", output)

        names = ("name", "id", "raw_capacity", "logical_capacity",
                 "used_capacity", "max_size", "is_virtual_provisioned",
                 "type", "ro_servers", "rw_servers")

        for name, value in izip(names, fs_fields):
            setattr(self, name, value)

        # Correct the bug in the CLI
        if (self.is_virtual_provisioned == "False" and
                int(self.max_size) > int(self.raw_capacity)):
            self.max_size = self.raw_capacity

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:fileSystem")


class CifsServer(StorageObject):

    def __init__(self, filer, output, metric_time):
        super(CifsServer, self).__init__(metric_time)
        self.name = None
        self.server = None
        self.full_comp_name = None
        self.fqdn = None
        self.ip = None
        self._filer = filer
        self.parse(output)

    def parse(self, output):
        reg_strs = {
            "name": r'CIFS\s+Server\s+([^\[]+)',
            "server": r'^\s*(.+)\s+:\s*$',
            "full_comp_name": r'^\s*Full\s+computer\s+name=(\S+)',
            "fqdn": r'^\s*FQDN=(\S+)',
            "ip": r'if=(.+)l=([\d\.]+)\s*b=',
        }
        self._do_parse(output, reg_strs)

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:cifsServer")


class Checkpoint(StorageObject):

    def __init__(self, filer, output, metric_time):
        super(Checkpoint, self).__init__(metric_time)
        self.name = None
        self.id = None
        self.capacity = None
        self.used_pct = None
        self.used_savvol_mb = None
        self.vpfs = None
        self.ro_servers = None
        self.rw_servers = None
        self.backupof = None
        self._filer = filer
        self.parse(output)

    def parse(self, output):
        """
        output => name,id,size,ckptpctused,ckptsavvolusedmb,vpfs,ROServers,
                  RWServers,cbackupof
        """

        values = output.split("|")
        names = ("name", "id", "capacity", "used_pct", "used_savvol_mb",
                 "vpfs", "ro_servers", "rw_servers", "backupof")

        for name, value in izip(names, values):
            setattr(self, name, value)

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:checkpoint")


class Vpfs(StorageObject):

    def __init__(self, filer, output, metric_time):
        super(Vpfs, self).__init__(metric_time)
        self.name = None
        self.id = None
        self.capacity = None
        self.ro_servers = None
        self.rw_servers = None
        self._filer = filer
        self.parse(output)

    def parse(self, output):
        """
        output => name,id,size,ROServers,RWServers
        """

        values = output.split("|")
        names = ("name", "id", "capacity", "ro_servers",
                 "rw_servers", "backupof")

        for name, value in izip(names, values):
            setattr(self, name, value)

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:vpfs")


class Disk(StorageObject):

    def __init__(self, filer, output, metric_time):
        super(Disk, self).__init__(metric_time)
        self.name = None
        self.id = None
        self.backend_id = None
        self.capacity = None
        self.array_serial_no = None
        self.raid_group = None
        self._filer = filer
        self.parse(output)

    def parse(self, output):
        """
        output => name,id,symmdev,size,symmid,protection
        """

        values = output.split("|")
        names = ("name", "id", "backend_id", "capacity", "array_serial_no", "raid_group")

        for name, value in izip(names, values):
            setattr(self, name, value)

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:disk")


class Interface(StorageObject):

    def __init__(self, filer, output, metric_time):
        super(Interface, self).__init__(metric_time)
        self.server = None
        self.name = None
        self.address = None
        self.device = None
        self._filer = filer
        self.parse(output)

    def parse(self, output):
        """
        output => server,name,address,device
        """

        values = output.split("|")
        names = ("server", "name", "address", "device")

        for name, value in izip(names, values):
            setattr(self, name, value)

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:interface")


class FileSystemMount(StorageObject):

    def __init__(self, filer, output, metric_time):
        super(FileSystemMount, self).__init__(metric_time)
        self.server = None
        self.filesystem = None
        self.filesystem_id = None
        self.path = None
        self._filer = filer
        self.parse(output)

    def parse(self, output):
        """
        output => server,filesystem,filesystemid,path
        """

        values = output.split("|")
        names = ("server", "filesystem", "filesystem_id", "path")

        for name, value in izip(names, values):
            setattr(self, name, value)

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:mount")


class FileSystemExport(StorageObject):

    def __init__(self, filer, output, metric_time):
        super(FileSystemExport, self).__init__(metric_time)
        self.server = None
        self.is_share = None
        self.name = None
        self.path = None
        self.netbios = None
        self.options = None
        self._filer = filer
        self.parse(output)

    def parse(self, output):
        """
        output => server,isshare,name,path,netbios,options
        """

        values = output.split("|")
        names = ("server", "is_share", "name", "path", "netbios", "options")

        for name, value in izip(names, values):
            setattr(self, name, value)

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:export")


class NasServer(StorageObject):

    def __init__(self, filer, output, metric_time):
        super(NasServer, self).__init__(metric_time)
        self.name = None
        self.id = None
        self.type = None
        self.version = None
        self.rootfs = None
        self.physicalhost = None
        self.status = None
        self.statusactual = None
        self._filer = filer
        self.parse(output)

    def parse(self, output):
        """
        output => name,id,type,version,rootfs,physicalhost,status,statusactual
        """

        values = output.split("|")
        names = ("name", "id", "type", "version", "rootfs", "physicalhost",
                 "status", "statusactual")

        for name, value in izip(names, values):
            setattr(self, name, value)

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:nasServer")


class CifsHost(StorageObject):

    def __init__(self, filer, output, metric_time):
        super(CifsHost, self).__init__(metric_time)
        self.server = None
        self.computer_name = None
        self.netbios = None
        self.cifs_domain = None
        self._filer = filer
        self.parse(output)

    def parse(self, output):
        """
        output => server,ComputerName,Netbios,cifsDomain
        """

        values = output.split("|")
        names = ("server", "computer_name", "netbios", "cifs_domain")

        for name, value in izip(names, values):
            setattr(self, name, value)

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:cifsHost")


class StoragePool(StorageObject):

    def __init__(self, filer, output, metric_time):
        super(StoragePool, self).__init__(metric_time)
        self.name = None
        self.id = None
        self.capacity = None
        self.free_capacity = None
        self.potential_capacity = None
        self.used_capacity = None
        self._filer = filer
        self.parse(output)

    def parse(self, output):
        """
        output => name,id,CapacityMB,AvailableMB,PotentialMB,usedMB
        """

        values = output.split("|")
        names = ("name", "id", "capacity", "free_capacity",
                 "potential_capacity", "used_capacity")

        for name, value in izip(names, values):
            setattr(self, name, value)

        if int(self.capacity) == 0:
            self.capacity = self.potential_capacity

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:storagePool")


class Quota(StorageObject):

    def __init__(self, metric_time):
        super(Quota, self).__init__(metric_time)
        self.rw_servers = None
        self.filesystem = None
        self.block_hard_limit = None
        self.block_soft_limit = None
        self.block_usage = None
        self.inode_hard_limit = None
        self.inode_soft_limit = None
        self.inode_usage = None
        self.path = None

    @staticmethod
    def _get_attr_names():
        names = ("rw_servers", "filesystem", "block_hard_limit",
                 "block_soft_limit", "block_usage", "inode_hard_limit",
                 "inode_soft_limit", "inode_usage", "path")
        return names

    def parse(self, output):
        values = output.split("|")
        names = self._get_attr_names()

        for name, value in izip(names, values):
            setattr(self, name, value)

        if self.block_hard_limit == "NoLimit":
            self.block_hard_limit = "-1"

        if self.block_soft_limit == "NoLimit":
            self.block_soft_limit = "-1"

        if self.inode_hard_limit == "NoLimit":
            self.inode_hard_limit = "-1"

        if self.inode_soft_limit == "NoLimit":
            self.inode_soft_limit = "-1"


class UserGroupQuota(Quota):

    def __init__(self, filer, output, metric_time):
        """
        output => RWServers,FileSystem,BlockHardLimit,BlockSoftLimit,
                  BlockUsage,InodeHardLimit,InodeSoftLimit,InodeUsage,
                  Path,TreeQuotaID,Name,ID
        """

        super(UserGroupQuota, self).__init__(metric_time)
        self.tree_quota_id = None
        self.name = None
        self.id = None
        self._filer = filer
        self.parse(output)

    def _get_attr_names(self):
        names = []
        names.extend(super(UserGroupQuota, self)._get_attr_names())
        names.extend(("tree_quota_id", "name", "id"))
        return names

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, self._get_file_source())


class UserQuota(UserGroupQuota):

    def __init__(self, filer, output, metric_time):
        super(UserQuota, self).__init__(filer, output, metric_time)
        self.parse(output)

    @staticmethod
    def _get_file_source():
        return "vnx:file:userQuota"


class GroupQuota(UserGroupQuota):

    def __init__(self, filer, output, metric_time):
        super(GroupQuota, self).__init__(filer, output, metric_time)
        self.parse(output)

    @staticmethod
    def _get_file_source():
        return "vnx:file:groupQuota"


class TreeQuota(Quota):

    def __init__(self, filer, output, metric_time):
        super(TreeQuota, self).__init__(metric_time)
        self.id = None
        self._filer = filer
        self.parse(output)

    def _get_attr_names(self):
        names = []
        names.extend(super(TreeQuota, self)._get_attr_names())
        names.append("id")
        return names

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:treeQuota")


class CeppServer(StorageObject):

    def __init__(self, filer, server, output, metric_time):
        super(CeppServer, self).__init__(metric_time)
        self.server = server
        self.ip = None
        self.state = None
        self.cava_version = 'N/A'
        self.name = 'N/A'
        self._filer = filer
        self.parse(output)

    def parse(self, output):
        tag_values = output.split(",")
        for tag_value in tag_values:
            tag_value_pair = tag_value.split("=")
            if len(tag_value_pair) == 2:
                if tag_value_pair[0].strip() == "IP":
                    self.ip = tag_value_pair[1].strip()
                elif tag_value_pair[0].strip() == "state":
                    self.state = tag_value_pair[1].strip()
                elif tag_value_pair[0].strip() == "cava version":
                    self.cava_version = tag_value_pair[1].strip()
                elif tag_value_pair[0].strip() == "server name":
                    self.name = tag_value_pair[1].strip()

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:ceppServer")


class CepaPoolInfo(StorageObject):

    def __init__(self, filer, output, metric_time):
        super(CepaPoolInfo, self).__init__(metric_time)
        self.server = None
        self.req_timeout = None
        self.retry_timeout = None
        self.pre_events = None
        self.post_events = None
        self.post_err_events = None
        self._cepp_servers = []
        self._filer = filer
        self.parse(output)

    def parse(self, output):
        reg_strs = {
            "server": r'^\s*(.+)\s+:\s*$',
            "req_timeout": r'req_timeout\s+=\s*(.*)',
            "retry_timeout": r'retry_timeout\s+=\s*(.*)',
            "pre_events": r'pre_events\s+=\s*(.*)',
            "post_events": r'post_events\s+=\s*(.*)',
            "post_err_events": r'post_err_events\s+=\s*(.*)',
            "_cepp_servers": r'^\s*(IP\s+=.*)',
        }
        self._do_parse(output, reg_strs)

        servers = []
        for lin in self._cepp_servers:
            cepp_server = CeppServer(self._filer, self.server, lin,
                                     self._metric_time)
            if cepp_server.is_valid():
                servers.append(cepp_server)
            else:
                _LOGGER.warn("Ignore data from %s: %s", self._filer.ip, lin)
        self._cepp_servers = servers

    def to_string(self, timestamp, idx):
        pool_info = self._to_tag_value(timestamp, idx, "vnx:file:ceppPool")
        server_info = self.cepp_server_to_string(timestamp, idx)
        return "".join((pool_info, server_info))

    def cepp_server_to_string(self, timestamp, idx):
        return "".join((server.to_string(timestamp, idx)
                        for server in self._cepp_servers))


def _parse(storage_object, names, output):
    output = output.split("\n")
    pat = reco(r'^"\d+/\d+/\d+\s+\d+:\d+:\d+')
    for lin in output:
        if pat.search(lin):
            break
    else:
        return

    values = lin.split(",")
    if not values:
        return

    for name, value in izip(names, values[1:]):
        if value == '""':
            value = "0"
        setattr(storage_object, name, value.strip('"'))


class SystemBasicPerf(StorageObject):

    def __init__(self, filer, svr_name, output, metric_time):
        """
        time,cpu_util,network_in_kb,network_out_kb,dvol_read_kb,dvol_write_kb
        "2014/05/09 15:18:00","1","2683","678","144","2461"
        """
        super(SystemBasicPerf, self).__init__(metric_time)
        #self.timestamp = None
        self.cpu_util = None
        self.network_in_kb = None
        self.network_out_kb = None
        self.dvol_read_kb = None
        self.dvol_write_kb = None
        self.server_name = svr_name
        self._filer = filer
        self.parse(output)

    def parse(self, output):
        names = ("cpu_util", "network_in_kb", "network_out_kb",
                 "dvol_read_kb", "dvol_write_kb")
        _parse(self, names, output)

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:systemBasicPerf")


class SystemCachePerf(StorageObject):

    def __init__(self, filer, svr_name, output, metric_time):
        """
        time,dnlc_hit_ratio,of_cache_hit_ratio,buffer_cache_hit
        "2014/05/09 20:47:28","","100","98"
        """
        super(SystemCachePerf, self).__init__(metric_time)
        #self.timestamp = None
        self.dnlc_hit_ratio = None
        self.of_cache_hit_ratio = None
        self.buffer_cache_hit = None
        self.server_name = svr_name
        self._filer = filer
        self.parse(output)

    def parse(self, output):
        names = ("dnlc_hit_ratio", "of_cache_hit_ratio",
                 "buffer_cache_hit")
        _parse(self, names, output)

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:systemCachePerf")


class SystemCifsPerf(StorageObject):

    def __init__(self, filer, svr_name, output, metric_time):
        """
        time,cifs_total_ops,cifs_read_ops,cifs_read_kb,cifs_avg_read_size,
        cifs_write_ops,cifs_write_kb,cifs_avg_write_size,
        cifs_share_connections,cifs_open_files
        "2014/05/09 15:18:06","0","0","0","","0","0","","0","0"
        """
        super(SystemCifsPerf, self).__init__(metric_time)
        #self.timestamp = None
        self.cifs_total_ops = None
        self.cifs_read_ops = None
        self.cifs_read_kb = None
        self.cifs_avg_read_size = None
        self.cifs_write_ops = None
        self.cifs_write_kb = None
        self.cifs_avg_write_size = None
        self.cifs_share_connections = None
        self.cifs_open_files = None
        self.server_name = svr_name
        self._filer = filer
        self.parse(output)

    def parse(self, output):
        names = ("cifs_total_ops", "cifs_read_ops",
                 "cifs_read_kb", "cifs_avg_read_size", "cifs_write_ops",
                 "cifs_write_kb", "cifs_avg_write_size",
                 "cifs_share_connections", "cifs_open_files")
        _parse(self, names, output)

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:systemCifsPerf")


class SystemNfsPerf(StorageObject):

    def __init__(self, filer, svr_name, output, metric_time):
        """
        time,nfs_total_ops,nfs_read_ops,nfs_read_kb,nfs_avg_read_size,
        nfs_write_ops,nfs_write_kb,nfs_avg_write_size, nfs_active_threads
        "2014/05/09 22:49:29","506","136","8574","6455","371","10474","940","3"
        """
        super(SystemNfsPerf, self).__init__(metric_time)
        #self.timestamp = None
        self.nfs_total_ops = None
        self.nfs_read_ops = None
        self.nfs_read_kb = None
        self.nfs_avg_read_size = None
        self.nfs_write_ops = None
        self.nfs_write_kb = None
        self.nfs_avg_write_size = None
        self.nfs_active_threads = None
        self.server_name = svr_name
        self._filer = filer
        self.parse(output)

    def parse(self, output):
        names = ("nfs_total_ops", "nfs_read_ops", "nfs_read_kb",
                 "nfs_avg_read_size", "nfs_write_ops", "nfs_write_kb",
                 "nfs_avg_write_size", "nfs_active_threads")
        _parse(self, names, output)

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:systemNfsPerf")


class SystemCifsOpsPerf(StorageObject):

    def __init__(self, filer, svr_name, metric_time, cifs_operation, values):
        super(SystemCifsOpsPerf, self).__init__(metric_time)
        _strip_values(values)
        self.cifs_op_calls = values[0]
        self.cifs_min_usecs = values[1]
        self.cifs_max_usecs = values[2]
        self.cifs_avg_usecs = values[3]
        self.cifs_op_prct = values[4]
        self.cifs_operation = cifs_operation
        self.server_name = svr_name
        self._filer = filer

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:cifsOpsPerf")


class SystemNfsOpsPerf(StorageObject):

    def __init__(self, filer, svr_name, metric_time, nfs_operation, values):
        super(SystemNfsOpsPerf, self).__init__(metric_time)
        _strip_values(values)
        self.nfs_op_calls = values[0]
        self.nfs_op_error_diff = values[1]
        self.nfs_op_usecs = values[2]
        self.nfs_op_prct = values[3]
        self.nfs_operation = nfs_operation
        self.server_name = svr_name
        self._filer = filer

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:nfsOpsPerf")


def _strip_values(values):
    for i in range(len(values)):
        values[i] = values[i].strip('"')
        if not values[i] or values[i] == "-":
            values[i] = "0"


class SystemDiskVolumePerf(StorageObject):

    def __init__(self, filer, svr_name, metric_time, disk_name, values):
        """
        the metrics are per second, say read_kb is read_kb per second
        """
        super(SystemDiskVolumePerf, self).__init__(metric_time)
        _strip_values(values)
        self.totol_io_ops = values[0]
        self.queue_depth = values[1]
        self.read_ops = values[2]
        self.read_kb = values[3]
        self.avg_read_size_bytes = values[4]
        self.write_ops = values[5]
        self.write_kb = values[6]
        self.avg_write_size_bytes = values[7]
        self.util = values[8]
        self.io_retries_diff = values[9]
        self.avg_service_usecs = values[10]
        self.avg_usecs = values[11]
        self.disk_name = disk_name
        self.server_name = svr_name
        #self.timestamp = timestamp
        self._filer = filer

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:diskVolumePerf")


class SystemMetaVolumePerf(StorageObject):

    def __init__(self, filer, svr_name, metric_time, filesystem, values):
        super(SystemMetaVolumePerf, self).__init__(metric_time)
        _strip_values(values)
        self.read_requests = values[0]
        self.read_kb = values[1]
        self.avg_read_size_bytes = values[2]
        self.read_ops = values[3]
        self.read_ops_prct = values[4]
        self.write_requests = values[5]
        self.write_kb = values[6]
        self.avg_write_size_bytes = values[7]
        self.write_ops = values[8]
        self.write_ops_prct = values[9]
        self.filesystem = filesystem
        self.server_name = svr_name
        #self.timestamp = timestamp
        self._filer = filer

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:metaVolumePerf")


class SystemNetDevicePerf(StorageObject):

    def __init__(self, filer, svr_name, metric_time, dev_name, values):
        super(SystemNetDevicePerf, self).__init__(metric_time)
        _strip_values(values)
        self.network_in_pkts = values[0]
        self.network_in_errors_diff = values[1]
        self.network_in_kb = values[2]
        self.network_out_pkts = values[3]
        self.network_out_errors_diff = values[4]
        self.network_out_kb = values[5]
        self.dev_name = dev_name
        self.server_name = svr_name
        #self.timestamp = timestamp
        self._filer = filer

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx,
                                  "vnx:file:systemNetDevicePerf")


class CifsServerPerf(StorageObject):

    def __init__(self, filer, svr_name, metric_time, cifs_server, values):
        super(CifsServerPerf, self).__init__(metric_time)
        _strip_values(values)
        self.cifs_total_ops = values[0]
        self.cifs_read_ops = values[1]
        self.cifs_write_ops = values[2]
        self.cifs_suspicious_ops_diff = values[3]
        self.cifs_total_kb = values[4]
        self.cifs_read_kb = values[5]
        self.cifs_write_kb = values[6]
        self.cifs_avg_usecs = values[7]
        self.cifs_server = cifs_server
        self.server_name = svr_name
        self._filer = filer

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:cifsServerPerf")


class NfsExportPerf(StorageObject):

    def __init__(self, filer, svr_name, metric_time, nfs_export, values):
        super(NfsExportPerf, self).__init__(metric_time)
        _strip_values(values)
        self.nfs_total_ops = values[0]
        self.nfs_read_ops = values[1]
        self.nfs_write_ops = values[2]
        self.nfs_suspicious_ops_diff = values[3]
        self.nfs_total_kb = values[4]
        self.nfs_read_kb = values[5]
        self.nfs_write_kb = values[6]
        self.nfs_avg_usecs = values[7]
        self.nfs_export = nfs_export
        self.server_name = svr_name
        self._filer = filer

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:nfsExportPerf")


class CifsClientPerf(StorageObject):

    def __init__(self, filer, svr_name, metric_time, cifs_client, values):
        super(CifsClientPerf, self).__init__(metric_time)
        _strip_values(values)
        self.cifs_total_ops = values[0]
        self.cifs_read_ops = values[1]
        self.cifs_write_ops = values[2]
        self.cifs_suspicious_ops_diff = values[3]
        self.cifs_total_kb = values[4]
        self.cifs_read_kb = values[5]
        self.cifs_write_kb = values[6]
        self.cifs_avg_usecs = values[7]
        self.cifs_client = cifs_client
        self.server_name = svr_name
        self._filer = filer

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:cifsClientPerf")


class NfsClientPerf(StorageObject):

    def __init__(self, filer, svr_name, metric_time, nfs_client, values):
        super(NfsClientPerf, self).__init__(metric_time)
        _strip_values(values)
        self.nfs_total_ops = values[0]
        self.nfs_read_ops = values[1]
        self.nfs_write_ops = values[2]
        self.nfs_suspicious_ops_diff = values[3]
        self.nfs_total_kb = values[4]
        self.nfs_read_kb = values[5]
        self.nfs_write_kb = values[6]
        self.nfs_avg_usecs = values[7]
        self.nfs_client = nfs_client
        self.server_name = svr_name
        self._filer = filer

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:nfsClientPerf")


class CifsUserPerf(StorageObject):

    def __init__(self, filer, svr_name, metric_time, cifs_user, values):
        super(CifsUserPerf, self).__init__(metric_time)
        _strip_values(values)
        self.cifs_total_ops = values[0]
        self.cifs_read_ops = values[1]
        self.cifs_write_ops = values[2]
        self.cifs_suspicious_ops_diff = values[3]
        self.cifs_total_kb = values[4]
        self.cifs_read_kb = values[5]
        self.cifs_write_kb = values[6]
        self.cifs_avg_usecs = values[7]
        self.cifs_server = values[8]
        self.cifs_user = cifs_user
        self.server_name = svr_name
        self._filer = filer

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:cifsUserPerf")


class NfsUserPerf(StorageObject):

    def __init__(self, filer, svr_name, metric_time, nfs_user, values):
        super(NfsUserPerf, self).__init__(metric_time)
        _strip_values(values)
        self.nfs_total_ops = values[0]
        self.nfs_read_ops = values[1]
        self.nfs_write_ops = values[2]
        self.nfs_suspicious_ops_diff = values[3]
        self.nfs_total_kb = values[4]
        self.nfs_read_kb = values[5]
        self.nfs_write_kb = values[6]
        self.nfs_avg_usecs = values[7]
        self.nfs_user = nfs_user
        self.server_name = svr_name
        self._filer = filer

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:nfsUserPerf")


class NfsGroupPerf(StorageObject):

    def __init__(self, filer, svr_name, metric_time, nfs_group, values):
        super(NfsGroupPerf, self).__init__(metric_time)
        _strip_values(values)
        self.nfs_total_ops = values[0]
        self.nfs_read_ops = values[1]
        self.nfs_write_ops = values[2]
        self.nfs_suspicious_ops_diff = values[3]
        self.nfs_total_kb = values[4]
        self.nfs_read_kb = values[5]
        self.nfs_write_kb = values[6]
        self.nfs_avg_usecs = values[7]
        self.nfs_group = nfs_group
        self.server_name = svr_name
        self._filer = filer

    def to_string(self, timestamp, idx):
        return self._to_tag_value(timestamp, idx, "vnx:file:nfsGroupPerf")


def _parse_server_objects(filer, StorageClass, objs_info, metric_time):
    current_server = None
    server_objs = []
    for lin in objs_info:
        if not lin:
            continue
        if lin.endswith(" $#"):
            current_server = lin.rstrip(" $#").strip()
        else:
            obj = StorageClass(filer, "%s|%s" % (current_server, lin),
                               metric_time)
            if obj.is_valid():
                server_objs.append(obj)
            else:
                _LOGGER.warn("Ignore data from %s: %s",
                             filer.ip, "\n".join(objs_info))
    return server_objs


def parse_server_objects(filer, StorageClass, objs_info,
                         metric_time, use_computing_service=True):
    if use_computing_service:
        import data_loader
        loader = data_loader.GlobalDataLoader.get_data_loader(None, None, None)
        return loader.run_computing_job(_parse_server_objects,
                                        (filer, StorageClass, objs_info,
                                         metric_time))
    else:
        return _parse_server_objects(filer, StorageClass, objs_info,
                                     metric_time)


def _parse_export_objects(filer, export_info, metric_time):
    handling_cifs = False
    current_state = "start"
    current_server = None
    current_export = None
    current_netbios = ""
    current_options = ""
    exports = []

    def _create_export_object(server, export, netbios, options, metric_time):
        ex_info = "|".join((server, export + netbios, options.rstrip(",")))
        export = FileSystemExport(filer, ex_info, metric_time)
        if export.is_valid():
            exports.append(export)
        else:
            _LOGGER.debug("Ignore data from %s for FileSystemExport: %s",
                          filer.ip, ex_info)

    for lin in export_info:
        if lin.endswith(" $#"):
            if current_state == "handle_option":
                # this is the last export on the current server, save it
                _create_export_object(current_server, current_export,
                                      current_netbios, current_options,
                                      metric_time)
            current_server = lin.rstrip(" $#").strip()
            current_state = "handle_server"
        else:
            match = search(r'(\w+)\|.*\|.+\|', lin)
            if match:
                if current_state == "handle_option":
                    # this is a new export for the current server,
                    # save the previous one
                    _create_export_object(current_server, current_export,
                                          current_netbios, current_options,
                                          metric_time)
                current_export = lin
                current_netbios = ""
                current_options = ""
                if match.group(1) == "True":
                    handling_cifs = True
                else:
                    handling_cifs = False
                current_state = "handle_export"
            else:
                match = search(r'<OPTION>(.+)</OPTION>', lin)
                if match:
                    current_options = current_options + match.group(1) + ","
                    if handling_cifs:
                        match = search("netbios=(.+)", match.group(1))
                        if match:
                            current_netbios = match.group(1)
                    current_state = "handle_option"
    # the last export on the last server
    if current_state == "handle_option":
        _create_export_object(current_server, current_export,
                              current_netbios, current_options, metric_time)
    return exports


def parse_export_objects(filer, export_info, metric_time,
                         use_computing_service=True):
    if use_computing_service:
        import data_loader
        loader = data_loader.GlobalDataLoader.get_data_loader(None, None, None)
        return loader.run_computing_job(_parse_export_objects,
                                       (filer, export_info, metric_time))
    else:
        return _parse_export_objects(filer, export_info, metric_time)


def _parse_perf_objects(filer, svr_name, output, name_reg, step, StorageClass,
                        metric_time):
    pat = reco(r'^"(\d+/\d+/\d+\s+\d+:\d+:\d+)')
    head_line = None
    value_line = None
    perfs = []

    for lin in output.split("\n"):
        if lin.startswith('"Timestamp",'):
            head_line = lin
        elif head_line:
            match = pat.search(lin)
            if match:
                value_line = lin.strip()
                break

    if not head_line or not value_line:
        _LOGGER.debug("Ignore data from %s for %s: %s",
                      filer.ip, StorageClass.__name__, output)
        return perfs

    heads = head_line.split('","')
    values = value_line.split('","')
    name_pat = reco(name_reg)
    fields_cnt = len(heads)
    assert fields_cnt % step == 1
    if fields_cnt == len(values) and fields_cnt > step:
        for i, j in izip(range(1, fields_cnt, step),
                         range(step + 1, fields_cnt + step, step)):
            match = name_pat.search(heads[i])
            if not match:
                _LOGGER.warn("Didn't find a name, %s: %s",
                             heads[i], name_reg)
                continue
            perf = StorageClass(filer, svr_name, metric_time,
                                match.group(1), values[i:j])
            if perf.is_valid():
                perfs.append(perf)
            else:
                _LOGGER.debug("Ignore data from %s for %s: %s",
                              filer.ip, StorageClass.__name__, values[i:j])
    else:
        _LOGGER.debug("Ignore data from %s for %s: %s",
                      filer.ip, StorageClass.__name__, output)
    return perfs


def parse_perf_objects(filer, svr_name, output, name_reg, step, StorageClass,
                       metric_time, use_computing_service=True):
    if use_computing_service:
        import data_loader
        loader = data_loader.GlobalDataLoader.get_data_loader(None, None, None)
        return loader.run_computing_job(_parse_perf_objects, (filer, svr_name,
                                                          output, name_reg,
                                                          step, StorageClass,
                                                          metric_time))
    else:
        return _parse_perf_objects(filer, svr_name, output, name_reg,
                                   step, StorageClass, metric_time)


def _parse_cifsserver_objects(filer, cifsserver_info, metric_time):
    nas_server_line = None
    state = "start"
    cifs_servers = []
    section_info = []
    for lin in cifsserver_info:
        if state == "start":
            match = search(r'^\S+\s+:\s*$', lin)
            if match:
                nas_server_line = lin
                state = "server"
        elif state == "server":
            match = search(r'^\s*CIFS\s+Server\s+', lin)
            if match:
                section_info.append(nas_server_line)
                section_info.append(lin)
                state = "cifs_server"
            else:
                match = search(r'^\S+\s+:\s*$', lin)
                if match:
                    nas_server_line = lin
                    state = "server"
        elif state == "cifs_server":
            match = search(r'^\s*CIFS\s+Server\s+', lin)
            if match:
                cifs_server = CifsServer(filer, section_info, metric_time)
                if cifs_server.is_valid():
                    cifs_servers.append(cifs_server)
                else:
                    _LOGGER.debug("Ignore data from %s for %s : %s",
                                  "CifsServer", filer.ip,
                                  "\n".join(section_info))
                del section_info[:]
                section_info.append(nas_server_line)
                section_info.append(lin)
                state = "cifs_server"
            else:
                match = search(r'^\S+\s+:\s*$', lin)
                if match:
                    cifs_server = CifsServer(filer, section_info, metric_time)
                    if cifs_server.is_valid():
                        cifs_servers.append(cifs_server)
                    else:
                        _LOGGER.debug("Ignore data from %s for %s : %s",
                                      "CifsServer", filer.ip,
                                      "\n".join(section_info))
                    del section_info[:]
                    nas_server_line = lin
                    state = "server"
                else:
                    section_info.append(lin)

    if state == "cifs_server" and section_info:
        cifs_server = CifsServer(filer, section_info, metric_time)
        if cifs_server.is_valid():
            cifs_servers.append(cifs_server)
        else:
            _LOGGER.debug("Ignore data from %s for %s : %s",
                          "CifsServer", filer.ip, "\n".join(section_info))
    return cifs_servers


def parse_cifsserver_objects(filer, cifsserver_info, metric_time,
                             use_computing_service=True):
    if use_computing_service:
        import data_loader
        loader = data_loader.GlobalDataLoader.get_data_loader(None, None, None)
        return loader.run_computing_job(_parse_cifsserver_objects,
                                       (filer, cifsserver_info, metric_time))
    else:
        return _parse_cifsserver_objects(filer, cifsserver_info, metric_time)


def _parse_cepa_pool_objects(filer, cepa_info, metric_time):
    state = "begin"
    cepa_pools = []
    server_cepa_info = []
    for lin in cepa_info:
        if state == "begin":
            match = search(r'.+\s+:\s*$', lin)
            if match:
                server_cepa_info.append(lin)
                state = "server"
        elif state == "server":
            match = search(r'.+\s+:\s*$', lin)
            if match:
                cp = CepaPoolInfo(filer, server_cepa_info, metric_time)
                if cp.is_valid():
                    cepa_pools.append(cp)
                else:
                    _LOGGER.debug("Ignore data from %s for CepaPoolInfo: %s",
                                  filer.ip, "\n".join(server_cepa_info))
                del server_cepa_info[:]
            server_cepa_info.append(lin)

    if server_cepa_info:
        cp = CepaPoolInfo(filer, server_cepa_info, metric_time)
        if cp.is_valid():
            cepa_pools.append(cp)
        else:
            _LOGGER.debug("Ignore data from %s for CepaPoolInfo: %s",
                          filer.ip, "\n".join(server_cepa_info))
    return cepa_pools


def parse_cepa_pool_objects(filer, cepa_info, metric_time,
                            use_computing_service=True):
    if use_computing_service:
        import data_loader
        loader = data_loader.GlobalDataLoader.get_data_loader(None, None, None)
        return loader.run_computing_job(_parse_cepa_pool_objects,
                                        (filer, cepa_info, metric_time))
    else:
        return _parse_cepa_pool_objects(filer, cepa_info, metric_time)


def _create_file_objects(filer, output, StorageClass, metric_time):
    objs = []
    for lin in output:
        obj = StorageClass(filer, lin, metric_time)
        if obj.is_valid():
            objs.append(obj)
        else:
            _LOGGER.debug("Ignore data from %s for %s: %s",
                          lin, StorageClass.__name__, filer.ip)
    return objs


def create_file_objects(filer, output, StorageClass, metric_time,
                        use_computing_service=True):
    if use_computing_service:
        import data_loader
        loader = data_loader.GlobalDataLoader.get_data_loader(None, None, None)
        return loader.run_computing_job(_create_file_objects,
                                        (filer, output, StorageClass,
                                         metric_time))
    else:
        return _create_file_objects(filer, output, StorageClass, metric_time)
