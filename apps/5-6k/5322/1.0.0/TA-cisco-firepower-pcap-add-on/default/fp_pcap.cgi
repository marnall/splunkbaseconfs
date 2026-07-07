#!/usr/bin/perl

#  fp_pcap.cgi - Version 1.0.0  06 Nov 20
#  Retrieve Firepower IPS event pcap file via HTTP GET
#
#  Installation:
#    Copy fp_pcap.cgi to /var/sf/htdocs/ on FMC
#    sudo chown www:www fp_pcap.cgi
#    sudo chmod 755 fp_pcap.cgi
#
#  Usage:
#    pcap file - https://<FMC>/fp_pcap.cgi?sensor=<sensor>&event_id=<event_id>&event_sec=<event_sec>&text=0
#    pcap text - https://<FMC>/fp_pcap.cgi?sensor=<sensor>&event_id=<event_id>&event_sec=<event_sec>&text=1

use SF;
use SF::SFDBI;
use SF::i18n;
use SF::PacketRender;
use File::Temp;
use File::Path;

main();
sub main
{
  my $www = new SF;

  my $sensor = 'none';
  my $event_id = 0;
  my $event_sec = 0;
  my $text = 0;
  my $sensor_id = 0;

  $sensor = $1 if ($www->param("sensor") =~ /^([\w\-\.]+)/);
  $event_id = $1 if ($www->param("event_id") =~ /^(\d+)/);
  $event_sec = $1 if ($www->param("event_sec") =~ /^(\d+)/);
  $text = $1 if ($www->param("text") =~ /^(\d)/);

  my $sql = "SELECT MAX(id) FROM sensor WHERE name = '$sensor'";

  my $tempdir = File::Temp::tempdir();
  my $pcap_file = "$tempdir/pcap";

  my $dbc = SF::SFDBI::connect();
  if (defined($dbc))
  {
    my $qry = $dbc->prepare($sql);
    $qry->execute();
    my @row = $qry->fetchrow_array;
    $sensor_id = $row[0];
    $qry->finish();
    $dbc->disconnect();
  }

  SF::PacketRender::EventPacketsToPcap({sensor_id => $sensor_id,
                                        event_id  => $event_id,
                                        event_sec => $event_sec,
                                        pcap_file => $pcap_file});

  if ($text)
  {
    system("tshark -r $pcap_file -xO ip,icmp,tcp,udp,dns,smtp,http -z follow,tcp,ascii,0 >$pcap_file.txt");
    $pcap_file = "$pcap_file.txt";
    print $www->header(-type => "text/plain");
  }
  else { print $www->header(-attachment => "event.pcap", -type => "application/pcap"); }

  if (open(FILE, "<$pcap_file"))
  {
    while (<FILE>) { print; }
    close(FILE);
  }

  File::Path::rmtree($tempdir);
  exit(0);
}
