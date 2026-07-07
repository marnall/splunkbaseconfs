#!/usr/bin/perl
###############################################################################
#
# Copyright (C) 2013-2014 Cisco and/or its affiliates. All rights reserved.
#
# THE PRODUCT AND DOCUMENTATION ARE PROVIDED AS IS WITHOUT WARRANTY
# OF ANY KIND, AND CISCO DISCLAIMS ALL WARRANTIES AND REPRESENTATIONS,
# EXPRESS OR IMPLIED, WITH RESPECT TO THE PRODUCT, DOCUMENTATION AND
# RELATED MATERIALS INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE; WARRANTIES
# ARISING FROM A COURSE OF DEALING, USAGE OR TRADE PRACTICE; AND WARRANTIES
# CONCERNING THE NON-INFRINGEMENT OF THIRD PARTY RIGHTS.
#
# IN NO EVENT SHALL CISCO BE LIABLE FOR ANY DAMAGES RESULTING FROM
# LOSS OF DATA, LOST PROFITS, LOSS OF USE OF EQUIPMENT OR LOST CONTRACTS
# OR FOR ANY SPECIAL, INDIRECT, INCIDENTAL, PUNITIVE, EXEMPLARY OR
# CONSEQUENTIAL DAMAGES IN ANY WAY ARISING OUT OF OR IN CONNECTION WITH
# THE USE OR PERFORMANCE OF THE PRODUCT OR DOCUMENTATION OR RELATING TO
# THIS AGREEMENT, HOWEVER CAUSED, EVEN IF IT HAS BEEN MADE AWARE OF THE
# POSSIBILITY OF SUCH DAMAGES.  CISCO'S ENTIRE LIABILITY TO LICENSEE,
# REGARDLESS OF THE FORM OF ANY CLAIM OR ACTION OR THEORY OF LIABILITY
# (INCLUDING CONTRACT, TORT, OR WARRANTY), SHALL BE LIMITED TO THE
# LICENSE FEES PAID BY LICENSEE TO USE THE PRODUCT.
#
###############################################################################
#
#  Change Log
#
#   1.0   - cogrady - ORIGINAL RELEASE WITH INTRODUCTION OF SPLUNK APP
#   1.0.2 - cogrady - Reorder the path to prioritize away from the openssl
#                       binary included with Splunk
#   1.0.5 - cogrady - Remove "HOPOPT" for IP proto in favor of "Unknown",
#                       add flags that would allow for flow collection,
#                       log to a debug.log for verbose output while a daemon
#   2.0   - cogrady - Optimizing event processing, added flow collection
#   2.1   - cogrady - Added test command-line option, move RNA collection
#                       into a seperate process, add bookmark migraition to
#                       support new methodology, tweaked File / Malware log
#                       processing for added consistency
#   2.1.1 - cogrady - Fixed bug in sha256 lookups for File / Malware events
#   2.1.2 - cogrady - Tweaked sec intel event handling, add translation of
#                       monitor rules in connection logs
#   2.1.3 - cogrady - Pass through an unexpected die() while processing logs,
#                       use FindBin for lib path
#   2.1.4 - cogrady - Fix logic in connection test
#   2.1.5 - cogrady - Re-fixed logic in connection test -- only working when
#                       attempting to read data from the connection
#   2.1.6 - cogrady - Die early if running on Windows until fully supported,
#                       added timestamp to verbose() messages
#   2.2.0 - cogrady - Add EXTRA_DATA flag to IPS event request if requested in
#                       config, added dump of effective config in debug mode
#   2.2.1 - cogrady - Add error handling around lock_retrieve() call, now
#                       remove corrupt metadata file, more comprehensive test-
#                       mode
#   2.2.2 - suddesai - Updated the SSL socket creation stanzas to force
#                       'TLSv1' encryption for better compatibility with 
#                       Firepower 6.x
#
###############################################################################

use strict;
use warnings;

use POSIX;
use Data::Dumper;
use FindBin;
use Getopt::Long;
use Socket;
use Storable qw( lock_store lock_retrieve );

use lib "$FindBin::Bin/lib";
use IO::Socket::SSL;
use SFStreamer;
$SFStreamer::debug = 0;  # Turn off debugging to start
use SFPkcs12;

# Look to see if the IPv6 libs are available
my $IP6_THERE = 0;
eval {
    require Socket6;
    require IO::Socket::INET6;
};
$IP6_THERE = 1 unless $@;


###############################################################################
# Settings and contants
###############################################################################

my $DO_ROTOTATION      = 1;     # 1 = Rotate logs at MAX_LOG_LINES / 0 = Don't do that
my $MAX_LOG_LINES      = 9999;  # The maximum number of lines to write to a log before rotating logs
my $PID_FILE           = './estreamer_client.pid';
my $DEBUG_FILE         = './estreamer_debug.log';
my $METADATA_FILE      = './metadata.dat';
my $DEFAULT_PORT       = 8302;
my $DEFAULT_EXTRA_DATA = 0;
my $DEFAULT_PACKETS    = 0;
my $DEFAULT_FLOWS      = 0;
my $DEFAULT_USERS      = 0;
my $DEFAULT_METADATA   = 0;
my $DEFAULT_WATCH      = 0;


###############################################################################
# Globals
###############################################################################

# Base flags to use for requests
my $req_flags = $FLAG_METADATA_4 | $FLAG_DETAIL_REQUEST | $FLAG_SEND_ARCHIVE_TIMESTAMP;
# my $req_flags = $FLAG_IDS | $FLAG_IMPACT_ALERTS | $FLAG_IDS_IMPACT_FLAG | $FLAG_METADATA_4 | $FLAG_EXTRA_DATA | $FLAG_POLICY_EVENTS_6 | $FLAG_DETAIL_REQUEST | $FLAG_RNA_EVENTS_7 | $FLAG_RNA | $FLAG_RUA | $FLAG_SEND_ARCHIVE_TIMESTAMP;

# OUTPUT_PLUGIN to package the versions we need
# Oddly, for SFStream.pm to do what we want
our $OUTPUT_PLUGIN = {
    flags              => $req_flags,
    # The following values are from pages 60 and 61 of the 5.3 eStreamer Integration Guide
    # Only the appropriate values for 4.10 and later are included below:
    ids_events_ver     => 0,  # 2 - 4.9 - 4.10.x, 3 - 5.0 - 5.1, 4 - 5.1.1.x, 5- 5.2.x, 6 - 5.3+
    metadata           => 4,  # 4 - 4.7+
    policy_events_ver  => 0,  # 6 - 4.10.0 - 4.10.x, 7 - 5.0 - 5.0.2, 8 - 5.1+
    rna_events_ver     => 0,  # 7 - 4.10.0 - 4.10.x, 8 - 5.0.x, 9 - 5.1.x, 10 - 5.2+
    rna_flow_ver       => 0,  # 5 - 4.9.1 - 4.10.x, 6 - 5.0.x, 7 - 5.1.0.x, 8 - 5.1.1.x, 9 - 5.2+
    rua_ver            => 0,  # 1 - 4.7 - 4.10.x, 2 - 5.0.x, 3 - 5.1-5.1.x, 4 - 5.2+
    fireamp_events_ver => 0,  # 1 - 5.1.0.x, 2 - 5.1.1.x, 3 - 5.2.x, 4 - 5.3+
    filelog_events_ver => 0,  # 1 - 5.1.1 - 5.1.x, 2 - 5.2.x, 3 - 5.3+
    impact_flag_ver    => 0,  # 1 - 5.2.x and earlier, 2 - 5.3+
};

# Metadata bits
my %metadata;

# Prepopulate as many of the bits as we can

$metadata{'devices'}{'0'} = 'Defense Center';

$metadata{'security_zones'}{'00000000-0000-0000-0000-000000000000'} = 'N/A';

$metadata{'interfaces'}{'00000000-0000-0000-0000-000000000000'} = 'N/A';

$metadata{'corr_event_types'}{'0'} = 'Unknown';
$metadata{'corr_event_types'}{'1'} = 'Intrusion Event';
$metadata{'corr_event_types'}{'2'} = 'Host Discovery';
$metadata{'corr_event_types'}{'3'} = 'User Activity';
$metadata{'corr_event_types'}{'4'} = 'Whitelist';
$metadata{'corr_event_types'}{'5'} = 'Malware Event';

$metadata{'corr_host_type'}{'0'} = 'Host';
$metadata{'corr_host_type'}{'1'} = 'Bridge';
$metadata{'corr_host_type'}{'2'} = 'Router';

$metadata{'corr_criticallity'}{'0'} = 'None';
$metadata{'corr_criticallity'}{'1'} = 'Low';
$metadata{'corr_criticallity'}{'2'} = 'Medium';
$metadata{'corr_criticallity'}{'3'} = 'High';

$metadata{'users'}{'0'} = 'Unknown';

