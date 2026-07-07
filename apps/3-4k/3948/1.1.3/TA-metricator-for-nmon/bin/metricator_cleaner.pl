#!/usr/bin/perl

# Program name: metricator_cleaner.pl
# Compatibility: Perl x
# Purpose - Clean nmon and csv files when retention expired
# Author - Guilhem Marchand

$version = "2.0.0";

use Time::Local;
use Time::HiRes;
use Getopt::Long;
use POSIX 'strftime';
use File::stat;    # use the object-oriented interface to stat

# LOGGING INFORMATION:
# - The program uses the standard logging Python module to display important messages in Splunk logs
# - Every message of the script will be indexed and accessible within Splunk splunkd logs

#################################################
##      Arguments Parser
#################################################

# Default values
my $CSV_REPOSITORY    = "csv_repository";
my $APP               = "";
my $CONFIG_REPOSITORY = "config_repository";
my $MAXSECONDS        = "";
my $verbose;

$result = GetOptions(
    "csv_repository=s"    => \$CSV_REPOSITORY,       # string
    "config_repository=s" => \$CONFIG_REPOSITORY,    # string
    "cleancsv"            => \$CLEANCSV,             # string
    "approot=s"           => \$APP,                  # string
    "maxseconds_csv=s"    => \$MAXSECONDS_CSV,       # string
    "version"             => \$VERSION,              # flag
    "help"                => \$help                  # flag
);

# Show version
if ($VERSION) {
    print("nmon_clean.pl version $version \n");

    exit 0;
}

# Show help
if ($help) {

    print( "

Help for metricator_cleaner.pl:

In default configuration (eg. no options specified) the script will purge any nmon file (*.nmon) in default nmon_repository
        	
Available options are:
	
--cleancsv :Activate the purge of csv files from csv repository and config repository (see also options above)
--maxseconds_csv <value> :Set the maximum file retention in seconds for csv data, every files older than this value will be permanently removed
--approot <value> :Set a custom value for the Application root directory (default are: nmon / TA-metricator-for-nmon / PA-nmon)
--csv_repository <value> :Set a custom location for directory containing csv data (default: csv_repository)
--config_repository <value> :Set a custom location for directory containing config data (default: config_repository)
--version :Show current program version \n
"
    );

    exit 0;
}

#################################################
##      Parameters
#################################################

# Default values for CSV retention (4 hours less 1 minute)
my $MAXSECONDS_CSV_DEFAULT = 86400;

#################################################
##      Functions
#################################################

#################################################
##      Program
#################################################

# Processing starting time
my $t_start = [Time::HiRes::gettimeofday];

# Local time
my $time = strftime "%d-%m-%Y %H:%M:%S", localtime;

# Default Environment Variable SPLUNK_HOME, this shall be automatically defined if as the script shall be launched by Splunk
my $SPLUNK_HOME = $ENV{SPLUNK_HOME};

# Verify SPLUNK_HOME definition
if ( not $SPLUNK_HOME ) {
    print(
"\n$time ERROR: The environment variable SPLUNK_HOME could not be verified, if you want to run this script manually you need to export it before processing \n"
    );
    die;
}

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

# Verify existence of APP
if ( !-d "$APP" ) {
    print(
"\n$time ERROR: The Application root directory could not be found, is the TA-metricator-for-nmon installed ?\n"
    );
    die;
}

# var directories
my $APP_MAINVAR = "$SPLUNK_HOME/var/log/metricator";
my $APP_VAR = "$APP_MAINVAR/var";

if ( !-d "$APP_MAINVAR" ) {
    print(
"\n$time INFO: main var directory not found ($APP_MAINVAR),  no need to run.\n"
    );
    exit 0;
}


####################################################################
#############		Main Program
####################################################################

# check retention
if ( not "$MAXSECONDS_CSV" ) {
    $MAXSECONDS_CSV = $MAXSECONDS_CSV_DEFAULT;
}

# Print starting message
print("$time Starting nmon cleaning:\n");
print("Splunk Root Directory $SPLUNK_HOME nmon_cleaner version: $version Perl version: $] \n");

# Set current epoch time
$epoc = time();

# If the csv switch is on, purge csv data

if ($CLEANCSV) {

    # Counter
    $count = 0;

    # CSV Items to clean
    @cleaning =
      ( "$APP_VAR/$CSV_REPOSITORY/*.csv", "$APP_VAR/$CONFIG_REPOSITORY/*.csv" );

    # Enter loop
    foreach $key (@cleaning) {

        @files = glob($key);

        foreach $file (@files) {
            if ( -f $file ) {

                # Get file timestamp
                my $file_timestamp = stat($file)->mtime;

                # Get difference
                my $timediff = $epoc - $file_timestamp;

                # If retention has expired
                if ( $timediff > $MAXSECONDS_CSV ) {

                    # information
                    print ("Max set retention of $MAXSECONDS_CSV seconds seconds expired for file: $file \n");

                    # purge file
                    unlink $file;

                    # Increment counter
                    $count++;
                }
            }
        }

        if ( $count eq 0 ) {
            print ("$key, no action required. \n");
        }
        else {
            print("INFO: $count files were permanently removed from $key \n");
        }    

    }
}

#############################################
#############  Main Program End 	############
#############################################

# Show elapsed time
my $t_end = [Time::HiRes::gettimeofday];
print "Elapsed time was: ",
  Time::HiRes::tv_interval( $t_start, $t_end ) . " seconds \n";

exit(0);
