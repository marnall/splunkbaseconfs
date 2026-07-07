import os
import sys
import shutil
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lib")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bin", "qianxin_ti")))

from pathlib import Path
from bin.qianxin_ti.common_lib_entry import rtoml, pysnooper
from bin.qianxin_ti.common_log import logger
from bin.qianxin_ti.common_util import QianxinConfHelper, Utils
from bin.qianxin_ti.common_kvstore_helper import SplunkKvstoreHelper
from bin.qianxin_ti.common_constants import (
    CFG_SYNC_KVSTORE,
    LOG_DETECTION_STATISTICS_DATA_FILE,
    QAX_CONF_PATH,
    CLUSTER_SPLUNK_CONFIG,
)
from splunklib.binding import HTTPError, AuthenticationError

logger.info("Sync splunk cluster")


def run():
    cfg_sync(LOG_DETECTION_STATISTICS_DATA_FILE, "QAX_statistics")
    cfg_sync(QAX_CONF_PATH, "QAX_conf")


def cfg_sync(cfg_toml_file: str, cfg_name: str, force_push=False):
    service = get_service_special()
    kv_conn = SplunkKvstoreHelper(CFG_SYNC_KVSTORE, custom_service=service)
    kv_conn.create_kv_if_not_exist(CFG_SYNC_KVSTORE)

    # 获取云端数据和时间，以及本地数据和时间。
    try:
        remote = kv_conn.query_by_id(cfg_name)
        if remote:
            r_ts = remote.get("sync_update", 0)
    except AuthenticationError:
        logger.error("Not logged in. Stop sync progress.")
        return
    except HTTPError:
        # 当云端数据不存在时，设置比较位为-1，即可自动更新
        r_ts = -1
    local, local_ts = get_local_current_config_file(cfg_toml_file)
    if force_push:
        Utils.update_toml_data_file(remote, cfg_toml_file, during_sync=True)
        logger.info(f"use force push mode.push result")
        return
    if int(r_ts) < int(local_ts):
        if local:
            local.update({"_key": cfg_name})
            kv_conn.insert(local)
            # 这样是因为如果key存在就不能insert，但是不会抛异常。再执行一次更新就可以了。
            kv_conn.update(cfg_name, local)
            logger.info(f"Local cfg of {cfg_name} is newer, updated to kvstore.")
    elif int(r_ts) > int(local_ts):
        Utils.update_toml_data_file(remote, cfg_toml_file, during_sync=True)
        logger.info(f"Local cfg of {cfg_name} is older, use kvstore to update local cfg.")
    else:
        logger.info(f"No need to update {cfg_name}")
    return


def get_service_special():
    # 当连接服务器失败时，尝试使用集群化存储的连接信息来进行访问
    try:
        if not Path.exists(CLUSTER_SPLUNK_CONFIG):
            return QianxinConfHelper.get_splunk_service()
        else:
            load_auth_string(CLUSTER_SPLUNK_CONFIG)
            return QianxinConfHelper.get_splunk_service()
    except shutil.SameFileError:
        logger.error(f"Please check cluster config, it might be wrong. The local config is already cluster config.")
    except:
        logger.error(f"Failed to use cluster config.")


def load_auth_string(path) -> str:
    with open(path, "r") as f:
        dt = f.read()
    ins = QianxinConfHelper()
    de = ins.decrypt_cert(str(dt))
    ins.save_to_conf(de)


def get_local_current_config_file(cfg: str) -> None:
    with open(cfg, "r") as f:
        dt = rtoml.load(f)
    if dt and dt.get("sync_update"):
        return (dt, dt["sync_update"])
    return (dt, 0)


if __name__ == "__main__":
    run()
