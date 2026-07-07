#!/usr/bin/perl
#
# $Id: onyphe.pl,v 8ac58d2e7f92 2019/04/04 14:45:54 gomor $
#
use strict;
use warnings;

#
# configuration
#
# Uncomment if you need a proxy.
#$ENV{HTTP_PROXY} = 'http://user:pass@proxy:8080/';
#$ENV{HTTPS_PROXY} = $ENV{HTTP_PROXY};

#my $apikey = '<YOUR_API_KEY>';

my $log_level = 1;
#
# /configuration
#

use FindBin qw($Bin);
use lib "$Bin/../lib";

use Splunklib::Intersplunk qw(
   readResults outputResults isGetInfo outputGetInfo
);

if (isGetInfo(\@ARGV)) {
   outputGetInfo(undef, \*STDOUT);
   exit(0);
}

use Metabrik::Api::Onyphe;
use Metabrik::String::Json;
use Metabrik::Network::Address;
use Metabrik::Log::File;

my $log = Metabrik::Log::File->new_brik_init or exit(1);
$log->output($ENV{SPLUNK_HOME}.'/var/log/splunk/onyphe.log');
$log->level($log_level);
$log->brik_init;

my $ao = Metabrik::Api::Onyphe->new_brik_init or exit(1);
$ao->apikey($apikey);
$ao->log($log);

my $sj = Metabrik::String::Json->new_brik_init or exit(1);
$sj->log($log);

my $na = Metabrik::Network::Address->new_brik_init or exit(1);
$na->log($log);

# @ARGV example: ip=src_ip api=ip
my $ip = 'src_ip'; # Default to search based on src_ip field
my $api = 'ip';    # Default to use ip API
my $mode = 'simple';   # Default to use simple API
my $search = ''; # Default to search nothing
my $autoscroll = 0;  # No autoscroll by default
my $maxpage = 0;  # Max page not specified, crawling all pages
my $output = 'json'; # JSON output by default.

for my $arg (@ARGV) {
   my ($k, $v) = split(/=/, $arg);
   if ($k eq 'ip') {
      $ip = $v;
   }
   elsif ($k eq 'api') {
      $api = $v;
   }
   elsif ($k eq 'autoscroll') {
      $autoscroll = ($v eq 'true' || $v eq 1) ? 1 : 0;
   }
   elsif ($k eq 'maxpage') {
      $maxpage = $v;
   }
   elsif ($k eq 'mode' && ($v eq 'simple' || $v eq 'search')) {
      $mode = $v;
   }
   elsif ($k eq 'search') {
      $search = $v;
   }
   elsif ($k eq 'output' && ($v eq 'json' || $v eq 'splunk')) {
      $output = $v;
   }
}

my $ready = {
   ip => 1,
   threatlist => 1,
   inetnum => 1,
   geoloc => 1,
   pastries => 1,
   synscan => 1,
   reverse => 1,
   forward => 1,
   resolver => 1,
   onionscan => 1,
   datascan => 1,
   sniffer => 1,
   ctl => 1,
   datashot => 1,
   onionshot => 1,
};

if (!exists($ready->{$api})) {
   $log->error("API not ready yet: $api");
   exit(2);
}

my $ary = readResults(\*STDIN, undef, 1);
my $results = $ary->[0];
my $header = $ary->[1];
my $lookup = $ary->[2];

# Avoid sending an API request for a value we have already
# looked-up. For instance, don't lookup threatlists for a
# given IP address that is seen far too often in your logs.
my $cache = {};

my @splunk = ();
for my $result (@$results) {
   my $onyphe;
   if ($mode eq 'simple') {
      if (! (defined($lookup->{$ip}) && defined($result->[$lookup->{$ip}]))
      ) {
         next;
      }

      my $value = $result->[$lookup->{$ip}];

      # Skip reserved IP addresses
      if ($na->is_ip($value) && $na->is_ip_reserved($value)) {
         next;
      }

      if (exists($cache->{$value})) {
         $onyphe = $cache->{$value};
      }
      else {
         $onyphe = $ao->$api($value) or next;
         $cache->{$value} = $onyphe;
      }
   }
   # Search API
   else {
      if (exists($cache->{$search})) {
         $onyphe = $cache->{$search};
      }
      else {
         my $search_api = 'search_'.$api;
         $search =~ s{^"|"$}{}g;
         $search =~ s{\\"}{"}g;

         my @r = ();
         my $page = 1;
         $log->verbose("search1[$search] page[$page]");
         my $s1_results = $ao->$search_api($search, $apikey, $page) or next;
         push @r, @$s1_results;

         if ($autoscroll) {
            # No max page given, we use the max_page from query result.
            if (!$maxpage) {
               $maxpage = $s1_results->[0]{max_page};
            }
            # Autoscroll asked and maxpage given, use the greatest one.
            else {
               $maxpage = ($maxpage > $s1_results->[0]{max_page})
                  ? $s1_results->[0]{max_page} : $maxpage;
            }
         }

         if ($autoscroll && ++$page <= $maxpage) {
            $log->verbose("search2[$search] maxpage[$maxpage]");
            for ($page..$maxpage) {
               $log->verbose("search2[$search] page[$_]");
               my $s2_results = $ao->$search_api($search, $apikey, $_) or next;
               push @r, @$s2_results;
            }
         }

         $onyphe = \@r;
         $cache->{$search} = $onyphe;
      }
   }

   if (@$onyphe > 0 && defined($onyphe->[0]{results})) {
      my %categories = ();
      for my $this_onyphe (@$onyphe) {
         my $onyphe_results = $this_onyphe->{results};

         for my $this (@$onyphe_results) {
            my $category = $this->{'@category'};
            push @{$categories{$category}}, $this;
         }
      }

      if ($output eq 'json') {
         for my $category (keys %categories) {
            my $this_field = 'onyphe_'.$category;
            add_field($lookup, $header, $this_field);
            $result->[$lookup->{$this_field}] = $sj->encode(
               { onyphe => { $category => $categories{$category} } },
            );
         }
      }
      else {  # splunk output
         for my $category (keys %categories) {
            my $this_field = 'onyphe_'.$category;
            add_field($lookup, $header, $this_field);
            $result->[$lookup->{$this_field}] = $category;

            for my $r (@{$categories{$category}}) {
               $log->debug(Data::Dumper::Dumper($r));
               my $copy = [ @$result ];  # Copy results to add new events.
               for my $k (keys %$r) {
                  my $result_field = 'onyphe_'.$k;
                  add_field($lookup, $header, $result_field);
                  if (ref($r->{$k}) eq 'ARRAY') {
                     $copy->[$lookup->{$result_field}] =
                        join("\n", @{$r->{$k}});
                  }
                  elsif (ref($r->{$k}) eq 'HASH') {
                     $copy->[$lookup->{$result_field}] = $sj->encode(
                        { $result_field => $r->{$k} },
                     );
                  }
                  else {
                     $copy->[$lookup->{$result_field}] = $r->{$k};
                  }
               }
               $log->debug(Data::Dumper::Dumper($copy));
               push @splunk, $copy;
            }
         }
      }
   }
}

# In splunk output mode, we have created new events, so we update the
# link to future CSV results.
if ($output eq 'splunk') {
   $ary->[0] = \@splunk;
}

outputResults($ary, undef, undef, '\n', \*STDOUT);

exit(0);

#
# Subs
#

# When we add a new field, we also give it an offset.
sub add_field {
   my ($lookup, $header, $field) = @_;

   if (!exists($lookup->{$field})) {
      push @$header, $field;
      my $offset = keys %$lookup;
      $lookup->{$field} = $offset;
   }

   return 1;
}
