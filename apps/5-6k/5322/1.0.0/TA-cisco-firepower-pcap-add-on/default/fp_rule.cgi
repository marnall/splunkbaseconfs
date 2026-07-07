#!/usr/bin/perl

#  fp_rule.cgi - Version 1.0.0  06 Nov 20
#  Retrieve Firepower IPS event Snort rule via HTTP GET
#
#  Installation:
#    Copy fp_rule.cgi to /var/sf/htdocs/ on FMC
#    sudo chown www:www fp_rule.cgi
#    sudo chmod 755 fp_rule.cgi
#
#  Usage:
#    https://<FMC>/fp_rule.cgi?sid=<sid>

use SF;
use SF::SFDBI;

main();
sub main
{
  my $www = new SF;

  my $sid = 0;
  $sid = $1 if ($www->param("sid") =~ /^(\d+)/);

  my $sql = "SELECT category, action, rule_text FROM rule_header WHERE sid = $sid";
  my $doc_file = "../rule-docs/$sid.txt";

  print $www->header(-type => "text/plain");

  my $dbc = SF::SFDBI::connect();
  if (defined($dbc))
  {
    my $qry = $dbc->prepare($sql);
    $qry->execute();
    my @row = $qry->fetchrow_array;
    print "@row\n\n";
    $qry->finish();
    $dbc->disconnect();
  }

  if (open(FILE, "<$doc_file"))
  {
    while (<FILE>)
    {
      print;
    }
    close(FILE);
  }
  else
  {
    print "Additional information not available.";
  }

  exit(0);
}
