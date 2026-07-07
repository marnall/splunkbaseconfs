#!/usr/bin/perl

use JSON;
use Data::Dumper;
 
my $version = "";
my $app = "SA-devforall";
my $path = "/opt/git/SA-devforall";
my $buildPath = "/tmp/$app";
my $output = "";
my $build = 0;

print "What version will this build be?: ";
$version = <STDIN>;
chomp $version;

`sudo chown -R dveuve $path`;

open(FIN, $path . "/default/app.conf");
while(<FIN>){
	my $line = $_;
	chomp($line);
	if($line =~ /^build = (\d*)/){
		$build = $1;
		$build++;
		$output .= "build = $build\n";
	}elsif($line =~ /^version/){
		$output .= "version = $version\n";
	}else{
		$output .= $line . "\n";
	}
}
close(FIN);
open(FOUT, ">" . $path . "/default/app.conf");
print FOUT $output;
close(FOUT);


print `rm -rf $buildPath`;

print `cp -r $path $buildPath`;

print `find $buildPath -type f -name ".DS_Store" -delete`;
print `find $buildPath -type d -name ".git" -exec rm -rf {} \\;`;
print `find $buildPath -type f -name "*.pyc" -exec rm -rf {} \\;`;
print `find $buildPath -type f -name "*.pyo" -exec rm -rf {} \\;`;
print `rm $buildPath/README.md`;

print `rm $buildPath/.gitignore`;
print `rm -rf $buildPath/local`;
print `rm -rf $buildPath/.vscode`;
print `rm -rf $buildPath/.idea`;
print `rm -rf $buildPath/.sfdx`;
print `rm $buildPath/metadata/local.meta`;
print `rm -rf $buildPath/default.*`;
print `rm -rf $buildPath/build_scripts`;
print `rm -rf $buildPath/locale`;

print "Running: " . "cd /tmp/ && export COPYFILE_DISABLE=1 && tar czvf $app.tgz $app/\n";
print `cd /tmp/ && export COPYFILE_DISABLE=1 && tar czvf $app.tgz $app/`;
print `cd /tmp/ && cp $app.tgz /Volumes/GoogleDrive/My\\ Drive/Apps/$app.spl `;




print "Checking for private files...\n";
print `find /opt/splunk-SA-jsforall/splunk/etc/users/admin/$app/ -type f | grep -v lookups | grep -v ui-prefs | grep -v viewstates | grep -v local.meta | grep -v history | xargs -n 1 -I xxx cat xxx`;