$metadata{'ip_protos'}{'0'}   = 'Unknown';
$metadata{'ip_protos'}{'1'}   = 'ICMP';
$metadata{'ip_protos'}{'2'}   = 'IGMP';
$metadata{'ip_protos'}{'3'}   = 'GGP';
$metadata{'ip_protos'}{'4'}   = 'IPv4';
$metadata{'ip_protos'}{'5'}   = 'ST';
$metadata{'ip_protos'}{'6'}   = 'TCP';
$metadata{'ip_protos'}{'7'}   = 'CBT';
$metadata{'ip_protos'}{'8'}   = 'EGP';
$metadata{'ip_protos'}{'9'}   = 'IGP';
$metadata{'ip_protos'}{'10'}  = 'BBN-RCC-MON';
$metadata{'ip_protos'}{'11'}  = 'NVP-II';
$metadata{'ip_protos'}{'12'}  = 'PUP';
$metadata{'ip_protos'}{'13'}  = 'ARGUS';
$metadata{'ip_protos'}{'14'}  = 'EMCON';
$metadata{'ip_protos'}{'15'}  = 'XNET';
$metadata{'ip_protos'}{'16'}  = 'CHAOS';
$metadata{'ip_protos'}{'17'}  = 'UDP';
$metadata{'ip_protos'}{'18'}  = 'MUX';
$metadata{'ip_protos'}{'19'}  = 'DCN-MEAS';
$metadata{'ip_protos'}{'20'}  = 'HMP';
$metadata{'ip_protos'}{'21'}  = 'PRM';
$metadata{'ip_protos'}{'22'}  = 'XNS-IDP';
$metadata{'ip_protos'}{'23'}  = 'TRUNK-1';
$metadata{'ip_protos'}{'24'}  = 'TRUNK-2';
$metadata{'ip_protos'}{'25'}  = 'LEAF-1';
$metadata{'ip_protos'}{'26'}  = 'LEAF-2';
$metadata{'ip_protos'}{'27'}  = 'RDP';
$metadata{'ip_protos'}{'28'}  = 'IRTP';
$metadata{'ip_protos'}{'29'}  = 'ISO-TP4';
$metadata{'ip_protos'}{'30'}  = 'NETBLT';
$metadata{'ip_protos'}{'31'}  = 'MFE-NSP';
$metadata{'ip_protos'}{'32'}  = 'MERIT-INP';
$metadata{'ip_protos'}{'33'}  = 'DCCP';
$metadata{'ip_protos'}{'34'}  = '3PC';
$metadata{'ip_protos'}{'35'}  = 'IDPR';
$metadata{'ip_protos'}{'36'}  = 'XTP';
$metadata{'ip_protos'}{'37'}  = 'DDP';
$metadata{'ip_protos'}{'38'}  = 'IDPR-CMTP';
$metadata{'ip_protos'}{'39'}  = 'TP++';
$metadata{'ip_protos'}{'40'}  = 'IL';
$metadata{'ip_protos'}{'41'}  = 'IPv6';
$metadata{'ip_protos'}{'42'}  = 'SDRP';
$metadata{'ip_protos'}{'43'}  = 'IPv6-Route';
$metadata{'ip_protos'}{'44'}  = 'IPv6-Frag';
$metadata{'ip_protos'}{'45'}  = 'IDRP';
$metadata{'ip_protos'}{'46'}  = 'RSVP';
$metadata{'ip_protos'}{'47'}  = 'GRE';
$metadata{'ip_protos'}{'48'}  = 'MHRP';
$metadata{'ip_protos'}{'49'}  = 'BNA';
$metadata{'ip_protos'}{'50'}  = 'ESP';
$metadata{'ip_protos'}{'51'}  = 'AH';
$metadata{'ip_protos'}{'52'}  = 'I-NLSP';
$metadata{'ip_protos'}{'53'}  = 'SWIPE';
$metadata{'ip_protos'}{'54'}  = 'NARP';
$metadata{'ip_protos'}{'55'}  = 'MOBILE';
$metadata{'ip_protos'}{'56'}  = 'TLSP';
$metadata{'ip_protos'}{'57'}  = 'SKIP';
$metadata{'ip_protos'}{'58'}  = 'IPv6-ICMP';
$metadata{'ip_protos'}{'59'}  = 'IPv6-NoNxt';
$metadata{'ip_protos'}{'60'}  = 'IPv6-Opts';
$metadata{'ip_protos'}{'62'}  = 'CFTP';
$metadata{'ip_protos'}{'64'}  = 'SAT-EXPAK';
$metadata{'ip_protos'}{'65'}  = 'KRYPTOLAN';
$metadata{'ip_protos'}{'66'}  = 'RVD';
$metadata{'ip_protos'}{'67'}  = 'IPPC';
$metadata{'ip_protos'}{'69'}  = 'SAT-MON';
$metadata{'ip_protos'}{'70'}  = 'VISA';
$metadata{'ip_protos'}{'71'}  = 'IPCV';
$metadata{'ip_protos'}{'72'}  = 'CPNX';
$metadata{'ip_protos'}{'73'}  = 'CPHB';
$metadata{'ip_protos'}{'74'}  = 'WSN';
$metadata{'ip_protos'}{'75'}  = 'PVP';
$metadata{'ip_protos'}{'76'}  = 'BR-SAT-MON';
$metadata{'ip_protos'}{'77'}  = 'SUN-ND';
$metadata{'ip_protos'}{'78'}  = 'WB-MON';
$metadata{'ip_protos'}{'79'}  = 'WB-EXPAK';
$metadata{'ip_protos'}{'80'}  = 'ISO-IP';
$metadata{'ip_protos'}{'81'}  = 'VMTP';
$metadata{'ip_protos'}{'82'}  = 'SECURE-VMTP';
$metadata{'ip_protos'}{'83'}  = 'VINES';
$metadata{'ip_protos'}{'84'}  = 'TTP';
$metadata{'ip_protos'}{'84'}  = 'IPTM';
$metadata{'ip_protos'}{'85'}  = 'NSFNET-IGP';
$metadata{'ip_protos'}{'86'}  = 'DGP';
$metadata{'ip_protos'}{'87'}  = 'TCF';
$metadata{'ip_protos'}{'88'}  = 'EIGRP';
$metadata{'ip_protos'}{'89'}  = 'OSPF';
$metadata{'ip_protos'}{'90'}  = 'Sprite-RPC';
$metadata{'ip_protos'}{'91'}  = 'LARP';
$metadata{'ip_protos'}{'92'}  = 'MTP';
$metadata{'ip_protos'}{'93'}  = 'AX.25';
$metadata{'ip_protos'}{'94'}  = 'IPIP';
$metadata{'ip_protos'}{'95'}  = 'MICP';
$metadata{'ip_protos'}{'96'}  = 'SCC-SP';
$metadata{'ip_protos'}{'97'}  = 'ETHERIP';
$metadata{'ip_protos'}{'98'}  = 'ENCAP';
$metadata{'ip_protos'}{'100'} = 'GMTP';
$metadata{'ip_protos'}{'101'} = 'IFMP';
$metadata{'ip_protos'}{'102'} = 'PNNI';
$metadata{'ip_protos'}{'103'} = 'PIM';
$metadata{'ip_protos'}{'104'} = 'ARIS';
$metadata{'ip_protos'}{'105'} = 'SCPS';
$metadata{'ip_protos'}{'106'} = 'QNX';
$metadata{'ip_protos'}{'107'} = 'A/N';
$metadata{'ip_protos'}{'108'} = 'IPComp';
$metadata{'ip_protos'}{'109'} = 'SNP';
$metadata{'ip_protos'}{'110'} = 'Compaq-Peer';
$metadata{'ip_protos'}{'111'} = 'IPX-in-IP';
$metadata{'ip_protos'}{'112'} = 'VRRP';
$metadata{'ip_protos'}{'113'} = 'PGM';
$metadata{'ip_protos'}{'115'} = 'L2TP';
$metadata{'ip_protos'}{'116'} = 'DDX';
$metadata{'ip_protos'}{'117'} = 'IATP';
$metadata{'ip_protos'}{'118'} = 'STP';
$metadata{'ip_protos'}{'119'} = 'SRP';
$metadata{'ip_protos'}{'120'} = 'UTI';
$metadata{'ip_protos'}{'121'} = 'SMP';
$metadata{'ip_protos'}{'122'} = 'SM';
$metadata{'ip_protos'}{'123'} = 'PTP';
$metadata{'ip_protos'}{'124'} = 'IS-IS over IPv4';
$metadata{'ip_protos'}{'125'} = 'FIRE';
$metadata{'ip_protos'}{'126'} = 'CRTP';
$metadata{'ip_protos'}{'127'} = 'CRUDP';
$metadata{'ip_protos'}{'128'} = 'SSCOPMCE';
$metadata{'ip_protos'}{'129'} = 'IPLT';
$metadata{'ip_protos'}{'130'} = 'SPS';
$metadata{'ip_protos'}{'131'} = 'PIPE';
$metadata{'ip_protos'}{'132'} = 'SCTP';
$metadata{'ip_protos'}{'133'} = 'FC';
$metadata{'ip_protos'}{'134'} = 'RSVP-E2E-IGNORE';
$metadata{'ip_protos'}{'135'} = 'Mobility Header';
$metadata{'ip_protos'}{'136'} = 'UDPLite';
$metadata{'ip_protos'}{'137'} = 'MPLS-in-IP';
$metadata{'ip_protos'}{'138'} = 'manet';
$metadata{'ip_protos'}{'139'} = 'HIP';
$metadata{'ip_protos'}{'140'} = 'Shim6';
$metadata{'ip_protos'}{'141'} = 'WESP';
$metadata{'ip_protos'}{'142'} = 'ROHC';

$metadata{'app_protos'}{'0'} = 'Unknown';

$metadata{'client_apps'}{'0'} = 'Unknown';

$metadata{'source_apps'}{'0'} = 'Unknown';

$metadata{'payloads'}{'0'} = 'Unknown';

$metadata{'blocked'}{'0'} = 'No';
$metadata{'blocked'}{'1'} = 'Yes';
$metadata{'blocked'}{'2'} = 'Would';

$metadata{'geolocations'}{'0'} = 'unknown';

$metadata{'fw_rule_reasons'}{'0'}   = 'N/A';
$metadata{'fw_rule_reasons'}{'1'}   = 'IP Block';
$metadata{'fw_rule_reasons'}{'2'}   = 'IP Monitor';
$metadata{'fw_rule_reasons'}{'4'}   = 'User Bypass';
$metadata{'fw_rule_reasons'}{'8'}   = 'File Monitor';
$metadata{'fw_rule_reasons'}{'16'}  = 'File Block';
$metadata{'fw_rule_reasons'}{'32'}  = 'Intrusion Monitor';
$metadata{'fw_rule_reasons'}{'64'}  = 'Intrusion Block';
$metadata{'fw_rule_reasons'}{'128'} = 'File Resume Block';
$metadata{'fw_rule_reasons'}{'256'} = 'File Resume Allow';
$metadata{'fw_rule_reasons'}{'512'} = 'File Custom Detection';

$metadata{'os_fingerprints'}{'00000000-0000-0000-0000-000000000000'}{'os'}     = 'Unknown';
$metadata{'os_fingerprints'}{'00000000-0000-0000-0000-000000000000'}{'vendor'} = 'Unknown';
$metadata{'os_fingerprints'}{'00000000-0000-0000-0000-000000000000'}{'ver'}    = 'Unknown';

$metadata{'file_shas'}{'0000000000000000000000000000000000000000000000000000000000000000'} = 'Unknown';

$metadata{'url_reputations'}{'0'} = 'Unknown';

$metadata{'url_categories'}{'0'} = 'Unknown';

$metadata{'source_detectors'}{'0'} = 'Unknown';

$metadata{'source_types'}{'0'} = 'RNA';

$metadata{'malware_event_types'}{'0'} = 'Unknown';

$metadata{'file_types'}{'0'} = 'Unknown';

$metadata{'directions'}{'0'} = 'Unknown';
$metadata{'directions'}{'1'} = 'Download';
$metadata{'directions'}{'2'} = 'Upload';

$metadata{'file_actions'}{'0'} = 'N/A';
$metadata{'file_actions'}{'1'} = 'Detect';
$metadata{'file_actions'}{'2'} = 'Block';
$metadata{'file_actions'}{'3'} = 'Malware Cloud Lookup';
$metadata{'file_actions'}{'4'} = 'Malware Block';
$metadata{'file_actions'}{'5'} = 'Malware Whitelist';
$metadata{'file_actions'}{'6'} = 'Cloud Lookup Timeout';

$metadata{'file_dispositions'}{'0'} = 'N/A';
$metadata{'file_dispositions'}{'1'} = 'Clean';
$metadata{'file_dispositions'}{'2'} = 'Neutral';
$metadata{'file_dispositions'}{'3'} = 'Malware';
$metadata{'file_dispositions'}{'4'} = 'Cache Miss';
$metadata{'file_dispositions'}{'5'} = 'No Cloud Response';

$metadata{'clouds'}{'00000000-0000-0000-0000-000000000000'} = 'N/A';

$metadata{'fireamp_detectors'}{'0'} = 'RNA';

