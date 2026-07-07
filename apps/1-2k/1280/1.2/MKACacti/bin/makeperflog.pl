#!/usr/bin/perl

###########################################################################################################
#
# Created by MKAdvantage
#
# Script does the following things
#
# 1. get a list of all of the rrd files in /usr/share/cacti/rra
# 2. Do "rrdtool info <rrdfile>" on each of the rrd files
# 3. Parse out the "last_ds" portion to get min, max, avg, dev and loss values in ms.  YOU MAY NEED TO PARSE OUT THE "value" FIELD.
        DO AN "rrdtool info <rrdfile>" and match up the values to what you see in the graphs!
# 4. Create a log file in the following format:  Date host_index key=value...key=value poller=<poller name>
# 5. Write to /usr/share/cacti/log/cacti_perf.log
# 6. Splunk forwarder picks up the file
#
# This script is currently designed to work with Advanced Ping only.  It will pull loss, avg, min, max and dev
# values.
#
# This script also assumes that the values in the rrd are stored in the "last_ds" field.  It can be stored here or in the
# value field in the output of "rrdtool info <rrdfile>".  Please refer to the rrdtool man page or Cacti documentation
#
#
##########################################################################################################

###########################################################################################################
#
# The bourne shell would look kind of like this, but each value, date and host is on one line
#
# for i in `/bin/ls -1 /usr/share/cacti/rra  | /bin/grep rrd`;do /bin/date; /bin/echo $i | /bin/sed 's/\.rrd//g'; /usr/bin/rrdtool info $i | /bin/grep last_ds | /bin/sed 's/"//g' | /bin/sed 's/ds\[//g' | /bin/sed 's/\]\.last_ds//g';/bin/echo -e "*****";done

#
################################################################################################################

use strict;
#my $makeoutput;
my @records;
my @rrds;
my $rrd;
my $record;
my $rrdcmd;
my $grep;
my $rrddir;
my $ls;
my $echo;
my $cacti_perf_log;
my $date;
my $getrrdlist;
my $poller;

##############################################################
#
# Assign values to vars
#
#############################################################
$poller = "CactiPoller1";  # NOTE THIS COMES FROM THE /opt/splunkforwarder/etc/system/local/inputs.conf file
$ls = "/bin/ls -1 ";
$grep = "/bin/grep ";
$rrdcmd = "/usr/bin/rrdtool info ";
$echo = "/bin/echo ";
$cacti_perf_log = "/usr/share/cacti/log/cacti_perf.log";
$rrddir = "/usr/share/cacti/rra";
$date=time();

$getrrdlist=$ls." ".$rrddir." | ".$grep." rrd";

@rrds = `$getrrdlist`;

open (CACTIPERF,"+>>$cacti_perf_log");



foreach $rrd (@rrds)
        {
                chomp $rrd;
                #print "Current rrd is $rrd\n";

                my $rrdcmdexec = $rrdcmd." ".$rrddir."/".$rrd;

                #print "Current rrdcmd is $rrdcmdexec\n";

                open CMD, "$rrdcmdexec |" or die "Cannot find command: $!";


                $rrd =~ s/\.rrd//g;
                $rrd =~ s/_\d+$//g;
                $rrd =~ s/_loss//g;
                $rrd =~ s/_avg//g;
                $rrd =~ s/_/\./g;

                print CACTIPERF $date." ".$rrd." ";

                while (<CMD>)
                        {
                                my $line = $_;
                                if ($line =~ /last_ds/)  # NOTE:  your value could be in the "value" field depending on how you set up Cacti
                                        {
                                        $line =~ s/"//g;
                                        $line =~ s/ds\[//g;
                                        $line =~ s/\]\.last_ds//g;
                                        chomp $line;
                                        print CACTIPERF $line." ";
                                        }

                        }

                print CACTIPERF "poller = $poller\n";
                close(CMD);
        }

