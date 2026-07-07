#!/usr/bin/perl

# Program name: metricator_reader.pl
# Compatibility: Perl x
# Purpose - read nmon data from fifo file
# Author - Guilhem Marchand

my $version = "2.0.0";

use Getopt::Long;
use File::stat;
use File::Copy;
use POSIX 'strftime';

#################################################
##      Arguments Parser
#################################################

# Default values
my $APP       = "";
my $fifo_name = "";
my $VERSION   = "";
my $help      = "";

my $result = GetOptions(
    "fifo=s"  => \$fifo_name,    # string
    "version" => \$VERSION,      # flag
    "help"    => \$help          # flag
);

# Show version
if ($VERSION) {
    print("metricator_reader.pl version $version \n");

    exit 0;
}

# Show help
if ($help) {

    print( "

Help for metricator_reader.pl:

The script should be run in the backgroud to continously read nmon data from fifo files.

Available options are:

--fifo <name of fifo> :Name of the pre-configured fifo file
--version :Show current program version \n
"
    );

    exit 0;
}

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
my $APP_VAR     = "$APP_MAINVAR/var";

if ( !-d "$APP_MAINVAR" ) {
    print(
"\n$time INFO: main var directory not found ($APP_MAINVAR),  no need to run.\n"
    );
    exit 0;
}

# check fifo_name
if ( not "$fifo_name" ) {
    print("\n$time ERROR: the --fifo_name <name of fifo> is mandatory\n");
    die;
}

# define the full path to the fifo file
my $fifo_path = "$APP_VAR/nmon_repository/$fifo_name/nmon.fifo";

# At startup, rotate any existing non empty .dat file if nmon_data.dat is not empty

# define the various files to be written

# realtime files
my $nmon_config_dat   = "$APP_VAR/nmon_repository/$fifo_name/nmon_config.dat";
my $nmon_header_dat   = "$APP_VAR/nmon_repository/$fifo_name/nmon_header.dat";
my $nmon_data_dat     = "$APP_VAR/nmon_repository/$fifo_name/nmon_data.dat";
my $nmon_external_dat = "$APP_VAR/nmon_repository/$fifo_name/nmon_external.dat";
my $nmon_external_header_dat =
  "$APP_VAR/nmon_repository/$fifo_name/nmon_external_header.dat";
my $nmon_timestamp_dat =
  "$APP_VAR/nmon_repository/$fifo_name/nmon_timestamp.dat";
my $nmon_error_dat = "$APP_VAR/nmon_repository/$fifo_name/nmon_error.dat";

my @nmon_dat = (
    "$nmon_config_dat",   "$nmon_header_dat",
    "$nmon_data_dat",     "$nmon_timestamp_dat",
    "$nmon_external_dat", "$nmon_external_header_dat",
    "$nmon_error_dat"
);

my $file;
my $rotated_file;

# Remove any existing rotated file
foreach $file (@nmon_dat) {
    $rotated_file = "$file.rotated";
    if ( -e $rotated_file ) {
        unlink $rotated_file;
    }
}

# Manage existing files and do the rotation if required
if ( !-z $nmon_data_dat ) {
    foreach $file (@nmon_dat) {
        $rotated_file = "$file.rotated";
        move( $file, $rotated_file );
    }
}
else {
    foreach $file (@nmon_dat) {
        if ( -e $file ) {
            unlink $file;
        }
    }
}

####################################################################
#############		Main Program
####################################################################

if ( !-p $fifo_path ) {
    print(
"\n$time INFO: The fifo file $fifo_path does not exist yet, we are not ready to start.\n"
    );
    exit 0;

}
else {

    my $fifoh;

# Open the named pipe "a la shell" to ensure that we we will quite when the nmon process has ended as well
    open( $fifoh, "$APP/bin/metricator_reader.sh $fifo_path|" );

    while (<$fifoh>) {
        chomp($_);

        my $nmon_config_match = '^[AAA|BBB].+';
        my $nmon_header_match =
'^(?!AAA|BBB|TOP)[a-zA-Z0-9\-\_]*,(?!T\d{3,})[^,]*,(?!T\d{3,})[^,]*.*';
        my $nmon_header_TOP_match = '^TOP,(?!\d*,)';
        my $nmon_timestamp_match  = '^ZZZZ,T\d*';
        my $nmon_error_match      = '^ERROR,T\d*';

        if ( $_ =~ /$nmon_config_match/ ) {
            open( my $fh, '>>', $nmon_config_dat )
              or die "Could not open file '$nmon_config_dat' $!";
            print $fh "$_\n";
            close $fh;
        }

        elsif ( $_ =~ /$nmon_header_match/ ) {
            open( my $fh, '>>', $nmon_header_dat )
              or die "Could not open file '$nmon_header_dat' $!";
            print $fh "$_\n";
            close $fh;
        }

        elsif ( $_ =~ /$nmon_header_TOP_match/ ) {
            open( my $fh, '>>', $nmon_header_dat )
              or die "Could not open file '$nmon_header_dat' $!";
            print $fh "$_\n";
            close $fh;
        }

        elsif ( $_ =~ /$nmon_error_match/ ) {
            open( my $fh, '>>', $nmon_error_dat )
              or die "Could not open file '$nmon_error_dat' $!";
            print $fh "$_\n";
            close $fh;
        }

        elsif ( $_ =~ /$nmon_timestamp_match/ ) {
            open( my $fh, '>>', $nmon_timestamp_dat )
              or die "Could not open file '$nmon_timestamp_dat' $!";
            print $fh "$_\n";
            close $fh;
            open( my $fh, '>>', $nmon_data_dat )
              or die "Could not open file '$nmon_data_dat' $!";
            print $fh "$_\n";
            close $fh;
        }

        else {
            open( my $fh, '>>', $nmon_data_dat )
              or die "Could not open file '$nmon_data_dat' $!";
            print $fh "$_\n";
            close $fh;
        }

    }
    close $fifoh;
    exit(0);

}
