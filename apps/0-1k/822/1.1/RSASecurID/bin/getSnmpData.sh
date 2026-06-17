#!/bin/sh

snmpget -v 2c -c $1 $2 -O sQ sysName.0 ifInOctets.1 ifInOctets.2 ifInOctets.3 ifOutOctets.1 ifOutOctets.2 ifOutOctets.3 ifInUcastPkts.1 ifInUcastPkts.2 ifInUcastPkts.3 ifOutUcastPkts.1 ifOutUcastPkts.2 ifOutUcastPkts.3 icmpInMsgs.0 icmpInEchos.0 icmpInDestUnreachs.0 icmpOutMsgs.0 icmpOutDestUnreachs.0 icmpOutEchoReps.0 tcpCurrEstab.0 tcpInSegs.0 tcpOutSegs.0 tcpRetransSegs.0 tcpActiveOpens.0 tcpPassiveOpens.0 tcpInErrs.0 udpInDatagrams.0 udpNoPorts.0 udpInErrors.0 udpOutDatagrams.0
