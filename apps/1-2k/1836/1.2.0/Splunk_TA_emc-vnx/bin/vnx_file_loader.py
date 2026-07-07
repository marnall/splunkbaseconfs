from re import compile as reco
from re import search
import logging
import threading
import os
import os.path as op
import time

from timed_popen import timed_popen
import vnx_file_objects as vfo
import storage_object as so


__all__ = ['VnxFiler']

_LOGGER = logging.getLogger("ta_vnx")


class VnxFiler(so.StorageObject):
    NAS_XML = "/nas/bin/nas_xml "
    NAS_FS = "/nas/sbin/rootnas_fs "
    NAS_STORAGE = "/nas/bin/nas_storage "
    NAS_DISK = "/nas/sbin/rootnas_disk "
    NAS_SERVER = "/nas/bin/nas_server "
    NAS_POOL = "/nas/bin/nas_pool "
    SERVER_CIFS = "/nas/bin/server_cifs "
    SERVER_CEPP = "/nas/bin/server_cepp "

    CABINET_INFO = NAS_XML + "-info:"
    STORAGE_ARRAY = NAS_STORAGE + "-query:* -fields:serial -format:'%s,'"
    MOUNTED_UXFS = NAS_FS + ("-query:id=-11:InUse==y:type==uxfs:"
                             "IsTemporarilyUnmounted==False -fields:name,id,"
                             "rawcapacity,logicalcapacity,usedcapacity,maxsize"
                             ",virtuallyprovisioned,type,ROServers,RWServers"
                             " -format:'%s|%s|%s|%s|%s|%s|%s|%s|%L|%L\\n'")
    ROOT_FS = NAS_FS + ("-query:IsRoot==True:id=-1:id=+11 -fields:name,id,size,"
                        "maxsize,virtuallyprovisioned,type,ROServers,RWServers"
                        " -format:'%s|%s|%s|%s|%s|%s|%L|%L\\n'")
    UMOUNTED_UXFS = NAS_FS + ("-query:IsRoot==False:InUse==n:type==uxfs "
                              "-fields:name,id,size,maxsize,"
                              "virtuallyprovisioned,type,ROServers,RWServers"
                              " -format:'%s|%s|%s|%s|%s|%s|%L|%L\\n'")
    NMFS = NAS_FS + ("-query:InUse==y:type==nmfs -fields:name,id,size,maxsize,"
                     "virtuallyprovisioned,type,ROServers,RWServers "
                     "-format:'%s|%s|%s|%s|%s|%s|%L|%L\\n'")
    TEMP_UNMOUNTED_UXFS = NAS_FS + ("-query:IsRoot==False:InUse==y:"
                                    "IsTemporarilyUnmounted==True:type==uxfs "
                                    "-fields:name,id,size,maxsize,"
                                    "virtuallyprovisioned,type,ROServers,"
                                    "RWServers "
                                    "-format:'%s|%s|%s|%s|%s|%s|%L|%L\\n'")
    CKPT = NAS_FS + ("-query:InUse==y:type=ckpt -fields:name,id,size,"
                     "ckptpctused,ckptsavvolusedmb,vpfs,ROServers,RWServers,"
                     "cbackupof -format:'%s|%s|%s|%s|%s|%s|%L|%L|%q\\n' "
                     "-query:* -fields:id -format:'%s'")
    VPFS = NAS_FS + ("-query:type==vpfs -fields:name,id,size,ROServers,"
                     "RWServers -format:'%s|%s|%s|%L|%L\\n'")
    DISK = NAS_DISK + ("-query:* -fields:name,id,symmdev,size,symmid,protection "
                       "-format:'%s|%s|%s|%s|%s|%s\\n'")
    IFCONFIG = NAS_SERVER + ("-query:type=^vdm -fields:name,ifconfigtable "
                             "-format:'%s $#\\n%q' -query:* -fields:name,"
                             "address,device -format:'%s|%s|%s\\n'")
    MOUNT = NAS_SERVER + ("-query:* -fields:name,mounts -format:'%s $#\\n%q' "
                          "-query:* -fields:filesystem,filesystemid,path "
                          "-format:'%s|%s|%s\\n'")
    EXPORT = NAS_SERVER + ("-query:* -fields:name,exports -format:'%s $#\\n%q'"
                           " -query:* -fields:isshare,name,path,options "
                           "-format:'%s|%s|%s|\\n%s\\n'")
    SERVER = NAS_SERVER + ("-query:* -fields:name,id,type,version,rootfs,"
                           "physicalhost,status,statusactual "
                           "-format:'%s|%s|%s|%s|%s|%s|%s|%s\\n'")
    CIFS_HOST = NAS_SERVER + ("-query:* -fields:Name,CifsHosts "
                              "-format:'%s $#\\n%q' -query:* -fields:"
                              "ComputerName,Netbios,cifsDomain "
                              "-format:'%s|%s|%s\\n'")
    STORAGE_POOL = NAS_POOL + ("-query:+CapacityMB=-1:AvailableMB=-1:"
                               "PotentialMB=-1 -fields:name,id,CapacityMB,"
                               "AvailableMB,PotentialMB,usedMB "
                               "-format:'%s|%s|%s|%s|%s|%s\\n'")
    CIFS_SERVER = "%s ALL" % SERVER_CIFS
    USER_QUOTA = NAS_SERVER + ("-query:* -fields:UserQuotas -format:'%q' "
                               "-query:* -fields:RWServers,FileSystem,"
                               "BlockHardLimit,BlockSoftLimit,BlockUsage,"
                               "InodeHardLimit,InodeSoftLimit,InodeUsage,Path,"
                               "TreeQuotaID,Name,ID -format:"
                               "'%,L|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s\\n'")
    GROUP_QUOTA = NAS_SERVER + ("-query:* -fields:GroupQuotas -format:'%q' "
                                "-query:* -fields:RWServers,FileSystem,"
                                "BlockHardLimit,BlockSoftLimit,BlockUsage,"
                                "InodeHardLimit,InodeSoftLimit,InodeUsage,"
                                "Path,TreeQuotaID,Name,ID -format:"
                                "'%,L|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s\\n'")
    TREE_QUOTA = NAS_SERVER + ("-query:* -fields:TreeQuotas -format:'%q' "
                               "-query:* -fields:RWServers,FileSystem,"
                               "BlockHardLimit,BlockSoftLimit,BlockUsage,"
                               "InodeHardLimit,InodeSoftLimit,InodeUsage,"
                               "Path,ID "
                               "-format:'%,L|%s|%s|%s|%s|%s|%s|%s|%s|%s\\n'")
    CEPA_POOL = "%s ALL -pool -info" % SERVER_CEPP
    _log_template = "platform=Vnx File,ip=%s,cmd=%s,reason=%s"
    _this_dir = op.dirname(op.abspath(__file__))

    def __init__(self, ip, ip2, username, password, site=""):
        self.site = site
        self.ip = ip.strip()
        self._ip2 = ip2.strip()
        self._username = username
        self._password = password
        self.name = None
        self.hostname = None
        self.serial_no = None
        self.model = None
        self.version = None
        self.array_serial_no = None
        self._timed_out_count = 0

    @staticmethod
    def platform():
        return "VNX File"

    def is_alive(self):
        return self._timed_out_count < 3000

    def to_string(self, timestamp, idx):
        self._metric_time = time.time()
        self._filer = so.VnxProxy("serial_no", self.serial_no)
        nas_frame = self._to_tag_value(self._metric_time, idx,
                                       "vnx:file:nasframe")
        del self._filer
        return nas_frame

    def collect_perf_metrics(self):
        """
        every metrics collecting is a blocking call, each will take at least
        "interval" seconds (sampling time) to finish, so use this function
        with care, it may take a while to return
        returns: {
            "SystemBasicPerf": [SystemBasicPerf, ...]
            "SystemCachePerf": [SystemCachePerf, ...]
            "SystemCifsPerf": [SystemCifsPerf, ...]
            "SystemCifsOpsPerf": [SystemCifsOpsPerf, ...]
            "SystemNfsPerf": [SystemNfsPerf, ...]
            "SystemNfsOpsPerf": [SystemNfsOpsPerf, ...]
            "SystemDiskVolumePerf": [SystemDiskVolumeOpsPerf, ...]
            "SystemMetaVolumePerf": [SystemMetaVolumeOpsPerf, ...]
            "SystemNetDevicePerf": [SystemNetDevicePerf, ...]
            "CifsServerPerf": [CifsServerPerf, ...]
            "NfsExportPerf": [NfsExportClientPerf, ...]
            "CifsClientPerf": [CifsClientPerf, ...]
            "NfsClientPerf": [NfsClientPerf, ...]
            "NfsUserPerf": [NfsUserPerf, ...]
            "NfsGroupPerf": [NfsGroupPerf, ...]
            "CifsUserPerf": [CifsUserPerf, ...]
        }
        """

        perf_metrics = {}
        servers = self._get_servers()
        if not servers:
            return perf_metrics

        sys_perf = self.collect_system_perf_metrics(servers)
        cifs_perf = self.collect_all_cifs_perf_metrics(servers)
        nfs_perf = self.collect_all_nfs_perf_metrics(servers)

        perf_metrics.update(sys_perf)
        perf_metrics.update(cifs_perf)
        perf_metrics.update(nfs_perf)
        return perf_metrics

    def collect_system_perf_metrics(self, servers=None):
        """
        every metrics collecting is a blocking call, each will take at least
        interval seconds (sampling time) to finish, so use this function with
        care, it may take a while to return
        returns: {
            "SystemBasicPerf": [SystemBasicPerf, ...]
            "SystemCachePerf": [SystemCachePerf, ...]
            "SystemNetDevicePerf": [SystemNetDevicePerf, ...]
            "SystemDiskVolumePerf": [SystemDiskVolumeOpsPerf, ...]
            "SystemMetaVolumePerf": [SystemMetaVolumeOpsPerf, ...]
        }
        """

        perf_metrics = {}
        servers = self._get_servers()
        if not servers:
            return perf_metrics

        basic_perf = self.collect_basic_perf_metrics(servers)
        cache_perf = self.collect_cache_perf_metrics(servers)
        net_device_perf = self.collect_net_device_perf_metrics(servers)
        disk_vol_perf = self.collect_disk_volume_perf_metrics(servers)
        meta_vol_perf = self.collect_meta_volume_perf_metrics(servers)

        perf_metrics.update(basic_perf)
        perf_metrics.update(cache_perf)
        perf_metrics.update(net_device_perf)
        perf_metrics.update(disk_vol_perf)
        perf_metrics.update(meta_vol_perf)
        return perf_metrics

    def collect_all_nfs_perf_metrics(self, servers=None):
        """
        every metrics collecting is a blocking call, each will take at least
        "interval" seconds (sampling time) to finish, so use this function
        with care, it may take a while to return
        returns: {
            "SystemNfsPerf": [SystemNfsPerf, ...]
            "SystemNfsOpsPerf": [SystemNfsOpsPerf, ...]
            "NfsExportPerf": [NfsExportClientPerf, ...]
            "NfsClientPerf": [NfsClientPerf, ...]
            "NfsUserPerf": [NfsUserPerf, ...]
            "NfsGroupPerf": [NfsGroupPerf, ...]
        }
        """

        perf_metrics = {}
        servers = self._get_servers()
        if not servers:
            return perf_metrics

        nfs_perf = self.collect_nfs_perf_metrics(servers)
        nfs_ops_perf = self.collect_nfs_ops_perf_metrics(servers)
        nfs_export_perf = self.collect_nfs_export_perf_metrics(servers)
        nfs_client_perf = self.collect_nfs_client_perf_metrics(servers)
        nfs_user_perf = self.collect_nfs_user_perf_metrics(servers)
        nfs_group_perf = self.collect_nfs_group_perf_metrics(servers)

        perf_metrics.update(nfs_perf)
        perf_metrics.update(nfs_ops_perf)
        perf_metrics.update(nfs_export_perf)
        perf_metrics.update(nfs_client_perf)
        perf_metrics.update(nfs_user_perf)
        perf_metrics.update(nfs_group_perf)
        return perf_metrics

    def collect_all_cifs_perf_metrics(self, servers=None):
        """
        every metrics collecting is a blocking call, each will take at least
        "interval" seconds (sampling time) to finish, so use this function
        with care, it may take a while to return
        returns: {
            "SystemCifsPerf": [SystemCifsPerf, ...]
            "SystemCifsOpsPerf": [SystemCifsOpsPerf, ...]
            "CifsServerPerf": [CifsServerPerf, ...]
            "CifsClientPerf": [CifsClientPerf, ...]
            "CifsUserPerf": [CifsUserPerf, ...]
        }
        """

        perf_metrics = {}
        servers = self._get_servers()
        if not servers:
            return perf_metrics

        cifs_perf = self.collect_cifs_perf_metrics(servers)
        cifs_ops_perf = self.collect_cifs_ops_perf_metrics(servers)
        cifs_server_perf = self.collect_cifs_server_perf_metrics(servers)
        cifs_client_perf = self.collect_cifs_client_perf_metrics(servers)
        cifs_user_perf = self.collect_cifs_user_perf_metrics(servers)

        perf_metrics.update(cifs_perf)
        perf_metrics.update(cifs_ops_perf)
        perf_metrics.update(cifs_server_perf)
        perf_metrics.update(cifs_client_perf)
        perf_metrics.update(cifs_user_perf)
        return perf_metrics

    def collect_basic_perf_metrics(self, servers, interval=2):
        _LOGGER.info("start collect basic_perf for %s", self.ip)
        basic_perf = self._do_collect_perf_metrics("basic-std",
                                                   interval, servers,
                                                   vfo.SystemBasicPerf)
        _LOGGER.info("end collect basic_perf for %s", self.ip)
        return {"SystemBasicPerf": basic_perf}

    def collect_cache_perf_metrics(self, servers, interval=2):
        _LOGGER.info("start collect cache_perf for %s", self.ip)
        cache_perf = self._do_collect_perf_metrics("caches-std",
                                                   interval, servers,
                                                   vfo.SystemCachePerf)
        _LOGGER.info("end collect cache_perf for %s", self.ip)
        return {"SystemCachePerf": cache_perf}

    def collect_cifs_perf_metrics(self, servers, interval=2):
        _LOGGER.info("start cifs_perf for %s", self.ip)
        cifs_perf = self._do_collect_perf_metrics("cifs-std",
                                                  interval, servers,
                                                  vfo.SystemCifsPerf)
        _LOGGER.info("end cifs_perf for %s", self.ip)
        return {"SystemCifsPerf": cifs_perf}

    def collect_cifs_ops_perf_metrics(self, servers, interval=2):
        _LOGGER.info("start cifs_ops_perf %s", self.ip)
        ops = self._do_collect_perf_metrics("cifsOps-std",
                                            interval, servers,
                                            self._handle_cifs_ops_perf)
        _LOGGER.info("end cifs_ops_perf for %s", self.ip)
        return {"SystemCifsOpsPerf": ops}

    def collect_nfs_ops_perf_metrics(self, servers, interval=2):
        _LOGGER.info("start nfs_ops_perf for %s", self.ip)
        ops = self._do_collect_perf_metrics("nfsOps-std",
                                            interval, servers,
                                            self._handle_nfs_ops_perf)
        _LOGGER.info("end nfs_ops_perf for %s", self.ip)
        return {"SystemNfsOpsPerf": ops}

    def collect_nfs_perf_metrics(self, servers, interval=2):
        _LOGGER.info("start nfs_perf for %s", self.ip)
        nfs_perf = self._do_collect_perf_metrics("nfs-std",
                                                 interval, servers,
                                                 vfo.SystemNfsPerf)
        _LOGGER.info("end nfs_perf for %s", self.ip)
        return {"SystemNfsPerf": nfs_perf}

    def collect_disk_volume_perf_metrics(self, servers, interval=2):
        _LOGGER.info("start disk_vol_perf for %s", self.ip)
        vol = self._do_collect_perf_metrics("diskVolumes-std",
                                            interval, servers,
                                            self._handle_disk_vol_perf)
        _LOGGER.info("end disk_vol_perf for %s", self.ip)
        return {"SystemDiskVolumePerf": vol}

    def collect_meta_volume_perf_metrics(self, servers, interval=2):
        _LOGGER.info("start meta_vol_perf for %s", self.ip)
        vol = self._do_collect_perf_metrics("metaVolumes-std",
                                            interval, servers,
                                            self._handle_meta_vol_perf)
        _LOGGER.info("end meta_vol_perf for %s", self.ip)
        return {"SystemMetaVolumePerf": vol}

    def collect_net_device_perf_metrics(self, servers, interval=2):
        _LOGGER.info("start net_device_perf for %s", self.ip)
        device = self._do_collect_perf_metrics("netDevices-std",
                                               interval, servers,
                                               self._handle_net_device_perf)
        _LOGGER.info("end net_device_perf for %s", self.ip)
        return {"SystemNetDevicePerf": device}

    def collect_nfs_export_perf_metrics(self, servers, interval=2):
        _LOGGER.info("start nfs_export_perf for %s", self.ip)
        nfs = self._do_collect_perf_metrics("nfs.export",
                                            interval, servers,
                                            self._handle_nfs_export_perf)
        _LOGGER.info("end nfs_export_perf for %s", self.ip)
        return {"NfsExportPerf": nfs}

    def collect_cifs_server_perf_metrics(self, servers, interval=2):
        _LOGGER.info("start cifs_server_perf for %s", self.ip)
        cifs = self._do_collect_perf_metrics("cifs.server",
                                             interval, servers,
                                             self._handle_cifs_server_perf)
        _LOGGER.info("end cifs_server_perf for %s", self.ip)
        return {"CifsServerPerf": cifs}

    def collect_cifs_client_perf_metrics(self, servers, interval=2):
        _LOGGER.info("start cifs_client_perf for %s", self.ip)
        cifs = self._do_collect_perf_metrics("cifs.client",
                                             interval, servers,
                                             self._handle_cifs_client_perf)
        _LOGGER.info("end cifs_client_perf for %s", self.ip)
        return {"CifsClientPerf": cifs}

    def collect_cifs_user_perf_metrics(self, servers, interval=2):
        _LOGGER.info("start cifs_user_perf for %s", self.ip)
        cifs = self._do_collect_perf_metrics("cifs.user",
                                             interval, servers,
                                             self._handle_cifs_user_perf)
        _LOGGER.info("end cifs_user_perf for %s", self.ip)
        return {"CifsUserPerf": cifs}

    def collect_nfs_client_perf_metrics(self, servers, interval=2):
        _LOGGER.info("start nfs_client_perf for %s", self.ip)
        nfs = self._do_collect_perf_metrics("nfs.client",
                                            interval, servers,
                                            self._handle_nfs_client_perf)
        _LOGGER.info("end nfs_client_perf for %s", self.ip)
        return {"NfsClientPerf": nfs}

    def collect_nfs_user_perf_metrics(self, servers, interval=2):
        _LOGGER.info("start nfs_user_perf %s", self.ip)
        nfs = self._do_collect_perf_metrics("nfs.user",
                                            interval, servers,
                                            self._handle_nfs_user_perf)
        _LOGGER.info("end nfs_user_perf for %s", self.ip)
        return {"NfsUserPerf": nfs}

    def collect_nfs_group_perf_metrics(self, servers, interval=2):
        _LOGGER.info("start nfs_group_perf for %s", self.ip)
        nfs = self._do_collect_perf_metrics("nfs.group",
                                            interval, servers,
                                            self._handle_nfs_group_perf)
        _LOGGER.info("end nfs_group_perf for %s", self.ip)
        return {"NfsGroupPerf": nfs}

    def _do_collect_perf_metrics(self, cmd, interval, servers, handler):
        if not servers:
            return {}
        else:
            svrs = (svr.name for svr in servers
                    if svr.type == "nas" and svr.status == "enabled" and
                       svr.statusactual in ("online, active", "online, ready"))

        template = ("export NAS_DB=/nas; /nas/bin/server_stats %s -monitor %s "
                    "-interval %s -count 1 -format csv -terminationsummary no")
        perf_metrics = []
        timed_out = 0
        for svr in svrs:
            for ip in (self.ip, self._ip2):
                if ip:
                    cli = template % (svr, cmd, interval)
                    ssh_cmd = self._get_ssh_cmd()
                    cli = ssh_cmd + ["%s@%s" % (self._username, ip), cli]
                    begin = time.time()
                    output = timed_popen(cli, interval + 10)
                    if self._timed_out(output, ip, cmd):
                        timed_out += 1
                        continue

                    self._dump(cli, output[0])
                    self._timed_out_count = 0
                    metric_time = begin + (time.time() - begin) / 2
                    perf = handler(self, svr, output[0], metric_time)
                    if isinstance(perf, list):
                        perf_metrics.extend(perf)
                    elif perf.is_valid():
                        perf_metrics.append(perf)

                    if not perf_metrics:
                        _LOGGER.info("Get no result for %s from %s %s",
                                     cmd, svr, ip)
                        _LOGGER.debug("Ingore data from %s %s for %s: %s",
                                      svr, ip, cmd, output[0])
                    # if not timed out, break always
                    break

            if timed_out == 1 and self.ip and self._ip2:
                timed_out = 0
                self.ip, self._ip2 = self._ip2, self.ip
                _LOGGER.warn("Swapping primary and secondary %s <-> %s",
                             self.ip, self._ip2)
        return perf_metrics

    def collect_inventory_info(self):
        """
        returns: {
            "NasFrame": [VnxFiler],
            "FileSystem": [FileSystem,...],,
            "Checkpoint": [Checkpoint,...],,
            "Vpfs": [Vpfs,...],,
            "Disk": [Disk,...],
            "Interface": [Interface,...],
            "FileSystemMount": [FileSystemMount,...],
            "FileSystemExport": [FilesystemExport,...],
            "Cifshost": [Cifshost,...],
            "NasServer": [NasServer,...],
            "StoragePool": [StoragePool,...],
            "CifsServer": [CifsServer,...],
            "UserQuota": [UserQuota,...],
            "GroupQuota": [GroupQuota,...],
            "TreeQuota": [TreeQuota,...],
            "CepaPool": [CepaPool,...],
        },
        """
        batch_cmd = self._get_inventory_batch_cmd()
        cmd_handlers = {
            "MOUNTED_UXFS": self._init_fs_info,
            "ROOT_FS": self._init_fs_info,
            "UMOUNTED_UXFS": self._init_fs_info,
            "NMFS": self._init_fs_info,
            "TEMP_UNMOUNTED_UXFS": self._init_fs_info,
            "CKPT": self._init_ckpt_info,
            "VPFS": self._init_vpfs_info,
            "DISK": self._init_disk_info,
            "IFCONFIG": self._init_ifconfig_info,
            "MOUNT": self._init_mount_info,
            "EXPORT": self._init_export_info,
            "CIFS_HOST": self._init_cifshost_info,
            "SERVER": self._init_server_info,
            "NAS_POOL": self._init_nas_pool,
            "CIFS_SERVER": self._init_cifsserver_info,
            "USER_QUOTA": self._init_userquota_info,
            "GROUP_QUOTA": self._init_groupquota_info,
            "TREE_QUOTA": self._init_treequota_info,
            "CEPA_POOL": self._init_cepa_pool_info,
        }
        self._get_system_info(True)
        if not self.is_valid():
            return {}

        _LOGGER.info("start inventory for %s", self.ip)
        for ip in (self.ip, self._ip2):
            if ip:
                res = self._do_collect(ip, batch_cmd, cmd_handlers, 2400)
                for objname in ("FileSystem", "Disk", "NasServer"):
                    if not res.get(objname, None):
                        _LOGGER.error(self._log_template,
                                ip, "nas_cmd", "missing_inventories")
                        break
                else:
                    res["NasFrame"] = [self]
                    _LOGGER.info("end inventory for %s", self.ip)
                    return res
        return {}

    @staticmethod
    def _handle_net_device_perf(filer, svr_name, output, metric_time):
        name_reg = r"device\s+(.+)\s+Network"
        return vfo.parse_perf_objects(filer, svr_name, output, name_reg,
                                      6, vfo.SystemNetDevicePerf, metric_time)

    @staticmethod
    def _handle_disk_vol_perf(filer, svr_name, output, metric_time):
        name_reg = r"dVol\s+([^\s]+)"
        return vfo.parse_perf_objects(filer, svr_name, output, name_reg,
                                      12, vfo.SystemDiskVolumePerf,
                                      metric_time)

    @staticmethod
    def _handle_meta_vol_perf(filer, svr_name, output, metric_time):
        name_reg = r"MetaVol\s+([^\s]+)"
        return vfo.parse_perf_objects(filer, svr_name, output, name_reg,
                                      10, vfo.SystemMetaVolumePerf,
                                      metric_time)

    @staticmethod
    def _handle_cifs_ops_perf(filer, svr_name, output, metric_time):
        name_reg = r"SMB Operation\s+([^\s]+)"
        return vfo.parse_perf_objects(filer, svr_name, output, name_reg,
                                      5, vfo.SystemCifsOpsPerf, metric_time)

    @staticmethod
    def _handle_nfs_ops_perf(filer, svr_name, output, metric_time):
        name_reg = r"NFS Op\s+([^\s]+)"
        return vfo.parse_perf_objects(filer, svr_name, output, name_reg,
                                      4, vfo.SystemNfsOpsPerf, metric_time)

    @staticmethod
    def _handle_cifs_server_perf(filer, svr_name, output, metric_time):
        name_reg = r"CIFS\s+([^\s]+)"
        return vfo.parse_perf_objects(filer, svr_name, output, name_reg,
                                      8, vfo.CifsServerPerf, metric_time)

    @staticmethod
    def _handle_nfs_export_perf(filer, svr_name, output, metric_time):
        name_reg = r"NFS Export\s+([^\s]+)"
        return vfo.parse_perf_objects(filer, svr_name, output, name_reg,
                                      8, vfo.NfsExportPerf, metric_time)

    @staticmethod
    def _handle_cifs_client_perf(filer, svr_name, output, metric_time):
        name_reg = r"Client id=([^\s]+)"
        return vfo.parse_perf_objects(filer, svr_name, output, name_reg,
                                      8, vfo.CifsClientPerf, metric_time)

    @staticmethod
    def _handle_cifs_user_perf(filer, svr_name, output, metric_time):
        name_reg = r"CIFS User id=([^\s]+)"
        return vfo.parse_perf_objects(filer, svr_name, output, name_reg,
                                      8, vfo.CifsUserPerf, metric_time)

    @staticmethod
    def _handle_nfs_client_perf(filer, svr_name, output, metric_time):
        name_reg = r"Client id=([^\s]+)"
        return vfo.parse_perf_objects(filer, svr_name, output, name_reg,
                                      8, vfo.NfsClientPerf, metric_time)

    @staticmethod
    def _handle_nfs_user_perf(filer, svr_name, output, metric_time):
        name_reg = r"NFS User id=([^\s]+)"
        return vfo.parse_perf_objects(filer, svr_name, output, name_reg,
                                      8, vfo.NfsUserPerf, metric_time)

    @staticmethod
    def _handle_nfs_group_perf(filer, svr_name, output, metric_time):
        name_reg = r"NFS Group id=([^\s]+)"
        return vfo.parse_perf_objects(filer, svr_name, output, name_reg,
                                      8, vfo.NfsGroupPerf, metric_time)

    def _check_failover(self, ip):
        if ip == self._ip2 and self.ip != self._ip2:
            self.ip, self._ip2 = self._ip2, self.ip
            _LOGGER.info("CS: %s takes over", ip)

    def _get_server_info(self):
        cmd = ("export NAS_DB=/nas;"
               'echo "<<SERVER>>"; %s; echo "<</SERVER>>"; ' % self.SERVER)
        cmd_handlers = {
            "SERVER": self._init_server_info,
        }

        for ip in (self.ip, self._ip2):
            if ip:
                res = self._do_collect(ip, cmd, cmd_handlers)
                if res.get("NasServer", None):
                    self._check_failover(ip)
                    return res["NasServer"]
        return None

    def _get_system_info(self, force_refresh=False):
        if not force_refresh and self.is_valid():
            return

        batch_cmd = (
            "export NAS_DB=/nas;"
            'echo "<<CABINET_INFO>>"; %s; echo "<</CABINET_INFO>>";' % self.CABINET_INFO,
            'echo "<<STORAGE_ARRAY>>"; %s; echo ""; echo "<</STORAGE_ARRAY>>";' % self.STORAGE_ARRAY)
        batch_cmd = "".join(batch_cmd)
        cmd_handlers = {
            "CABINET_INFO": self._init_cabinet_info,
            "STORAGE_ARRAY": self._init_array_info,
        }

        for ip in (self.ip, self._ip2):
            if ip:
                res = self._do_collect(ip, batch_cmd, cmd_handlers)
                if self.is_valid():
                    self._check_failover(ip)
                    break
                elif res and not self.is_valid():
                    _LOGGER.error(self._log_template, ip, "get_system_info",
                                  "missing_system_info")

    def _get_servers(self):
        self._get_system_info()
        if not self.is_valid():
            return None

        servers = self._get_server_info()
        if not servers:
            _LOGGER.warn("Servers info is not available for %s, ignore",
                         self.ip)
            return None
        return servers

    def _get_inventory_batch_cmd(self):
        batch_cmd = ("export NAS_DB=/nas; ",
            'echo "<<MOUNTED_UXFS>>"; %s; echo "<</MOUNTED_UXFS>>"; ' % self.MOUNTED_UXFS,
            'echo "<<ROOT_FS>>"; %s; echo "<</ROOT_FS>>"; ' % self.ROOT_FS,
            'echo "<<UMOUNTED_UXFS>>"; %s; echo "<</UMOUNTED_UXFS>>"; ' % self.UMOUNTED_UXFS,
            'echo "<<NMFS>>"; %s; echo "<</NMFS>>"; ' % self.NMFS,
            'echo "<<TEMP_UNMOUNTED_UXFS>>"; %s; echo "<</TEMP_UNMOUNTED_UXFS>>"; ' % self.TEMP_UNMOUNTED_UXFS,
            'echo "<<CKPT>>"; %s; echo "<</CKPT>>"; ' % self.CKPT,
            'echo "<<VPFS>>"; %s; echo "<</VPFS>>"; ' % self.VPFS,
            'echo "<<DISK>>"; %s; echo "<</DISK>>"; ' % self.DISK,
            'echo "<<IFCONFIG>>"; %s; echo "<</IFCONFIG>>"; ' % self.IFCONFIG,
            'echo "<<MOUNT>>"; %s; echo "<</MOUNT>>"; ' % self.MOUNT,
            'echo "<<EXPORT>>"; %s; echo "<</EXPORT>>"; ' % self.EXPORT,
            'echo "<<CIFS_HOST>>"; %s ; echo "<</CIFS_HOST>>"; ' % self.CIFS_HOST,
            'echo "<<SERVER>>"; %s; echo "<</SERVER>>"; ' % self.SERVER,
            'echo "<<NAS_POOL>>"; %s; echo "<</NAS_POOL>>"; ' % self.STORAGE_POOL,
            'echo "<<CIFS_SERVER>>"; %s; echo "<</CIFS_SERVER>>"; ' % self.CIFS_SERVER,
            'echo "<<USER_QUOTA>>"; %s; echo "<</USER_QUOTA>>"; ' % self.USER_QUOTA,
            'echo "<<GROUP_QUOTA>>"; %s; echo "<</GROUP_QUOTA>>"; ' % self.GROUP_QUOTA,
            'echo "<<TREE_QUOTA>>"; %s; echo "<</TREE_QUOTA>>"; ' % self.TREE_QUOTA,
            'echo "<<CEPA_POOL>>"; %s; echo "<</CEPA_POOL>>"; ' % self.CEPA_POOL)
        batch_cmd = "".join(batch_cmd)
        return batch_cmd

    def _timed_out(self, output, ip, cmd):
        if output[1] and len(output[1]) < 200 and output[1].strip():
            _LOGGER.error(self._log_template, ip, cmd, output[1])

        if output[-1] and not output[0]:
            self._timed_out_count += 1
            _LOGGER.error(self._log_template, ip, cmd, "timed_out")
            return True
        return False

    def _do_collect(self, ip, batch_cmd, handlers, timeout=20):
        res = {}
        start_pat = reco(r'<<(\w+)>>')
        end_pat = reco(r'<</(\w+)>>')
        ssh_cmd = self._get_ssh_cmd()
        cmd = ssh_cmd + ["%s@%s" % (self._username, ip), batch_cmd]
        begin = time.time()
        output = timed_popen(cmd, timeout + 10)
        if self._timed_out(output, ip, batch_cmd):
            return res

        self._timed_out_count = 0
        metric_time = begin + (time.time() - begin) / 2
        current_cmd = None
        cmd_output = []
        for lin in output[0].split("\n"):
            lin = lin.rstrip()
            m = end_pat.search(lin)
            if m:
                if current_cmd and cmd_output:
                    if current_cmd in handlers:
                        (objname, objs) = handlers[current_cmd](cmd_output,
                                                                metric_time)
                        res.setdefault(objname, []).extend(objs)
                    else:
                        _LOGGER.warn("I don't understand this cmd: %s",
                                     current_cmd)
                del cmd_output[:]
                current_cmd = None
                continue

            m = start_pat.search(lin)
            if m:
                current_cmd = m.group(1)
                continue

            if current_cmd:
                cmd_output.append(lin)
        self._dump(batch_cmd, output[0])
        return res

    def _init_cabinet_info(self, cab_info, metric_time=None):
        for lin in cab_info:
            if self.name is None:
                m = search(r'CELERRA_CABINET\s+NAME=\'(.+?)\'\s+', lin)
                if m:
                    self.name = m.group(1)

            if self.model is None:
                m = search(r'PRODUCT_NAME=\'(.+?)\'\s+', lin)
                if m:
                    self.model = m.group(1)

            if self.serial_no is None:
                m = search(r'SERIAL_NO=\'(.+?)\'', lin)
                if m:
                    self.serial_no = m.group(1)

            if self.hostname is None:
                m = search(r'CONTROL_STATION\s+HOSTNAME=\'(.+?)\'', lin)
                if m:
                    self.hostname = m.group(1)

            if self.version is None:
                m = search(r'VERSION=\'(.+?)\'', lin)
                if m:
                    self.version = m.group(1)
        return ("NasFrame", ())

    def _init_array_info(self, array_info, metric_time=None):
        self.array_serial_no = array_info[0].strip(r',')
        return ("NasFrame", ())

    def _init_fs_info(self, output, metric_time):
        return ("FileSystem", vfo.create_file_objects(self, output,
                                                      vfo.FileSystem,
                                                      metric_time))

    def _init_ckpt_info(self, output, metric_time):
        return ("Checkpoint", vfo.create_file_objects(self, output,
                                                      vfo.Checkpoint,
                                                      metric_time))

    def _init_vpfs_info(self, output, metric_time):
        return ("Vpfs", vfo.create_file_objects(self, output, vfo.Vpfs,
                                                metric_time))

    def _init_disk_info(self, output, metric_time):
        return ("Disk", vfo.create_file_objects(self, output, vfo.Disk,
                                                metric_time))

    def _init_ifconfig_info(self, output, metric_time):
        ifs = vfo.parse_server_objects(self, vfo.Interface, output,
                                       metric_time)
        return ("Interface", ifs)

    def _init_mount_info(self, output, metric_time):
        mounts = vfo.parse_server_objects(self, vfo.FileSystemMount, output,
                                          metric_time)
        return ("FileSystemMount", mounts)

    def _init_cifshost_info(self, output, metric_time):
        cifs_hosts = vfo.parse_server_objects(self, vfo.CifsHost, output,
                                              metric_time)
        return ("CifsHost", cifs_hosts)

    def _init_server_info(self, output, metric_time):
        nas_servers = vfo.create_file_objects(self, output,
                                              vfo.NasServer,
                                              metric_time, False)
        return ("NasServer", nas_servers)

    def _init_nas_pool(self, output, metric_time):
        return ("StoragePool", vfo.create_file_objects(self, output,
                                                       vfo.StoragePool,
                                                       metric_time))

    def _init_userquota_info(self, output, metric_time):
        return ("UserQuota", vfo.create_file_objects(self, output,
                                                     vfo.UserQuota,
                                                     metric_time))

    def _init_groupquota_info(self, output, metric_time):
        return ("GroupQuota", vfo.create_file_objects(self, output,
                                                      vfo.GroupQuota,
                                                      metric_time))

    def _init_treequota_info(self, output, metric_time):
        return ("TreeQuota", vfo.create_file_objects(self, output,
                                                     vfo.TreeQuota,
                                                     metric_time))

    def _init_cifsserver_info(self, cifsserver_info, metric_time):
        cifs_servers = vfo.parse_cifsserver_objects(self, cifsserver_info,
                                                    metric_time)
        return ("CifsServer", cifs_servers)

    def _init_export_info(self, export_info, metric_time):
        exports = vfo.parse_export_objects(self, export_info, metric_time)
        return ("FileSystemExport", exports)

    def _init_cepa_pool_info(self, cepa_info, metric_time):
        cepa_pools = vfo.parse_cepa_pool_objects(self, cepa_info, metric_time)
        return ("CepaPool", cepa_pools)

    def _get_ssh_cmd(self):
        if os.name == "nt":
            local_dir = op.join(op.dirname(self._this_dir), "local")
            return ["plink.exe", "-i", op.join(local_dir, "id_rsa.ppk")]
        else:
            return ["ssh"]

    def _dump(self, cli, output):
        if _LOGGER.level == logging.DEBUG:
            model = self.model if self.model is not None else ""
            version = self.version if self.version is not None else ""
            model = model.replace(" ", "_")
            file_name = "_".join(("vnx_file", model, version,
                                  str(threading.current_thread().ident)))
            file_name = op.join(self._this_dir, file_name)
            with open(file_name, "a") as f:
                f.write("\n***%s %s %s\n%s\n" % (time.ctime(), self.ip,
                                                 cli, output))