$metadata{'fireamp_types'}{'0'}          = 'N/A';
$metadata{'fireamp_types'}{'1'}          = 'Threat Detected in Network File Transfer';
$metadata{'fireamp_types'}{'2'}          = 'Threat Detected in Network File Transfer (Retrospective)';
$metadata{'fireamp_types'}{'553648143'}  = 'Threat Quarantined';
$metadata{'fireamp_types'}{'553648145'}  = 'Threat Detected in Exclusion';
$metadata{'fireamp_types'}{'553648146'}  = 'Cloud Recall Restore from Quarantine Started';
$metadata{'fireamp_types'}{'553648147'}  = 'Cloud Recall Quarantine Started';
$metadata{'fireamp_types'}{'553648149'}  = 'Quarantined Item Restored';
$metadata{'fireamp_types'}{'553648150'}  = 'Quarantine Restore Started';
$metadata{'fireamp_types'}{'553648154'}  = 'Cloud Recall Restore from Quarantine';
$metadata{'fireamp_types'}{'553648155'}  = 'Cloud Recall Quarantine';
$metadata{'fireamp_types'}{'553648168'}  = 'Blocked Execution';
$metadata{'fireamp_types'}{'554696714'}  = 'Scan Started';
$metadata{'fireamp_types'}{'554696715'}  = 'Scan Completed, No Detections';
$metadata{'fireamp_types'}{'1090519054'} = 'Threat Detected';
$metadata{'fireamp_types'}{'1091567628'} = 'Scan Completed With Detections';
$metadata{'fireamp_types'}{'2164260880'} = 'Quarantine Failure';
$metadata{'fireamp_types'}{'2164260884'} = 'Quarantine Restore Failed';
$metadata{'fireamp_types'}{'2164260892'} = 'Cloud Recall Restore from Quarantine Failed';
$metadata{'fireamp_types'}{'2164260893'} = 'Cloud Recall Quarantine Attempt Failed';
$metadata{'fireamp_types'}{'2165309453'} = 'Scan Failed';

$metadata{'fireamp_subtypes'}{'0'}  = 'N/A';
$metadata{'fireamp_subtypes'}{'1'}  = 'Create';
$metadata{'fireamp_subtypes'}{'2'}  = 'Execute';
$metadata{'fireamp_subtypes'}{'4'}  = 'Scan';
$metadata{'fireamp_subtypes'}{'22'} = 'Move';

$metadata{'si_src_dests'}{'0'} = 'N/A';

$metadata{'file_storages'}{'0'}  = 'N/A';
$metadata{'file_storages'}{'1'}  = 'File Stored';
$metadata{'file_storages'}{'2'}  = 'File Stored';
$metadata{'file_storages'}{'3'}  = 'Unable to Store File';
$metadata{'file_storages'}{'4'}  = 'Unable to Store File';
$metadata{'file_storages'}{'5'}  = 'Unable to Store File';
$metadata{'file_storages'}{'6'}  = 'Unable to Store File';
$metadata{'file_storages'}{'7'}  = 'Unable to Store File';
$metadata{'file_storages'}{'8'}  = 'File Size is Too Large';
$metadata{'file_storages'}{'9'}  = 'File Size is Too Small';
$metadata{'file_storages'}{'10'} = 'Unable to Store File';
$metadata{'file_storages'}{'11'} = 'File Not Stored, Disposition Unavailable';

$metadata{'file_sandboxes'}{'0'}  = 'N/A';
$metadata{'file_sandboxes'}{'1'}  = 'Sent for Analysis';
$metadata{'file_sandboxes'}{'2'}  = 'Sent for Analysis';
$metadata{'file_sandboxes'}{'4'}  = 'Sent for Analysis';
$metadata{'file_sandboxes'}{'5'}  = 'Failed to Send';
$metadata{'file_sandboxes'}{'6'}  = 'Failed to Send';
$metadata{'file_sandboxes'}{'7'}  = 'Failed to Send';
$metadata{'file_sandboxes'}{'8'}  = 'Failed to Send';
$metadata{'file_sandboxes'}{'9'}  = 'File Size is Too Small';
$metadata{'file_sandboxes'}{'10'} = 'File Size is Too Large';
$metadata{'file_sandboxes'}{'11'} = 'Sent for Analysis';
$metadata{'file_sandboxes'}{'12'} = 'Analysis Complete';
$metadata{'file_sandboxes'}{'13'} = 'Failure (Network Issue)';
$metadata{'file_sandboxes'}{'14'} = 'Failure (Rate Limit)';
$metadata{'file_sandboxes'}{'15'} = 'Failure (File Too Large)';
$metadata{'file_sandboxes'}{'16'} = 'Failure (File Read Error)';
$metadata{'file_sandboxes'}{'17'} = 'Failure (Internal Library Error)';
$metadata{'file_sandboxes'}{'19'} = 'File Not Sent, Disposition Unavailable';
$metadata{'file_sandboxes'}{'20'} = 'Failure (Cannot Run File)';
$metadata{'file_sandboxes'}{'21'} = 'Failure (Analysis Timeout)';
$metadata{'file_sandboxes'}{'22'} = 'Sent for Analysis';
$metadata{'file_sandboxes'}{'23'} = 'File Not Supported';


# Field translations for consistent field names
my %field_translations = (
    'event_usec'                 => '',
    'file_event_timestamp'       => '',
    'event_sec'                  => '',
    'event_second'               => '',
    'policy_tv_sec'              => '',
    'timestamp'                  => '',
    'event_microsecond'          => '',
    'tv_sec'                     => 'orig_event_sec',
    'tv_usec'                    => 'orig_event_usec',
    'src_ip6_addr'               => '',
    'dest_ip6_addr'              => '',
    'name_string_length'         => '',
    'name_string_data'           => 'name',
    'name_length'                => '',
    'name_string'                => 'name',
    'desc_length'                => '',
    'desc'                       => 'description',
    'desc_string_length'         => '',
    'desc_string_data'           => 'description',
    'event_type_length'          => '',
    'event_type_data'            => 'event_type',
    'sensor_id'                  => 'sensor',
    'sensorId'                   => 'sensor',
    'generator_id'               => 'gid',
    'sig_gen'                    => 'gid',
    'signature_id'               => 'sid',
    'sig_id'                     => 'sid',
    'signature_revision'         => 'rev',
    'rule_rev'                   => 'rev',
    'classification_id'          => 'class',
    'type_id'                    => 'type',
    'subtype_id'                 => 'subtype',
    'policy_sensor_id'           => 'policy_sensor',
    'sha'                        => 'sha256',
    'file_sha'                   => 'sha256',
    'parent_sha'                 => 'parent_sha256',
    'policy_id'                  => 'corr_policy',
    'src_addr'                   => 'src_ip',
    'ip_source'                  => 'src_ip',
    'ip_src'                     => 'src_ip',
    'src_ip_addr'                => 'src_ip',
    'initiatorIp'                => 'src_ip',
    'dst_addr'                   => 'dest_ip',
    'ip_destination'             => 'dest_ip',
    'ip_dst'                     => 'dest_ip',
    'dest_ip_addr'               => 'dest_ip',
    'responderIp'                => 'dest_ip',
    'sport_itype'                => 'src_port',
    'port_src'                   => 'src_port',
    'initiatorPort'              => 'src_port',
    'dst_port'                   => 'dest_port',
    'dport_icode'                => 'dest_port',
    'port_dst'                   => 'dest_port',
    'responderPort'              => 'dest_port',
    'ip_protocol'                => 'ip_proto',
    'protocol'                   => 'ip_proto',
    'transport_proto'            => 'ip_proto',
    'file_type_id'               => 'file_type',
    'web_app_id'                 => 'web_app',
    'web_application_id'         => 'web_app',
    'webApp'                     => 'web_app',
    'client_app_id'              => 'client_app',
    'client_application_id'      => 'client_app',
    'clientId'                   => 'client_app',
    'app_protocol_id'            => 'app_proto',
    'application_protocol_id'    => 'app_proto',
    'app_id'                     => 'app_proto',
    'applicationId'              => 'app_proto',
    'src_service_id'             => 'src_app_proto',
    'dest_service_id'            => 'dest_app_proto',
    'connection_second'          => 'connection_sec',
    'connection_time'            => 'connection_sec',
    'tcpFlags'                   => 'tcp_flags',
    'netflowSource'              => 'netflow_src',
    'instanceId'                 => 'instance_id',
    'connection_instance_id'     => 'instance_id',
    'connection_instance'        => 'instance_id',
    'connection_counter'         => 'connection_id',
    'connectId'                  => 'connection_id',
    'firstPktsecond'             => 'first_pkt_sec',
    'lastPktsecond'              => 'last_pkt_sec',
    'initiatorPkts'              => 'src_pkts',
    'responderPkts'              => 'dest_pkts',
    'initiatorBytes'             => 'src_bytes',
    'responderBytes'             => 'dest_bytes',
    'fileCount'                  => 'file_count',
    'ipsCount'                   => 'ips_count',
    'netbiosDomain'              => 'netbios_domain',
    'clientVersion'              => 'client_version',
    'monitorRules[0]'            => 'monitor_rule_1',
    'monitorRules[1]'            => 'monitor_rule_2',
    'monitorRules[2]'            => 'monitor_rule_3',
    'monitorRules[3]'            => 'monitor_rule_4',
    'monitorRules[4]'            => 'monitor_rule_5',
    'monitorRules[5]'            => 'monitor_rule_6',
    'monitorRules[6]'            => 'monitor_rule_7',
    'monitorRules[7]'            => 'monitor_rule_8',
    'src_dest'                   => 'sec_intel_ip',
    'layer'                      => 'ip_layer',
    'urlCategory'                => 'url_category',
    'urlReputation'              => 'url_reputation',
    'firewall_rule_id'           => 'fw_rule',
    'ruleId'                     => 'fw_rule',
    'rule_id'                    => 'fw_rule', # Need to watch for correlation events, then rename to corr_rule
    'ruleAction'                 => 'fw_rule_action',
    'action'                     => 'file_action', # Need to be careful of other instances of this field
    'ruleReason'                 => 'fw_rule_reason',
    'impact_flag'                => 'impact_bits',
    'impact_flags'               => 'impact_bits',
    'priority_id'                => 'priority',
    'cloud_uuid'                 => 'cloud',
    'firewall_policy_uuid'       => 'fw_policy',
    'policyRevision'             => 'fw_policy',
    'interface_ingress_uuid'     => 'iface_ingress',
    'ingressIntf'                => 'iface_ingress',
    'interface_egress_uuid'      => 'iface_egress',
    'egressIntf'                 => 'iface_egress',
    'security_zone_ingress_uuid' => 'sec_zone_ingress',
    'ingressZone'                => 'sec_zone_ingress',
    'security_zone_egress_uuid'  => 'sec_zone_egress',
    'egressZone'                 => 'sec_zone_egress',
    'ip_src_country'             => 'src_ip_country',
    'initiator_country'          => 'src_ip_country',
    'ip_dst_country'             => 'dest_ip_country',
    'responder_country'          => 'dest_ip_country',
    'userId'                     => 'user',
    'user_id'                    => 'user', # Need to watch for Malware events, then rename to agent_user
    'src_uid'                    => 'src_user',
    'dest_uid'                   => 'dest_user',
    'vlanId'                     => 'vlan_id',
    'packet_data'                => 'packet',
    'uid'                        => 'source',
    'network_proto'              => 'net_proto',
    'net_protocol'               => 'net_proto',
    'country_code'               => 'id',
    'rule_name'                  => 'name',
    'detection_name'             => 'detection',
);


# Keep track of how many lines where written to the log
my $logfile_fh;
my $logfile_open = 0;
my $lines_written = 0;

# Child processes to keep track of
my @children;


###############################################################################
# Signal handler
###############################################################################

