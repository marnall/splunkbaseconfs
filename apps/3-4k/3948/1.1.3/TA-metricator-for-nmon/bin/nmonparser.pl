#!/usr/bin/perl

# Program name: nmonparser.pl
# Compatibility: Perl x
# Purpose - nmon data processing for Splunk
# Author - Guilhem Marchand

my $version = "2.0.3";

use Time::Local;
use Time::HiRes;
use Getopt::Long;
use POSIX 'strftime';
use File::Copy;
use Data::Dumper;
use Config;
use FindBin;
use Net::Domain qw(hostname hostfqdn hostdomain domainname);

# Identify the guest OS
my $guestos = "$Config{osname}";

# Text::CSV_XS should run faster, however let's be compatible with both Text::CSV and Text::CSV_XS module
# depending on availability with priority to Text::CSV_XS
# For AIX OS, we provide the Text::CSV module since the Text::CSV_XS compilation is an issue

my $csv_module;
if ( $guestos eq 'aix' ) {
    $csv_module = 'Text::CSV';
    eval "use lib '$FindBin::Bin/lib/aix'";
    eval "use Text::CSV";
}
else {
    if ( eval { require Text::CSV_XS } ) {
        $csv_module = 'Text::CSV_XS';
    }
    else {
        $csv_module = 'Text::CSV';
    }
    eval("use $csv_module;");
}

#use warnings;

#################################################
##      Args
#################################################

# Default values

my $OPMODE   = "";
my $VERSION  = "";
my $USE_FQDN = "";
my $help     = "";
my $DEBUG    = "";
my $SILENT   = "";
my $SHOW_ZERO   = "";
my $result   = "";

$result = GetOptions(
    "mode=s"   => \$OPMODE,      # string
    "version"  => \$VERSION,     # flag
    "use_fqdn" => \$USE_FQDN,    # flag
    "help"     => \$help,        # flag
    "debug"    => \$DEBUG,       # flag
    "silent"   => \$SILENT,      # flag
    "show_zero_values"   => \$SHOW_ZERO,      # flag
);

# Show version
if ($VERSION) {
    print("nmonparser.pl version $version \n");
    exit 0;
}

# Show help
if ($help) {

    print( "

Help for nmonparser.pl:

Perl nmonparser converter is usually automatically called by Splunk to process Nmon raw data.
Splunk reads the nmon file content and will stream it to nmonparser.pl in stdout. (eg. cat <my file> | ./nmonparser.pl)

Available options are:
	
--mode <colddata | fifo> :Force the script to consider the data as cold data (nmon process has over), or fifo mode.
--use_fqdn :Use the host fully qualified domain name (fqdn) as the hostname value instead of the value returned by nmon.
--show_zero_values :Use this option to allow the TA to generate metrics with 0 values. The default behavior \n
is to remove any metric having a zero value before it reaches Splunk ingestion.
**CAUTION:** This option must not be used when managing nmon data generated out of Splunk (eg. central repositories)
--debug :Activate debugging mode for testing purposes
--version :Show current program version
--silent: Do not output the per section detail logging to save data volume \n
"
    );

    exit 0;
}

#################################################
##      Parameters
#################################################

# Customizations goes here:
# Sections of Performance Monitors with standard dynamic header but no "device" notion that would require the data to be transposed
# You can add or remove any section depending on your needs
my @static_vars = "";

# Some specific sections per OS
my @Solaris_static_section = "";

# Some specfic sections for micro partitions (AIX or Power Linux)
my @LPAR_static_section = "";

# This is the TOP section which contains Performance data of top processes
# It has a specific structure and requires specific treatment
my @top_vars = "";

# This is the UARG section which contains full command line arguments with some other information such as PID, user, group and so on
# It has a specific structure and requires specific treatment
my @uarg_vars = "";

# Sections of Performance Monitors with Dynamic header (eg. device context) and that can be incremented (DISKBUSY1...)
my @dynamic_vars1 = "";

# Sections that won't be incremented
my @dynamic_vars2 = "";

# disks extended statistics (DG*)
my @disk_extended_section = "";

# Sections of Performance Monitors for Solaris

# Zone, Project, Task... performance
my @solaris_WLM = "";

# Veritas Storage Manager
my @solaris_VxVM = "";

my @solaris_dynamic_various = "";

# AIX only dynamic sections
my @AIX_dynamic_various = "";

# AIX Workload Management
my @AIX_WLM = "";

# nmon external
my @nmon_external = "";

# nmon external with transposition of data
my @nmon_external_transposed = "";

#################################################
## 	Your Customizations Go Here
#################################################

# Processing starting time
my $t_start = [Time::HiRes::gettimeofday];

# Initial states for Analysis
my $colddata = "False";
my $fifo     = "False";

# Local time
my $time = strftime "%d-%m-%Y %H:%M:%S", localtime;

# Local Time in epoch
my $time_epoch = time();

# Minute of the hour, to be used for file naming convention
my $minute = strftime "%M", localtime;

# Default Environment Variable SPLUNK_HOME, this shall be automatically defined if as the script shall be launched by Splunk
my $SPLUNK_HOME = $ENV{SPLUNK_HOME};

# Verify SPLUNK_HOME definition
if ( not $SPLUNK_HOME ) {
    print(
"\n$time ERROR: The environment variable SPLUNK_HOME could not be verified, if you want to run this script manually you need to export it before processing"
    );
    die;
}

# Empty init APP
my $APP = "";

# Discover TA-metricator-for-nmon path
if ( length($APP) == 0 ) {

    if ( -d "$SPLUNK_HOME/etc/apps/TA-metricator-for-nmon" ) {
        $APP = "$SPLUNK_HOME/etc/apps/TA-metricator-for-nmon";
    }
    elsif ( -d "$SPLUNK_HOME/etc/peer-apps/TA-metricator-for-nmon" ) {
        $APP = "$SPLUNK_HOME/etc/peer-apps/TA-metricator-for-nmon";
    }

}

else {

    if ( !-d "$APP" ) {
        print(
"\n$time ERROR: The Application root directory could be verified using your custom setting: $APP \n"
        );
        die;
    }

}

# load configuration from json config file
# the config_file json may exist in default or local (if customized)
# this will define the list of nmon section we want to extract

my $json_config = "";
my $json        = "";

if ( -e "$APP/local/nmonparser_config.json" ) {
    $json_config = "$APP/local/nmonparser_config.json";
}
else {
    $json_config = "$APP/default/nmonparser_config.json";
}

open( $json, "< $json_config" )
  or die "ERROR: Can't open $json_config : $!";

while (<$json>) {
    chomp($_);

    $_ =~ s/\"//g;       #remove quotes
    $_ =~ s/\,\s/,/g;    #remove comma space

    # static_section
    if ( $_ =~ /^\s*static_section:\[([\w\,\s]*)\],{0,}$/ ) {
        @static_vars = split( ',', $1 );
    }

    # Solaris_static_section
    if ( $_ =~ /^\s*Solaris_static_section:\[([\w\,\s]*)\],{0,}$/ ) {
        @Solaris_static_section = split( ',', $1 );
    }

    # LPAR_static_section
    if ( $_ =~ /^\s*LPAR_static_section:\[([\w\,\s]*)\],{0,}$/ ) {
        @LPAR_static_section = split( ',', $1 );
    }

    # top_section
    if ( $_ =~ /^\s*top_section:\[([\w\,\s]*)\],{0,}$/ ) {
        @top_vars = split( ',', $1 );
    }

    # uarg_section
    if ( $_ =~ /^\s*uarg_section:\[([\w\,\s]*)\],{0,}$/ ) {
        @uarg_vars = split( ',', $1 );
    }

    # dynamic_section1
    if ( $_ =~ /^\s*dynamic_section1:\[([\w\,\s]*)\],{0,}$/ ) {
        @dynamic_vars1 = split( ',', $1 );
    }

    # dynamic_section2
    if ( $_ =~ /^\s*dynamic_section2:\[([\w\,\s]*)\],{0,}$/ ) {
        @dynamic_vars2 = split( ',', $1 );
    }

    # disk_extended_section
    if ( $_ =~ /^\s*disk_extended_section:\[([\w\,\s]*)\],{0,}$/ ) {
        @disk_extended_section = split( ',', $1 );
    }

    # solaris_WLM
    if ( $_ =~ /^\s*solaris_WLM:\[([\w\,\s]*)\],{0,}$/ ) {
        @solaris_WLM = split( ',', $1 );
    }

    # solaris_VxVM
    if ( $_ =~ /^\s*solaris_VxVM:\[([\w\,\s]*)\],{0,}$/ ) {
        @solaris_VxVM = split( ',', $1 );
    }

    # solaris_dynamic_various
    if ( $_ =~ /^\s*solaris_dynamic_various:\[([\w\,\s]*)\],{0,}$/ ) {
        @solaris_dynamic_various = split( ',', $1 );
    }

    # AIX_dynamic_various
    if ( $_ =~ /^\s*AIX_dynamic_various:\[([\w\,\s]*)\],{0,}$/ ) {
        @AIX_dynamic_various = split( ',', $1 );
    }

    # AIX_WLM
    if ( $_ =~ /^\s*AIX_WLM:\[([\w\,\s]*)\],{0,}$/ ) {
        @AIX_WLM = split( ',', $1 );
    }

    # nmon_external
    if ( $_ =~ /^\s*nmon_external:\[([\w\,\s]*)\],{0,}$/ ) {
        @nmon_external = split( ',', $1 );
    }

    # nmon_external
    if ( $_ =~ /^\s*nmon_external_transposed:\[([\w\,\s]*)\],{0,}$/ ) {
        @nmon_external_transposed = split( ',', $1 );
    }

}

close $json;

# Identify the Technical Add-on version
my $APP_CONF_FILE = "$APP/default/app.conf";
my $addon_version = "Unknown";

if ( -e $APP_CONF_FILE ) {

    # Open
    open FILE, '+<', "$APP_CONF_FILE" or die "$time ERROR:$!\n";

    while ( defined( my $l = <FILE> ) ) {
        chomp $l;
        if ( $l =~ m/version\s*=\s*([\d|\.]*)/ ) {
            $addon_version = $1;
        }
    }
}

# var main directory
my $APP_MAINVAR = "$SPLUNK_HOME/var/log/metricator";
my $APP_VAR     = "$APP_MAINVAR/var";

# If may main directories do not exist
if ( !-d "$APP_MAINVAR" ) { mkdir "$APP_MAINVAR"; }
if ( !-d "$APP_VAR" )     { mkdir "$APP_VAR"; }

# Spool directory for NMON files processing
my $SPOOL_DIR = "$APP_VAR/spool";
if ( !-d "$SPOOL_DIR" ) { mkdir "$SPOOL_DIR"; }

#  Output directory of csv files to be managed by Splunk
my $OUTPUT_DIR = "$APP_VAR/csv_workingdir";
if ( !-d "$OUTPUT_DIR" ) { mkdir "$OUTPUT_DIR"; }

# CSV Perf data working directory (files are moved at the end from DATA_DIR to DATAWORKING_DIR)
my $OUTPUTFINAL_DIR = "$APP_VAR/csv_repository";
if ( !-d "$OUTPUTFINAL_DIR" ) { mkdir "$OUTPUTFINAL_DIR"; }

# Config csv data
my $OUTPUTCONF_DIR = "$APP_VAR/config_repository";
if ( !-d "$OUTPUTCONF_DIR" ) { mkdir "$OUTPUTCONF_DIR"; }

# ID reference file, will be used to temporarily store the last execution result for a given nmon file, and prevent Splunk from
# generating duplicates by relaunching the conversion process
# Splunk when using a custom archive mode, launches twice the custom script

# Supplementary note: Since V1.2.2, ID_REF & CONFIG_REF are overwritten if running real time mode
my $ID_REF = "$APP_VAR/id_reference.txt";

# Config Reference file
my $CONFIG_REF = "$APP_VAR/config_reference.txt";

# BBB extraction flag
my $BBB_FLAG = "$APP_VAR/BBB_status.flag";

# Network interface outdated state file (Unix only)
# remove any existing file at startup time
my $OUTDATED_NETIF_NMON_STATE = "$APP_VAR/outdated_network_int_nmon.state";
if ( -f "$OUTDATED_NETIF_NMON_STATE" ) {
    unlink $OUTDATED_NETIF_NMON_STATE;
}

#################################################
## 	Various
#################################################

# Used for date string to epoch time
my %month;
@month{qw/Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec/} = 0 .. 11;

my %mon2num = qw(
  jan 1  feb 2  mar 3  apr 4  may 5  jun 6
  jul 7  aug 8  sep 9  oct 10 nov 11 dec 12
);

####################################################################
#############		Main Program
####################################################################

# Verify existence of OUTPUT_DIR
if ( !-d "$SPOOL_DIR" ) {
    print("\n$time ERROR: Spool Directory $SPOOL_DIR does not exist !\n");
    die;
}

# Verify existence of OUTPUT_DIR
if ( !-d "$OUTPUT_DIR" ) {
    print(
"\n $time ERROR: Directory for csv output $OUTPUT_DIR does not exist !\n"
    );
    die;
}

# Initialize common variables
&initialize;

# Clean spool directory at program start-up
unlink glob "$SPOOL_DIR/*.nmon";

# Read nmon file from stdin (eg. cat <my nmon file> | nmonparser)
# will remove blank lines if any
my $file = "$SPOOL_DIR/nmonparser.$$.nmon";
open my $fh, '>', $file or die $!;

while (<STDIN>) {
    next if /^$/;
    last if /^$/;
    print $fh $_;
}
close $fh;

# Open temp nmon
open FILE, '+<', "$file" or die "$time ERROR:$!\n";

####################################################################################################
#############		NMON data structure verification				############
####################################################################################################

# Set some default values
my $SN                   = "-1";
my $HOSTNAME             = "-1";
my $DATE                 = "-1";
my $nmon_day             = "-1";
my $nmon_month           = "-1";
my $nmon_year            = "-1";
my $nmon_hour            = "-1";
my $nmon_minute          = "-1";
my $nmon_second          = "-1";
my $TIME                 = "-1";
my $logical_cpus         = "-1";
my $virtual_cpus         = "-1";
my $INTERVAL             = "-1";
my $SNAPSHOTS            = "-1";
my $OStype               = "Unknown";
my $last_known_epochtime = "0";
my $bytes                = "0";

# Set HOSTNAME
if ($USE_FQDN) {
    $HOSTNAME = hostfqdn();
}

