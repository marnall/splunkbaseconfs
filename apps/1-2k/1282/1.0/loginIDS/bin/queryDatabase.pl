#!/usr/bin/perl

use strict;
use warnings;
use DBI;

# Path to file where last read position is saved
my $lastRead = shift; 

# Query to be executed. <lastPostition> is replaced with position
# read from $lastRead
# THE FIRST FIELD RETURNED HAS TO BE AN ID THAT IS SAVED TO CONTINUE AT <lastPosition>
my $query = shift;

# Separator
$"=",";

# Variables for databaseconnection
my $DB_data_source = "";
my $DB_username = "";
my $DB_password = "";

################ MAIN ###################

# read dbconfig file

my $localConfig = $ENV{'SPLUNK_HOME'}."/etc/apps/loginIDS/local/loginIDS.conf";
#print $localConfig."\n";
if (-e $localConfig) {
   open(CONFIG, "< ".$localConfig);
   my $db_type = "";
   my $db_location = "";
   while(my $line = <CONFIG>){
      next unless ($line =~ /^(\w+)\s=\s(.*)$/);
      my $key = $1;
      my $value = $2;
      if($key eq "db_type"){
         $db_type = $value;
      }
      if($key eq "db_location"){
         $db_location = $value;
      }
      if($key eq "db_user"){
         $DB_username = $value;
      }
      if($key eq "db_password"){
         $DB_password = $value;
      }
   }
   close(CONFIG);
   $DB_data_source = "dbi:" . $db_type . ":dbname=" . $db_location if ($db_type eq "SQLite");
   $DB_data_source = "dbi:mysql" . ":" . $DB_username . ":" . $db_location if ($db_type eq "MySQL");
} else {
   exit 1;
}

#print $DB_data_source . "  " . $DB_username . "  " .$DB_password . "\n";

# id of last read tupel
my $lastPosition = 0;

if (open(LAST, "< ".$lastRead)) {
    $lastPosition = <LAST>;
    chomp($lastPosition);
#    print "# Last position in ".$lastRead." was ".$lastPosition."\n";
    close(LAST);
}

my $newPosition = $lastPosition;

my $dbh = DBI->connect($DB_data_source, $DB_username, $DB_password, { RaiseError => 1, AutoCommit => 1 }) or die "Could not connect to database: " . $DBI::errstr . "\n";

my ($id, $timestamp, $falsePositive, $alertName, $service, $source, $destination, $loginName);
$query =~ s/<lastPosition>/$lastPosition/;
my $res = $dbh->selectall_arrayref($query) or die "Could not fetch data from database: " .$DBI::errstr . "\n";
foreach my $row (@$res){
    foreach (@$row) { $_ = '' unless defined }; # Define values that where NULL in the database
    print "@$row\n";
    $newPosition=@$row[0];
}
$dbh->disconnect();

open(NEW, "> ".$lastRead) or die "# Could not write to ".$lastRead."\n";
print NEW $newPosition."\n";
close(NEW);
