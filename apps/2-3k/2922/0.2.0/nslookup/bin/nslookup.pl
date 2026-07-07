#!/usr/bin/perl
use strict;
use warnings;

use FindBin qw($Bin);
use lib "$Bin/lib";

use Data::Dumper;
use Splunklib::Intersplunk qw(readResults outputResults isGetInfo outputGetInfo);

if (isGetInfo(\@ARGV)) {
   outputGetInfo(undef, \*STDOUT);
   exit(0);
}

use Net::Nslookup;

# @ARGV example: field=_raw action=encode mode=replace
my $field = 'src_ip';
my $action = 'reverse';
my $mode = 'append';
my $timeout = 5;
for my $arg (@ARGV) {
   my ($k, $v) = split(/=/, $arg);
   if ($k eq 'field') {
      $field = $v;
   }
   elsif ($k eq 'action') {
      $action = $v;
   }
   elsif ($k eq 'mode') {
      $mode = $v;
   }
   elsif ($k eq 'timeout') {
      $timeout = $v;
   }
}

my $ary = readResults(\*STDIN, undef, 1);
my $results = $ary->[0];
my $header = $ary->[1];
my $lookup = $ary->[2];

my $new_field;
if ($mode eq 'append') {
   $new_field = 'nslookup_'.$field;
}
else {
   $new_field = $field;
}

# Add the field if it does not exists
if (! exists($lookup->{$new_field})) {
   push @$header, $new_field;
   my $new = keys %$lookup;
   $lookup->{$new_field} = $new;
}

for my $result (@$results) {
   if ($action eq 'reverse') {
      my $rev = nslookup(
         host => $result->[$lookup->{$field}],
         type => "PTR",
         timeout => $timeout,
      );
      $result->[$lookup->{$new_field}] = $rev || $result->[$lookup->{$field}];
   }
}

outputResults($ary, undef, undef, '\n', \*STDOUT);

exit(0);
