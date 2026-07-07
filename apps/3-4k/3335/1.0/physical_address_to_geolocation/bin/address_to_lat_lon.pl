#!/usr/bin/perl

### Author:  James Donn (jim@splunk.com)
### Date:    March 2016
### Purpose: Given a physical address, obtain all of the geo location information.
###          - This script is called from a Splunk Alert.
###          - The Splunk Alert is triggered for addresses that are not yet in the address_geo index.
###          - The data is stored in an index because the number of addresses may grow to be too large for a lookup file.
###          - We are only adding missing information, so that we do not breach our free Google API limits.
use strict;

### Directions:
###	Edit the Customer varibles below and then copy to the $SPLUNK_HOME/bin/scripts/ folder.

### Customer variables
### Get your personal Google API Key here:
###    https://console.developers.google.com/apis/credentials/key?project=instant-bonbon-125919&type=SERVER_SIDE
###    Learn about your limits - https://developers.google.com/maps/documentation/geocoding/usage-limits#premium-usage-limits
###    Daily quotas reset at midnight Pacific Time (PT).
my $api_key        = '<enter your key>';
my $username       = "<enter your username>";
my $password       = "<enter your password>";
my $splunk_home    = "/opt/splunk/";
my $app_name       = "physical_address_to_geolocation";
my $kv_geolocation = "geolocation";
my $kv_reconcile   = "reconcile";
my $file           = "$splunk_home/etc/apps/$app_name/data/logs/output.log";
my $api_status     = "$splunk_home/etc/apps/$app_name/data/logs/api_status.log";
my $reconcile      = "$splunk_home/etc/apps/$app_name/data/logs/reconcile.log";
my $debug_file     = "$splunk_home/etc/apps/$app_name/data/logs/debug.log";
my $debug          = 1;

### Variables passed in from the Splunk alert
my ($searchCount, $searchTerms, $searchQuery, $searchName, $searchReason, $searchURL, $searchTags, $searchPath);
$searchCount   = $ARGV[0]; # $1 - Number of events returned
$searchTerms   = $ARGV[1]; # $2 - Search terms
$searchQuery   = $ARGV[2]; # $3 - Fully qualified query string
$searchName    = $ARGV[3]; # $4 - Name of saved search
$searchReason  = $ARGV[4]; # $5 - Reason saved search triggered
$searchURL     = $ARGV[5]; # $6 - URL/Permalink of saved search
if ($ARGV[7]) {            ### We received tags
   $searchTags = $ARGV[6]; # $7 - Tags, if any, otherwise $7 is $8
   $searchPath = $ARGV[7]; # $8 - Path to raw saved results in Splunk instance
} else {                   ### We didn't receive tags
   $searchPath = $ARGV[6]; # $7 - Path to raw saved results in Splunk instance
}