# Set signal handler to break event loop and drop to cleanup
my $SIG_RECEIVED = undef;
$SIG{TERM} = \&signalHandler;
$SIG{INT}  = \&signalHandler;
$SIG{HUP}  = \&signalHandler;
$SIG{PIPE} = 'IGNORE';

# Handle signals
sub signalHandler
{
    my $sig = shift;
    verbose("signalHandler [$$]: $sig received");
    $sig = defined $sig ? $sig : "UNKNOWN";
    $SIG_RECEIVED = $sig;

    foreach my $child (@children)
    {
        kill($sig, $child);
    }
}


###############################################################################
# Main
###############################################################################

# Get the OS name
my $os_name = $^O;

# TEMPORARY - If we're in Windows...
die("Windows is not currently supported with the eStreamer client at this time.\n") if $os_name =~ m/MSWin32/i;

# Grab command line options
my $cli_opt = processCommandLine();


# Let's fork (if desired)
if (defined $cli_opt->{daemon}) {
    verbose("Daemonizing process");
    daemonize();
}


verbose("Effective Config: ".Dumper($cli_opt));


# Save the process ID to the PID file
if (!$cli_opt->{test})
{
    my $pid_fh;
    open($pid_fh, '>', $PID_FILE)
        or die("Unable to open PID file ($PID_FILE) for writing\n");
    print($pid_fh $$);
    close($pid_fh);
}

# Prioritize the path for the sake of OpenSSL (Splunk openssl breaks on CentOS, and likely others)
local $ENV{PATH} = "/bin:/sbin:/usr/bin:/usr/sbin:$ENV{PATH}";


# Process the pkcs12
verbose("Setting up auth certificate");
my $pkcs12_opts;
$pkcs12_opts->{file}     = $cli_opt->{pkcs12_file}     if (defined $cli_opt->{pkcs12_file});
$pkcs12_opts->{password} = $cli_opt->{pkcs12_password} if (defined $cli_opt->{pkcs12_password});
$cli_opt->{verbose} ? ($pkcs12_opts->{verbose} = 1) : ($pkcs12_opts->{verbose} = 0);
my ($crtfile, $keyfile) = SFPkcs12::processPkcs12($pkcs12_opts);


# If we're just doing a test run
if ($cli_opt->{test})
{
    # Load the metadata href
    verbose("Retrieving metadata from file $METADATA_FILE");
    %metadata = loadMetadata($METADATA_FILE);

    # Connect to server
    verbose("Connecting to $cli_opt->{server} port $cli_opt->{port}");
    my $client = new IO::Socket::SSL( Domain        => $cli_opt->{domain},
                                      PeerAddr      => $cli_opt->{server},
                                      PeerPort      => $cli_opt->{port},
                                      Proto         => 'tcp',
                                      SSL_use_cert  => 1,
                                      SSL_cert_file => $crtfile,
                                      SSL_key_file  => $keyfile,
                                      SSL_verify_mode => 'SSL_VERIFY_NONE',
				      SSL_version => 'TLSv1')
        or die("Can't connect to $cli_opt->{server} port $cli_opt->{port}: ".IO::Socket::SSL::errstr()."\n\n");

    # Let's open the connection to the eStreamer server properly
    verbose("Opening event stream");
    SFStreamer::req_data($client, 1, $req_flags);

    # Attempt to get some data
    SFStreamer::get_wire_data($client, 1);

    # Close the connection
    verbose("Closing the connection and event stream");
    close($client);

    verbose("Saving metadata to file $METADATA_FILE");
    saveMetadata($METADATA_FILE, %metadata);

    # If we got here, nothing went wrong
    verbose("Testing complete, without errors.\n");

    # No more to do
    exit 0;
}

# Load the metadata href
verbose("Retrieving metadata from file $METADATA_FILE");
%metadata = loadMetadata($METADATA_FILE);

# Make sure we're good to go on the bookmarks, resuming from where we left off in a previous version of the app
verbose("Migrating prior version bookmark (if necessary)");
migrateBookmarks();


# Here is where we need to kick off each thread -- one for RNA and one for everything else

my $pid;
my $is_parent = 1;

# Are we logging flows?
if ($cli_opt->{log_flows} && $is_parent)
{
    # Let's start the RNA processor
    $pid = fork();

    # If this is the parent process
    if ($pid)
    {
        push(@children, $pid);
    }

    # This is the child
    elsif ($pid == 0)
    {
        # Mark us as a child
        $is_parent = 0;

        # Kick off the processing
        connectAndProcess('rna');
    }

    # Something went terribly wrong
    else
    {
        die("Unable to fork() for RNA processing\n");
    }
}

# Are we logging user activities?
if ($cli_opt->{log_users} && $is_parent)
{
    # Let's start the RUA processor
    $pid = fork();

    # If this is the parent process
    if ($pid)
    {
        push(@children, $pid);
    }

    # This is the child
    elsif ($pid == 0)
    {
        # Mark us as a child
        $is_parent = 0;
        
        # Kick off the processing
        connectAndProcess('rua');
    }

    # Something went terribly wrong
    else
    {
        die("Unable to fork() for RUA processing\n");
    }
}

# What we should do as the parent process
if ($is_parent)
{   
    # Kick off the processing
    connectAndProcess('other');

    # Add a short delay here
    sleep(10);

    # Clean up 
    SFPkcs12::cleanUp();

    # This is a HACK since I can't share %metadata with the threads
    my %meta_rna = loadMetadata('rna.dat');
    unlink('rna.dat');
    my %meta_rua = loadMetadata('rua.dat');
    unlink('rua.dat');
    my %meta_other = loadMetadata('other.dat');
    unlink('other.dat');

    my %meta_tmp = (%metadata, %meta_rna);   %metadata = %meta_tmp;
    %meta_tmp    = (%metadata, %meta_rua);   %metadata = %meta_tmp;
    %meta_tmp    = (%metadata, %meta_other); %metadata = %meta_tmp;

    verbose("Saving metadata to file");
    saveMetadata($METADATA_FILE, %metadata);

    # Remove the PID file
    unlink($PID_FILE);
}


# Nothing else should happen after this -- remaining code is in functions


###############################################################################
# Process "main" Function
###############################################################################

sub connectAndProcess
{
    my ($type) = @_;   # Valid: rna, rua, other
    my $bookmark_fh;
    my $last_timestamp;
    my $bmark_file;
    my $meta_file;
    my $client;
    my $splunk_running = 1;
    my $timeout_count = 0;

    verbose("Starting processing for $type");

    # Let's fix some things in prep for the connection

    # RNA type
    if ($type eq 'rna')
    {
        verbose("Building connection parameters for RNA");

        # Add the RNA flags
        $req_flags = $req_flags | $FLAG_RNA_EVENTS_7 | $FLAG_RNA;

        # Set the flags and version details appropriately for RNA
        $OUTPUT_PLUGIN->{flags}        = $req_flags;
        $OUTPUT_PLUGIN->{rna_flow_ver} = 9;

        # Set the bookmark filename
        $bmark_file = 'rna.bmark';
        $meta_file  = 'rna.dat';
    }

    # RUA type
    elsif ($type eq 'rua')
    {
        verbose("Building connection parameters for RUA");

        # Add the RUA flags
        $req_flags = $req_flags | $FLAG_RUA;

        # Set the flags and version details appropriately for RUA
        $OUTPUT_PLUGIN->{flags}   = $req_flags;
        $OUTPUT_PLUGIN->{rua_ver} = 4;

        # Set the bookmark filename
        $bmark_file = 'rua.bmark';
        $meta_file  = 'rua.dat';
    }

    # Anything else
    else
    {
        verbose("Building connection parameters for all other events");

        # Add all the other flags
        $req_flags = $req_flags | $FLAG_IDS | $FLAG_IMPACT_ALERTS | $FLAG_IDS_IMPACT_FLAG | $FLAG_POLICY_EVENTS_6;

        # If we also want extra data, add that flag
        if ($cli_opt->{log_extra_data})
        {
            $req_flags = $req_flags | $FLAG_EXTRA_DATA;
        }

        # If we also want packets, add that flag
        if ($cli_opt->{log_packets})
        {
            $req_flags = $req_flags | $FLAG_PKTS;
        }

        # Set the flags and version details appropriately for "other"
        $OUTPUT_PLUGIN->{flags}              = $req_flags;
        $OUTPUT_PLUGIN->{ids_events_ver}     = 6;
        $OUTPUT_PLUGIN->{policy_events_ver}  = 8;
        $OUTPUT_PLUGIN->{fireamp_events_ver} = 4;
        $OUTPUT_PLUGIN->{filelog_events_ver} = 3;
        $OUTPUT_PLUGIN->{impact_flag_ver}    = 2;

        # Set the bookmark filename
        $bmark_file = 'other.bmark';
        $meta_file  = 'other.dat';
    }


    # Connect to server
    verbose("Connecting to $cli_opt->{server} port $cli_opt->{port}");
    $client = new IO::Socket::SSL( Domain        => $cli_opt->{domain},
                                   PeerAddr      => $cli_opt->{server},
                                   PeerPort      => $cli_opt->{port},
                                   Proto         => 'tcp',
                                   SSL_use_cert  => 1,
                                   SSL_cert_file => $crtfile,
                                   SSL_key_file  => $keyfile,
                                   SSL_verify_mode => 'SSL_VERIFY_NONE',
                                   SSL_version => 'TLSv1')
        or die("Can't connect to $cli_opt->{server} port $cli_opt->{port}: ".IO::Socket::SSL::errstr()."\n\n");

    # Open the bookmark file and grab the last bookmark
    ($bookmark_fh, $last_timestamp) = openBookmark($bmark_file);
    verbose("Starting bookmark is $last_timestamp");

    # Open the log file
    openReopenLog();

    # Request the data
    verbose("Requesting Event Stream");
    SFStreamer::req_data($client, $last_timestamp, $req_flags);


    # Main event loop
    verbose("Entering Event Loop");
    if ($cli_opt->{watch}) {
        $splunk_running = isSplunkRunning();
    }
    eval {
        while (!defined($SIG_RECEIVED) && $splunk_running)
        {
            my $record;
            my @rec_list;

            # Add a 30 second timeout for feed collection
            eval {
                local $SIG{ALRM} = sub { die "timeout\n" };
                alarm 30;

                # Pull a record or records off the wire and de-serialize it
                @rec_list = SFStreamer::get_feed($client);

                alarm 0;
            };

            # If we're good to go
            if ($@ eq '')
            {
                # Handle data records
                foreach $record (@rec_list){
                    if($record->{'header'}{'msg_type'} == $SFStreamer::TYPE_DATA){
                        # Grab the bookamrk
                        if (exists($record->{header}{archive_timestamp}))
                        {
                            $last_timestamp = $record->{header}{archive_timestamp}
                                unless $record->{header}{archive_timestamp} < $last_timestamp;
                        }
            
                        # send record to output plugin
                        outputRecord($record);

                        # Update the Bookmark to the just processed record.
                        updateBookmark($bookmark_fh, $last_timestamp) if $last_timestamp;
                    }
                }

                # Reset the timeout count
                $timeout_count = 0;
            }

            # We timed out waiting for more logs
            elsif ($@ eq "timeout\n")
            {
                verbose("Waiting for more logs");

                # Increment the timeout count
                $timeout_count++;
            }

            # If we received a die() for any other reason...
            else
            {
                # Something went wrong, so let's die as intended
                die($@);
            }

            # Refresh tracking var
            if ($cli_opt->{watch})
            {
                $splunk_running = isSplunkRunning();
            }
        }
    };

    if ($@) {
        warn $@;
    };

    # Clean Up
    verbose("Received Signal: $SIG_RECEIVED") if $SIG_RECEIVED;
    verbose("Splunk not running")             if !$splunk_running;
    verbose("Cleaning Up");
    close $client;
    close $bookmark_fh;
    close $logfile_fh;

    # Save the metadata fro this thread
    saveMetadata($meta_file, %metadata);

    verbose("Done with processing for $type");

    # Return 0
    return 0;
}