while ( defined( my $l = <FILE> ) ) {
    chomp $l;

# Set HOSTNAME
# if the option --use_fqdn has been set, use the fully qualified domain name by the running OS
# The value will be equivalent to the stdout of the os "hostname -f" command
# CAUTION: This option must not be used to manage nmon data out of Splunk ! (eg. central repositories)

    if ( not $USE_FQDN ) {
        if ( ( rindex $l, "AAA,host," ) > -1 ) {
            ( my $t1, my $t2, $HOSTNAME ) = split( ",", $l );
        }
    }

    # Set VERSION
    if ( ( rindex $l, "AAA,version," ) > -1 ) {
        ( my $t1, my $t2, $VERSION ) = split( ",", $l );
    }

    # Set DATE
    if ( ( rindex $l, "AAA,date," ) > -1 ) {
        ( my $t1, my $t2, $DATE ) = split( ",", $l );
    }

    # Set TIME
    if ( ( rindex $l, "AAA,time," ) > -1 ) {
        ( my $t1, my $t2, $TIME ) = split( ",", $l );
    }

    # Set day, month, year
    if ( $l =~ m/AAA,date,(\w+)\-(\w+)\-(\w+)/ ) {
        $nmon_day   = $1;
        $nmon_month = $2;
        $nmon_year  = $3;
    }

    # Set hour, minute, second
    if ( $l =~ m/AAA,time,(\d+)\:(\d+)[\:|\.](\d+)/ ) {
        $nmon_hour   = $1;
        $nmon_minute = $2;
        $nmon_second = $3;
    }

    # Get Nmon version
    if ( $l =~ m/AAA\,version\,(.+)/ ) {
        $VERSION = $1;
    }

    # Get interval
    if ( $l =~ m/AAA\,interval\,(d+)/ ) {
        $INTERVAL = $1;
    }

    # Get interval
    if ( $l =~ m/AAA\,snapshots\,(d+)/ ) {
        $SNAPSHOTS = $1;
    }

    # Get logical_cpus
    if ( $l =~ m/AAA\,cpus\,\d+\,(\d+)/ ) {
        $logical_cpus = $1;
    }

    # If not defined in second position, set it from first
    elsif ( $l =~ m/AAA\,cpus\,(\d+)/ ) {
        $logical_cpus = $1;
    }

    # Get virtual_cpus
    if ( $l =~ m/BBB[a-zA-Z].+Online\sVirtual\sCPUs.+\:\s(\d+)\"/ ) {
        $virtual_cpus = $1;
    }

    # If undefined, set it equal to logical_cpus
    if ( $virtual_cpus == "-1" ) {
        $virtual_cpus = $logical_cpus;
    }

# Search for old nmon versions time format, eg. dd/mm/yy
# If found, let's convert it into the nmon format used with later versions: dd/MMM/YYYY

    if ( $l =~ m/AAA,date,[0-9]+\/[0-9]+\/[0-9]+/ ) {
        print(
"ERROR: hostname: $HOSTNAME Detected obsolete Nmon version, please consider upgrading this hosts! \n"
        );
        print("ERROR: hostname: $HOSTNAME Ignoring nmon data \n");
        close FILE;
        unlink $file;
        exit 1;
    }

# Verify we do not have any line that contain ZZZZ without beginning the line by ZZZZ
# In such case, the nmon data is bad and buggy, converting it would generate

    if ( $l =~ m/.+ZZZZ,/ ) {
        print(
"ERROR: hostname: $HOSTNAME Detected Bad Nmon structure, found ZZZZ lines truncated! (ZZZZ lines contains the event timestamp and should always begin the line) \n"
        );
        print("ERROR: hostname: $HOSTNAME Ignoring nmon data \n");
        close FILE;
        unlink $file;
        exit 1;
    }

    # Identify Linux hosts
    if ( $l =~ m/AAA,OS,Linux/ ) {
        $OStype = "Linux";
    }

    # Identify Solaris hosts
    if ( $l =~ m/AAA,OS,Solaris,.+/ ) {
        $OStype = "Solaris";
    }

    # Identify AIX hosts
    if ( $l =~ m/^AAA,AIX,(.+)/ ) {
        $OStype = "AIX";
    }

}

# Process nmon file provided in argument
my @nmon_files = "$SPOOL_DIR/nmonparser.$$.nmon";

@nmon_files = sort(@nmon_files);
chomp(@nmon_files);
our $FILENAME;

foreach $FILENAME (@nmon_files) {

    my $start = time();
    my @now   = localtime($start);
    my $now   = join( ":", @now[ 2, 1, 0 ] );

    # Parse nmon file, skip if unsuccessful
    if ( (&get_nmon_data) gt 0 ) { next; }
    $now = time();
    $now = $now - $start;

    # Get nmon file number of lines
    open( FILE, $FILENAME ) or die "$time ERROR: Can't open '$FILENAME': $!";
    my $lines = "";
    $lines++ while (<FILE>);
    close FILE;

    # If SN could not be identified
    if ( $SN == "-1" ) {
        $SN = $HOSTNAME;
    }

    # Get nmon file size in bytes
    $bytes = -s $FILENAME;

    # Get idnmon
    my $idnmon = "${DATE}:${TIME},${HOSTNAME},${SN},$bytes";

    # Partial idnmon
    my $partial_idnmon;

    # Print Main information
    print "${time} Reading NMON data: $lines lines $bytes bytes\n";

    # Print SPLUNK_HOME
    print "Splunk Root Directory (\$SPLUNK_HOME): $SPLUNK_HOME \n";

    # Show addon type
    print "addon type: $APP \n";

    # Show application version
    print "addon version: $addon_version \n";

    # Show program version
    print "nmonparser version: $version \n";

    # Show OS guest
    print "Guest Operating System: $^O\n";

    # Show NMON OS
    print "NMON OStype: $OStype \n";

    # Show perl version
    print "Perl version: $] \n";

    # Show Nmon version
    print "NMON VERSION: $VERSION \n";

    # Show hostname
    print "HOSTNAME: $HOSTNAME \n";

    # Show TIME
    print "TIME of Nmon Data: $TIME \n";

    # Show DATE
    print "DATE of Nmon Data: $DATE \n";

    # Show INTERVAL
    print "INTERVAL: $INTERVAL \n";

    # Show SNAPSHOTS
    print "SNAPSHOTS: $SNAPSHOTS \n";

    # Show logical_cpus
    print "logical_cpus: $logical_cpus \n";

    # Show virtual_cpus
    print "virtual_cpus: $virtual_cpus \n";

    # Show SerialNumber
    print "SerialNumber: $SN \n";

    #
    # PERMANENT FAILURES: Avoid inconsistent data to be generated
    #

    if ( $HOSTNAME == "-1" ) {
        print("ERROR: The hostname could not be extracted from Nmon data ! \n");
        unlink $FILENAME;
        exit 1;
    }

    if ( $DATE == "-1" ) {
        print("ERROR: date could not be extracted from Nmon data ! \n");
        unlink $FILENAME;
        exit 1;
    }

    if ( $TIME == "-1" ) {
        print("ERROR: time could not be extracted from Nmon data ! \n");
        unlink $FILENAME;
        exit 1;
    }

    if ( $logical_cpus == "-1" ) {
        print(
"ERROR: The number of logical cpus (logical_cpus) could not be extracted from Nmon data ! \n"
        );
        unlink $FILENAME;
        exit 1;
    }

    # If virtual_cpus could not be identified, set it equal to logical_cpus
    if ( $virtual_cpus == "-1" ) {
        $virtual_cpus = $logical_cpus;
    }

#####################
    # Data status store #
#####################

# Various status are stored in different files
# This includes the id check file, the config check file and status per section containing last epochtime proceeded
# These items will be stored in a per host dedicated directory

    # create a directory under APP_VAR
    # This directory will be used to store per section last epochtime status
    my $HOSTNAME_VAR = "$APP_VAR/${HOSTNAME}_${SN}";
    if ( !-d "$HOSTNAME_VAR" ) { mkdir "$HOSTNAME_VAR"; }

    # Overwrite ID_REF and CONFIG_REF
    $ID_REF     = "$HOSTNAME_VAR/${HOSTNAME}.id_reference.txt";
    $CONFIG_REF = "$HOSTNAME_VAR/${HOSTNAME}.config_reference.txt";
    $BBB_FLAG   = "$HOSTNAME_VAR/${HOSTNAME}.BBB_status.flag";

###############
    # ID Check #
###############

# This section prevents Splunk from generating duplicated data for the same Nmon file
# While using the archive mode, Splunk may opens twice the same file sequentially
# If the Nmon file id is already present in our reference file, then we have already proceeded this Nmon and nothing has to be done
# Last execution result will be extracted from it to stdout

    # Change . to : if present in TIME
    $TIME =~ s/\./\:/g;

    # Date of starting Nmon (format: DD-MM-YYYY hh:mm:ss)
    my $NMON_DATE = "$DATE $TIME";

    $NMON_DATE =~ s/JAN/01/g;
    $NMON_DATE =~ s/FEB/02/g;
    $NMON_DATE =~ s/MAR/03/g;
    $NMON_DATE =~ s/APR/04/g;
    $NMON_DATE =~ s/MAY/05/g;
    $NMON_DATE =~ s/JUN/06/g;
    $NMON_DATE =~ s/JUL/07/g;
    $NMON_DATE =~ s/AUG/08/g;
    $NMON_DATE =~ s/SEP/09/g;
    $NMON_DATE =~ s/OCT/10/g;
    $NMON_DATE =~ s/NOV/11/g;
    $NMON_DATE =~ s/DEC/12/g;

    my $day;
    my $month;
    my $year;
    my $hour;
    my $min;
    my $sec;
    my $starting_epochtime;
    my $ZZZZ_epochtime;
    my $ending_epochtime;

# Convert date string to epoch time (note: we could have made this easier but we want to only use core modules !)
    ( $day, $month, $year, $hour, $min, $sec ) = split /\W+/, $NMON_DATE;
    $starting_epochtime =
      timelocal( $sec, $min, $hour, $day, $month - 1, $year );

    # Search for the last timestamp in data

    # Open NMON file for reading
    if ( !open( FIC, $file ) ) {
        die( "Error while trying to open NMON Source file '" . $file . "'" );
    }

    # Initialize variables
    my $timestamp = "";
    my $cpu_cores = "";

    while ( defined( my $l = <FIC> ) ) {
        chomp $l;

        # Get timestamp"
        if ( ( rindex $l, "ZZZZ," ) > -1 ) {
            ( my $t1, my $t2, my $timestamptmp1, my $timestamptmp2 ) =
              split( ",", $l );
            $timestamp = $timestamptmp2 . " " . $timestamptmp1;

            $timestamp =~ s/JAN/01/g;
            $timestamp =~ s/FEB/02/g;
            $timestamp =~ s/MAR/03/g;
            $timestamp =~ s/APR/04/g;
            $timestamp =~ s/MAY/05/g;
            $timestamp =~ s/JUN/06/g;
            $timestamp =~ s/JUL/07/g;
            $timestamp =~ s/AUG/08/g;
            $timestamp =~ s/SEP/09/g;
            $timestamp =~ s/OCT/10/g;
            $timestamp =~ s/NOV/11/g;
            $timestamp =~ s/DEC/12/g;

     # Convert timestamp string to epoch time (from format: DD-MM-YYYY hh:mm:ss)
            ( $day, $month, $year, $hour, $min, $sec ) = split /\W+/,
              $timestamp;
            $ZZZZ_epochtime =
              timelocal( $sec, $min, $hour, $day, $month - 1, $year );

        }

        # Retrieve the list of CPUxx available
        # This will be used to iterate in the CPUnn section
        if ( $l =~ /^(CPU\d*),CPU/ ) {
            $cpu_cores = "$cpu_cores,$1";
        }

    }

    # Last epochtime in data is
    $ending_epochtime = $ZZZZ_epochtime;

    # Evaluate if we are dealing with real time data or cold data

    if ( $OPMODE eq "colddata" ) {

        $colddata = True;
        print "ANALYSIS: Enforcing colddata mode using --mode option \n";

    }

    elsif ( $OPMODE eq "fifo" ) {

        $fifo = True;
        print("ANALYSIS: Enforcing fifo mode using --mode option \n");

    }

    else {

        $colddata = True;
        print "ANALYSIS: Assuming Nmon cold data \n";

    }

    # Set the full idnmon
    $idnmon = "$idnmon,$starting_epochtime,$ending_epochtime";

    # Set the partial idnmon
    $partial_idnmon = "$idnmon,$starting_epochtime";

    # Open ID_REF file

    # Notes: fifo mode will always proceed data

    if ( -e $ID_REF ) {

        open( ID_REF, "< $ID_REF" ) or die "ERROR: Can't open $ID_REF : $!";
        chomp $ID_REF;

        if ( $colddata eq "True" ) {

            if ( grep { /$partial_idnmon/ } <ID_REF> ) {

                # If the idnmon was found, print file content and exit
                open( ID_REF, "< $ID_REF" )
                  or die "ERROR: Can't open $ID_REF : $!";
                while (<ID_REF>) {
                    print;
                }
                close ID_REF;

                # remove spool nmon
                unlink $file;

                exit;

            }
        }

    }

# If last_known_epochtime could not be found (eg. we never proceeded this nmon file), set it equal to starting_epochtime
    if ( $last_known_epochtime eq "" ) {

        $last_known_epochtime = $starting_epochtime;

    }

    # If we are here, then we need to process

    # Open for writing, and write the idnmon to it
    open( ID_REF, "> $ID_REF" ) or die "ERROR: Can't open $ID_REF : $!";
    print ID_REF "NMON ID: $partial_idnmon\n";

    # Print idnmon for stdout
    print "NMON ID: $partial_idnmon\n";

    # Open ID_REF for writing in append mode
    open( ID_REF, ">>$ID_REF" );

    # Show and Save timestamps information
    print "Starting_epochtime: $starting_epochtime \n";
    print ID_REF "Starting_epochtime: $starting_epochtime \n";
    print "Ending_epochtime: $ending_epochtime \n";
    print ID_REF "Ending_epochtime: $ending_epochtime \n";
    print ID_REF "Last known timestamp is: $last_known_epochtime \n";

####################################################################################################
#############		NMON config Section						############
####################################################################################################

    # Extract config elements from NMON files, section AAA, section BBB

    # CONFIG Section
    my @config_vars = ("CONFIG");
    my $config_lastepoch;
    my $time_delta;
    my @cpunn_vars;
    my @rawdataheader;

# Set time_delta_limit, by default we should generate configuration by cycle of 24 hours unless the process
# has been restarted
    my $time_delta_limit = 86400;

    foreach $key (@config_vars) {
        my $BASEFILENAME =
          "$OUTPUTCONF_DIR/${HOSTNAME}_${minute}_${key}.events.csv";

        # Set default for config_run:
        # 0 --> Extract configuration
        # 1 --> Don't Extract configuration
        # default is extract
        my $config_run = 0;

# If the BBB_FLAG is found and we are in real time, the last configuration extraction did not extracted BBB section, proceed any way

        if ( -e $BBB_FLAG ) {

# remove the flag, if the BBB extraction fails again, it will be created again (in real mode)
            unlink $BBB_FLAG;
        }

        else {

            # Search in ID_REF for a last matching execution
            if ( -e $CONFIG_REF ) {

                open( CONFIG_REF, "< $CONFIG_REF" )
                  or die "ERROR: Can't open $CONFIG_REF : $!";
                chomp $CONFIG_REF;

                # Only proceed if hostname has the same value
                if ( <CONFIG_REF> =~ m/$HOSTNAME:\s(\d+)/ ) {
                    $config_lastepoch = $1;
                }

                # Evaluate the delta
                $time_delta = ( $time_epoch - $config_lastepoch );

                # Only generate data once per hour
                if ( $time_delta < $time_delta_limit ) {
                    $config_run = "1";
                }

                elsif ( $time_delta > $time_delta_limit ) {
                    $config_run = "0";
                }

            }

            if ( $config_run eq "0" ) {

# Real time restricts configuration extraction once per hour, with the exception of the BBB extraction failure
                if ( $fifo eq "True" ) {

                    my $limit = ( ($starting_epochtime) + ( 4 * $INTERVAL ) );

                    print "last known epoch is $last_known_epochtime \n";

                    if ( $last_known_epochtime < $limit ) {

                        print "CONFIG section will be extracted \n";

                        # run sub routine
                        &config_extract($BASEFILENAME);

                    }

                    else {

                        print
"CONFIG section: Assuming we already extracted for this file \n";

                        print ID_REF
"CONFIG section: Assuming we already extracted for this file \n";

                    }

                }

                # cold data mode implies to always extract config
                elsif ( $colddata eq "True" ) {

                    # run sub routine
                    &config_extract($BASEFILENAME);

                }

            }

            elsif ( $config_run eq "1" ) {

                print
"CONFIG section: will not be extracted (time delta of $time_delta seconds is inferior to $time_delta_limit seconds) \n";
                print ID_REF
"CONFIG section: will not be extracted (time delta of $time_delta seconds is inferior to $time_delta_limit seconds) \n";

            }

        }

    }    # end foreach

####################################################################################################
#############		NMON Sections with static fields (eg. no devices)		############
####################################################################################################

    # Static variables (number of fields always the same)
    local $key;
    foreach $key (@static_vars) {

        # For CPUnn, iterate within the cpu_cores available in the host
        if ( $key eq "CPUnn" ) {

            # retrieve the list of available cores
            @cpunn_vars = split( ',', $cpu_cores );
            foreach $subkey (@cpunn_vars) {
                &multi_dimension_metrics_fn($subkey);
            }    # end foreach
        }
        else {
            &multi_dimension_metrics_fn($key);
        }
    }    # end foreach

    local $key;
    foreach $key (@nmon_external) {

# UPTIME is a special case, we extract load average and store them as native metrics
# we extracts as well as events to manage the server uptime which is not a metric
        if ( $key eq "UPTIME" ) {
            &uptime_metrics_fn($key);
            &multi_dimension_events_fn($key);
        }
        elsif ( $key eq "DF_STORAGE" ) {
            &df_external_metrics_fn($key);
        }
        elsif ( $key eq "DF_INODES" ) {
            &df_external_metrics_fn($key);
        }
        else {
            &multi_dimension_metrics_fn($key);
        }
    }    # end foreach

    # These sections are specific for Micro Partitions, can be AIX or PowerLinux
    if ( $OStype eq "AIX" || $OStype eq "Linux" || $OStype eq "Unknown" ) {
        local $key;
        foreach $key (@LPAR_static_section) {
            &multi_dimension_metrics_fn($key);
        }    # end foreach
    }

    # Solaris Specific
    if ( $OStype eq "Solaris" || $OStype eq "Unknown" ) {
        local $key;
        foreach $key (@Solaris_static_section) {
            &multi_dimension_metrics_fn($key);
        }    # end foreach
    }

####################################################################################################
#############		TOP & UARG		############
####################################################################################################

    # TOP
    local $key;
    foreach $key (@top_vars) {
        &top_metrics_fn($key);
    }    # end foreach

    # UARG
    local $key;
    foreach $key (@uarg_vars) {
        &uarg_events_fn($key);
    }    # end foreach

####################################################################################################
#############		NMON Sections with variable fields (eg. with devices)		############
####################################################################################################

    # Dynamic Sections, manage up to 20 sections, 3000 devices

    local $key;
    foreach $key (@dynamic_vars1) {
        &mono_dimension_metrics_fn($key);
    }

    local $key;
    foreach $mainkey (@dynamic_vars1) {

        # Search for supplementary sections
        $init = 0;

        do {
            $init = $init + 1;
            $key = join '', $mainkey, $init;
            &mono_dimension_metrics_fn($key);
        } while ( $init < 20 );

    }

    # Dynamic Sections with no increment
    local $key;
    foreach $key (@dynamic_vars2) {
        &mono_dimension_metrics_fn($key);
    }

    # Disks extended stats
    local $key;
    foreach $key (@disk_extended_section) {
        &mono_dimension_metrics_fn($key);
    }

    # AIX Specific sections, run this for OStype AIX or unknown

    if ( $OStype eq "AIX" || $OStype eq "Unknown" ) {

        local $key;
        foreach $key (@AIX_dynamic_various) {
            &mono_dimension_metrics_fn($key);
        }

        local $key;
        foreach $key (@AIX_WLM) {
            &mono_dimension_metrics_fn($key);
        }

    }

    # Solaris Specific sections, run this for OStype Solaris or unknown

    # WLM Stats

    if ( $OStype eq "Solaris" || $OStype eq "Unknown" ) {

        local $key;
        foreach $key (@solaris_WLM) {
            &mono_dimension_metrics_fn($key);
        }

        # VxVM volumes
        local $key;
        foreach $key (@solaris_VxVM) {
            &mono_dimension_metrics_fn($key);
        }

        # Other dynamics
        local $key;
        foreach $key (@solaris_dynamic_various) {
            &mono_dimension_metrics_fn($key);
        }

        # nmon external with transposition
        local $key;
        foreach $key (@nmon_external_transposed) {
            &mono_dimension_metrics_fn($key);
        }

    }

##########################
    # Move final Perf csv data
##########################

    # Move final files Performance data files
    my @move = ("$OUTPUT_DIR/*.csv");

    # Enter loop
    local $key;
    foreach $key (@move) {

        my @files = glob($key);

        foreach $file (@files) {
            if ( -f $file ) {
                move( $file, "$OUTPUTFINAL_DIR/" );
            }
        }
    }

#############################################
#############  Main Program End 	############
#############################################

    # Close Temp NMON File
    close(INSERT);

    # Delete temp nmon file
    unlink("$FILENAME");

    if ($SILENT) {

        # Print an informational message if running in silent mode
        print
"Output mode is configured to run in minimal mode using the --silent option \n";
    }

    # Show elapsed time
    my $t_end = [Time::HiRes::gettimeofday];
    print "Elapsed time was: ",
      Time::HiRes::tv_interval( $t_start, $t_end ) . " seconds \n";

    # Save Elapsed to ID_REF
    print ID_REF "Elapsed time was: ",
      Time::HiRes::tv_interval( $t_start, $t_end ) . " seconds \n";

}
exit(0);