### Grab the search_id and create an endpointURL and use it with the REST API.
my $server = `hostname`; chop($server);
my (@dirs, $endpointURL, @search_results, @debug);
@dirs = split(/\//, $searchPath);
$endpointURL = "https\:\/\/$server\:8089/services/search/jobs/$dirs[7]/results";
push @search_results, "searchCount=>$searchCount<\nsearchTerms=>$searchTerms<\nsearchQuery=>$searchQuery<\nsearchName=>$searchName<\nsearchReason=>$searchReason<\nsearchURL=>$searchURL<\nsearchPath=>$searchPath<\n";

### Slurp in the endpoint!  This is all of the data that is returned from the search.  
push @search_results, `curl -u $username:$password -k $endpointURL`;
# if ($debug) {push(@debug, "Search Results = @search_results\n");}

### Parse out search results and format it for the Google API call
my (@results,@api_results,@api_status,@reconcile,$kv_key,$address,$cust_id,$cust_name,$cust_city,$cust_state,$cust_street,$cust_zip,$cust_lat,$cust_lon,$key_id,$location_type,$in_reconciliation);
for (my $i=0; $i<=$#search_results; $i++) {

   ### !!!REMOVE POST DEV!!! Break out of the loop early so we dont exceed the limit while developing 
   # if ($i == 250) {last;}

   ### Capture the fields from the search and replace spaces with pluses in the results to make the Google API happy.
   ### If you are re-using this script, this will need to be updated for each new search since the fields returned will be different.
   if ($search_results[$i] =~ m/offset/){
      if ($search_results[$i+2] =~ m/\<[^\<]+\<[^\<]+\>([^\<]+)/) {
         $kv_key = $1;
      }
      if ($search_results[$i+5] =~ m/\<[^\<]+\<[^\<]+\>([^\<]+)/) {
         $cust_city = $1;
         $cust_city =~ s/\s+/+/g;
      }
      if ($search_results[$i+8] =~ m/\<[^\<]+\<[^\<]+\>([^\<]+)/) {
         $cust_id = $1;
      }
      if ($search_results[$i+11] =~ m/\<[^\<]+\<[^\<]+\>([^\<]+)/) {
         $cust_lat = $1;
      }
      if ($search_results[$i+14] =~ m/\<[^\<]+\<[^\<]+\>([^\<]+)/) {
         $cust_lon = $1;
      }
      if ($search_results[$i+17] =~ m/\<[^\<]+\<[^\<]+\>([^\<]+)/) {
         $cust_name = $1;
      }
      if ($search_results[$i+20] =~ m/\<[^\<]+\<[^\<]+\>([^\<]+)/) {
         $cust_state = $1;
         $cust_state =~ s/\s+/+/g;
      }
      if ($search_results[$i+23] =~ m/\<[^\<]+\<[^\<]+\>([^\<]+)/) {
         $cust_street = $1;
         $cust_street =~ s/\s+/+/g;
      }
      if ($search_results[$i+26] =~ m/\<[^\<]+\<[^\<]+\>([^\<]+)/) {
         $cust_zip = $1;
      }
      if ($search_results[$i+29] =~ m/\<[^\<]+\<[^\<]+\>([^\<]+)/) {
         $in_reconciliation = $1;
      }
      if ($search_results[$i+32] =~ m/\<[^\<]+\<[^\<]+\>([^\<]+)/) {
         $key_id = $1;
      }
      if ($search_results[$i+35] =~ m/\<[^\<]+\<[^\<]+\>([^\<]+)/) {
         $location_type = $1;
      }
      $address = "$cust_street,+$cust_city,+$cust_state+$cust_zip";
      # if ($debug) {push(@debug, "Search Vars:\naddress=>$address<\ncust_id=>$cust_id<\ncust_name=>$cust_name<\ncust_city=>$cust_city<\ncust_state=>$cust_state<\ncust_street=>$cust_street<\ncust_zip=>$cust_zip<\ncust_lat=>$cust_lat<\ncust_lon=>$cust_lon<\nkey_id=>$key_id<\n");}

      ### Test for a complete list of variables.  If they DNE, go to the next one in the loop.
      if ($cust_id && $cust_name && $cust_city && $cust_state && $cust_street && $cust_zip && $cust_lat && $cust_lon && $key_id && $in_reconciliation) { 
         push(@debug, "VARS are COMPLETE:\naddress=>$address<\ncust_id=>$cust_id<\ncust_name=>$cust_name<\ncust_city=>$cust_city<\ncust_state=>$cust_state<\ncust_street=>$cust_street<\ncust_zip=>$cust_zip<\ncust_lat=>$cust_lat<\ncust_lon=>$cust_lon<\nkey_id=>$key_id<\nin_reconciliation=>$in_reconciliation<\n");
      } else {
         push(@debug, "VARS are MISSING:\naddress=>$address<\ncust_id=>$cust_id<\ncust_name=>$cust_name<\ncust_city=>$cust_city<\ncust_state=>$cust_state<\ncust_street=>$cust_street<\ncust_zip=>$cust_zip<\ncust_lat=>$cust_lat<\ncust_lon=>$cust_lon<\nkey_id=>$key_id<\nin_reconciliation=>$in_reconciliation<\n");
         next;
      }

      ### Get the location data from Google for each of the search results, below is an example of the command:
      ### curl https://maps.googleapis.com/maps/api/geocode/json?address=1600+Amphitheatre+Parkway,+Mountain+View,+CA&key=$api_key
      ### If the address is already in reconciliation, break out of the loop early so we dont exceed the API limits.
      if ($in_reconciliation =~ m/yes/) {
         last;
         if ($debug) {push(@debug, "Record is in reconciliation, we are SKIPPING the API query.\n")};
      } else {
         push @api_results, `curl https://maps.googleapis.com/maps/api/geocode/json?address=$address&key=$api_key`;
      }

      ### Now clean up the pluses
      $cust_city   =~ s/\+/ /g;
      $cust_state  =~ s/\+/ /g;
      $cust_street =~ s/\+/ /g;

      ### Evaluate the results - written for the Google Maps API JSON results
      my $time="\{ \"time\" : \"" . localtime . "\" \}";
      my $count = 0;
      my (@cust_lat, @cust_lon, @location_type, @formatted_address) = ();
      for (my $j=0; $j<=$#api_results; $j++) {

         ### Get the formatted address, lat, lon, and location type; increment the count
         if ($api_results[$j] =~ m/\"formatted_address\" \: \"([^"]+)\"/)  {push(@formatted_address,$1);}

         ### The location placement in the array moves around depending on the results, it cannot be incrementally 
         ### referenced to the formated_address.
         if ($api_results[$j] =~ m/\"location\" \: \{/) {
            if ($api_results[$j+1] =~ m/\"lat\" \: ([^,]+)\,/)             {push(@cust_lat,$1);++$count;}
            if ($api_results[$j+2] =~ m/\"lng\" \: ([^\n]+)\n/)            {push(@cust_lon,$1);}
            if ($api_results[$j+4] =~ m/\"location_type\" \: \"([^"]+)\"/) {push(@location_type,$1);}
         }

         ### Check for error messages.  If you find one, go to the next step in the loop so you do not over write the KV record.
         if ($api_results[$j] =~ m/error_message\" \:(.*)\n/) {
            my $error_message = $1;
            push(@debug, "error_message = >$error_message<\n");
            next;
         }
      }
      if ($debug) {push(@debug, "NEW Vars:\nCOUNT=>$count<\nCUST_LAT=>$#cust_lat<\nCUST_LON=>$#cust_lon<\nLOC_TYPE=>$#location_type<\naddress=>$address<\ncust_lat=>$cust_lat<\ncust_lon=>$cust_lon<\nlocation_type=>$location_type<\n");}

      ### If we have a single count on the location, UPDATE geolocation kv store.  
      ### More or less than one location indicates a problem.
      if ($count == 1) {
         push @results, @api_results;
         push(@api_status, "$time\n");
         push @api_status, @api_results;
         push @debug, `curl -k -u $username:$password https://localhost:8089/servicesNS/nobody/$app_name/storage/collections/data/$kv_geolocation/$key_id -H 'Content-Type: application/json' -d '{"cust_id": "$cust_id", "cust_name": "$cust_name", "cust_street": "$cust_street", "cust_city": "$cust_city", "cust_state": "$cust_state", "cust_zip": "$cust_zip", "cust_lat": "@cust_lat[0]", "cust_lon": "@cust_lon[0]", "location_type": "@location_type[0]", "in_reconciliation": "no"}'`;

         if ($debug) {push(@debug, "\nPushed to API: user:pass=$username:$password, app=$app_name, kv_coll=$kv_geolocation, keyid=$key_id\n cust_id: $cust_id, cust_name: $cust_name, cust_street: $cust_street, cust_city: $cust_city, cust_state: $cust_state, cust_zip: $cust_zip, cust_lat: @cust_lat[0], cust_lon: @cust_lon[0], location_type: @location_type[0], in_reconciliation: yes\n");}

      ### If there are multiple results for one location, ADD to kv_reconcile.
      } elsif ($count > 1) {
         push @reconcile, @api_results;
         push(@api_status, "$time\n");
         push @api_status, @api_results;

         ### Since there are going to be multiple results, we need to loop through the API push
         for (my $k=0; $k<=$#cust_lat; $k++) {
            push @debug, "MAX_ARGV = $#cust_lat\nNOW SERVING = $k\n";
            push @debug, `curl -k -u $username:$password https://localhost:8089/servicesNS/nobody/$app_name/storage/collections/data/$kv_reconcile -H 'Content-Type: application/json' -d '{"cust_id": "$cust_id", "cust_name": "$cust_name", "formatted_address": "@formatted_address[$k]", "cust_lat": "@cust_lat[$k]", "cust_lon": "@cust_lon[$k]", "location_type": "@location_type[$k]", "kv_key": "$key_id"}'`;
            ### Now update the in_reconciliation field in the geolocation kv store
            push @debug, `curl -k -u $username:$password https://localhost:8089/servicesNS/nobody/$app_name/storage/collections/data/$kv_geolocation/$key_id -H 'Content-Type: application/json' -d '{"cust_id": "$cust_id", "cust_name": "$cust_name", "cust_street": "$cust_street", "cust_city": "$cust_city", "cust_state": "$cust_state", "cust_zip": "$cust_zip", "cust_lat": "DNE", "cust_lon": "DNE", "location_type": "DNE", "in_reconciliation": "yes"}'`;

            if ($debug) {push(@debug, "\nPushed to RECONCILE API: user:pass=$username:$password, app=$app_name, kv_coll=$kv_geolocation\n cust_id: $cust_id, cust_name: $cust_name, formatted_address: @formatted_address[$k], cust_lat: @cust_lat[$k], cust_lon: @cust_lon[$k], location_type: @location_type[$k], kv_key: $key_id\n");}
         }

      ### If there are zero results, record them so that we do not populate the KV store with garbage.
      } else {
         push @debug, @api_results;
         push(@api_status, "$time\n");
         push @api_status, @api_results;
         push @debug, "\nPushed to NO WHERE, Something went wrong...\nZERO COUNT = >$count<\ncust_id = >$cust_id<\n";
      }
      @api_results = ();

      ### Pretty up the debug list
      $address =~ s/\+/ /g;
      my $time=localtime;
      push(@debug, "$time: $address\n\n\n\n");
   }
}

### Write the results to a file
open (OUTPUT, ">$file") or die "Can't write to $file: $!";
foreach my $line (@results) {
   print OUTPUT ("$line");
}
close (OUTPUT);

### Write the reconcile events to a file
open (OUTPUT, ">$reconcile") or die "Can't write to $reconcile: $!";
foreach my $line (@reconcile) {
   print OUTPUT ("$line");
}
close (OUTPUT);

### Write the debug log
open (OUTPUT, ">$debug_file") or die "Can't write to $debug_file: $!";
foreach my $line (@debug) {
   print OUTPUT ("$line");
}
close (OUTPUT);

### Write the API status
open (OUTPUT, ">$api_status") or die "Can't write to $api_status: $!";
foreach my $line (@api_status) {
   print OUTPUT ("$line");
}
close (OUTPUT);

### Delete the results file
# unlink $file;
