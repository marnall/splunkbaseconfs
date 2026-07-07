import json
import datetime
import atlas
import tempfile
from solnlib.modular_input import checkpointer
import os
import dateutil.parser

def validate_input(self, definition):
    return


def init_client(helper):
    opt_account = helper.get_arg("account")
    opt_group_id = helper.get_arg("group_id")
    opt_cluster_id = helper.get_arg("cluster_id")

    return atlas.AtlasClient(
        opt_group_id,
        opt_cluster_id,
        opt_account["public_key"],
        opt_account["private_key"],
    )


def setup_file_checkpointing(helper):
    if not helper.ckpt:
        ckpt_dir = helper.context_meta.get("checkpoint_dir", tempfile.mkdtemp())
        if not os.path.exists(ckpt_dir):
            os.makedirs(ckpt_dir)
        helper.ckpt = checkpointer.FileCheckpointer(ckpt_dir)

    helper.log_debug("File checkpointing: {0}".format(ckpt_dir))
    return helper


def fetch_cluster_logs(atlas, file_name, starts, end):
    """Fetch logs for all hosts that are assigned to the cluster"""
    hosts = atlas.fetch_cluster_hosts()

    logs = {}
    for host in hosts:
        host_logs = atlas.fetch_host_logs(host, file_name, starts[host], end)
        logs[host] = host_logs

    return logs


def get_log_timestamp(file, entry):
    if file == "mongodb-audit-log.gz" or file == "mongos-audit-log.gz":
        return entry["ts"]["$date"]

    return entry["t"]["$date"]

def collect_events(helper, ew):
    helper = setup_file_checkpointing(helper)
    helper.log_debug("action=init_checkpointing status=completed")

    inputname = helper.get_input_stanza_names()
    inputtype = helper.get_input_type()

    opt_file = helper.get_arg("file")
    opt_interval = helper.get_arg("interval")
    opt_cluster_id = helper.get_arg("cluster_id")

    atlas_client = init_client(helper)
    helper.log_info(
        f"action=init_client status=completed interval={opt_interval} file={opt_file} input={inputname}"
    )

    helper.log_info(
        f"action=fetch_cluster_hosts status=started cluster_id={opt_cluster_id}"
    )

    cluster_hosts = atlas_client.fetch_cluster_hosts()
    helper.log_info(
        f"action=fetch_cluster_hosts status=completed cluster_id={opt_cluster_id} hosts={','.join(cluster_hosts)}"
    )

    if not cluster_hosts:
        helper.log_error(
            "action=fetch_cluster_hosts status=completed msg='could not retrieve cluster hosts'"
        )
        return

    starts = {}
    end = datetime.datetime.utcnow()

    for host in cluster_hosts:
        opt_checkpoint = "{0:s}-{1:s}-{2:s}".format(inputtype, inputname, host)

        helper.log_info("action=get_checkpoint status=completed")
        if helper.get_check_point(opt_checkpoint):
            checkpoint = helper.get_check_point(opt_checkpoint)
            starts[host] = dateutil.parser.parse(checkpoint, ignoretz=True)
            helper.log_info(
                f"action=get_checkpoint host={host} msg='found checkpoint {checkpoint}'"
            )

        else:
            starts[host] = end - datetime.timedelta(seconds=int(opt_interval))

    for host, start in starts.items():
        helper.log_info(f"host={host} start_time={start} end_time={end}")

    cluster_logs = fetch_cluster_logs(atlas_client, opt_file, starts, end)
    helper.log_info(
        f"action=fetch_cluster_logs status=completed hosts={cluster_logs.keys()}"
    )

    for host, host_logs in cluster_logs.items():
        if not host_logs:
            helper.log_error(f"action=ingest_logs msg='could not find logs for {host}'")
            continue
        latest_entry = get_log_timestamp(opt_file, host_logs[-1])
        helper.log_info(f"action=ingest_logs host={host} latest_entry={latest_entry}")

        for log_entry in host_logs:
            log_entry["hostname"] = host
            log_entry_ts = get_log_timestamp(opt_file, log_entry)
            if dateutil.parser.parse(log_entry_ts, ignoretz=True) < starts[host]:
                helper.log_info(f"action=ingest_logs msg='entry {log_entry_ts} older than latest seen entry: {latest_entry}, skipping'")
                continue

            sourcetype = "cluster_logs_input" + "://" + helper.get_input_stanza_names()
            event = helper.new_event(
                source=sourcetype,
                index=helper.get_output_index(),
                sourcetype=f"mongodb:atlas:{opt_file}",
                data=json.dumps(log_entry),
            )
            ew.write_event(event)

        opt_checkpoint = "{0:s}-{1:s}-{2:s}".format(inputtype, inputname, host)

        helper.save_check_point(opt_checkpoint, latest_entry)
        helper.log_info(f"action=save_checkpoint host={host} value={latest_entry}")