###############################################################################
# Functions
###############################################################################

#  Open or re-open the log file
sub openReopenLog
{
    # If we're logging to a file...
    if ($cli_opt->{logfile})
    {
        # If we're already open, close the handle
        if ($logfile_open)
        {
            close $logfile_fh;
        }

        # Generate a filename to include a timestamp
        my $ts = time();
        my $logfile_name = $cli_opt->{logfile}.'.'.$ts;

        # While the filename exists
        while (-e $logfile_name)
        {
            # increment the timestamp by 1
            $ts++;

            # Update the filename
            $logfile_name = $cli_opt->{logfile}.'.'.$ts;
        }

        # Open the filehandle
        open($logfile_fh, '>', $logfile_name) or
            die "Unable to open $cli_opt->{logfile} for writing";
    }

    # If we're going to the console...
    else
    {
        # If not already open, use STDOUT
        if (!$logfile_open)
        {
            $logfile_fh = \*STDOUT;
        }
    }

    # Show file as open, and reset written count
    $logfile_open = 1;
    $lines_written = 0;
}

# If an old bookmark file exists, and new ones don't, let's update them appropriately to resume
sub migrateBookmarks
{
    my $file_handle;
    my $time_stamp = 0;

    # Let's check for the old bookmark
    if (-e 'estreamer.bmark')
    {
        # We have an old bookmark, so let's get the old bookmark value
        open($file_handle, '<', 'estreamer.bmark')
            or die "Unable to open bookmark file (estreamer.bmark) for reading\n";
        $time_stamp = int(<$file_handle>) || time;
        close $file_handle;
    }

    # Update the rna.bmark if it does not exist
    unless (-e 'rna.bmark')
    {
        open($file_handle, '>', 'rna.bmark')
            or die "Unable to open bookmark file: rna.bmark\n";
        seek($file_handle, 0, 0);
        print($file_handle $time_stamp, "\n");
        close($file_handle);
    }

    # Update the rua.bmark if it does not exist
    unless (-e 'rua.bmark')
    {
        open($file_handle, '>', 'rua.bmark')
            or die "Unable to open bookmark file: rua.bmark\n";
        seek($file_handle, 0, 0);
        print($file_handle $time_stamp, "\n");
        close($file_handle);
    }

    # Update the other.bmark if it does not exist
    unless (-e 'other.bmark')
    {
        open($file_handle, '>', 'other.bmark')
            or die "Unable to open bookmark file: other.bmark\n";
        seek($file_handle, 0, 0);
        print($file_handle $time_stamp, "\n");
        close($file_handle);
    }

    # It should be safe to delete the old bookmark file
    unlink('estreamer.bmark');
}

# Open the bookmark file
sub openBookmark
{
    my ($filename) = @_;
    my $file_handle;
    my $rval;

    # If we're grabbing everything
    if ($cli_opt->{start} eq 'all')
    {
        # Start from 0
        $rval->{bmark} = 0;
    }

    # If we're starting from now
    elsif ($cli_opt->{start} eq 'now')
    {
        # Grab the current timestsamp
        $rval->{bmark} = time();
    }

    # Anything else
    else
    {
        # Grab the current timestamp
        $rval->{bmark} = time();

        if (-e $filename)
        {
            open($file_handle, '<', $filename)
                or die "Unable to open bookmark file ($filename) for reading\n";
            $rval->{bmark} = int(<$file_handle>) || time;
            close $file_handle;
        }
    }
    open($file_handle, '>', $filename)
        or die "Unable to open bookmark file: $filename\n";
    $rval->{handle} = $file_handle;
    updateBookmark($rval->{handle}, $rval->{bmark});

    return ($rval->{handle}, $rval->{bmark}) if wantarray;
    return $rval;
}

# Write a new time stamp to the bookmark file
sub updateBookmark
{
    my ($file_handle, $time_stamp) = @_;
    seek($file_handle, 0, 0)
        or die "Fatal: Unable to reset bookmark file position\n";
    print($file_handle $time_stamp, "\n");
    truncate($file_handle, tell($file_handle))
        or die "Unable to truncate bookmark file\n";
}

# Load the metadata href from a file to aid resolution later
sub loadMetadata
{
    my ($file) = @_;
    my %meta;

    # We'll load the data only if the file exists
    if (-e $file)
    {
        # We need to catch errors
        eval
        {
            # Load the metadata href from the metadata file
            %meta = %{lock_retrieve($file)};
        } or do {
            # Warn and cleanup to keep on keepin' on
            warn("Error loading metadata from file ($file): $@");

            # Remove the corrupt file -- we'll just start over
            unlink($file);
        };
    }

    return %meta;
}

# Save the metadata href to a file to prevent resolution trouble later
sub saveMetadata
{
    my ($file, %meta) = @_;

    # Save the metadata href to the metadata file
    lock_store \%meta, $file;
}

# Print if verbose flag is set
sub verbose {
    my ($msg) = @_;
    return unless $cli_opt->{verbose};
    my $datetime = strftime('%b %d %H:%M:%S', localtime);;
    warn("$datetime [$$] $msg\n");
}