############################################
#############  Subroutines 	############
############################################

##################################################################
## Configuration Extraction
##################################################################

sub config_extract {

    my $BASEFILENAME = shift;

    unless ( open( INSERT, ">$BASEFILENAME" ) ) {
        die("ERROR: ERROR: Can not open /$BASEFILENAME\n");
    }

    # Initialize variables
    my $section      = "CONFIG";
    my $time         = "";
    my $date         = "";
    my $hostnameT    = "Unknown";
    my $SerialNumber = "Unknown";
    my $count        = 0;
    my $BBB_count    = 0;
    my $splunk_hostname;

    # Get nmon/server settings (search string, return column, delimiter)
    my $AIXVER = &get_setting( "AIX", 2, "," );

    # Allow hostname os
    if ($USE_FQDN) {
        $HOSTNAME = hostfqdn();
    }
    else {
        $HOSTNAME = &get_setting( "host", 2, "," );
    }

    my $SPLUNK_HOSTNAME_OVERRIDE = False;
    my $SERIALNUM_OVERRIDE       = False;
    my $SERIALNUM_OVERRIDE_VALUE = "none";
    my $NMON_SPLUNK_LOCAL_CONF   = "$APP/local/nmon.conf";
    my $NMON_SYS_LOCAL_CONF      = "/etc/nmon.conf";
    my $NMON_LOCAL_CONF;
    my $SPLUNK_SYSTEM_INPUTS = "$SPLUNK_HOME/etc/system/local/inputs.conf";

    # Define the local conf with the higher priority
    if ( -e $NMON_SYS_LOCAL_CONF ) {
        $NMON_LOCAL_CONF = $NMON_SYS_LOCAL_CONF;
    }
    elsif ( -e $NMON_SPLUNK_LOCAL_CONF ) {
        $NMON_LOCAL_CONF = $NMON_SPLUNK_LOCAL_CONF;
    }
    else {
        $NMON_LOCAL_CONF = "none";
    }

    # Load config configuration
    if ( $NMON_LOCAL_CONF ne "none" && -e $NMON_LOCAL_CONF ) {

        open( NMON_LOCAL_CONF, "< $NMON_LOCAL_CONF" )
          or die "ERROR: Can't open $NMON_LOCAL_CONF : $!";
        chomp $NMON_LOCAL_CONF;

        while ( defined( my $l = <NMON_LOCAL_CONF> ) ) {
            chomp $l;

            if ( $l =~ m/^override_sys_serialnum=\"1\"/ ) {
                $SERIALNUM_OVERRIDE = True;
            }

            if ( $l =~ m/^override_sys_serialnum_value=\"([a-zA-Z0-9\-\_]*)\"/ )
            {
                $SERIALNUM_OVERRIDE_VALUE = $1;
            }

            # if hostname override, open splunk local configuration
            if ( $l =~ m/^override_sys_hostname=\"1\"/ ) {
                $SPLUNK_HOSTNAME_OVERRIDE = True;
            }

            if ( $SPLUNK_HOSTNAME_OVERRIDE eq "True" ) {

                if ( -e $SPLUNK_SYSTEM_INPUTS ) {

                    # Open
                    open FILE, '+<', "$SPLUNK_SYSTEM_INPUTS"
                      or die "$time ERROR:$!\n";

                    while ( defined( my $l = <FILE> ) ) {
                        chomp $l;

                        if ( $l =~ m/host\s*=\s*(.+)/ ) {

                            # break at first occurrence
                            $splunk_hostname = $1;
                            last;
                        }

                    }

                    # if not hostname could be found
                    if ( $splunk_hostname eq "" ) {
                        $SPLUNK_HOSTNAME_OVERRIDE = False;
                    }

                    close SPLUNK_SYSTEM_INPUTS;
                }

            }

        }

        close NMON_LOCAL_CONF;

    }

    # hostname override
    if ( $SPLUNK_HOSTNAME_OVERRIDE eq "True" ) {
        $HOSTNAME = $splunk_hostname;
    }

    # serialnum override
    if ( $SERIALNUM_OVERRIDE eq "True" ) {
        $SN = $SERIALNUM_OVERRIDE_VALUE;
    }

    $DATE = &get_setting( "AAA,date", 2, "," );
    $TIME = &get_setting( "AAA,time", 2, "," );

    # for AIX
    if ( $SERIALNUM_OVERRIDE eq "False" ) {
        if ( $AIXVER ne "-1" ) {
            $SN = &get_setting( "systemid", 4, "," );
            $SN = ( split( /\s+/, $SN ) )[0];    # "systemid IBM,SN ..."
        }

        # for Power Linux
        else {
            $SN = &get_setting( "serial_number", 4, "," );
            $SN = ( split( /\s+/, $SN ) )[0];    # "serial_number=IBM,SN ..."
        }

        # undeterminated
        if ( $SN eq "-1" ) {
            $SN = $HOSTNAME;
        }
        elsif ( $SN eq "" ) {
            $SN = $HOSTNAME;
        }

    }

    elsif ( $SERIALNUM_OVERRIDE eq "True" ) {
        $SN = $SERIALNUM_OVERRIDE_VALUE;
    }

    # write event header

    my $write =
      $section . "," . $DATE . ":" . $TIME . "," . $HOSTNAME . "," . $SN;
    print( INSERT "$write\n" );
    $count++;

    # Open NMON file for reading
    if ( !open( FIC, $file ) ) {
        die( "ERROR: while trying to open NMON Source file '" . $file . "'" );
    }

    while ( defined( my $l = <FIC> ) ) {
        chomp $l;

        # CONFIG Section"

        if ( $l =~ /^AAA/ ) {

            my $x = $l;

            # Manage some fields we statically set
            $x =~ s/CONFIG,//g;
            $x =~ s/Time,//g;

            my $write = $x;

            # Manage the host rewrite
            if ( $write =~ /^AAA,host,/ ) {
                $write = "AAA,host,$HOSTNAME";
            }

            # Manage the serialnum rewrite
            if ( $write =~ /^AAA,SerialNumber,/ ) {
                $write = "AAA,SerialNumber,$SERIALNUM_OVERRIDE_VALUE";
            }

            print( INSERT "$write\n" );
            $count++;

        }

        if ( $l =~ /^BBB/ ) {

            my $x = $l;

            # Manage some fields we statically set
            $x =~ s/CONFIG,//g;
            $x =~ s/Time,//g;

            my $write = $x;

            print( INSERT "$write\n" );
            $count++;
            $BBB_count++;

        }

    }

# If we extracted at least 10 lines of BBB data, estimate we successfully extracted it
    if ( $BBB_count > 10 ) {

        if ( -e $BBB_FLAG ) {

            unlink $BBB_FLAG;

        }

    }

    else {

        open( BBB_FLAG, ">$BBB_FLAG" );
        print BBB_FLAG "BBB_status KO";

        print "CONFIG section: BBB section not extracted (no data yet) \n";

        print ID_REF
          "CONFIG section: BBB section not extracted (no data yet) \n";

    }

    print "$key section: Wrote $count line(s)\n";
    print ID_REF "$key section: Wrote $count line(s)\n";

    # Open CONFIG_REF for writing in create mode
    open( CONFIG_REF, ">$CONFIG_REF" );

    # save configuration extraction
    print CONFIG_REF "$HOSTNAME: $time_epoch \n";

}

##################################################################
## Extract data for Static fields
##################################################################

sub multi_dimension_events {

    my $nmon_var = shift;
    my $key      = $nmon_var;

    my @rawdata;
    my @rawdataheader;
    my $x;
    my @cols;
    my $TS;
    my $n;
    my $sanity_check                  = 0;
    my $sanity_check_timestampfailure = 0;
    my $count                         = 0;
    my $last_epoch_filter;
    my $startline;

    @rawdata = grep( /^$nmon_var,/, @nmon );

    if ( @rawdata < 1 ) { return (1); }
    else {

        @rawdataheader = grep( /^$nmon_var,([^T].+),/, @nmon );

        if ( @rawdataheader < 1 ) {
            $msg =
"WARN: hostname: $HOSTNAME :$key section data is not consistent: the data header could not be identified, dropping the section to prevent data inconsistency \n";
            print "$msg";
            print ID_REF "$msg";

            $sanity_check = "1";

        }

        else {

            unless ( open( INSERT, ">$BASEFILENAME" ) ) {
                die("ERROR: Can not open /$BASEFILENAME\n");
            }

        }

    }

    # Sort rawdata
    @rawdata = sort(@rawdata);

    @cols = split( /,/, $rawdata[0] );
    $x = join( ",", @cols[ 2 .. @cols - 1 ] );
    $x =~ s/\%/_PCT/g;
    $x =~ s/\(MB\)/_MB/g;
    $x =~ s/-/_/g;
    $x =~ s/ /_/g;
    $x =~ s/__/_/g;
    $x =~ s/,_/,/g;
    $x =~ s/_,/,/g;
    $x =~ s/^_//;
    $x =~ s/_$//;

    # Count the number fields in header
    my @c                 = $x =~ /,/g;
    my $fieldsheadercount = @c;

    print INSERT (qq|type,serialnum,hostname,OStype,ZZZZ,$x\n|);

# For CPUnn case, filter on perf data only (multiple headers are present in rawdata)
    if ( $nmon_var eq "CPUnn" ) {
        @rawdata = grep( /^CPU\d*,T.+,/, @nmon );
    }

    $n = @cols;
    $n = $n - 1;    # number of columns -1

# Define the starting line to read (exclusion of csv header)
# For CPUnn, we don't need to filter the header as we already filtered on perf data

    if ( $nmon_var eq "CPUnn" ) {
        $startline = 0;
    }
    else {
        $startline = 1;
    }

    for ( $i = $startline ; $i < @rawdata ; $i++ ) {

        $TS = $UTC_START + $INTERVAL * ($i);

        @cols = split( /,/, $rawdata[$i] );
        $x = join( ",", @cols[ 2 .. $n ] );
        $x =~ s/,,/,-1,/g;    # replace missing data ",," with a ",-1,"

        my @c              = $x =~ /,/g;
        my $fieldsrawcount = @c;

        # section dynamic name
        $datatype = @cols[0];

        if ( $fieldsrawcount != $fieldsheadercount ) {

            $msg =
"WARN: hostname: $HOSTNAME :$key section is not consistent: $fieldsrawcount fields in data, $fieldsheadercount fields in header, extra fields detected (more fields in data than header), dropping this section to prevent data inconsistency \n";
            print "$msg";
            print ID_REF "$msg";

            $sanity_check = "1";

        }

# If the timestamp could not be found, there is a data anomaly and the section is not consistent
        if ( not $DATETIME{ $cols[1] } ) {

            $sanity_check                  = "1";
            $sanity_check_timestampfailure = "1";

        }

        # If sanity check is ok, write data
        if ( $sanity_check == 0 ) {

            $timestamp = $DATETIME{ @cols[1] };

     # Convert timestamp string to epoch time (from format: YYYY-MM-DD hh:mm:ss)
            my ( $year, $month, $day, $hour, $min, $sec ) = split /\W+/,
              $timestamp;
            my $ZZZZ_epochtime =
              timelocal( $sec, $min, $hour, $day, $month - 1, $year );

            # Write data
            print INSERT (
                qq|$datatype,$SN,$HOSTNAME,$OStype,$DATETIME{@cols[1]},$x\n|);
            $count++;

        }

    }
    print INSERT (qq||);

    # If sanity check has failed, remove data
    if ( $sanity_check != 0 && $sanity_check_timestampfailure != 0 ) {

        $msg =
"ERROR: hostname: $HOSTNAME :$key section is not consistent: Detected anomalies in events timestamp, dropping this section to prevent data inconsistency \n";
        print "$msg";
        print ID_REF "$msg";

        unlink $BASEFILENAME;
    }

    elsif ( $sanity_check != 0 ) {

        unlink $BASEFILENAME

    }

    else {
        if ( $count >= 1 ) {

            if ( not $SILENT ) {
                print "$key section: Wrote $count line(s)\n";
                print ID_REF "$key section: Wrote $count line(s)\n";
            }

        }

        else {
            # Hey, only a header ! Don't keep empty files please
            unlink $BASEFILENAME;
        }
    }

}    # End Insert

####################################################################################################
#############		DF external Section						############
####################################################################################################

# for DF_STORAGE & DF_INODES data, we need to transpose the final data on a per dimension basis

sub df_external_metrics {

    # first argument is the nmon section
    my $nmon_var = shift;

    my @rawdata;
    my $x;
    my @cols;
    my $TS;
    my $n;
    my $sanity_check                  = 0;
    my $sanity_check_timestampfailure = 0;

    my $metric_category = metrics_dict($nmon_var);
    my $nmon_section    = lc $nmon_var;
    my $metric_name     = "os.unix.nmon.$metric_category.$nmon_section";

# Filter rawdata for this section, CPUnn has a special case that contains dynamic number of sub-sections
    @rawdata = grep( /^$nmon_var,/, @nmon );

    if ( @rawdata < 1 ) { return (1); }
    else {
        @rawdataheader = grep( /^$nmon_var,([^T].+),/, @nmon );
        if ( @rawdataheader < 1 ) {
            $msg =
"WARN: hostname: $HOSTNAME :$key section data is not consistent: the data header could not be identified, dropping the section to prevent data inconsistency \n";
            print "$msg";
            print ID_REF "$msg";
            $sanity_check = "1";
        }

        else {
            unless ( open( INSERT, ">$BASEFILENAME.temp" ) ) {
                die("ERROR: Can not open /$BASEFILENAME.temp\n");
            }

        }

    }

    # Sort rawdata
    @rawdata = sort(@rawdata);

    @cols = split( /,/, $rawdata[0] );
    $x = join( ",", @cols[ 2 .. @cols - 1 ] );
    $x =~ s/\%/_PCT/g;
    $x =~ s/\(MB\)/_MB/g;
    $x =~ s/-/_/g;
    $x =~ s/ /_/g;
    $x =~ s/__/_/g;
    $x =~ s/,_/,/g;
    $x =~ s/_,/,/g;
    $x =~ s/^_//;
    $x =~ s/_$//;

    # Count the number fields in header
    my @c                 = $x =~ /,/g;
    my $fieldsheadercount = @c;

    print INSERT (qq|metric_timestamp,metric_name,$x\n|);

    $n = @cols;
    $n = $n - 1;    # number of columns -1

    # Define the starting line to read (exclusion of csv header)
    $startline = 1;

    for ( $i = $startline ; $i < @rawdata ; $i++ ) {

        $TS = $UTC_START + $INTERVAL * ($i);

        @cols = split( /,/, $rawdata[$i] );
        $x = join( ",", @cols[ 2 .. $n ] );
        $x =~ s/,,/,-1,/g;    # replace missing data ",," with a ",-1,"

        my @c              = $x =~ /,/g;
        my $fieldsrawcount = @c;

        # section dynamic name
        $datatype = @cols[0];

        if ( $fieldsrawcount != $fieldsheadercount ) {

            $msg =
"WARN: hostname: $HOSTNAME :$key section is not consistent: $fieldsrawcount fields in data, $fieldsheadercount fields in header, extra fields detected (more fields in data than header), dropping this section to prevent data inconsistency \n";
            print "$msg";
            print ID_REF "$msg";

            $sanity_check = "1";

        }

# If the timestamp could not be found, there is a data anomaly and the section is not consistent
        if ( not $DATETIME{ $cols[1] } ) {

            $sanity_check                  = "1";
            $sanity_check_timestampfailure = "1";

        }

        # If sanity check is ok, write data
        if ( $sanity_check == 0 ) {

            $timestamp = $DATETIME{ @cols[1] };

     # Convert timestamp string to epoch time (from format: YYYY-MM-DD hh:mm:ss)
            my ( $year, $month, $day, $hour, $min, $sec ) = split /\W+/,
              $timestamp;
            my $ZZZZ_epochtime =
              timelocal( $sec, $min, $hour, $day, $month - 1, $year );

            # Write only new data
            print INSERT (qq|$ZZZZ_epochtime,$metric_name,$x\n|);

        }

    }
    print INSERT (qq||);

    # Transposition of the data on a per dimension basis

    #use strict;
    #use warnings;

    my $count = 0;

    my $csvfile = "$BASEFILENAME.temp";
    open( my $FILE, $csvfile ) or die "Can't open $csvfile: $!";

    my $out_file = \*STDOUT;

    # open($out_file,">",....);

    unless ( open( INSERT, ">$BASEFILENAME" ) ) {
        die("ERROR: Can not open /$BASEFILENAME\n");
    }

    my $header =
"metric_timestamp,metric_name,OStype,serialnum,hostname,dimension_mount,dimension_filesystem,_value";
    my @out_head =
      qw(metric_timestamp metric_name dimension_mount dimension_filesystem _value);

    my $csv;
    my $out_csv;

    if ( $csv_module eq 'Text::CSV' ) {
        $csv     = Text::CSV->new();
        $out_csv = Text::CSV->new();
    }
    elsif ( $csv_module eq 'Text::CSV_XS' ) {
        $csv     = Text::CSV_XS->new();
        $out_csv = Text::CSV_XS->new();
    }

    $out_csv->column_names(@out_head);
    $out_csv->combine(@out_head);

    my $l;
    my $metric_timestamp;
    my $full_metric_name;
    my $dimension_mount;
    my $dimension_filesystem;
    my $value;

    # write header
    print INSERT "$header\n";
    $count++;

    my @head = @{ $csv->getline($FILE) };
    $csv->column_names( \@head );
    @head = grep { !/metric_timestamp|metric_name|mount|filesystem/ } @head;
    while ( my $row = $csv->getline_hr($FILE) ) {
        my %out;
        @out{@out_head} =
          @{$row}{ 'metric_timestamp', 'metric_name', 'mount', 'filesystem' };
        for (@head) {
            $out{metric_name} = $_;
            $out{_value}      = $row->{$_};
            $out_csv->combine( map { $out{$_} } @out_head );
            $l = $out_csv->string;

            # filter out the results
            if ( $l =~ m/^(\d+),([^,]*),([^,]*),([^,]*),([^,]*)$/ ) {

                # filter only numbers and positive values
                $metric_timestamp     = $1;
                $full_metric_name     = "$metric_name.$2";
                $dimension_mount      = $3;
                $dimension_filesystem = $4;
                $value                = $5;
                if ( $value =~ m/^[0-9,.E]+$/ ) {
                    print INSERT
"$metric_timestamp,$full_metric_name,$OStype,$SN,$HOSTNAME,$dimension_mount,$dimension_filesystem,$value\n";
                    $count++;
                }
            }

        }
    }

    close(INSERT);
    unlink "$BASEFILENAME.temp";

    # end transposition

    # If we wrote more than the header
    if ( $count > 1 ) {

        if ( $sanity_check == 0 ) {

            if ( not $SILENT ) {
                print "$key section: Wrote $count line(s)\n";
                print ID_REF "$key section: Wrote $count line(s)\n";
            }

        }

        else {
            # Something happened, don't let bad file in place
            unlink $BASEFILENAME;
        }

    }

}    # End Insert

####################################################################################################
#############		NMON TOP Section						############
####################################################################################################

# for TOP data, we need to transpose the final data on a per dimension basis

sub top_metrics {

    # first argument is the section key
    my $key = shift;

    my $sanity_check = 0;

    # define default values for metric store
    my $metric_category = metrics_dict("TOP");
    my $nmon_section    = "top";
    my $metric_name     = "os.unix.nmon.$metric_category.$nmon_section";

    # AIX specific: some systems may generate the WLMclass dimension field
    my $top_has_wlm = "False";

    # Solaris specific dimensions
    my $top_has_project = "False";

    foreach $key (@top_vars) {
        my $BASEFILENAME =
          "$OUTPUT_DIR/${HOSTNAME}_${minute}_${key}.metrics.csv";

        # Open NMON file for reading
        if ( !open( FIC, $file ) ) {
            die(
                "Error while trying to open NMON Source file '" . $file . "'" );
        }

        # If we find the section, enter the process
        if ( grep { /TOP,\d+/ } <FIC> ) {

            @rawdataheader = grep( /^TOP,\+PID,/, @nmon );
            if ( @rawdataheader < 1 ) {
                $msg =
"WARN: hostname: $HOSTNAME :$key section data is not consistent: the data header could not be identified, dropping the section to prevent data inconsistency \n";
                print "$msg";
                print ID_REF "$msg";

                $sanity_check = "1";

            }

            else {

                unless ( open( INSERT, ">$BASEFILENAME.temp" ) ) {
                    die("ERROR: Can not open /$BASEFILENAME\n");
                }

            }

            # Manage AIX dim
            if ( grep { /WLMclass/ } <@rawdataheader> ) {
                $top_has_wlm = "True";
            }

            # Manage Solaris dim
            elsif ( grep { /Project/ } <@rawdataheader> ) {
                $top_has_project = "True";
            }

            # Initialize variables
            my $timestamp = "";

            # Open NMON file for reading
            if ( !open( FIC, $file ) ) {
                die(    "Error while trying to open NMON Source file '"
                      . $file
                      . "'" );
            }

            while ( defined( my $l = <FIC> ) ) {
                chomp $l;

                # Get timestamp"
                if ( ( rindex $l, "ZZZZ," ) > -1 ) {
                    ( my $t1, my $t2, my $timestamptmp1, my $timestamptmp2 ) =
                      split( ",", $l );
                    $timestamp = $timestamptmp2 . " " . $timestamptmp1;
                }

                # TOP Section"

                # Get and write csv header

                if ( $l =~ /^TOP,.PID/ ) {

                    my $x = $l;

                    # convert unwanted characters
                    $x =~ s/\%/pct_/g;

                    # $x =~ s/\W*//g;
                    $x =~ s/\/s/ps/g;    # /s  - ps
                    $x =~ s/\//s/g;      # / - s
                    $x =~ s/\(/_/g;
                    $x =~ s/\)/_/g;
                    $x =~ s/ /_/g;
                    $x =~ s/-/_/g;
                    $x =~ s/_KBps//g;
                    $x =~ s/_tps//g;
                    $x =~ s/[:,]*\s*$//;

                    $x =~ s/\+//g;
                    $x =~ s/\=0//g;

                    # Manage some fields we statically set
                    $x =~ s/TOP,//g;
                    $x =~ s/Time,//g;

                    my $write = metric_timestamp . "," . metric_name . "," . $x;

                    print( INSERT "$write\n" );

                }

                # Get and write NMON section
                if (   ( ( rindex $l, "TOP," ) > -1 )
                    && ( length($timestamp) > 0 ) )
                {

                    ( my @line ) = split( ",", $l );
                    my $section = "TOP";

                    # Convert month pattern to month numbers (eg. %b to %m)
                    $timestamp =~ s/JAN/01/g;
                    $timestamp =~ s/FEB/02/g;
                    $timestamp =~ s/MAR/03/g;
                    $timestamp =~ s/APR/04/g;
                    $timestamp =~ s/MAY/05/g;
                    $timestamp =~ s/JUN/06/g;
                    $timestamp =~ s/JUL/07/g;
                    $timestamp =~ s/AUG/08/g;
                    $timestamp =~ s/SEP/09/g;
                    $timestamp =~ s/OCT/10/g;
                    $timestamp =~ s/NOV/11/g;
                    $timestamp =~ s/DEC/12/g;

                    my ( $day, $month, $year, $hour, $min, $sec ) =
                      split /\W+/, $timestamp;
                    my $ZZZZ_epochtime =
                      timelocal( $sec, $min, $hour, $day, $month - 1, $year );

                    my $write =
                      $ZZZZ_epochtime . "," . $metric_name . "," . $line[1];
                    my $i = 3
                      ; ###########################################################################

                    while ( $i <= $#line ) {
                        $write = $write . ',' . $line[$i];
                        $i     = $i + 1;
                    }

                    # write
                    print( INSERT $write . "\n" );

                }

            }

            close(INSERT);

            # Transposition of the TOP data on a per dimension basis

            #use strict;
            #use warnings;

            my $count = 0;
            my $header;
            my @out_head;

            my $csvfile = "$BASEFILENAME.temp";
            open( my $FILE, $csvfile ) or die "Can't open $csvfile: $!";

            my $out_file = \*STDOUT;

            # open($out_file,">",....);

            unless ( open( INSERT, ">$BASEFILENAME" ) ) {
                die("ERROR: Can not open /$BASEFILENAME\n");
            }

            # Manage AIX dim
            if ( $top_has_wlm eq "True" ) {
                $header =
"metric_timestamp,metric_name,OStype,serialnum,hostname,dimension_Command,dimension_PID,dimension_WLMclass,_value";
                @out_head =
                  qw(metric_timestamp metric_name dimension_Command dimension_PID dimension_VMWclass _value);
            }

            # Manage Solaris dim
            elsif ( $top_has_project eq "True" ) {
                $header =
"metric_timestamp,metric_name,OStype,serialnum,hostname,dimension_Command,dimension_PID,dimension_Project,dimension_Zone,_value";
                @out_head =
                  qw(metric_timestamp metric_name dimension_Command dimension_PID dimension_Project dimension_Zone _value);
            }

            else {
                $header =
"metric_timestamp,metric_name,OStype,serialnum,hostname,dimension_Command,dimension_PID,_value";
                @out_head =
                  qw(metric_timestamp metric_name dimension_Command dimension_PID _value);
            }

            my $csv;
            my $out_csv;

            if ( $csv_module eq 'Text::CSV' ) {
                $csv     = Text::CSV->new();
                $out_csv = Text::CSV->new();
            }
            elsif ( $csv_module eq 'Text::CSV_XS' ) {
                $csv     = Text::CSV_XS->new();
                $out_csv = Text::CSV_XS->new();
            }

            $out_csv->column_names(@out_head);
            $out_csv->combine(@out_head);

            my $l;

            # write header
            print INSERT "$header\n";
            $count++;

            my @head = @{ $csv->getline($FILE) };
            $csv->column_names( \@head );

            # Manage AIX dim
            if ( $top_has_wlm eq "True" ) {
                @head =
                  grep { !/metric_timestamp|metric_name|Command|PID|WLMclass/ }
                  @head;
            }

            # Manage Solaris dim
            elsif ( $top_has_project eq "True" ) {
                @head = grep {
                    !/metric_timestamp|metric_name|Command|PID|Project|Zone/
                } @head;
            }

            else {
                @head =
                  grep { !/metric_timestamp|metric_name|Command|PID/ } @head;
            }

            while ( my $row = $csv->getline_hr($FILE) ) {
                my %out;

                # Manage AIX dim
                if ( $top_has_wlm eq "True" ) {
                    @out{@out_head} = @{$row}{
                        'metric_timestamp', 'metric_name',
                        'Command',          'PID',
                        'WLMclass'
                    };
                }

                # Manage Solaris dim
                elsif ( $top_has_project eq "True" ) {
                    @out{@out_head} = @{$row}{
                        'metric_timestamp', 'metric_name',
                        'Command',          'PID',
                        'Project',          'Zone'
                    };
                }

                else {
                    @out{@out_head} =
                      @{$row}{ 'metric_timestamp', 'metric_name', 'Command',
                        'PID' };
                }

                for (@head) {
                    $out{metric_name} = $_;
                    $out{_value}      = $row->{$_};
                    $out_csv->combine( map { $out{$_} } @out_head );
                    $l = $out_csv->string;

                    my $value;
                    my $timestamp;
                    my $full_metric_name;
                    my $full_data;

                    # remove any garbage
                    if ( $l =~ m/^(\d+),([^,]*),(.*)$/ ) {

                        $timestamp        = $1;
                        $full_metric_name = "$metric_name.$2";
                        $full_data        = $3;

                        if ( $full_data =~ m/.*,([0-9\.\-]*)/ ) {
                            $value = $1;

                            # Save money and exclude non useful values
                            if ( $value > 0 ) {
                                print INSERT
"$timestamp,$full_metric_name,$OStype,$SN,$HOSTNAME,$full_data \n";
                                $count++;
                            }

                        }

                    }

                }
            }

            close(INSERT);
            unlink "$BASEFILENAME.temp";

            # end transposition

            # If we wrote more than the header
            if ( $count > 1 ) {

                if ( $sanity_check == 0 ) {

                    if ( not $SILENT ) {
                        print "$key section: Wrote $count line(s)\n";
                        print ID_REF "$key section: Wrote $count line(s)\n";
                    }

                }

                else {
                    # Something happened, don't let bad file in place
                    unlink $BASEFILENAME;
                }

            }

        }    # end find the section

    }    # end foreach

}

####################################################################################################
#############		NMON UARG Section						############
####################################################################################################

sub uarg_events {

    # first argument is the nmon section
    my $nmon_var = shift;

    # UARG Section (specific)
    # Applicable for OStype AIX, Linux, Solaris or Unknown

    if (   $OStype eq "AIX"
        || $OStype eq "Linux"
        || $OStype eq "Solaris"
        || $OStype eq "Unknown" )
    {

        my $sanity_check = 0;

        foreach $key (@uarg_vars) {
            $BASEFILENAME =
              "$OUTPUT_DIR/${HOSTNAME}_${minute}_${key}.events.csv";

            # Open NMON file for reading
            if ( !open( FIC, $file ) ) {
                die(    "Error while trying to open NMON Source file '"
                      . $file
                      . "'" );
            }

            # If we find the section, enter the process
            if ( grep { /UARG,T/ } <FIC> ) {

                @rawdataheader = grep( /^UARG,\+Time,/, @nmon );
                if ( @rawdataheader < 1 ) {
                    $msg =
"WARN: hostname: $HOSTNAME :$key section data is not consistent: the data header could not be identified, dropping the section to prevent data inconsistency \n";
                    print "$msg";
                    print ID_REF "$msg";

                    $sanity_check = "1";

                }

                else {

                    unless ( open( INSERT, ">$BASEFILENAME" ) ) {
                        die("ERROR: Can not open /$BASEFILENAME\n");
                    }

                }

                # Open NMON file for reading
                if ( !open( FIC, $file ) ) {
                    die(    "Error while trying to open NMON Source file '"
                          . $file
                          . "'" );
                }

                # Initialize variables
                my $timestamp = "";
                $count = 0;

                while ( defined( my $l = <FIC> ) ) {
                    chomp $l;

                    # Get timestamp"
                    if ( ( rindex $l, "ZZZZ," ) > -1 ) {
                        ( my $t1, my $t2, my $timestamptmp1, my $timestamptmp2 )
                          = split( ",", $l );
                        $timestamp = $timestamptmp2 . " " . $timestamptmp1;
                    }

                    # UARG Section"

                    # Get and write csv header

                    if ( $l =~ /^UARG,\+Time,/ ) {

                        my $x = $l;

                        # convert unwanted characters
                        $x =~ s/\%/pct_/g;

                        # $x =~ s/\W*//g;
                        $x =~ s/\/s/ps/g;    # /s  - ps
                        $x =~ s/\//s/g;      # / - s
                        $x =~ s/\(/_/g;
                        $x =~ s/\)/_/g;
                        $x =~ s/ /_/g;
                        $x =~ s/-/_/g;
                        $x =~ s/_KBps//g;
                        $x =~ s/_tps//g;
                        $x =~ s/[:,]*\s*$//;

                        $x =~ s/\+//g;
                        $x =~ s/\=0//g;

                        $x =~ s/\+Time/Time/g;

                        # Manage some fields we statically set
                        $x =~ s/UARG,//g;
                        $x =~ s/Time,//g;

                     # Specifically for UARG, set OS type based on header fields

                        if ( $l =~
/^UARG,\+Time,PID,PPID,COMM,THCOUNT,USER,GROUP,FullCommand/
                          )
                        {

                            my $write =
                                type . ","
                              . serialnum . ","
                              . hostname . ","
                              . OStype . ","
                              . ZZZZ . ","
                              . PID . ","
                              . PPID . ","
                              . COMM . ","
                              . THCOUNT . ","
                              . USER . ","
                              . GROUP . ","
                              . FullCommand;

                            print( INSERT "$write\n" );
                            $count++;

                        }

                        elsif ( $l =~ /^UARG,\+Time,PID,ProgName,FullCommand/ )
                        {

                            my $write =
                                type . ","
                              . serialnum . ","
                              . hostname . ","
                              . OStype . ","
                              . ZZZZ . ","
                              . PID . ","
                              . ProgName . ","
                              . FullCommand;

                            print( INSERT "$write\n" );
                            $count++;

                        }

                    }

                    # Get and write NMON section
                    if (   ( ( rindex $l, "UARG," ) > -1 )
                        && ( length($timestamp) > 0 ) )
                    {

                        ( my @line ) = split( ",", $l );
                        my $section = "UARG";

                        # Convert month pattern to month numbers (eg. %b to %m)
                        $timestamp =~ s/JAN/01/g;
                        $timestamp =~ s/FEB/02/g;
                        $timestamp =~ s/MAR/03/g;
                        $timestamp =~ s/APR/04/g;
                        $timestamp =~ s/MAY/05/g;
                        $timestamp =~ s/JUN/06/g;
                        $timestamp =~ s/JUL/07/g;
                        $timestamp =~ s/AUG/08/g;
                        $timestamp =~ s/SEP/09/g;
                        $timestamp =~ s/OCT/10/g;
                        $timestamp =~ s/NOV/11/g;
                        $timestamp =~ s/DEC/12/g;

                        # For AIX

# In this section, we statically expect 7 fields: PID,PPID,COMM,THCOUNT,USER,GROUP,FullCommand
# The FullCommand may be very problematic as it may almost contain any kind of char, comma included
# This field will have " separator added

                        if ( $l =~
m/^UARG\,T\d+\,\s*([0-9]*)\s*\,\s*([0-9]*)\s*\,\s*([a-zA-Z\-\/\_\:\.0-9]*)\s*\,\s*([0-9]*)\s*\,\s*([a-zA-Z\-\/\_\:\.0-9]*\s*)\,\s*([a-zA-Z\-\/\_\:\.0-9]*)\s*\,(.+)/
                          )
                        {

                            $PID         = $1;
                            $PPID        = $2;
                            $COMM        = $3;
                            $THCOUNT     = $4;
                            $USER        = $5;
                            $GROUP       = $6;
                            $FullCommand = $7;

                            $x = '"'
                              . $PID . '","'
                              . $PPID . '","'
                              . $COMM . '","'
                              . $THCOUNT . '","'
                              . $USER . '","'
                              . $GROUP . '","'
                              . $FullCommand . '"';

                            my $write =
                                $section . ","
                              . $SN . ","
                              . $HOSTNAME . ","
                              . $OStype . ","
                              . $timestamp . ","
                              . $x;

                            print( INSERT $write . "\n" );
                            $count++;

                        }

                        # For Linux

# In this section, we statically expect 3 fields: PID,ProgName,FullCommand
# The FullCommand may be very problematic as it may almost contain any kind of char, comma included
# Let's separate groups and insert " delimiter

                        if ( $l =~
m/^UARG\,T\d+\,([0-9]*)\,([a-zA-Z\-\/\_\:\.0-9]*)\,(.+)/
                          )
                        {

                            $PID         = $1;
                            $ProgName    = $2;
                            $FullCommand = $3;

                            $x = '"'
                              . $PID . '","'
                              . $ProgName . '","'
                              . $FullCommand . '"';

                            my $write =
                                $section . ","
                              . $SN . ","
                              . $HOSTNAME . ","
                              . $OStype . ","
                              . $timestamp . ","
                              . $x;

                            print( INSERT $write . "\n" );
                            $count++;

                        }

                    }

                }

                # If we wrote more than the header
                if ( $count >= 1 ) {

                    if ( $sanity_check == 0 ) {

                        if ( not $SILENT ) {
                            print "$key section: Wrote $count line(s)\n";
                            print ID_REF "$key section: Wrote $count line(s)\n";
                        }

                    }

                    else {
                        # Something happened, don't let bad file in place
                        unlink $BASEFILENAME;
                    }

                }

                # Else remove the file without more explanations
                else {
                    unlink $BASEFILENAME;
                }

            }    # end find the section

        }    # end foreach

    }

}

##################################################################
## Extract data for Variable fields
##################################################################

sub multi_dimension_metrics {

    # first argument is the nmon section
    my $nmon_var = shift;

    my @rawdata;
    my $j;
    my @cols;
    my $TS;
    my $n;
    my @devices;
    my $sanity_check                  = 0;
    my $sanity_check_timestampfailure = 0;
    $count = 0;

    # define default values for metric store
    my $metric_category;
    my $nmon_section;
    my $metric_name;

    # Manage CPUnn specific case
    if ( $nmon_var =~ m/CPU[0-9]+/ ) {
        $metric_category = metrics_dict("CPUnn");
        $nmon_section    = "cpunn";
        $metric_name = "os.unix.nmon.$metric_category.$nmon_section.$nmon_var";
    }
    else {
        $metric_category = metrics_dict($nmon_var);
        $nmon_section    = lc $nmon_var;
        $metric_name     = "os.unix.nmon.$metric_category.$nmon_section";
    }

    # retrieve rawdata for this section
    @rawdata = grep( /^$nmon_var,/, @nmon );

    if ( @rawdata < 1 ) { return (1); }
    else {

        # retrieve the header
        @rawdataheader = grep( /^$nmon_var,([^T].+),/, @nmon );

        if ( @rawdataheader < 1 ) {
            $msg =
"WARN: hostname: $HOSTNAME :$key section data is not consistent: the data header could not be identified, dropping the section to prevent data inconsistency \n";
            print "$msg";
            print ID_REF "$msg";

        }

        else {

            unless ( open( INSERT, ">$BASEFILENAME" ) ) {
                die("ERROR: Can not open /$BASEFILENAME\n");
            }

        }

    }

    @rawdata = sort(@rawdata);

    $rawdata[0] =~ s/\%/_PCT/g;
    $rawdata[0] =~ s/\(/_/g;
    $rawdata[0] =~ s/\)/_/g;
    $rawdata[0] =~ s/ /_/g;
    $rawdata[0] =~ s/__/_/g;
    $rawdata[0] =~ s/,_/,/g;
    $rawdata[0] =~ s/_,/,/g;
    $rawdata[0] =~ s/_$//g;

    @devices = split( /,/, $rawdata[0] );

    print INSERT (
        qq|metric_timestamp,metric_name,OStype,serialnum,hostname,_value\n|);

    $n = @rawdata;
    $n--;

    # Count the number fields in header
    my @c                 = $rawdata[0] =~ /,/g;
    my $fieldsheadercount = @c;

    # Count the number fields in first line of data
    my @c              = $rawdata[1] =~ /,/g;
    my $fieldsrawcount = @c;

# if the number of fields in header and first line of data differs, the data is not consistent
    if ( $fieldsrawcount != $fieldsheadercount ) {
        $sanity_check = "1";
    }

    for ( $i = 1 ; $i < @rawdata ; $i++ ) {

        $TS = $UTC_START + $INTERVAL * ($i);
        $rawdata[$i] =~ s/,$//;
        @cols = split( /,/, $rawdata[$i] );

        $timestamp = $DATETIME{ $cols[1] };

     # Convert timestamp string to epoch time (from format: YYYY-MM-DD hh:mm:ss)
        my ( $year, $month, $day, $hour, $min, $sec ) = split /\W+/, $timestamp;

        if ( $month == 0 ) {
            print
"ERROR, section $key has failed to identify the timestamp of these data, affecting current timestamp which may be inaccurate\n";
            my ( $sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst )
              = localtime(time);
            $month = $mon;
            $day   = $mday;
        }

        my $ZZZZ_epochtime =
          timelocal( $sec, $min, $hour, $day, $month - 1, $year );

        # Set data and verify structure
        $l =
"$ZZZZ_epochtime,$metric_name.$devices[2],$OStype,$SN,$HOSTNAME,$cols[2]";

        # Verify structure, if value has not value, set to -1
        if ( $l =~ m/^.*,$/ ) {
            $l = "$l-1";
        }

        if ($SHOW_ZERO) {
            # remove metrics with: -1.0 / -1
            if (   $l !~ m/.*\-1\.0$/
                && $l !~ m/.*\-1$/ )
            {
                print INSERT (qq|$l\n|);
                $count++;
            }
        }
        else {
            # remove metrics with: -1.0 / -1 / -0.0 / 0.0 / 0
            if (   $l !~ m/.*\-1\.0$/
                && $l !~ m/.*\-1$/
                && $l !~ m/.*\-0\.0$/
                && $l !~ m/.*,0\.0$/
                && $l !~ m/.*,0\.00$/
                && $l !~ m/.*,0$/ )
            {
                print INSERT (qq|$l\n|);
                $count++;
            }
        }
        for ( $j = 3 ; $j < @cols ; $j++ ) {

            $finaldata =
"$ZZZZ_epochtime,$metric_name.$devices[$j],$OStype,$SN,$HOSTNAME,$cols[$j]";

# If the timestamp could not be found, there is a data anomaly and the section is not consistent
            if ( not $DATETIME{ $cols[1] } ) {

                $sanity_check                  = "1";
                $sanity_check_timestampfailure = "1";

            }

            # If sanity check has not failed, write data
            if ( $sanity_check != "1" ) {

                $timestamp = $DATETIME{ $cols[1] };

     # Convert timestamp string to epoch time (from format: YYYY-MM-DD hh:mm:ss)
                my ( $year, $month, $day, $hour, $min, $sec ) = split /\W+/,
                  $timestamp;
                my $ZZZZ_epochtime =
                  timelocal( $sec, $min, $hour, $day, $month - 1, $year );

                # Set data and verify structure
                $l =
"$ZZZZ_epochtime,$metric_name.$devices[$j],$OStype,$SN,$HOSTNAME,$cols[$j]";

                # Verify structure, if value has not value, set to -1.0
                if ( $l =~ m/^.*,$/ ) {
                    $l = "$l-1\.0";
                }

                if ($SHOW_ZERO) {
                    # remove metrics with: -1.0 / -1
                    if (   $l !~ m/.*\-1\.0$/
                        && $l !~ m/.*\-1$/ )
                    {
                        print INSERT (qq|$l\n|);
                        $count++;
                    }
                }
                else {
                    # remove metrics with: -1.0 / -1 / -0.0 / 0.0 / 0
                    if (   $l !~ m/.*\-1\.0$/
                        && $l !~ m/.*\-1$/
                        && $l !~ m/.*\-0\.0$/
                        && $l !~ m/.*,0\.0$/
                        && $l !~ m/.*,0\.00$/
                        && $l !~ m/.*,0$/ )
                    {
                        print INSERT (qq|$l\n|);
                        $count++;
                    }
                }

            }

        }
        if ( $i < $n ) { print INSERT (""); }

# For CPU_ALL and LPAR, we add the combo logical_cpus / virtual_cpus as part of the metrics
        if ( $nmon_var eq 'CPU_ALL' || $nmon_var eq 'LPAR' ) {
            print INSERT
"$ZZZZ_epochtime,$metric_name.logical_cpus,$OStype,$SN,$HOSTNAME,$logical_cpus\n";
            $count++;
            print INSERT
"$ZZZZ_epochtime,$metric_name.virtual_cpus,$OStype,$SN,$HOSTNAME,$virtual_cpus\n";
            $count++;
        }

    }

    print INSERT (qq||);

    # If sanity check has failed, remove data
    if ( $sanity_check != 0 && $sanity_check_timestampfailure != 0 ) {

        $msg =
"ERROR: hostname: $HOSTNAME :$key section is not consistent: Detected anomalies in events timestamp, dropping this section to prevent data inconsistency \n";
        print "$msg";
        print ID_REF "$msg";

        close(INSERT);
        unlink $BASEFILENAME;
    }

    elsif ( $sanity_check != 0 && $fieldsrawcount != $fieldsheadercount ) {
        $msg =
"WARN: hostname: $HOSTNAME :$key section is not consistent: $fieldsrawcount fields in data, $fieldsheadercount fields in header, extra fields detected (more fields in data than header), dropping this section to prevent data inconsistency \n";
        print "$msg";
        print ID_REF "$msg";

        close(INSERT);
        unlink $BASEFILENAME;

    }

    elsif ( $sanity_check != 0 ) {

        close(INSERT);
        unlink $BASEFILENAME

    }

    else {
        if ( $count >= 1 ) {

            if ( not $SILENT ) {
                print "$key section: Wrote $count line(s)\n";
                print ID_REF "$key section: Wrote $count line(s)\n";
            }

            # Close
            close(INSERT);

        }
        else {
            # Hey, only a header ! Don't keep empty files please
            close(INSERT);
            unlink $BASEFILENAME;
        }
    }

}    # End Insert

##################################################################
## Extract data for mono dimension sections
##################################################################

sub mono_dimension_metrics {

    # first argument is the nmon section
    my $nmon_var = shift;

    my @rawdata;
    my $j;
    my @cols;
    my $TS;
    my $n;
    my @devices;
    my $sanity_check                  = 0;
    my $sanity_check_timestampfailure = 0;
    $count = 0;

    # define default values for metric store
    my $metric_category = metrics_dict($nmon_var);
    my $nmon_section    = lc $nmon_var;
    my $metric_name     = "os.unix.nmon.$metric_category.$nmon_section";

    # verify if this is a DISK incremented section
    if ( $nmon_var =~ m/^(DISK[A-Z]*)\d*/ ) {
        my $submetric_name = lc $1;
        $metric_name = "os.unix.nmon.$metric_category.$submetric_name";
    }

    # retrieve rawdata for this section
    @rawdata = grep( /^$nmon_var,/, @nmon );

    if ( @rawdata < 1 ) { return (1); }
    else {

        # retrieve the header
        @rawdataheader = grep( /^$nmon_var,([^T].+),/, @nmon );

        if ( @rawdataheader < 1 ) {
            $msg =
"WARN: hostname: $HOSTNAME :$key section data is not consistent: the data header could not be identified, dropping the section to prevent data inconsistency \n";
            print "$msg";
            print ID_REF "$msg";

        }

        else {

            unless ( open( INSERT, ">$BASEFILENAME" ) ) {
                die("ERROR: Can not open /$BASEFILENAME\n");
            }

        }

    }

    @rawdata = sort(@rawdata);

    $rawdata[0] =~ s/\%/_PCT/g;
    $rawdata[0] =~ s/\(/_/g;
    $rawdata[0] =~ s/\)/_/g;
    $rawdata[0] =~ s/ /_/g;
    $rawdata[0] =~ s/__/_/g;
    $rawdata[0] =~ s/,_/,/g;
    $rawdata[0] =~ s/_,/,/g;
    $rawdata[0] =~ s/_$//g;

    @devices = split( /,/, $rawdata[0] );

    # Count the number fields in header
    my @c                 = $rawdata[0] =~ /,/g;
    my $fieldsheadercount = @c;

    # Count the number fields in first line of data
    my @c              = $rawdata[1] =~ /,/g;
    my $fieldsrawcount = @c;

# if the number of fields in header and first line of data differs, the data is not consistent
    if ( $fieldsrawcount != $fieldsheadercount ) {
        $sanity_check = "1";
    }

# For JFSFILE and JFSINODE, we use "dimension_mount" instead of regular "dimension_device" for the mount point dimension
# this is due to make easier the merge operation between JFSFILE and DF_STORAGE external collection

    my $header;

    if ( $nmon_var eq "JFSFILE" || $nmon_var eq "JFSINODE" ) {
        $header =
"metric_timestamp,metric_name,OStype,serialnum,hostname,dimension_mount,_value";
    }

    else {
        $header =
"metric_timestamp,metric_name,OStype,serialnum,hostname,dimension_device,_value";
    }

    print INSERT (qq|$header\n|);

    $n = @rawdata;
    $n--;
    for ( $i = 1 ; $i < @rawdata ; $i++ ) {

        $TS = $UTC_START + $INTERVAL * ($i);
        $rawdata[$i] =~ s/,$//;
        @cols = split( /,/, $rawdata[$i] );

        $timestamp = $DATETIME{ $cols[1] };

     # Convert timestamp string to epoch time (from format: YYYY-MM-DD hh:mm:ss)
        my ( $year, $month, $day, $hour, $min, $sec ) = split /\W+/, $timestamp;

        if ( $month == 0 ) {
            print
"ERROR, section $key has failed to identify the timestamp of these data, affecting current timestamp which may be inaccurate\n";
            my ( $sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst )
              = localtime(time);
            $month = $mon;
            $day   = $mday;
        }

        my $ZZZZ_epochtime =
          timelocal( $sec, $min, $hour, $day, $month - 1, $year );

        # Set data and verify structure
        $l =
"$ZZZZ_epochtime,$metric_name,$OStype,$SN,$HOSTNAME,$devices[2],$cols[2]";

        # Verify structure, if value has not value, set to -1
        if ( $l =~ m/^.*,$/ ) {
            $l = "$l-1";
        }

        if ($SHOW_ZERO) {
            # no data transposition required
            # Only write metrics!= to null, -nan
            if (   $l !~ m/^.*,$/
                && $l !~ m/^.*,\-nan$/ )
            {
                # Write
                print INSERT (qq|$l\n|);
                $count++;
            }
        }
        else {
            # no data transposition required
            if ($SHOW_ZERO) {
                # Only write metrics!= to null, -nan
                if (   $l !~ m/^.*,$/
                    && $l !~ m/^.*,\-nan$/ )
                {
                    # Write
                    print INSERT (qq|$l\n|);
                    $count++;
                }
            }
            else {
                # Only write metrics!= to null, 0.0, 0, -nan
                if (   $l !~ m/^.*,$/
                    && $l !~ m/^.*,0\.0$/
                    && $l !~ m/^.*,0$/
                    && $l !~ m/^.*,\-nan$/ )
                {
                    # Write
                    print INSERT (qq|$l\n|);
                    $count++;
                }
            }
        }

        # with data transposition
        for ( $j = 3 ; $j < @cols ; $j++ ) {

            $finaldata =
"$ZZZZ_epochtime,$metric_name,$OStype,$SN,$HOSTNAME,$devices[$j],$cols[$j]";

# If the timestamp could not be found, there is a data anomaly and the section is not consistent
            if ( not $DATETIME{ $cols[1] } ) {

                $sanity_check                  = "1";
                $sanity_check_timestampfailure = "1";

            }

            # If sanity check has not failed, write data
            if ( $sanity_check != "1" ) {

                $timestamp = $DATETIME{ $cols[1] };

     # Convert timestamp string to epoch time (from format: YYYY-MM-DD hh:mm:ss)
                my ( $year, $month, $day, $hour, $min, $sec ) = split /\W+/,
                  $timestamp;
                my $ZZZZ_epochtime =
                  timelocal( $sec, $min, $hour, $day, $month - 1, $year );

                # Set data and verify structure
                $l =
"$ZZZZ_epochtime,$metric_name,$OStype,$SN,$HOSTNAME,$devices[$j],$cols[$j]";

                if ($SHOW_ZERO) {
                    # no data transposition required
                    # Only write metrics!= to null, -nan
                    if (   $l !~ m/^.*,$/
                        && $l !~ m/^.*,\-nan$/ )
                    {
                        # Write
                        print INSERT (qq|$l\n|);
                        $count++;
                    }
                }
                else {
                    # no data transposition required
                    # no data transposition required
                    if ($SHOW_ZERO) {
                        # Only write metrics!= to null, -nan
                        if (   $l !~ m/^.*,$/
                            && $l !~ m/^.*,\-nan$/ )
                        {
                            # Write
                            print INSERT (qq|$l\n|);
                            $count++;
                        }
                    }
                    else {
                        # Only write metrics!= to null, 0.0, 0, -nan
                        if (   $l !~ m/^.*,$/
                            && $l !~ m/^.*,0\.0$/
                            && $l !~ m/^.*,0$/
                            && $l !~ m/^.*,\-nan$/ )
                        {
                            # Write
                            print INSERT (qq|$l\n|);
                            $count++;
                        }
                    }
                }

            }

        }
        if ( $i < $n ) { print INSERT (""); }
    }
    print INSERT (qq||);

    # If sanity check has failed, remove data
    if ( $sanity_check != 0 && $sanity_check_timestampfailure != 0 ) {

        $msg =
"ERROR: hostname: $HOSTNAME :$key section is not consistent: Detected anomalies in events timestamp, dropping this section to prevent data inconsistency \n";
        print "$msg";
        print ID_REF "$msg";

        close(INSERT);
        unlink $BASEFILENAME;
    }

    elsif ( $sanity_check != 0 && $fieldsrawcount != $fieldsheadercount ) {

        $msg =
"WARN: hostname: $HOSTNAME :$key section is not consistent: $fieldsrawcount fields in data, $fieldsheadercount fields in header, extra fields detected (more fields in data than header), dropping this section to prevent data inconsistency \n";
        print "$msg";
        print ID_REF "$msg";

        $sanity_check = "1";

        # If section is NET, create an empty state file
        if ( $nmon_var eq "NET" ) {
            my $f;
            open( $f, '>', $OUTDATED_NETIF_NMON_STATE )
              or die "Unable to open file $filename : $!";
            close($f) or die "Unable to close file : $filename $!";
        }

    }

    elsif ( $sanity_check != 0 ) {

        close(INSERT);
        unlink $BASEFILENAME

    }

    else {
        if ( $count >= 1 ) {

            if ( not $SILENT ) {
                print "$key section: Wrote $count line(s)\n";
                print ID_REF "$key section: Wrote $count line(s)\n";
            }

            # Close
            close(INSERT);

        }
        else {
            # Hey, only a header ! Don't keep empty files please
            close(INSERT);
            unlink $BASEFILENAME;
        }
    }

}    # End Insert

########################################################
###	Get an nmon setting from csv file            ###
###	finds first occurance of $search             ###
###	Return the selected column...$return_col     ###
###	Syntax:                                      ###
###     get_setting($search,$col_to_return,$separator)##
########################################################

sub get_setting {

    my $i;
    my $value = "-1";
    my ( $search, $col, $separator ) = @_;    # search text, $col, $separator

    for ( $i = 0 ; $i < @nmon ; $i++ ) {

        if ( $nmon[$i] =~ /$search/ ) {
            $value = ( split( /$separator/, $nmon[$i] ) )[$col];
            $value =~ s/["']*//g;             #remove non alphanum characters
            return ($value);
        }    # end if

    }    # end for

    return ($value);

}    # end get_setting

#####################
##  Clean up       ##
#####################

sub clean_up_line {

    # remove characters not compatible with nmon variable
    # Max rrdtool variable length is 19 chars
    # Variable can not contain special characters (% - () )
    my ($x) = @_;

    # print ("clean_up, before: $i\t$nmon[$i]\n");
    $x =~ s/\%/Pct/g;

    # $x =~ s/\W*//g;
    $x =~ s/\/s/ps/g;    # /s  - ps
    $x =~ s/\//s/g;      # / - s
    $x =~ s/\(/_/g;
    $x =~ s/\)/_/g;
    $x =~ s/ /_/g;
    $x =~ s/-/_/g;
    $x =~ s/_KBps//g;
    $x =~ s/_tps//g;
    $x =~ s/[:,]*\s*$//;
    $retval = $x;

}    # end clean up

##########################################
##  Extract headings from nmon csv file ##
##########################################

sub initialize {

    %MONTH2NUMBER = (
        "jan", 1, "feb", 2, "mar", 3, "apr", 4,  "may", 5,  "jun", 6,
        "jul", 7, "aug", 8, "sep", 9, "oct", 10, "nov", 11, "dec", 12
    );

    @MONTH2ALPHA = (
        "junk", "jan", "feb", "mar", "apr", "may", "jun", "jul",
        "aug",  "sep", "oct", "nov", "dec"
    );

}    # end initialize

# Get data from nmon file, extract specific data fields (hostname, date, ...)
sub get_nmon_data {

    my $key;
    my $x;
    my $category;
    my %toc;
    my @cols;

    # Read nmon file
    unless ( open( FILE, $FILENAME ) ) { return (1); }
    our @nmon = <FILE>;    # input entire file
    close(FILE);
    chomp(@nmon);

    # Cleanup nmon data remove trainig commas and colons
    for ( $i = 0 ; $i < @nmon ; $i++ ) {
        $nmon[$i] =~ s/[:,]*\s*$//;
    }

    # Get nmon/server settings (search string, return column, delimiter)
    $AIXVER = &get_setting( "AIX",  2, "," );
    $DATE   = &get_setting( "date", 2, "," );

# The hostname value returned by nmon and nmonparser.py can be overridden by setting the option
# override_sys_hostname="1" in local/nmon.conf
# If so, we will search for a value in $SPLUNK_HOME/etc/system/local/inputs.conf to set the hostname
# default is use system host name (see above)
# If the option is activated, and we failed finding a value, fall back to system hostname (see above)

# serial number override:
# the serial number used to achieve the frameID enrichment within the application can be overridden using the option:
# override_sys_serialnum="1" in local/nmon.conf or /etc/nmon.conf
# If so, we will search for the appropriated value in nmon.conf with the configuration name:
# override_sys_serialnum_value="<string>"

    # Allow hostname os
    if ($USE_FQDN) {
        $HOSTNAME = hostfqdn();
    }
    else {
        $HOSTNAME = &get_setting( "host", 2, "," );
    }

    my $SPLUNK_HOSTNAME_OVERRIDE = False;
    my $SERIALNUM_OVERRIDE       = False;
    my $SERIALNUM_OVERRIDE_VALUE = "none";
    my $NMON_SPLUNK_LOCAL_CONF   = "$APP/local/nmon.conf";
    my $NMON_SYS_LOCAL_CONF      = "/etc/nmon.conf";
    my $NMON_LOCAL_CONF;
    my $SPLUNK_SYSTEM_INPUTS = "$SPLUNK_HOME/etc/system/local/inputs.conf";

    # Define the local conf with the higher priority
    if ( -e $NMON_SYS_LOCAL_CONF ) {
        $NMON_LOCAL_CONF = $NMON_SYS_LOCAL_CONF;
    }
    elsif ( -e $NMON_SPLUNK_LOCAL_CONF ) {
        $NMON_LOCAL_CONF = $NMON_SPLUNK_LOCAL_CONF;
    }
    else {
        $NMON_LOCAL_CONF = "none";
    }

    # Load config configuration
    if ( $NMON_LOCAL_CONF ne "none" && -e $NMON_LOCAL_CONF ) {

        open( NMON_LOCAL_CONF, "< $NMON_LOCAL_CONF" )
          or die "ERROR: Can't open $NMON_LOCAL_CONF : $!";
        chomp $NMON_LOCAL_CONF;

        while ( defined( my $l = <NMON_LOCAL_CONF> ) ) {
            chomp $l;

            if ( $l =~ m/^override_sys_serialnum=\"1\"/ ) {
                $SERIALNUM_OVERRIDE = True;
            }

            if ( $l =~ m/^override_sys_serialnum_value=\"([a-zA-Z0-9\-\_]*)\"/ )
            {
                $SERIALNUM_OVERRIDE_VALUE = $1;
            }

            # if hostname override, open splunk local configuration
            if ( $l =~ m/^override_sys_hostname=\"1\"/ ) {
                $SPLUNK_HOSTNAME_OVERRIDE = True;
            }

            if ( $SPLUNK_HOSTNAME_OVERRIDE eq "True" ) {

                if ( -e $SPLUNK_SYSTEM_INPUTS ) {

                    # Open
                    open FILE, '+<', "$SPLUNK_SYSTEM_INPUTS"
                      or die "$time ERROR:$!\n";

                    while ( defined( my $l = <FILE> ) ) {
                        chomp $l;

                        if ( $l =~ m/host\s*=\s*(.+)/ ) {

                            # break at first occurrence
                            $splunk_hostname = $1;
                            last;
                        }

                    }

                    # if not hostname could be found
                    if ( $splunk_hostname eq "" ) {
                        $SPLUNK_HOSTNAME_OVERRIDE = False;
                    }

                    close SPLUNK_SYSTEM_INPUTS;
                }

            }

        }

        close NMON_LOCAL_CONF;

    }

    # hostname override
    if ( $SPLUNK_HOSTNAME_OVERRIDE eq "True" ) {
        $HOSTNAME = $splunk_hostname;
    }

    # serialnum override
    if ( $SERIALNUM_OVERRIDE eq "True" ) {
        $SN = $SERIALNUM_OVERRIDE_VALUE;
    }

    $INTERVAL = &get_setting( "interval", 2, "," );    # nmon sampling interval

    $MEMORY  = &get_setting( qq|lsconf,"Good Memory Size:|, 1, ":" );
    $MODEL   = &get_setting( "modelname",                   3, '\s+' );
    $NMONVER = &get_setting( "version",                     2, "," );

    $SNAPSHOTS = &get_setting( "snapshots", 2, "," );    # number of readings

    $STARTTIME = &get_setting( "AAA,time", 2, "," );
    ( $HR, $MIN ) = split( /\:/, $STARTTIME );

    # for AIX
    if ( $SERIALNUM_OVERRIDE eq "False" ) {
        if ( $AIXVER ne "-1" ) {
            $SN = &get_setting( "systemid", 4, "," );
            $SN = ( split( /\s+/, $SN ) )[0];            # "systemid IBM,SN ..."
        }

        # for Power Linux
        else {
            $SN = &get_setting( "serial_number", 4, "," );
            $SN = ( split( /\s+/, $SN ) )[0];    # "serial_number=IBM,SN ..."
        }

        # undeterminated
        if ( $SN eq "-1" ) {
            $SN = $HOSTNAME;
        }
        elsif ( $SN eq "" ) {
            $SN = $HOSTNAME;
        }

    }

    elsif ( $SERIALNUM_OVERRIDE eq "True" ) {
        $SN = $SERIALNUM_OVERRIDE_VALUE;
    }

    $TYPE = &get_setting( "^BBBP.*Type", 3, "," );
    if   ( $TYPE =~ /Shared/ ) { $TYPE = "SPLPAR"; }
    else                       { $TYPE = "Dedicated"; }

    $MODE = &get_setting( "^BBBP.*Mode", 3, "," );
    $MODE = ( split( /: /, $MODE ) )[1];

    # $MODE		=~s/\"//g;

    # Calculate UTC time (seconds since 1970)
    # NMON V9  dd/mm/yy
    # NMON V10+ dd-MMM-yyyy

    if ( $DATE =~ /[a-zA-Z]/ ) {    # Alpha = assume dd-MMM-yyyy date format
        ( $DAY, $MMM, $YR ) = split( /\-/, $DATE );
        $MMM = lc($MMM);
        $MON = $MONTH2NUMBER{$MMM};
    }
    else {
        ( $DAY, $MON, $YR ) = split( /\//, $DATE );
        $YR  = $YR + 2000;
        $MMM = $MONTH2ALPHA[$MON];
    }    # end if

## Calculate UTC time (seconds since 1970).  Required format for the rrdtool.

##  timelocal format
##    day=1-31
##    month=0-11
##    year = x -1900  (time since 1900) (seems to work with either 2006 or 106)

    $m = $MON - 1;    # jan=0, feb=2, ...

    $UTC_START = timelocal( 0, $MIN, $HR, $DAY, $m, $YR );
    $UTC_END = $UTC_START + $INTERVAL * $SNAPSHOTS;

    @ZZZZ = grep( /^ZZZZ,/, @nmon );
    for ( $i = 0 ; $i < @ZZZZ ; $i++ ) {

        @cols = split( /,/, $ZZZZ[$i] );
        ( $DAY, $MON, $YR ) = split( /-/, $cols[3] );
        $MON                  = lc($MON);
        $MON                  = "00" . $MONTH2NUMBER{$MON};
        $MON                  = substr( $MON, -2, 2 );
        $ZZZZ[$i]             = "$YR-$MON-$DAY $cols[2]";
        $DATETIME{ $cols[1] } = "$YR-$MON-$DAY $cols[2]";

    }    # end ZZZZ

    return (0);
}    # end get_nmon_data

# metrics_dictionary

sub metrics_dict {

    # arg1
    my $section = shift;

    # section_group
    my $section_group;

    my %metric_category_of = (
        "CPU_ALL"       => "cpu",
        "CPUnn"         => "cpu",
        "DGBACKLOG"     => "storage",
        "DGBUSY"        => "storage",
        "DGINFLIGHT"    => "storage",
        "DGIOTIME"      => "storage",
        "DGREAD"        => "storage",
        "DGREADMERGE"   => "storage",
        "DGREADS"       => "storage",
        "DGREADSERV"    => "storage",
        "DGSIZE"        => "storage",
        "DGWRITE"       => "storage",
        "DGWRITEMERGE"  => "storage",
        "DGWRITES"      => "storage",
        "DGWRITESERV"   => "storage",
        "DGXFER"        => "storage",
        "DISKBSIZE"     => "storage",
        "DISKBUSY"      => "storage",
        "DISKREAD"      => "storage",
        "DISKREADS"     => "storage",
        "DISKREADSERV"  => "storage",
        "DISKRIO"       => "storage",
        "DISKSVCTM"     => "storage",
        "DISKWAITTM"    => "storage",
        "DISKWIO"       => "storage",
        "DISKWRITE"     => "storage",
        "DISKWRITES"    => "storage",
        "DISKWRITESERV" => "storage",
        "DISKXFER"      => "storage",
        "FCREAD"        => "adapters",
        "FCWRITE"       => "adapters",
        "FCXFERIN"      => "adapters",
        "FCXFEROUT"     => "adapters",
        "FILE"          => "kernel",
        "IOADAPT"       => "adapters",
        "JFSFILE"       => "storage",
        "JFSINODE"      => "storage",
        "LPAR"          => "cpu",
        "MEM"           => "memory",
        "MEMNEW"        => "memory",
        "MEMUSE"        => "memory",
        "NET"           => "network",
        "NETERROR"      => "network",
        "NETPACKET"     => "network",
        "NFSCLIV2"      => "network",
        "NFSSVRV2"      => "network",
        "NFSCLIV3"      => "network",
        "NFSSVRV3"      => "network",
        "NFSCLIV4"      => "network",
        "NFSSVRV4"      => "network",
        "PAGE"          => "kernel",
        "POOLS"         => "cpu",
        "PROC"          => "kernel",
        "PROCSOL"       => "kernel",
        "SEA"           => "adapters",
        "SEACHPHY"      => "adapters",
        "SEAPACKET"     => "adapters",
        "TOP"           => "processes",
        "UARG"          => "processes",
        "VM"            => "memory",
        "WLMBIO"        => "processes",
        "WLMCPU"        => "processes",
        "WLMMEM"        => "processes",
        "WLMPROJECTCPU" => "processes",
        "WLMPROJECTMEM" => "processes",
        "WLMTASKCPU"    => "processes",
        "WLMTASKMEM"    => "processes",
        "WLMUSERCPU"    => "processes",
        "WLMUSERMEM"    => "processes",
        "WLMZONECPU"    => "processes",
        "WLMZONEMEM"    => "processes",
        "UPTIME"        => "system",
        "PROCCOUNT"     => "processes",
        "DF_STORAGE"    => "storage",
        "DF_INODES"     => "storage",
    );

    # some metrics will auto-increment, we want to match the metric group
    # but NFS is a specific case where we need to match the version number

    if ( $section =~ /(^NFS\w*)/ ) {
        $section_group = $1;
    }
    elsif ( $section =~ /(^\w*[a-zA-z])[0-9]{0,}/ ) {
        $section_group = $1;
    }

    # in case of failure
    else {
        $section_group = $section;
    }

    if ( exists( $metric_category_of{$section_group} ) ) {
        return $metric_category_of{$section_group};
    }
    else {
        return "custom";
    }

}

# Meta data
# arg1: file path
# arg2: file destination
# arg3: current nmon section
# arg4: OStype
# arg5: SN
# arg6: HOSTNAME

# The Meta data creation are not used currently due to the metrics specific Splunk licensing model
# this might change in the future.

sub meta {

    # arg1: file path
    my $filename = shift;

    # arg2: file destination
    my $output = shift;

    # arg3: current nmon section
    my $current_section = shift;

    # arg4: OStype
    my $OStype = shift;

    # arg5: SN
    my $SN = shift;

    # arg6: HOSTNAME
    my $HOSTNAME = shift;

    # current epoch time
    my $timestamp = time;

    # Get metric_category
    my $metric_category = metrics_dict($current_section);

    if ( -f $filename ) {

        # Get file size in bytes
        my $filesize = -s $filename;

        # Open Meta destination
        open( my $fh, '>', $output ) or die "Could not open file '$output' $!";

        # Write header
        print $fh
"metric_timestamp,metric_name,OStype,serialnum,hostname,metric_category,metric_section,_value\n";

        # Write Meta
        print $fh
"$timestamp,os.unix.nmon.meta.metric_fsize_bytes,$OStype,$SN,$HOSTNAME,$metric_category,$current_section,$filesize\n";

        # Close
        close $fh;

    }

}

##########################################################################
# UPTIME load average metrics extractions
##########################################################################

sub uptime_metrics {

    my $nmon_var = shift;

    my @rawdata;
    $count = 0;

    # define default values for metric store
    my $metric_category = metrics_dict($nmon_var);
    my $nmon_section    = lc $nmon_var;
    my $metric_name     = "os.unix.nmon.$metric_category.$nmon_section";

    # Filter rawdata for this section
    @rawdata = grep( /^$nmon_var,/, @nmon );

    if ( @rawdata < 1 ) { return (1); }
    else {

        # Open the destination file for writting
        unless ( open( INSERT, ">$BASEFILENAME" ) ) {
            die("ERROR: Can not open /$BASEFILENAME\n");
        }

        # Write the csv header
        print INSERT (
            qq|metric_timestamp,metric_name,OStype,serialnum,hostname,_value\n|
        );

        # Sort rawdata
        @rawdata = sort(@rawdata);

        # Extract and write the metrics
        foreach $l (@rawdata) {

            if ( $l =~
/UPTIME,(T\d*),\".*load[_\-\s]average:\s*([\d|\.]*);\s*([\d|\.]*);\s*([\d|\.]*)/
              )
            {

                $origin_timestamp          = $1;
                $uptime_load_average_1min  = $2;
                $uptime_load_average_5min  = $3;
                $uptime_load_average_15min = $4;
                $timestamp                 = $DATETIME{$origin_timestamp};

     # Convert timestamp string to epoch time (from format: YYYY-MM-DD hh:mm:ss)
                my ( $year, $month, $day, $hour, $min, $sec ) = split /\W+/,
                  $timestamp;

                if ( $month == 0 ) {
                    print
"ERROR, section $key has failed to identify the timestamp of these data, affecting current timestamp which may be inaccurate\n";
                    my (
                        $sec,  $min,  $hour, $mday, $mon,
                        $year, $wday, $yday, $isdst
                    ) = localtime(time);
                    $month = $mon;
                    $day   = $mday;
                }

                my $ZZZZ_epochtime =
                  timelocal( $sec, $min, $hour, $day, $month - 1, $year );

                if ($SHOW_ZERO) {
                    # remove metrics with: -1.0 / -1 / -0.0 / 0.0 / 0
                    if (   $uptime_load_average_1min !~ m/\-1\.0$/
                        && $uptime_load_average_1min !~ m/\-1$/
                        && $uptime_load_average_1min !~ m/\-0\.0$/
                        && $uptime_load_average_1min !~ m/0\.0$/
                        && $uptime_load_average_1min !~ m/0$/ )
                    {
                        print INSERT (
    qq|$ZZZZ_epochtime,$metric_name.load_average_1min,$OStype,$SN,$HOSTNAME,$uptime_load_average_1min\n|
                        );
                        $count++;
                    }
                }
                else {
                    # remove metrics with: -1.0 / -1
                    if (   $uptime_load_average_1min !~ m/\-1\.0$/
                        && $uptime_load_average_1min !~ m/\-1$/ )
                    {
                        print INSERT (
    qq|$ZZZZ_epochtime,$metric_name.load_average_1min,$OStype,$SN,$HOSTNAME,$uptime_load_average_1min\n|
                        );
                        $count++;
                    }
                }

                if ($SHOW_ZERO) {
                    # remove metrics with: -1.0 / -1 / -0.0 / 0.0 / 0
                    if (   $uptime_load_average_5min !~ m/\-1\.0$/
                        && $uptime_load_average_5min !~ m/\-1$/
                        && $uptime_load_average_5min !~ m/\-0\.0$/
                        && $uptime_load_average_5min !~ m/0\.0$/
                        && $uptime_load_average_5min !~ m/0$/ )
                    {
                        print INSERT (
    qq|$ZZZZ_epochtime,$metric_name.load_average_5min,$OStype,$SN,$HOSTNAME,$uptime_load_average_5min\n|
                        );
                        $count++;
                    }
                }
                else {
                    # remove metrics with: -1.0 / -1
                    if (   $uptime_load_average_5min !~ m/\-1\.0$/
                        && $uptime_load_average_5min !~ m/\-1$/ )
                    {
                        print INSERT (
    qq|$ZZZZ_epochtime,$metric_name.load_average_5min,$OStype,$SN,$HOSTNAME,$uptime_load_average_5min\n|
                        );
                        $count++;
                    }
                }

                if ($SHOW_ZERO) {
                    # remove metrics with: -1.0 / -1 / -0.0 / 0.0 / 0
                    if (   $uptime_load_average_15min !~ m/\-1\.0$/
                        && $uptime_load_average_15min !~ m/\-1$/
                        && $uptime_load_average_15min !~ m/\-0\.0$/
                        && $uptime_load_average_15min !~ m/0\.0$/
                        && $uptime_load_average_15min !~ m/0$/ )
                    {
                        print INSERT (
    qq|$ZZZZ_epochtime,$metric_name.load_average_15min,$OStype,$SN,$HOSTNAME,$uptime_load_average_15min\n|
                        );
                        $count++;
                    }
                }
                else {
                    # remove metrics with: -1.0 / -1
                    if (   $uptime_load_average_15min !~ m/\-1\.0$/
                        && $uptime_load_average_15min !~ m/\-1$/ )
                    {
                        print INSERT (
    qq|$ZZZZ_epochtime,$metric_name.load_average_15min,$OStype,$SN,$HOSTNAME,$uptime_load_average_15min\n|
                        );
                        $count++;
                    }
                }

            }

        }

        if ( $count > 1 ) {

            if ( not $SILENT ) {
                print "$key section: Wrote $count line(s)\n";
                print ID_REF "$key section: Wrote $count line(s)\n";
            }

            close(INSERT);

        }

        else {

            close(INSERT);
            unlink $BASEFILENAME;

        }

    }

}

################################################
# regular multi-dimension data managed as events
################################################

sub multi_dimension_events_fn {

    my $key = shift;

    $BASEFILENAME = "$OUTPUT_DIR/${HOSTNAME}_${minute}_${key}.events.csv";

    &multi_dimension_events($key);

    $now = time();
    $now = $now - $start;

    #$METAFILENAME =
    #"$OUTPUT_DIR/${HOSTNAME}_${minute}_${key}.events.meta.metrics.csv";

    #&meta( $BASEFILENAME, $METAFILENAME, $key, $OStype, $SN, $HOSTNAME );

}

##########################################################################
# regular multi-dimension data managed as metrics for the metric datastore
##########################################################################

sub multi_dimension_metrics_fn {

    my $key = shift;

    $BASEFILENAME = "$OUTPUT_DIR/${HOSTNAME}_${minute}_${key}.metrics.csv";

    &multi_dimension_metrics($key);

    $now = time();
    $now = $now - $start;

    #$METAFILENAME =
    #"$OUTPUT_DIR/${HOSTNAME}_${minute}_${key}.meta.metrics.csv";

    #&meta( $BASEFILENAME, $METAFILENAME, $key, $OStype, $SN, $HOSTNAME );

}

##########################################################################
# regular mono-dimension data managed as metrics for the metric datastore
##########################################################################

sub mono_dimension_metrics_fn {

    my $key = shift;

    $BASEFILENAME = "$OUTPUT_DIR/${HOSTNAME}_${minute}_${key}.metrics.csv";

    &mono_dimension_metrics($key);

    $now = time();
    $now = $now - $start;

    #$METAFILENAME =
    #"$OUTPUT_DIR/${HOSTNAME}_${minute}_${key}.meta.metrics.csv";

    #&meta( $BASEFILENAME, $METAFILENAME, $key, $OStype, $SN, $HOSTNAME );

}

##########################################################################
# DF_STORAGE & DF_INODES
##########################################################################

sub df_external_metrics_fn {

    my $key = shift;

    $BASEFILENAME = "$OUTPUT_DIR/${HOSTNAME}_${minute}_${key}.metrics.csv";

    &df_external_metrics($key);

    $now = time();
    $now = $now - $start;

    #$METAFILENAME =
    #"$OUTPUT_DIR/${HOSTNAME}_${minute}_${key}.meta.metrics.csv";

    #&meta( $BASEFILENAME, $METAFILENAME, $key, $OStype, $SN, $HOSTNAME );

}

########
# UPTIME
########

sub uptime_metrics_fn {

    my $key = shift;

    $BASEFILENAME = "$OUTPUT_DIR/${HOSTNAME}_${minute}_${key}.metrics.csv";

    &uptime_metrics($key);

    $now = time();
    $now = $now - $start;

    #$METAFILENAME =
    #"$OUTPUT_DIR/${HOSTNAME}_${minute}_${key}.meta.metrics.csv";

    #&meta( $BASEFILENAME, $METAFILENAME, $key, $OStype, $SN, $HOSTNAME );

}

#####
# TOP
#####

sub top_metrics_fn {

    my $key = shift;

    $BASEFILENAME = "$OUTPUT_DIR/${HOSTNAME}_${minute}_${key}.metrics.csv";

    &top_metrics($key);

    $now = time();
    $now = $now - $start;

    #$METAFILENAME =
    #"$OUTPUT_DIR/${HOSTNAME}_${minute}_${key}.meta.metrics.csv";

    #&meta( $BASEFILENAME, $METAFILENAME, $key, $OStype, $SN, $HOSTNAME );

}

######
# UARG
######

sub uarg_events_fn {

    my $key = shift;

    $BASEFILENAME = "$OUTPUT_DIR/${HOSTNAME}_${minute}_${key}.events.csv";

    &uarg_events($key);

    $now = time();
    $now = $now - $start;

    #$METAFILENAME =
    #"$OUTPUT_DIR/${HOSTNAME}_${minute}_${key}.meta.metrics.csv";

    #&meta( $BASEFILENAME, $METAFILENAME, $key, $OStype, $SN, $HOSTNAME );

}
