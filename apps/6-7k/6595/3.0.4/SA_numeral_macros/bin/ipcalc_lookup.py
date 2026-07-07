#!/usr/bin/env python

import csv
import sys
import ipaddress


def main():
    if len(sys.argv) != 8:
        print("Usage: python ipcalc_lookup.py [Address field] [Network field] [Netmask field] [Prefix field] [Broadcast field] [Network number field] [IP Version field]")
        sys.exit(1)

    address_field = sys.argv[1]
    network_field = sys.argv[2]
    netmask_field = sys.argv[3]
    prefix_field = sys.argv[4]
    broadcast_field = sys.argv[5]
    network_num_field = sys.argv[6]
    ipver_field = sys.argv[7]

    infile = sys.stdin
    outfile = sys.stdout

    r = csv.DictReader(infile)
    header = r.fieldnames

    w = csv.DictWriter(outfile, fieldnames=r.fieldnames)
    w.writeheader()

    for result in r:
        if result[address_field]:
            ipi = ipaddress.ip_interface(result[address_field])
            result[network_field] = str(ipi.network).split('/')[0]
            result[netmask_field] = ipi.netmask
            result[prefix_field] = str(ipi.network).split('/')[1]
            result[broadcast_field] = ipi.network.broadcast_address
            result[network_num_field] = int(ipaddress.ip_interface(str(ipi.network)))
            result[ipver_field] = int(ipi.version)
            w.writerow(result)

main()
