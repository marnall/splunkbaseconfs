#!/usr/bin/perl                                                                                                      
# 20121031 Kirby
# 20130206 Kirby
# 20130314 Kirby
# 20130401 Kirby

use strict;
use Carp;
use English '-no_match_vars';
use POSIX qw(strftime);
use Getopt::Long;
use PerlIO::gzip;
use Text::CSV::Slurp;
use Digest::MD5 qw(md5_hex);
use Mail::Sendmail;

#use Carp::Source::Always;
#use diagnostics;
#use warnings;

&main;

##################################################
sub main {
	my %opts;
	my $host;
	my $msg;
	my $key;
	my $month;
	my $time;
	my $weekday;
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
	my $date;
	my $emailrowcount     = 0;
	my $lastemailrowcount = -1;
	my $searchlink;
	my $hostmsg;
	my $index;
	my $sdate;
	my $year;
	my %count;

	GetOptions(
		"report=s"     => \$opts{report},
		"emailto=s"    => \$opts{emailto},
		"emailfrom=s"  => \$opts{emailfrom},
		"smtpserver=s" => \$opts{smtpserver},
		"threshold=i"  => \$opts{threshold},
		"name=s"       => \$opts{name},
		"link=s"       => \$opts{link},
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
		$count{raw}++;
		$msg = $key->{'_raw'};
		push @alltimes, $key->{'_time'};
		$index   = $key->{'index'};
		$date    = strftime '%Y-%m-%d', localtime( $key->{'_time'} );
		$sdate   = strftime '%Y/%m/%d', localtime( $key->{'_time'} );
		$time    = strftime '%H:%M', localtime( $key->{'_time'} );
		$month   = strftime '%b', localtime( $key->{'_time'} );
		$weekday = strftime '%a', localtime( $key->{'_time'} );
		$year    = strftime '%Y', localtime( $key->{'_time'} );
		$host    = $key->{'host'};

		# Mar 10 10:59:47.141 CDT:
		$msg =~ s|(\s+:\s+)?[A-Z][a-z][a-z]\s+\d\d? \d\d?:\d\d:\d\d\.\d\d\d [A-Z][A-Z][A-Z]?:\s+||g;

		# 2013 Mar 10 18:29:52 UTC:
		$msg =~ s|$year [A-Z][a-z][a-z]\s+\d\d?,? \d\d?:\d\d:\d\d\ [A-Z][A-Z][A-Z]?:\s+||g;

		# [Thu Mar 10 17:55:04 2013]
		$msg =~ s|\[$weekday [A-Z][a-z][a-z]\s+\d\d? \d\d?:\d\d:\d\d $year\]||g;

		# winbindd[*]: [2013/03/14 10:54:09.055844, 0]
		$msg =~ s|\[$sdate \d\d?:\d\d:\d\d\.\d+,\s+\d\]||g;

		# Mar 10, 2013 5:30:03 PM
		$msg =~ s|[A-Z][a-z][a-z]\s+\d\d?,? $year \d\d?:\d\d:\d\d [AP]M||g;

		# Mar 10, 11:23:59
		$msg =~ s|[A-Z][a-z][a-z]\s+\d\d?,? \d\d?:\d\d:\d\d||g;

		# Jan 8 00:53:05.852
		$msg =~ s|[A-Z][a-z][a-z]\s+\d\d? \d\d?:\d\d:\d\d\.\d\d+||g;

		# 2013-03-10 11:23:45,428
		$msg =~ s|$year-\d\d?-\d\d?\s+\d\d?:\d\d:\d\d,\d+||g;

		# Feb 27 2013 17:59:58.540 UTC :
		$msg =~ s|[A-Z][a-z][a-z]\s+\d\d? $year \d\d?:\d\d:\d\d\.\d\d+ [A-Z][A-Z][A-Z] :||g;

		#
		# catch any other clocks that were missed above and replace with **:**:** to help with dedup
		#
		$msg =~ s/(\D|^|\s)\d\d?:\d\d:\d\d(:\d\d|\s|$)([\.,]\d+)?/$1**:**:**/g;

		#
		# remove redundant information and digits of common log messages
		#
		$msg =~ s|$key->{'host'}||g;
		$msg =~ s|\n+|<br>\n|g;
		$msg =~ s|\r|<br>\r|g;
		$msg =~ s|\t|&nbsp;&nbsp;&nbsp;&nbsp;|g;
		$msg =~ s|PID \d+|PID *|g;
		$msg =~ s|pid\s*=\s*\d+|pid=*|g;
		$msg =~ s|\[\d+\]:|[*]:|g;
		$msg =~ s|\(\d+\)|\(*\)|g;
		$msg =~ s|:\d\d\d\d+|:****|g;
		$msg =~ s|^\d\d\d\d+:|****:|g;
		$msg =~ s|\s\d\d\d\d+:|****:|g;
		$msg =~ s| port \d\d\d+| port ***|g;
		$msg =~ s|\s+[A-Za-z0-9]+(: low on space \(SMTP-DAEMON needs )\d+( bytes \+ )\d+( blocks in /.*\), max avail: )\d+| *** $1 *** $2 *** $3 ***|;
		$msg =~ s|\s+[A-Za-z0-9]+(: SYSERR\(root\): putbody: write error: No space left on device)| *** $1|;
		$msg =~ s|\s+[A-Za-z0-9]+(: SYSERR\(root\): Error writing control file )[\A-Za-z0-9]+(: No space left on device)| *** $1 *** $2|;
		$msg =~ s|\s+[A-Za-z0-9]+(: SYSERR\(root\): queueup: cannot create data temp file ./)[\A-Za-z0-9]+(, uid=\d+: No space left on device)|*** $1 *** $2|;
		$msg =~ s|\s+[A-Za-z0-9]+(: SYSERR\(root\): queueup: cannot create queue file )[\A-Za-z0-9]+(, .*: No space left on device)|*** $1 *** $2|;
		$msg =~ s| Block: \d+| Block: ****|g;
		$msg =~ s|(ypserv.*: refused connect from )\d+\.\d+\.\d+\.\d+(:.*)|$1 **.**.**.** $2|;
		$msg =~ s|, reset code = [A-Za-z0-9]+||g;
		$msg =~ s|grandchild \#\d+|grandchild \#***|;
		$msg =~ s|^\s+||g;
		$msg =~ s|missed \d+ packets|missed *** packets|g;

		if ( $msg =~ m|^kernel:| ) {
			$msg =~ s|inode \d+|inode ***|g;
			$msg =~ s|inode=\d+|inode=***|g;
			$msg =~ s|rec_len=\d+|rec_len=***|g;
			$msg =~ s|name_len=\d+|name_len=***|g;
			$msg =~ s|block \d+|block ***|g;
			$msg =~ s|in group \d+|in group ***|g;
			$msg =~ s|inode \#\d+|inode \#***|g;
			$msg =~ s|mapped to \d+|mapped to ***|g;
			$msg =~ s|size \d+|size ***|g;
			$msg =~ s|directory #\d+|directory #***|g;
			$msg =~ s|block=\d+|block=***|g;
			$msg =~ s|blocknr = \d+|blocknr = ***|g;
			$msg =~ s|rw=\d+|rw=***|g;
			$msg =~ s|want=\d+|want=***|g;
			$msg =~ s|limit=\d+|limit=***|g;
			$msg =~ s|__ratelimit: \d+|__ratelimit: ***|g;
			$msg =~ s|code = \S+|code = ***|g;
			$msg =~ s|segfault at \d+|segfault at ***|g;
			$msg =~ s| ip \S+| ip ***|g;
			$msg =~ s| sp \S+| sp ***|g;
			$msg =~ s| (libc.*\[)\S+(\])| $1 *** $2|g;
			$msg =~ s|, reset code = .*||g;
			$msg =~ s|sector \d+|sector ***|g;
		}

		$serial                       = md5_hex( "$host" . "$date" . "$msg" );
		$alerts{$host}{$serial}{date} = $date;
		$alerts{$host}{$serial}{msg}  = $msg;
		$alerts{$host}{$serial}{count}++;
		push @{ $alerts{$host}{$serial}{times} }, $time;
	}

	@alltimes = sort @alltimes;

	$searchlink = $opts{link};
	$searchlink =~ s|^(https://.+/app/).*|$1|;

	$emailmsg = qq(<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
                <html>
                <meta content="text/html;charset=ISO-8859-1" http-equiv="Content-Type">
                <head> <title>$opts{name}</title> </head>
                <body link="black">
                <a href="${searchlink}search/flashtimeline?q=search%20eventtype%3D%22$opts{name}%22%20starttimeu%3D$alltimes[0]%20endtimeu%3D$alltimes[-1]">Click here to view in Splunk
                </a>
                <br><br>
                <table cellspacing=1 border=1 width="100%" rules=all>
        );

	foreach my $host ( sort keys %alerts ) {
		if ( $lastemailrowcount < $emailrowcount ) {
			$lastemailrowcount = $emailrowcount;
			$bgcolori++;
			$bgcolori = 0 if ( $bgcolori == 7 );
		}

		$hostmsg = qq(
                        <tr>
                        <td valign=top width="20%" bgcolor=$bgcolors[$bgcolori]> 
                        <b>
                        <a href="${searchlink}search/flashtimeline?q=search%20index%3D$index%20starttimeu%3D$alltimes[0]%20endtimeu%3D$alltimes[-1]%20host%3D%22${host}*%22">$host
                        </a>
                        </b>
                        </td>
                        <td valign=top width="80%">
                        <table border=0 width="100%" rules=all>
                );

		foreach my $serial ( keys %{ $alerts{$host} } ) {
			@times = sort @{ $alerts{$host}{$serial}{times} };

			if ( $alerts{$host}{$serial}{count} < $opts{threshold} ) {
				next;
			} else {
				$count{processed}++;
			}

			if ( $alerts{$host}{$serial}{count} >= 5 ) {
				$countfont = 'size=2 color=red';
			} else {
				$countfont = '';
			}
			if ( $alerts{$host}{$serial}{count} >= 10 ) {
				$countfont = 'size=4 color=red';
			}
			if ( $alerts{$host}{$serial}{count} >= 20 ) {
				$countfont = 'size=4 color=red';
			}
			if ( $alerts{$host}{$serial}{count} >= 50 ) {
				$countfont = 'size=5 color=red';
			}
			if ( $alerts{$host}{$serial}{count} >= 100 ) {
				$countfont = 'size=6 color=red';
			}

			$hostmsg .= qq(
                                <tr> <td valign=top width="20%" bgcolor=$bgcolors[$bgcolori]>
                                <font size=-1>
                                $alerts{$host}{$serial}{date}<br>
                                $times[0] to $times[-1]<br>
                                Count: <font $countfont>$alerts{$host}{$serial}{count}</font><br>
                                </font> </td>
                                <td valign=top width="80%" bgcolor=$bgcolors[$bgcolori]>
                                <font size=-1>$alerts{$host}{$serial}{msg}</font>
                                </td> </tr>
                        );
			$emailrowcount++;
		}

		$hostmsg .= qq(
                        </table>
                        </td>
                        </tr>
                );

		if ( $lastemailrowcount < $emailrowcount ) {

			# We have surpassed the threshold
			$emailmsg .= $hostmsg;
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

	print qq(Compacted $count{raw} records down to $count{processed}\n);

	return 0;
}
