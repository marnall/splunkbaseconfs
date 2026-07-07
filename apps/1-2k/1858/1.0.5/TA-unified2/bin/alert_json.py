#!/usr/bin/env python

from collections import OrderedDict
import os

def get_splunk_config(conf_file_name, section):
    import ConfigParser
    import StringIO
    import subprocess

    env = dict()
    env.update(os.environ)
    env["LD_LIBRARY_PATH"] = os.path.join(env["SPLUNK_HOME"], "lib")

    p1 = subprocess.Popen(["btool", conf_file_name, "list"], stdout=subprocess.PIPE, env=env)
    (p1_out, p1_err) = p1.communicate()

    f = StringIO.StringIO()
    f.write(p1_out)
    f.seek(0)
    cfgparse = ConfigParser.RawConfigParser()
    cfgparse.readfp(f)

    cfg = dict()
    for opt in cfgparse.options(section):
        cfg[opt] = cfgparse.get(section, opt)
        
    return cfg

cfg = get_splunk_config("unified2", "unified2")
outputcfg = get_splunk_config("unified2", "output")

import glob
import json
import socket
import string
import struct
import unified2.parser
import uuid


# Read config settings
CHECKPOINT_FILE = cfg["checkpoint_file"]
u2basename = cfg["input_u2"]

if os.path.exists(CHECKPOINT_FILE):
    with open(CHECKPOINT_FILE, "r") as f:
        checkpoint = json.load(f)
else:
    checkpoint = {"ts": 0, "record": 0}

files = list()
for fn in glob.glob("{0}*".format(u2basename)):
    ts = int(fn.replace("{0}.".format(u2basename), ""))
    if ts >= checkpoint["ts"]:
        files.append(fn)

files.sort()

if checkpoint["ts"] == 0 and len(files) > 0:
    files = [ files[-1] ]


if len(files) == 0:
    import sys
    sys.exit()


protocol_names = dict()
with open("/etc/protocols", "r") as f:
    for line in f:
        line = line.strip()
        if line == "" or line[0] == "#":
            continue
        parts = line.split()
        protocol_names[parts[1]] = parts[2]

sid_msg_map = dict()
with open(cfg["sid_msg_map"], "r") as f:
    for line in f:
        line = line.strip()
        if line == "" or line[0] == "#":
            continue
        k,v = line.split(" || ")[:2]
        sid_msg_map[k] = v

gen_msg_map = dict()
with open(cfg["gen_msg_map"], "r") as f:
    for line in f:
        line = line.strip()
        if line == "" or line[0] == "#":
            continue
        gen,k,v = line.split(" || ")[:3]
        if not gen in gen_msg_map:
            gen_msg_map[gen] = dict()
        gen_msg_map[gen][k] = v

classifications = dict()
class_id = 1
with open(cfg["classifications"], "r") as f:
    for line in f:
        line = line.strip()
        if line == "" or line[0] == "#":
            continue
        v = line.split(": ", 1)[1].split(",")[1]
        classifications[class_id] = v
        class_id += 1

def get_signature_info(pkt):
    d = OrderedDict([
        ("gen_id", pkt["generator_id"]),
        ("sig_id", pkt["signature_id"]),
        ("revision", pkt["signature_revision"]),
    ])
    if pkt["generator_id"] == 1:
        d["msg"] = sid_msg_map.get(str(pkt["signature_id"]), "Snort Rule")
    else:
        d["msg"] = gen_msg_map.get(str(pkt["generator_id"]), {}).get(str(pkt["signature_id"]), "Snort Rule")
    d["classification"] = classifications[pkt["classification_id"]]
    d["priority"] = pkt["priority_id"]
    return d

def format_pkt(pkt):
    d = OrderedDict([ ("ascii", ""), ("hex", list()) ])
    for byte in pkt["packet_data"]:
        d["ascii"] += byte if byte in string.printable else "."
        d["hex"].append("%2.02X" % ord(byte))
    d["hex"] = " ".join(d["hex"])
    return d

def get_packet_source(pkt):
    d = OrderedDict([ ("ip", socket.inet_ntoa(struct.pack("!L", pkt["ip_source"]))) ])
    if pkt["protocol"] == 6 or pkt["protocol"] == 17:
        d["port"] = pkt["sport_itype"]
    try:
        d["host"] = socket.gethostbyaddr(d["ip"])[0]
    except:
        d["host"] = "no data"
    return d

def get_packet_destination(pkt):
    d = OrderedDict([ ("ip", socket.inet_ntoa(struct.pack("!L", pkt["ip_destination"]))) ])
    if pkt["protocol"] == 6 or pkt["protocol"] == 17:
        d["port"] = pkt["dport_icode"]
    try:
        d["host"] = socket.gethostbyaddr(d["ip"])[0]
    except:
        d["host"] = "no data"
    return d

def format_ev(ev,ts):
    proto = protocol_names[str(ev["protocol"])]
    d = OrderedDict([
        ("sensor_id", ev["sensor_id"]),
        ("event_id", ev["event_id"]),
        ("event_uuid", str(uuid.uuid4())),
        ("event_second", ev["event_second"]),
        ("event_microsecond", ev["event_microsecond"]),
        ("signature", get_signature_info(ev)),
        ("protocol", proto),
        ("source", get_packet_source(ev)),
        ("destination", get_packet_destination(ev)),
        ("blocked", ev["blocked"]),
    ])
    if outputcfg["pcap"].lower() in ("1", "true", "yes", "on", True):
        d["packet"] = format_pkt(ev["packet"])

    if outputcfg["pretty"].lower() in ("1", "true", "yes", "on", True):
        return json.dumps(d, indent=4, separators=(',', ': '))
    else:
        return json.dumps(d)

cached = None


for fn in files:
    ts = int(fn.replace("{0}.".format(u2basename), ""))
    chk = checkpoint["record"] + 1 if ts == checkpoint["ts"] else 0
    ev = None
    for ev, ev_tail in unified2.parser.parse(fn):
        if "event_id" in ev:
            if ev["event_id"] < chk:
                continue
            if "packet_data" in ev:
                # Packet
                if cached is not None:
                    if cached["event_id"] == ev["event_id"]:
                        cached["packet"] = ev
                    if checkpoint["record"] > 0:
                        print format_ev(cached, ts)
                    cached = None
            else:
                cached = ev
    checkpoint = {"ts": ts, "record": ev["event_id"] if ev and "event_id" in ev else chk}

with open(CHECKPOINT_FILE, "w") as f:
    json.dump(checkpoint, f)