# Process the config file
sub processConfig
{
    my ($config_file) = @_;
    my $config_fh;
    my $opts;

    # Open the config, or die
    open($config_fh, '<', $config_file)
        or die "Unable to open config file ($config_file) for reading\n";
    
    # Work through the config one line at a time
    while (my $line = <$config_fh>)
    {
        # If the line isn't a comment
        if ($line =~ m/^([^#]+?)\s*=\s*(.*?)\s*$/)
        {
            # Save the key and value
            my $key = $1;
            my $value = $2;

            # Save to the href
            $opts->{$key} = $value;
        }
    }

    # Close the file and return the href
    close($config_fh);
    return $opts;
}

# Process the command line
sub processCommandLine {
    my $opts;
    my $config_opts;

    # Set the default options
    $opts->{port} = undef;
    $opts->{pkcs12_file} = undef;
    $opts->{pkcs12_password} = undef;
    $opts->{verbose} = 0;
    $opts->{start} = 'bookmark';
    $opts->{logfile} = undef;
    $opts->{config} = undef;
    $opts->{ipv6} = undef;
    $opts->{log_extra_data} = undef;
    $opts->{log_packets} = undef;
    $opts->{log_flows} = undef;
    $opts->{log_users} = undef;
    $opts->{log_metadata} = undef;
    $opts->{watch} = undef;
    $opts->{daemon} = undef;

    # Get the options from the command-line
    GetOptions ( "host=s"     => \$opts->{server},
                 "port=i"     => \$opts->{port},
                 "pkcs12=s"   => \$opts->{pkcs12_file},
                 "password=s" => \$opts->{pkcs12_password},
                 "verbose"    => \$opts->{verbose},
                 "ipv6"       => \$opts->{ipv6},
                 "start=s"    => \$opts->{start},
                 "logfile=s"  => \$opts->{logfile},
                 "config=s"   => \$opts->{config},
                 "watch"      => \$opts->{watch},
                 "daemon"     => \$opts->{daemon},
                 "test"       => \$opts->{test} );

    # If the config is defined, we'll get all our settings from there
    if ($opts->{config})
    {
        # Read the config options
        $config_opts = processConfig($opts->{config});

        # Take just the important ones (command line overrides config)
        $opts->{server} = $config_opts->{server} unless defined($opts->{server});
        $opts->{port} = $config_opts->{port} unless defined($opts->{port});
        $opts->{ipv6} = $config_opts->{ipv6} unless defined($opts->{ipv6});
        $opts->{port} = $config_opts->{port} unless defined($opts->{port});
        $opts->{pkcs12_file} = $config_opts->{pkcs12_file} unless defined($opts->{pkcs12_file});
        $opts->{pkcs12_password} = $config_opts->{pkcs12_password} unless defined($opts->{pkcs12_password});
        $opts->{log_extra_data} = $config_opts->{log_extra_data} unless defined($opts->{log_extra_data});
        $opts->{log_packets} = $config_opts->{log_packets} unless defined($opts->{log_packets});
        $opts->{log_flows} = $config_opts->{log_flows} unless defined($opts->{log_flows});
        $opts->{log_users} = $config_opts->{log_users} unless defined($opts->{log_users});
        $opts->{log_metadata} = $config_opts->{log_metadata} unless defined($opts->{log_metadata});
        $opts->{watch} = $config_opts->{watch} unless defined($opts->{watch});
        $opts->{verbose} = $config_opts->{debug} unless defined($opts->{debug});
    }

    # Set default values if still undefined
    $opts->{port} = $DEFAULT_PORT if !defined($opts->{port});
    $opts->{log_extra_data} = $DEFAULT_EXTRA_DATA if !defined($opts->{log_extra_data});
    $opts->{log_packets} = $DEFAULT_PACKETS if !defined($opts->{log_packets});
    $opts->{log_flows} = $DEFAULT_FLOWS if !defined($opts->{log_flows});
    $opts->{log_users} = $DEFAULT_USERS if !defined($opts->{log_users});
    $opts->{log_metadata} = $DEFAULT_METADATA if !defined($opts->{log_metadata});
    $opts->{watch} = $DEFAULT_WATCH if !defined($opts->{watch});

    $opts->{start} = 'bookmark' if ($opts->{start} !~ /^(now|all)$/);

    # Toggle IPv6/IPv4 Connectivity
    if (defined($opts->{ipv6}) && $opts->{ipv6} eq '1')
    {
        die "Required IPv6 perl Modules (Socket6 & IO::Socket::INET6) failed to load\n"
            unless $IP6_THERE;
        $opts->{domain} = AF_INET6;
    }
    else
    {
        $opts->{domain} = AF_INET;
    }

    # Show usage if no server set
    usage() unless (defined $opts->{server});

    # Return the options
    return $opts;
}

# If we get here...stuff is wrong...print usage and exit non-zero.
sub usage
{
    my $script = $0;

    # Strip off the path
    if ($script =~ /[\/\\]([^\/\\]+)$/)
    {
        $script = $1;
    }

    # There are more options, but I'm not going to bother exposing them here
    warn("Usage:  $script [options]\n");
    warn("Options:\n");
    warn("\t[-c]onfig=<config filename>\n");
    warn("\t[-l]ogfile=<log filename>\n");
    warn("\t[-t]est\n");
    warn("\t[-d]aemon\n\n");

    # Exit with non-zero
    exit (1);
}

# Start doing stuff with records
sub outputRecord {
    my ($rec) = @_;
    my @fields;
    my $rec_type_num = $rec->{'rec_type'};
    my $rec_type = $SFStreamer::RECORD_TYPES->{$rec_type_num};
    my $do_output = 1;
    my $is_rna = 0;

    # 5.2 Event
    if ($rec_type eq 'IPS EVENT') {
        if (exists $metadata{'ids_rules'}{$rec->{'generator_id'}.':'.$rec->{'signature_id'}}) {
            $rec->{'msg'} = $metadata{'ids_rules'}{$rec->{'generator_id'}.':'.$rec->{'signature_id'}};
        }
    }

    # Pre-5.2 Event
    elsif ($rec_type eq 'EVENT') {
        if (exists $metadata{'ids_rules'}{$rec->{'gen'}.':'.$rec->{'sid'}}) {
            $rec->{'msg'} = $metadata{'ids_rules'}{$rec->{'gen'}.':'.$rec->{'sid'}};
        }
    }

    # Policy event
    elsif ($rec_type eq 'POLICY' && $rec_type_num != $SFStreamer::COMPLIANCE_POLICY) {
        $rec->{'description'} = '';

        # Let's "fix" the IP fields for consistency
        if (exists($rec->{'src_ip6_addr'}) && $rec->{'src_ip_addr'} eq '0.0.0.0' && $rec->{'src_ip6_addr'} ne '::') {
            $rec->{'src_ip_addr'} = $rec->{'src_ip6_addr'};
        }
        if (exists($rec->{'dest_ip6_addr'}) && $rec->{'dest_ip_addr'} eq '0.0.0.0' && $rec->{'dest_ip6_addr'} ne '::') {
            $rec->{'dest_ip_addr'} = $rec->{'dest_ip6_addr'};
        }
        if (exists $metadata{'ids_rules'}{$rec->{'sig_gen'}.':'.$rec->{'sig_id'}}) {
            $rec->{'msg'} = $metadata{'ids_rules'}{$rec->{'sig_gen'}.':'.$rec->{'sig_id'}};
        }
    }

    # Packet "event"
    elsif ($rec_type eq 'PACKET') {
        # Generate packet header from data
        my $packet_header = pack('L', $rec->{'packet_sec'});  # tv_sec
        $packet_header   .= pack('L', $rec->{'packet_usec'}); # tv_usec
        $packet_header   .= pack('L', $rec->{'packet_len'});  # caplen
        $packet_header   .= pack('L', $rec->{'packet_len'});  # pktlen

        # Make a packet from the bits we have, and hex encode it
        $rec->{'packet_data'} = unpack("H*", $packet_header.$rec->{'packet_data'});
    }

    # FILELOG Event
    elsif ($rec_type eq 'FILELOG EVENT' || $rec_type eq 'FILELOG MALWARE EVENT') {
        if (exists $metadata{'file_actions'}{$rec->{'action'}}) {
            $rec->{'action'} = $metadata{'file_actions'}{$rec->{'action'}};
        }
    }

    # Malware Event
    elsif ($rec_type eq 'MALWARE EVENT') {
        # Resolve the hashes
        $rec->{'detection_name'}    = $rec->{'detection_name'}{'data'};
        $rec->{'user'}              = $rec->{'user'}{'data'};
        $rec->{'file_path'}         = $rec->{'file_path'}{'data'};
        $rec->{'file_sha'}          = $rec->{'file_sha'}{'data'};
        $rec->{'parent_fname'}      = $rec->{'parent_fname'}{'data'};
        $rec->{'parent_sha'}        = $rec->{'parent_sha'}{'data'};
        $rec->{'event_description'} = $rec->{'event_description'}{'data'};

        # Clean up prior to lookups
        $rec->{'detection_name'} =~ s/\0//g;
        $rec->{'file_sha'} =~ s/\0//g;

        if (exists $metadata{'file_actions'}{$rec->{'action'}}) {
            $rec->{'action'} = $metadata{'file_actions'}{$rec->{'action'}};
        }

        if (exists $metadata{'file_shas'}{$rec->{'file_sha'}} && $rec->{'detection_name'} eq '') {
            $rec->{'detection_name'} = $metadata{'file_shas'}{$rec->{'file_sha'}};
        }
    }

    # RNA Event
    elsif ($rec_type eq 'RNA') {

        $is_rna = 1 if SFStreamer::is_rna_rec_type($rec);

        # Right now we're only doing flow RNA records
        # if ($cli_opt->{log_flows} eq '1')
        if ($cli_opt->{log_flows} eq '1' && $rec->{'event_type'} eq '1003')
        {
            $do_output = 1;
        }

        # Anything else we're ignoring for now
        else {
            $do_output = 0;
        }
    }


    # With this version, we're not handling most of the RUA events (yet).
    # This will be something for the future version
    elsif ($rec_type eq 'RUA') {
        $do_output = 0;
    }


    # Everything else will be metadata handling

    elsif ($rec_type eq 'SENSOR') {
        $metadata{'devices'}{$rec->{'id'}} = $rec->{'name_string_data'};
    }
    elsif ($rec_type eq 'ZONE') {
        $rec->{'name_string'} = $rec->{'name_string'}{'data'};
        $metadata{'security_zones'}{$rec->{'uuid'}} = $rec->{'name_string'};
    }
    elsif ($rec_type eq 'INTERFACE') {
        $rec->{'name_string'} = $rec->{'name_string'}{'data'};
        $metadata{'interfaces'}{$rec->{'uuid'}} = $rec->{'name_string'};
    }
    elsif ($rec_type eq 'RULE') {
        if ($rec_type_num == $SFStreamer::COMPLIANCE_RULE) {
            $metadata{'corr_rules'}{$rec->{'id'}}{'name'} = $rec->{'name_string_data'};
            $metadata{'corr_rules'}{$rec->{'id'}}{'desc'} = $rec->{'desc_string_data'};
            $metadata{'corr_rules'}{$rec->{'id'}}{'type'} = $rec->{'event_type_data'};
        }
        else {
            $metadata{'ids_rules'}{$rec->{'generator_id'}.':'.$rec->{'rule_id'}} = $rec->{'msg'};
        }
    }
    elsif ($rec_type eq 'CLASSIFICATION') {
        $metadata{'classifications'}{$rec->{'id'}}{'name'} = $rec->{'name'};
        $metadata{'classifications'}{$rec->{'id'}}{'desc'} = $rec->{'desc'};
    }
    elsif ($rec_type eq 'PRIORITY') {
        $metadata{'priorities'}{$rec->{'priority_id'}} = $rec->{'name'};
    }
    elsif ($rec_type eq 'SERVICE') {
        $metadata{'app_protos'}{$rec->{'id'}} = $rec->{'name_string_data'};
    }
    elsif ($rec_type eq 'CLIENT APP') {
        $metadata{'client_apps'}{$rec->{'id'}} = $rec->{'name_string_data'};
    }
    elsif ($rec_type eq 'SOURCE APP') {
        $metadata{'source_apps'}{$rec->{'id'}} = $rec->{'name_string_data'};
    }
    elsif ($rec_type eq 'PAYLOAD') {
        $metadata{'payloads'}{$rec->{'id'}} = $rec->{'name_string_data'};
    }
    elsif ($rec_type eq 'NET PROTO') {
        $metadata{'net_protos'}{$rec->{'id'}} = $rec->{'name_string_data'};
    }
    elsif ($rec_type eq 'GEOLOCATION') {
        $rec->{'name_string'} = $rec->{'name_string'}{'data'};
        $metadata{'geolocations'}{$rec->{'country_code'}} = $rec->{'name_string'};
    }
    elsif ($rec_type eq 'FILELOG FILE TYPE') {
        $metadata{'file_types'}{$rec->{'id'}} = $rec->{'name_string_data'};
    }
    elsif ($rec_type eq 'ICMP TYPE') {
        $rec->{'description'} = $rec->{'description'}{'data'};
        $metadata{'icmp_types'}{$rec->{'protocol'}.':'.$rec->{'type'}} = $rec->{'description'};
    }
    elsif ($rec_type eq 'ICMP CODE') {
        $rec->{'description'} = $rec->{'description'}{'data'};
        $metadata{'icmp_codes'}{$rec->{'code'}} = $rec->{'description'};
    }
    elsif ($rec_type eq 'INTRUSION POLICY') {
        $rec->{'name_string'} = $rec->{'name_string'}{'data'};
        $metadata{'policies'}{$rec->{'uuid'}} = $rec->{'name_string'};
    }
    elsif ($rec_type eq 'FIREWALL POLICY') {
        $rec->{'name_string'} = $rec->{'name_string'}{'data'};
        $metadata{'policies'}{$rec->{'uuid'}} = $rec->{'name_string'};
        # Add the default action rule
        $metadata{'fw_rules'}{$rec->{'uuid'}}{'0'} = 'Default Action';
    }
    elsif ($rec_type eq 'FIREWALL RULE') {
        $rec->{'rule_name'} = $rec->{'rule_name'}{'data'};
        $metadata{'fw_rules'}{$rec->{'revision'}}{$rec->{'rule_id'}} = $rec->{'rule_name'};
    }
    elsif ($rec_type eq 'FIREWALL RULE ACTION') {
        $metadata{'fw_rule_actions'}{$rec->{'id'}} = $rec->{'name_string_data'};
    }
    elsif ($rec_type eq 'FIREWALL RULE REASON') {
        $rec->{'description'} = $rec->{'description'}{'data'};
        $metadata{'fw_rule_reasons'}{$rec->{'reason'}} = $rec->{'description'};
    }
    elsif ($rec_type eq 'FILELOG SHA') {
        $rec->{'name_string'} = $rec->{'name_string'}{'data'};
        $metadata{'file_shas'}{$rec->{'sha'}} = $rec->{'name_string'};
    }

    elsif ($rec_type eq 'FINGERPRINT') {
        $metadata{'os_fingerprints'}{$rec->{'fpuuid'}}{'os'} = $rec->{'os_name_data'};
        $metadata{'os_fingerprints'}{$rec->{'fpuuid'}}{'vendor'} = $rec->{'os_vendor_data'};
        $metadata{'os_fingerprints'}{$rec->{'fpuuid'}}{'ver'} = $rec->{'os_version_data'};
    }
    elsif ($rec_type eq 'RUA USER') {
        $metadata{'users'}{$rec->{'id'}} = $rec->{'name_string_data'};
    }
    elsif ($rec_type eq 'SYSTEM USER') {
        $metadata{'system_users'}{$rec->{'id'}} = $rec->{'name_string_data'};
    }
    elsif ($rec_type eq 'ATTRIBUTE') {
        $metadata{'attribs'}{$rec->{'id'}} = $rec->{'name_string_data'};
    }
    elsif ($rec_type eq 'FIREWALL URL REPUTATION') {
        $metadata{'url_reputations'}{$rec->{'id'}} = $rec->{'name_string_data'};
    }
    elsif ($rec_type eq 'FIREWALL URL CATEGORY') {
        $metadata{'url_categories'}{$rec->{'id'}} = $rec->{'name_string_data'};
    }
    elsif ($rec_type eq 'SOURCE DETECTOR') {
        $metadata{'source_detectors'}{$rec->{'id'}} = $rec->{'name_string_data'};
    }
    elsif ($rec_type eq 'SOURCE TYPE') {
        $metadata{'source_types'}{$rec->{'id'}} = $rec->{'name_string_data'};
    }
    elsif ($rec_type eq 'MALWARE EVENT TYPE') {
        $metadata{'malware_event_types'}{$rec->{'id'}} = $rec->{'name_string_data'};
    }
    elsif ($rec_type eq 'MALWARE FILE TYPE') {
        $metadata{'file_types'}{$rec->{'id'}} = $rec->{'name_string_data'};
    }
    elsif ($rec_type eq 'FIREAMP CLOUD') {
        $rec->{'name_string'} = $rec->{'name_string'}{'data'};
        $metadata{'clouds'}{$rec->{'uuid'}} = $rec->{'name_string'};
    }
    elsif ($rec_type eq 'EXTRA DATA TYPE') {
        $rec->{'extra_data_type_name'} = $rec->{'extra_data_type_name'}{'data'};
        $rec->{'encoding'} = $rec->{'encoding'}{'data'};
        $metadata{'xdata_types'}{$rec->{'type'}} = $rec->{'extra_data_type_name'};
    }
    elsif ($rec_type eq 'EXTRA DATA') {
        $rec->{'data'} = $rec->{'data'}{'data'};
        $rec->{'type'} = $metadata{'xdata_types'}{$rec->{'type'}} if exists($metadata{'xdata_types'}{$rec->{'type'}});
    }
    elsif ($rec_type eq 'MALWARE EVENT SUBTYPE') {
        $metadata{'fireamp_subtypes'}{$rec->{'id'}} = $rec->{'name_string_data'};
    }
    elsif ($rec_type eq 'MALWARE DETECTOR TYPE') {
        $metadata{'fireamp_detectors'}{$rec->{'id'}} = $rec->{'name_string_data'};
    }
    elsif ($rec_type eq 'IMPACT') {
        my $imp = $rec->{'description'}{'data'};
        if ($imp =~ m/\[Impact:\s(.+?)\]/) {
            $rec->{'description'} = $1;
        } else {
            $imp =~ s/\"/\'/g;
            $rec->{'description'} = $imp;
        }
        $rec->{'impact'} = getImpactFromBits($rec->{'impact'});
    }
    elsif ($rec_type eq 'FILE POLICY') {
        $rec->{'name_string'} = $rec->{'name_string'}{'data'};
        $metadata{'policies'}{$rec->{'uuid'}} = $rec->{'name_string'};
    }
    elsif ($rec_type eq 'SECURITY INTELLIGENCE SOURCE/DEST') {
        $metadata{'si_src_dests'}{$rec->{'id'}} = $rec->{'name_string_data'};
        # We're not actually going to listen to this, since it appears broken in 5.3 LA
    }
    # Policy definition
    elsif ($rec_type eq 'POLICY' && $rec_type_num == $SFStreamer::COMPLIANCE_POLICY) {
        $metadata{'policies'}{$rec->{'id'}} = $rec->{'name'};
    }

    # Anything else...
    else
    {
        # Let's go ahead and output it
        $do_output = 1;

        # ... but mark is as unhandled
        $rec->{'unhandled'} = 1;
    }

    # If we're outputting the record, then...
    if ($do_output) {

        # Add fields
        @fields = pushField(\@fields, 'rec_type', $rec_type_num);
        @fields = pushField(\@fields, 'rec_type_simple', $rec_type);

        # If the event has a timestamp, let's place that next (we'll ignore it as we go through the fields later)
        my $event_sec = 0;
        my $event_usec = 0;

        # See if we can find the timestamps
        if (exists $rec->{'event_second'}) {
            $event_sec = $rec->{'event_second'};
            $event_usec = $rec->{'event_microsecond'} if exists $rec->{'event_microsecond'};
        }
        elsif (exists $rec->{'event_sec'}) {
            $event_sec = $rec->{'event_sec'};      
        }
        elsif (exists $rec->{'file_event_timestamp'}) {
            $event_sec = $rec->{'file_event_timestamp'};
        }
        elsif (exists $rec->{'policy_tv_sec'}) {
            $event_sec = $rec->{'policy_tv_sec'};
        }
        elsif (exists $rec->{'timestamp'}) {
            $event_sec = $rec->{'timestamp'};
        }
        elsif (exists $rec->{'time'}) {
            $event_sec = $rec->{'time'};
        }

        # If not timestamp exists, let's try the archive timestamp
        if ($event_sec == 0) {
            $event_sec = $rec->{'header'}{'archive_timestamp'};
        }

        # Push the timestamp fields in where applicable
        if ($event_sec > 0) {
            @fields = pushField(\@fields, 'event_sec', $event_sec);
        }
        elsif ($event_sec == 0) {
            # If there is no timestamp, let the user determine if the log gets output
            $do_output = $cli_opt->{'log_metadata'};
        }
        if ($event_usec > 0) {
            @fields = pushField(\@fields, 'event_usec', $event_usec);
        }

        # We'll continue only if we're going to output the record
        if ($do_output) {

            # If this is an RNA record
            if ($is_rna)
            {
                # Get the RNA record and replace our 
                my $rna_rec = SFStreamer::parse_rna_record($rec);

                # Empty the order array
                @{$rec->{'order'}} = ();
                push(@{$rec->{'order'}}, 'sensor_id');
                push(@{$rec->{'order'}}, 'event_type');
                push(@{$rec->{'order'}}, 'event_subtype');

                # Copy the field order across, with some exceptions
                for my $rna_item (@{$rna_rec->{'order'}})
                {
                    if ($rna_item ne 'sensorId')
                    {
                        if ($rna_item eq 'url' || $rna_item eq 'netbiosDomain' || $rna_item eq 'clientVersion')
                        {
                            push(@{$rec->{'order'}}, $rna_item);
                            $rec->{$rna_item} = $rna_rec->{$rna_item}->{'data'};
                        }
                        else
                        {
                            push(@{$rec->{'order'}}, $rna_item);
                            $rec->{$rna_item} = $rna_rec->{$rna_item};
                        }
                    }
                }
            }

            # For each field, map it across, adding quotes where appropriate (for whitespace)
            foreach my $key (@{$rec->{'order'}}) {

                # Set the default values
                my $key_name = $key;
                my $value = $rec->{$key};
                $value =~ s/\0//g;

                # Let's do some auto-translation of the field names
                $key_name = $field_translations{$key_name} if exists($field_translations{$key_name});

                # Time to do some data extraction
                if ($key_name eq 'sensor' || $key_name eq 'policy_sensor') {
                    $value = $metadata{'devices'}{$value} if exists($metadata{'devices'}{$value});
                }
                #elsif ($key_name eq 'detection') {
                #    if ($rec_type eq 'MALWARE EVENT') {
                #        @fields = pushField(\@fields, 'detection_old', $value);
                #        if (exists $metadata{'file_shas'}{$rec->{'file_sha'}}) {
                #            $value = $metadata{'file_shas'}{$rec->{'file_sha'}};
                #        }
                #    }
                #}
                elsif ($key_name eq 'sha256') {
                    if ($rec_type eq 'FILELOG MALWARE EVENT') {
                        if (exists $metadata{'file_shas'}{$value} && $rec_type ne 'FILELOG SHA') {
                            @fields = pushField(\@fields, 'detection', $metadata{'file_shas'}{$value});
                        }
                    }
                }
                elsif ($key_name eq 'revision' && $rec_type eq 'FIREWALL RULE') {
                    $key_name = 'fw_policy';
                    $value = $metadata{'policies'}{$value} if exists $metadata{'policies'}{$value};
                }
                elsif ($key_name eq 'parent_sha256') {
                    @fields = pushField(\@fields, 'parent_detection', $metadata{'file_shas'}{$value}) if exists($metadata{'file_shas'}{$value});
                }
                elsif ($key_name eq 'corr_policy') {
                    $value = $metadata{'policies'}{$value} if exists $metadata{'policies'}{$value};
                }
                elsif ($key_name eq 'event_type' && $rec_type eq 'POLICY') {
                    $value = $metadata{'corr_event_types'}{$value} if exists $metadata{'corr_event_types'}{$value};
                }
                elsif ($key_name eq 'src_criticality' || $key_name eq 'dest_criticality') {
                    $value = $metadata{'corr_criticalities'}{$value} if exists $metadata{'corr_criticalities'}{$value};
                }
                elsif ($key_name eq 'src_host_type' || $key_name eq 'dest_host_type') {
                    $value = $metadata{'corr_host_types'}{$value} if exists $metadata{'corr_host_types'}{$value};
                }
                elsif ($key_name eq 'source_type') {
                    $value = $metadata{'source_types'}{$value} if exists $metadata{'source_types'}{$value};
                }
                elsif ($key_name eq 'source_type') {
                    $value = $metadata{'source_types'}{$value} if exists $metadata{'source_types'}{$value};
                }
                elsif ($key_name eq 'source') {
                    $value = $metadata{'source_apps'}{$value} if exists $metadata{'source_apps'}{$value};
                }
                elsif ($key_name eq 'sid') {
                    if ($rec_type ne 'RULE' && exists $rec->{'msg'}) {
                        @fields = pushField(\@fields, 'msg', $rec->{'msg'});
                    }
                }
                elsif ($key_name eq 'class') {
                    if (exists $metadata{'classifications'}{$value}) {
                        @fields = pushField(\@fields, 'class_desc', $metadata{'classifications'}{$value}{'desc'});
                        $value = $metadata{'classifications'}{$value}{'name'};
                    }
                }
                elsif ($key_name eq 'type') {
                    $value = $metadata{'fireamp_types'}{$value} if exists $metadata{'fireamp_types'}{$value};
                }
                elsif ($key_name eq 'subtype') {
                    $value = $metadata{'fireamp_subtypes'}{$value} if exists $metadata{'fireamp_subtypes'}{$value};
                }
                elsif ($key_name eq 'detector') {
                    if ($rec_type eq 'MALWARE EVENT') {
                        $value = $metadata{'fireamp_detectors'}{$value} if exists $metadata{'fireamp_detectors'}{$value};
                    }
                    else {
                        $value = $metadata{'source_detectors'}{$value} if exists $metadata{'source_detectors'}{$value};
                    }
                }
                elsif ($key_name eq 'priority' && $rec_type ne 'PRIORITY') {
                    $value = $metadata{'priorities'}{$value} if exists $metadata{'priorities'}{$value};
                }
                elsif ($key_name eq 'blocked') {
                    $value = $metadata{'blocked'}{$value} if exists $metadata{'blocked'}{$value};
                }
                elsif ($key_name eq 'ip_proto') {
                    $value = $metadata{'ip_protos'}{$value} if exists $metadata{'ip_protos'}{$value};
                }
                elsif ($key_name eq 'disposition' || $key_name eq 'retro_disposition' || $key_name eq 'spero_disposition') {
                    $value = $metadata{'file_dispositions'}{$value} if exists $metadata{'file_dispositions'}{$value};
                }
                elsif ($key_name eq 'file_storage_status') {
                    $value = $metadata{'file_storages'}{$value} if exists $metadata{'file_storages'}{$value};
                }
                elsif ($key_name eq 'file_sandbox_status') {
                    $value = $metadata{'file_sandboxes'}{$value} if exists $metadata{'file_sandboxes'}{$value};
                }
                elsif ($key_name eq 'file_type') {
                    $value = $metadata{'file_types'}{$value} if exists $metadata{'file_types'}{$value};
                }
                elsif ($key_name eq 'net_proto') {
                    $value = $metadata{'net_protos'}{$value} if exists $metadata{'net_protos'}{$value};
                }
                elsif ($key_name eq 'file_name') {
                    $value = $rec->{'file_name'}{'data'};
                }
                elsif ($key_name eq 'uri') {
                    $value = $rec->{'uri'}{'data'};
                }
                elsif ($key_name eq 'signature') {
                    $value = $rec->{'signature'}{'data'};
                }
                elsif ($key_name eq 'web_app') {
                    $value = $metadata{'payloads'}{$value} if exists $metadata{'payloads'}{$value};
                }
                elsif (($key_name eq 'client_app')) {
                    $value = $metadata{'client_apps'}{$value} if exists $metadata{'client_apps'}{$value};
                }
                elsif ($key_name eq 'app_proto') {
                    $value = $metadata{'app_protos'}{$value} if exists $metadata{'app_protos'}{$value};
                }
                elsif ($key_name eq 'src_app_proto') {
                    $value = $metadata{'app_protos'}{$value} if exists $metadata{'app_protos'}{$value};
                }
                elsif ($key_name eq 'dest_app_proto') {
                    $value = $metadata{'app_protos'}{$value} if exists $metadata{'app_protos'}{$value};
                }
                elsif ($key_name eq 'sec_intel_ip') {
                    if ($value eq '0') {
                        @fields = pushField(\@fields, 'sec_intel_event', 'No');
                    } else {
                        @fields = pushField(\@fields, 'sec_intel_event', 'Yes');
                    }
                    $value = $metadata{'si_src_dests'}{$value} if exists $metadata{'si_src_dests'}{$value};
                }
                elsif ($key_name eq 'url_category') {
                    $value = $metadata{'url_categories'}{$value} if exists $metadata{'url_categories'}{$value};
                }
                elsif ($key_name eq 'url_reputation') {
                    $value = $metadata{'url_reputations'}{$value} if exists $metadata{'url_reputations'}{$value};
                }
                if ($key_name eq 'event_type' && $is_rna) {
                    @fields = pushField(\@fields, 'event_desc', $SFStreamer::RNA_TYPE_NAMES->{$value}->{$rec->{'event_subtype'}}) if exists $SFStreamer::RNA_TYPE_NAMES->{$value}->{$rec->{'event_subtype'}};
                }
                elsif ($key_name eq 'fw_rule' && $rec_type eq 'POLICY') {
                    $key_name = 'corr_rule';
                    $value = $metadata{'corr_rules'}{$value}{'name'} if exists $metadata{'corr_rules'}{$value}{'name'};
                }
                elsif ($key_name eq 'fw_rule' && ($rec_type eq 'RULE' || $rec_type eq 'FIREWALL RULE')) {
                    $key_name = 'id';
                }
                elsif ($key_name eq 'fw_rule' && $rec_type ne 'FIREWALL RULE') {
                    if (exists($rec->{'policyRevision'})) {
                        $value = $metadata{'fw_rules'}{$rec->{'policyRevision'}}{$value} if exists $metadata{'fw_rules'}{$rec->{'policyRevision'}}{$value};
                    }
                    if (exists($rec->{'firewall_policy_uuid'})) {
                        $value = $metadata{'fw_rules'}{$rec->{'firewall_policy_uuid'}}{$value} if exists $metadata{'fw_rules'}{$rec->{'firewall_policy_uuid'}}{$value};
                    }
                }
                elsif ($key_name eq 'fw_rule_action') {
                    $value = $metadata{'fw_rule_actions'}{$value} if exists $metadata{'fw_rule_actions'}{$value};
                }
                elsif ($key_name eq 'fw_rule_reason') {
                    $value = $metadata{'fw_rule_reasons'}{$value} if exists $metadata{'fw_rule_reasons'}{$value};
                }
                elsif ($key_name eq 'policy_uuid') {
                    if ($rec_type eq 'MALWARE EVENT' || $rec_type eq 'FILELOG EVENT' || $rec_type eq 'FILELOG MALWARE EVENT') {
                        $key_name = 'file_policy';
                        $value = $metadata{'policies'}{$value} if exists $metadata{'policies'}{$value};
                    }
                    else {
                        $key_name = 'ids_policy';
                        $value = $metadata{'policies'}{$value} if exists $metadata{'policies'}{$value};
                    }
                }
                elsif ($key_name eq 'impact') {
                    if ($value eq '5') {
                        $value = 0; # Make it the same as a user would see in a Defense Center
                    }
                }
                elsif ($key_name eq 'impact_bits') {
                    @fields = pushField(\@fields, 'impact', getImpactFromBits($value)) if !exists $rec->{'impact'};
                }
                elsif ($key_name eq 'cloud') {
                    $value = $metadata{'clouds'}{$value} if exists $metadata{'clouds'}{$value};
                }
                elsif ($key_name eq 'fw_policy' || $key_name eq 'policyRevision') {
                    $value = $metadata{'policies'}{$value} if exists $metadata{'policies'}{$value};
                }
                elsif ($key_name eq 'iface_ingress' || $key_name eq 'iface_egress') {
                    $value = $metadata{'interfaces'}{$value} if exists $metadata{'interfaces'}{$value};
                }
                elsif ($key_name eq 'sec_zone_ingress' || $key_name eq 'sec_zone_egress') {
                    $value = $metadata{'security_zones'}{$value} if exists $metadata{'security_zones'}{$value};
                }
                elsif ($key_name eq 'direction') {
                    $value = $metadata{'directions'}{$value} if exists $metadata{'directions'}{$value};
                }
                elsif ($key_name eq 'rule_id' && $rec_type eq 'POLICY') {
                    $key_name = 'corr_rule';
                    $value = $metadata{'corr_rules'}{$value}{'name'} if exists $metadata{'corr_rules'}{$value};
                }
                elsif ($key_name eq 'src_os_fingerprint_uuid' && exists $metadata{'os_fingerprints'}{$value}) {
                    @fields = pushField(\@fields, 'src_os_name', $metadata{'os_fingerprints'}{$value}{'os'});
                    @fields = pushField(\@fields, 'src_os_vendor', $metadata{'os_fingerprints'}{$value}{'vendor'});
                    $key_name = 'src_os_ver';
                    $value = $metadata{'os_fingerprints'}{$value}{'ver'};
                }
                elsif ($key_name eq 'dest_os_fingerprint_uuid' && exists $metadata{'os_fingerprints'}{$value}) {
                    @fields = pushField(\@fields, 'dest_os_name', $metadata{'os_fingerprints'}{$value}{'os'});
                    @fields = pushField(\@fields, 'dest_os_vendor', $metadata{'os_fingerprints'}{$value}{'vendor'});
                    $key_name = 'dest_os_ver';
                    $value = $metadata{'os_fingerprints'}{$value}{'ver'};
                }
                elsif ($key_name eq 'src_ip_country' || $key_name eq 'dest_ip_country') {
                    $value = $metadata{'geolocations'}{$value} if exists $metadata{'geolocations'}{$value};
                }
                elsif ($key_name eq 'user' && $rec_type eq 'MALWARE EVENT') {
                    $key_name = 'agent_user';
                    $value = $metadata{'users'}{$value} if exists $metadata{'users'}{$value};
                }
                elsif ($key_name eq 'user' || $key_name eq 'src_user' || $key_name eq 'dest_user') {
                    $value = $metadata{'users'}{$value} if exists $metadata{'users'}{$value};
                }
                elsif ($key_name =~ m/monitor_rule_\d/) {
                    if ($value eq '0') {
                        $value = 'N/A';
                    }
                    if (exists($rec->{'policyRevision'})) {
                        $value = $metadata{'fw_rules'}{$rec->{'policyRevision'}}{$value} if exists $metadata{'fw_rules'}{$rec->{'policyRevision'}}{$value};
                    }
                    if (exists($rec->{'firewall_policy_uuid'})) {
                        $value = $metadata{'fw_rules'}{$rec->{'firewall_policy_uuid'}}{$value} if exists $metadata{'fw_rules'}{$rec->{'firewall_policy_uuid'}}{$value};
                    }
                }

                # Push the field and value into the array
                @fields = pushField(\@fields, $key_name, $value);
            }

            # Push the 'unhandled' field last
            if (exists $rec->{'unhandled'}) {
                @fields = pushField(\@fields, 'unhandled_by_client', 'Yes');
            }

            # Push the 'debug' field if it exists
            if (exists $rec->{'debug'}) {
                @fields = pushField(\@fields, 'debug', $rec->{'debug'});
            }

            # Join all the fields, separating them by comma spaces
            my $output = join(" ", @fields);

            # Remove any null characters left over
            $output =~ s/\0//g;

            # Print and flush the output
            print $logfile_fh $output, "\n";
            autoflush $logfile_fh 1;

            # Increment the number of lines written
            $lines_written++;

            # If we're doing rotation, and we have hit the max, reopen log file
            if ($DO_ROTOTATION && $lines_written == $MAX_LOG_LINES) {
                openReopenLog();
            }
        }
    }
}

# Push key=value pairs into the array
sub pushField
{
    my ($fields, $key, $value) = @_;

    # Validate the key name isn't one to skip
    if ($key ne 'block_type' && $key ne 'block_length' && $key ne 'pad' && $key ne '') {

        # If the value has a space or is empty, we'll wrap it in quotes
        if ($value =~ m/\s/ || $value eq '') {
            push @$fields, "$key=\"$value\"";
        }

        # Otherwise, just push the raw value
        else {
            push @$fields, "$key=$value";
        }
    }
    return @$fields;
}

# Calculate the impact from the impact bits
sub getImpactFromBits
{
    my ($impact_bits) = @_;
    my $impact = 0; # Default to unknown impact

    # Compare bits to the corresponding masks
    if ($impact_bits & 0b11011000) {
        $impact = 1;
    }
    elsif (($impact_bits & 0b00000110) == 0b00000110) {
        $impact = 2;
    }
    elsif ($impact_bits & 0b00000010) {
        $impact = 3;
    }
    elsif ($impact_bits & 0b00000001) {
        $impact = 4;
    }

    # Return the resulting impact score
    return $impact;
}

# Check to see if splunk is running (this is a hack)
sub isSplunkRunning
{
    my $running = 0;
    my $splunk_pid = `pidof splunkd`;
    if ($splunk_pid =~ m/(\d+)/)
    {
        $running = 1;
    }
    return $running;
}

# Daemonize the process
sub daemonize
{
    POSIX::setsid or die "setsid: $!";

    # Fork
    my $pid = fork();

    # Check PID for state
    if ($pid < 0) {
        # Error
        die "couldnt fork: $!\n";
    }
    elsif ($pid) {
        # Parent    
        exit 0;
    }

    # Child

    # Prep the environment
    umask 0;
    foreach (0 .. (POSIX::sysconf (&POSIX::_SC_OPEN_MAX) || 1024))
    { POSIX::close $_ }

    if ($cli_opt->{verbose})
    {
        open(STDIN, "</dev/null");
        open(STDOUT, ">$DEBUG_FILE");
        open(STDERR, ">>$DEBUG_FILE");
    }
    else
    {
        open(STDIN, "</dev/null");
        open(STDOUT, ">/dev/null");
        open(STDERR, ">&STDOUT");
    }
}


