#!/usr/bin/perl                                                                                                      
# Matt Kirby
# 2012-10-31

use strict;
use Carp;
use English '-no_match_vars';
use POSIX qw(strftime);
use Getopt::Long;
use PerlIO::gzip;
use Text::CSV::Slurp;
use Digest::MD5 qw(md5_hex);
use Mail::Sendmail;

&main;

##################################################
sub main {
	my %opts;
	my $computername;
	my $eventtype;
	my $eventcode;
	my $msg;
	my $key;
	my $date;
	my $time;
	my $emailmsg;
	my %alerts;
	my $serial;
	my %mail;
	my @times;
	my @alltimes;
	my $countfont;
	my @bgcolors = ( '#eae1e1', '#EDEDF1', '#dee8e8', '#efe5ef', '#e9f6ea', '#efe8dd', '#dbe7ed' );
	my $bgcolori = 0;
	my $filehandle;
	my $categorystring;
	my $emailrowcount     = 0;
	my $lastemailrowcount = -1;
	my $premsg;
	my $searchlink;

	GetOptions(
		"report=s"     => \$opts{report},
		"emailto=s"    => \$opts{emailto},
		"emailfrom=s"  => \$opts{emailfrom},
		"smtpserver=s" => \$opts{smtpserver},
		"name=s"       => \$opts{name},
		"link=s"       => \$opts{link},
		"threshold=i"  => \$opts{threshold},
	);

	unless ( -f $opts{report} ) {
		croak "The file $opts{report} does not exist\n";
	}
	unless ("$opts{emailto}") {
		croak "Missing emailto parameter\n";
	}
	unless ("$opts{emailfrom}") {
		croak "Missing emailfrom parameter\n";
	}
	unless ("$opts{smtpserver}") {
		croak "Missing smtpserver parameter\n";
	}
	unless ("$opts{name}") {
		croak "Missing name parameter\n";
	}
	unless ("$opts{link}") {
		croak "Missing link parameter\n";
	}
	unless ("$opts{threshold}") {
		croak "Missing threshold parameter\n";
	}

	open $filehandle, "<:gzip", "$opts{report}" or croak $!;
	my $data = Text::CSV::Slurp->load( filehandle => $filehandle );
	close $filehandle;

	foreach my $key ( @{$data} ) {
		$date = strftime '%Y-%m-%d', localtime( $key->{'_time'} );
		$time = strftime '%H:%M',    localtime( $key->{'_time'} );
		$msg  = $key->{'Message'};
		$msg =~ s|\n+|<br>\n|g;
		$msg =~ s|\r|<br>\r|g;
		$msg =~ s|\t|&nbsp;&nbsp;&nbsp;&nbsp;|g;
		$msg =~ s|Source Port:\s+\d+|Source Port: *****|g;
		$computername = $key->{'host'};
		push @alltimes, $key->{'_time'};

		foreach my $premsg ( split /\n/, $key->{'_pre_msg'} ) {
			if ( $premsg =~ m|^CategoryString| ) {
				$categorystring = $premsg;
				$categorystring =~ s|CategoryString=(.*)|$1|;
			} elsif ( $premsg =~ m|^EventCode| ) {
				$eventcode = $premsg;
				$eventcode =~ s|EventCode=(.*)|$1|;
			} elsif ( $premsg =~ m|^EventType| ) {
				$eventtype = $premsg;
				$eventtype =~ s|EventType=(.*)|$1|;
			}
		}
		$serial = md5_hex( "$computername" . "$eventtype" . "$date" . "$msg" );

		$alerts{$computername}{$serial}{type}           = $key->{'Type'};
		$alerts{$computername}{$serial}{sourcetype}     = $key->{'_sourcetype'};
		$alerts{$computername}{$serial}{date}           = $date;
		$alerts{$computername}{$serial}{msg}            = $msg;
		$alerts{$computername}{$serial}{CategoryString} = $categorystring;
		$alerts{$computername}{$serial}{count}++;
		push @{ $alerts{$computername}{$serial}{times} }, $time;
	}

	@alltimes   = sort @alltimes;
	$searchlink = $opts{link};
	$searchlink =~ s|^(https://.+/app/).*|$1|;

	$emailmsg = qq(<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
                <html>
                <meta content="text/html;charset=ISO-8859-1" http-equiv="Content-Type">
                <head><title>$opts{name}</title> </head>
                <body link="black">
                <a href="${searchlink}search/flashtimeline?q=search%20eventtype%3D%22$opts{name}%22%20starttimeu%3D$alltimes[0]%20endtimeu%3D$alltimes[-1]">Click here to view in Splunk</a><br><br>
                <table cellspacing=1 border=1 width="100%" rules=all>
        );

	foreach my $computername ( sort keys %alerts ) {
		if ( $lastemailrowcount < $emailrowcount ) {
			$lastemailrowcount = $emailrowcount;
			$bgcolori++;
			$bgcolori = 0 if ( $bgcolori == 7 );
		}

		foreach my $serial ( keys %{ $alerts{$computername} } ) {
			@times = sort @{ $alerts{$computername}{$serial}{times} };

			if ( $alerts{$computername}{$serial}{count} < $opts{threshold} ) {
				next;
			}

			if ( $alerts{$computername}{$serial}{count} >= 5 ) {
				$countfont = 'size=3';
			} else {
				$countfont = '';
			}
			if ( $alerts{$computername}{$serial}{count} >= 20 ) {
				$countfont = 'size=4 color=red';
			}
			if ( $alerts{$computername}{$serial}{count} >= 50 ) {
				$countfont = 'size=5 color=red';
			}
			if ( $alerts{$computername}{$serial}{count} >= 100 ) {
				$countfont = 'size=6 color=red';
			}

			$emailmsg .= qq(
                                <tr>
                                <td valign=top width="33%" bgcolor=$bgcolors[$bgcolori]>
                                <b><a href="${searchlink}search/flashtimeline?q=search%20starttimeu%3D$alltimes[0]%20endtimeu%3D$alltimes[-1]%20host%3D%22${computername}*%22">$computername</a></b><br>
                                <font size=-1>
                                Type: $alerts{$computername}{$serial}{type}<br>
                                Date: $alerts{$computername}{$serial}{date}<br>
                                From $times[0] to $times[-1]<br>
                                sourcetype: $alerts{$computername}{$serial}{sourcetype}<br>
                                Category: $alerts{$computername}{$serial}{CategoryString}<br>
                                Count: <font $countfont>$alerts{$computername}{$serial}{count}</font><br>
                                </font>
                                </td>
                                <td valign=top width="67%" bgcolor=$bgcolors[$bgcolori]>
                                <font size=-1>$alerts{$computername}{$serial}{msg}</font>
                                </td>
                                </tr>
                        );
			$emailrowcount++;
		}
	}
	$emailmsg .= qq(</tr></table></body></html>\n);

	%mail = (
		To             => "$opts{emailto}",
		From           => "$opts{emailfrom}",
		smtp           => "$opts{smtpserver}",
		subject        => $opts{name},
		'content-type' => "text/html",
		Message        => $emailmsg
	);
	if ( $emailrowcount > 0 ) {
		sendmail(%mail) or croak $Mail::Sendmail::error;
		print "OK.  Log says: " . $Mail::Sendmail::log . "\n";
	}

	return 0;
}
